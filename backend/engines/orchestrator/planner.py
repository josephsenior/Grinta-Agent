from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

from backend.core.logger import forge_logger as logger
from backend.models.llm_utils import check_tools

ChatCompletionToolParam = Any

if TYPE_CHECKING:
    from backend.controller.state.state import State
    from backend.events.action import Action
    from backend.models.llm import LLM
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
    ) -> None:
        self._config = config
        self._llm = llm
        self._safety = safety_manager

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

        return tools

    def _should_use_short_tool_descriptions(self) -> bool:
        if not self._llm:
            return False
        model = self._llm.config.model
        return any(substr in model for substr in ("gpt-4", "o3", "o1", "o4"))

    def _add_core_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        from backend.engines.orchestrator.tools.bash import create_cmd_run_tool
        from backend.engines.orchestrator.tools.condensation_request import (
            CondensationRequestTool,
        )
        from backend.engines.orchestrator.tools.finish import FinishTool
        from backend.engines.orchestrator.tools.think import ThinkTool

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
        from backend.engines.orchestrator.tools.browser import BrowserTool

        tools.append(BrowserTool)

    def _add_editor_tools(self, tools: list, use_short_tool_desc: bool) -> None:
        from backend.engines.orchestrator.tools.llm_based_edit import (
            LLMBasedFileEditTool,
        )
        from backend.engines.orchestrator.tools.str_replace_editor import (
            create_str_replace_editor_tool,
        )

        if getattr(self._config, "enable_ultimate_editor", False):
            from backend.engines.orchestrator.tools import create_ultimate_editor_tool

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
        pass


    def build_llm_params(
        self,
        messages: list,
        state: "State",
        tools: list["ChatCompletionToolParam"],
    ) -> dict:
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
                agent_name=getattr(state, "agent_name", "Orchestrator"),
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

