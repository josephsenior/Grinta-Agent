from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

from forge.core.logger import forge_logger as logger
from forge.llm.llm_utils import check_tools

from .types import PromptOptimizerBundle

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam

    from forge.controller.state.state import State
    from forge.events.action import Action
    from forge.llm.llm import LLM
    from .safety import CodeActSafetyManager


QUESTION_PATTERNS = [
    r"\bwhy\b",
    r"\bhow does\b",
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bexplain\b",
    r"\btell me\b",
    r"\b\?\s*$",
    r"\bcan you explain\b",
]

ACTION_PATTERNS = [
    r"\bcreate\b",
    r"\bmake\b",
    r"\bwrite\b",
    r"\bedit\b",
    r"\bmodify\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\bfix\b",
    r"\bimplement\b",
    r"\badd\b",
    r"\bupdate\b",
    r"\bchange\b",
    r"\bbuild\b",
    r"\brun\b",
    r"\binstall\b",
]


class CodeActPlanner:
    """Assembles tools, messages, and LLM request payloads for CodeAct."""

    def __init__(
        self,
        config,
        llm: "LLM",
        safety_manager: "CodeActSafetyManager",
        prompt_optimizer: PromptOptimizerBundle | None,
        tool_optimizer,
    ) -> None:
        self._config = config
        self._llm = llm
        self._safety = safety_manager
        self._prompt_optimizer = prompt_optimizer
        self._tool_optimizer = tool_optimizer

    # ------------------------------------------------------------------ #
    # Tool assembly
    # ------------------------------------------------------------------ #
    def build_toolset(self) -> list["ChatCompletionToolParam"]:
        use_short_desc = self._should_use_short_tool_descriptions()
        tools: list["ChatCompletionToolParam"] = []

        self._add_core_tools(tools, use_short_desc)
        self._add_browsing_tool(tools)
        self._add_specialized_tools(tools, use_short_desc)
        self._add_editor_tools(tools, use_short_desc)

        if self._tool_optimizer:
            tools = self._apply_tool_optimization(tools)

        return tools

    def _should_use_short_tool_descriptions(self) -> bool:
        if not self._llm:
            return False
        model = self._llm.config.model
        return any(substr in model for substr in ("gpt-4", "o3", "o1", "o4"))

    def _add_core_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        from forge.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
        from forge.agenthub.codeact_agent.tools.condensation_request import (
            CondensationRequestTool,
        )
        from forge.agenthub.codeact_agent.tools.finish import FinishTool
        from forge.agenthub.codeact_agent.tools.think import ThinkTool

        if getattr(self._config, "enable_cmd", True):
            tools.append(create_cmd_run_tool(use_short_description=use_short_tool_desc))
        if getattr(self._config, "enable_think", True):
            tools.append(ThinkTool)
        if getattr(self._config, "enable_finish", True):
            tools.append(FinishTool)
        if getattr(self._config, "enable_condensation_request", False):
            tools.append(CondensationRequestTool)

    def _add_browsing_tool(self, tools: list) -> None:
        if not getattr(self._config, "enable_browsing", False):
            return
        import sys

        platform_name = getattr(sys, "platform", "")
        if platform_name == "win32":
            logger.warning("Windows runtime does not support browsing yet")
            return
        from forge.agenthub.codeact_agent.tools.browser import BrowserTool

        tools.append(BrowserTool)

    def _add_editor_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        from forge.agenthub.codeact_agent.tools.llm_based_edit import (
            LLMBasedFileEditTool,
        )
        from forge.agenthub.codeact_agent.tools.str_replace_editor import (
            create_str_replace_editor_tool,
        )

        if getattr(self._config, "enable_ultimate_editor", False):
            from forge.agenthub.codeact_agent.tools import create_ultimate_editor_tool

            tools.append(
                create_ultimate_editor_tool(use_short_description=use_short_tool_desc)
            )
        elif getattr(self._config, "enable_llm_editor", False):
            tools.append(LLMBasedFileEditTool)
        elif getattr(self._config, "enable_editor", True):
            tools.append(
                create_str_replace_editor_tool(
                    use_short_description=use_short_tool_desc
                )
            )

    def _add_specialized_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        from forge.agenthub.codeact_agent.tools.ipython import IPythonTool
        from forge.agenthub.codeact_agent.tools.task_tracker import (
            create_task_tracker_tool,
        )
        from forge.agenthub.codeact_agent.tools.database import get_database_tools

        if getattr(self._config, "enable_jupyter", False):
            tools.append(IPythonTool)
            tools.extend(get_database_tools())

        # Task tracker is always available (enable_plan_mode defaults to True)
        # Agent decides when to use it based on task complexity
        if getattr(self._config, "enable_plan_mode", True):
            tools.append(create_task_tracker_tool(use_short_tool_desc))

    # ------------------------------------------------------------------ #
    # Prompt optimization hooks
    # ------------------------------------------------------------------ #
    def apply_prompt_optimization(
        self,
        messages: list,
        state: "State",
    ) -> list:
        bundle = self._prompt_optimizer
        if not bundle or not messages:
            return messages

        try:
            from forge.prompt_optimization.models import PromptCategory

            system_message = messages[0] if messages[0].get("role") == "system" else None
            if not system_message:
                return messages

            optimizer = bundle["optimizer"]
            variant = optimizer.select_variant("codeact_system", PromptCategory.CODEACT_SYSTEM)
            if not variant:
                return messages

            optimized = list(messages)
            optimized[0] = {**system_message, "content": variant.content}
            setattr(state, "_prompt_variant_id", variant.id)
            return optimized
        except Exception as exc:  # pragma: no cover - optimization optional
            logger.warning("Prompt optimization failed: %s", exc)
            return messages

    def record_prompt_execution(
        self,
        state: "State",
        success: bool,
        execution_time: float,
        token_cost: float = 0.0,
        error_message: Optional[str] = None,
    ) -> None:
        bundle = self._prompt_optimizer
        if not bundle:
            return

        try:
            from forge.prompt_optimization.models import PromptCategory

            variant_id = getattr(state, "_prompt_variant_id", None)
            if not variant_id:
                return

            optimizer = bundle["optimizer"]
            optimizer.record_execution(
                variant_id=variant_id,
                prompt_id="codeact_system",
                category=PromptCategory.CODEACT_SYSTEM,
                success=success,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=error_message,
                metadata={
                    "agent_name": getattr(state, "agent_name", "CodeActAgent"),
                    "task": getattr(state, "current_task", "unknown"),
                },
            )
            bundle["storage"].auto_save()
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("Failed to track prompt performance: %s", exc)

    # ------------------------------------------------------------------ #
    # Tool optimization hooks
    # ------------------------------------------------------------------ #
    def _apply_tool_optimization(
        self,
        tools: list["ChatCompletionToolParam"],
    ) -> list["ChatCompletionToolParam"]:
        if not self._tool_optimizer:
            return tools

        optimized: list["ChatCompletionToolParam"] = []
        for tool in tools:
            try:
                tool_dict = dict(tool)
                function_info = tool_dict.get("function") if isinstance(tool_dict, dict) else None
                tool_name = (
                    function_info.get("name")
                    if isinstance(function_info, dict)
                    else None
                )
                if not tool_name:
                    optimized.append(tool)
                    continue
                optimized.append(self._tool_optimizer.optimize_tool(tool, tool_name))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to optimize tool %s: %s", tool, exc)
                optimized.append(tool)
        return optimized

    def track_tool_usage(self, actions: Iterable["Action"]) -> None:
        if not self._tool_optimizer:
            return

        for action in actions:
            tool_name = self._map_action_to_tool(action)
            if not tool_name:
                continue
            self._ensure_tool_variant_exists(tool_name, action)
            self._tool_optimizer.track_tool_execution(
                tool_name=tool_name,
                success=True,
                execution_time=0.0,
                token_cost=0.0,
                error_message=None,
                metadata={
                    "action_type": getattr(action, "action", None),
                    "action_id": getattr(action, "id", None),
                },
            )

    def _map_action_to_tool(self, action: "Action") -> Optional[str]:
        mapping = {
            "think": "think",
            "run": "execute_bash",
            "run_powershell": "execute_powershell",
            "finish": "finish",
            "browse_interactive": "browse_interactive",
            "str_replace_editor": "str_replace_editor",
            "llm_based_edit": "llm_based_edit",
            "ipython_run_cell": "ipython_run_cell",
            "condensation_request": "condensation_request",
            "task_tracking": "task_tracker",
        }
        action_attr = getattr(action, "action", None)
        return mapping.get(action_attr) if isinstance(action_attr, str) else None

    def _ensure_tool_variant_exists(
        self,
        tool_name: str,
        action: "Action",
    ) -> None:
        bundle = self._prompt_optimizer
        if not bundle or not self._tool_optimizer:
            return

        try:
            raw_prompt_ids = getattr(self._tool_optimizer, "tool_prompt_ids", {})
            prompt_id = raw_prompt_ids.get(tool_name)
            if not prompt_id:
                return

            registry = bundle["registry"]
            variants = registry.get_variants_for_prompt(prompt_id)
            if variants:
                return

            from forge.prompt_optimization.tool_descriptions import (
                get_optimized_description,
            )

            optimized_desc = get_optimized_description(tool_name)
            if not optimized_desc:
                return

            description = optimized_desc.get("description", "")
            parameters = optimized_desc.get("parameters", {})

            self._tool_optimizer.create_tool_variants(
                tool_name=tool_name,
                original_description=description,
                original_parameters=parameters,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to ensure tool variant exists for %s: %s",
                tool_name,
                exc,
            )

    # ------------------------------------------------------------------ #
    # LLM parameter assembly
    # ------------------------------------------------------------------ #
    def build_llm_params(
        self,
        messages: list,
        state: "State",
        tools: list["ChatCompletionToolParam"],
        ace_context: Optional[str],
    ) -> dict:
        messages = self.apply_prompt_optimization(messages, state)
        if ace_context and messages and messages[0].get("role") == "system":
            messages = list(messages)
            messages[0] = {
                **messages[0],
                "content": f"{messages[0]['content']}\n\n{ace_context}",
            }

        tool_choice = self._determine_tool_choice(messages, state)

        params = {
            "messages": messages,
            "tools": check_tools(tools, self._llm.config),
            "stream": True,
        }

        if tool_choice and self._llm_supports_tool_choice():
            params["tool_choice"] = tool_choice

        params["extra_body"] = {
            "metadata": state.to_llm_metadata(
                model_name=self._llm.config.model,
                agent_name=getattr(state, "agent_name", "CodeActAgent"),
            )
        }
        return params

    def _determine_tool_choice(self, messages: list, state: "State") -> Optional[str]:
        last_user_msg = self._get_last_user_message(messages)
        if not last_user_msg:
            return "auto"

        if self._is_question(last_user_msg):
            return "auto"
        if self._is_action(last_user_msg):
            return "required"

        return self._safety.should_enforce_tools(last_user_msg, state, default="required")

    def _llm_supports_tool_choice(self) -> bool:
        model_lower = self._llm.config.model.lower()
        supported = [
            "gpt-4",
            "gpt-3.5",
            "claude-3",
            "claude-sonnet",
            "claude-opus",
            "claude-haiku",
            "gemini",
            "mistral",
            "command",
            "deepseek",
        ]
        return any(substr in model_lower for substr in supported)

    def _get_last_user_message(self, messages: list) -> Optional[str]:
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                return message.get("content", "")
        return None

    def _is_question(self, message: str) -> bool:
        return any(re.search(pattern, message.lower()) for pattern in QUESTION_PATTERNS)

    def _is_action(self, message: str) -> bool:
        return any(re.search(pattern, message.lower()) for pattern in ACTION_PATTERNS)

