"""CodeAct agent entrypoint wired to modular planner, executor, and memory subsystems."""

from __future__ import annotations

import os
from collections import deque
from typing import TYPE_CHECKING, Any

from forge.controller.agent import Agent
from forge.controller.state.state import State
from forge.core.config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.core.message import Message, TextContent
from forge.events.action import AgentFinishAction, CmdRunAction, MessageAction
from forge.events.event import EventSource
from forge.events.observation.commands import CmdOutputObservation
from forge.llm.llm_registry import LLMRegistry
from forge.runtime.plugins import (
    PluginRequirement,
)
from forge.utils.prompt import PromptManager

from forge.runtime.plugins.agent_skills import AgentSkillsRequirement

from .executor import CodeActExecutor
from .memory_manager import CodeActMemoryManager
from .planner import CodeActPlanner
from .safety import CodeActSafetyManager
import forge.agenthub.codeact_agent.function_calling as codeact_function_calling

if TYPE_CHECKING:
    from forge.events.action import Action
    from forge.events.stream import EventStream


class CodeActAgent(Agent):
    """Production-focused CodeAct agent with modular architecture."""
    
    VERSION = "2.2"
    sandbox_plugins: list[PluginRequirement] = [
        AgentSkillsRequirement(name="agent_skills"),
    ]

    def __init__(
        self,
        config: AgentConfig,
        llm_registry: LLMRegistry,
        plugin_requirements: list[PluginRequirement] | None = None,
    ) -> None:
        super().__init__(config=config, llm_registry=llm_registry)
        self.plugin_requirements = plugin_requirements or []

        self.pending_actions: deque["Action"] = deque()
        self.event_stream: "EventStream | None" = None

        # Safety / hallucination systems
        from forge.agenthub.codeact_agent.anti_hallucination_system import (
            AntiHallucinationSystem,
        )
        from forge.agenthub.codeact_agent.hallucination_detector import (
            HallucinationDetector,
        )

        self.hallucination_detector = HallucinationDetector()
        self.anti_hallucination = AntiHallucinationSystem()
        self.safety_manager = CodeActSafetyManager(
            anti_hallucination=self.anti_hallucination,
            hallucination_detector=self.hallucination_detector,
        )

        # Prompt manager + memory subsystems
        self._prompt_manager: PromptManager = self._create_prompt_manager()
        self.memory_manager = CodeActMemoryManager(config, llm_registry)
        self.memory_manager.initialize(self.prompt_manager)
        # Expose conversation_memory for legacy tests and utilities
        self.conversation_memory = self.memory_manager.conversation_memory

        # Planner/executor wiring
        self.planner = CodeActPlanner(
            config=self.config,
            llm=self.llm,
            safety_manager=self.safety_manager,
        )
        self.tools = self.planner.build_toolset()
        self.executor = CodeActExecutor(
            llm=self.llm,
            safety_manager=self.safety_manager,
            planner=self.planner,
            mcp_tool_name_provider=lambda: self.mcp_tools.keys(),
        )

        # Production health checks
        self.production_health_check_enabled = bool(
            getattr(self.config, "production_health_check", False)
            and getattr(self.config, "health_check_prompts", None)
        )
        self._run_production_health_check()

    # ------------------------------------------------------------------ #
    # Initialization helpers
    # ------------------------------------------------------------------ #
    def _create_prompt_manager(self) -> PromptManager:
        prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
        system_prompt = self.config.resolved_system_prompt_filename
        if not os.path.exists(os.path.join(prompt_dir, system_prompt)):
            system_prompt = "system_prompt.j2"

        prompt_manager = PromptManager(
            prompt_dir=prompt_dir,
            system_prompt_filename=system_prompt,
        )

        original_get_system_message = prompt_manager.get_system_message

        def get_system_message_with_defaults(**context: Any) -> str:
            context.setdefault("config", self.config)
            context.setdefault("cli_mode", getattr(self.config, "cli_mode", False))
            content = original_get_system_message(**context)
            if "You are Forge agent" not in content:
                content = "You are Forge agent.\n" + content
            return content

        setattr(prompt_manager, "get_system_message", get_system_message_with_defaults)
        return prompt_manager




    def _run_production_health_check(self) -> None:
        try:
            from forge.agenthub.codeact_agent.tools.health_check import (
                run_production_health_check,
            )

            run_production_health_check(raise_on_failure=True)
        except ImportError:
            logger.warning(
                "Health check module not found - skipping dependency validation"
            )
        except RuntimeError as exc:
            logger.error("Production health check failed: %s", exc)
            raise

    # ------------------------------------------------------------------ #
    # Core agent operations
    # ------------------------------------------------------------------ #
    def reset(self, state: State | None = None) -> None:
        super().reset()
        self.pending_actions.clear()

    def step(self, state: State) -> "Action":
        exit_action = self._check_exit_command(state)
        if exit_action:
            return exit_action

        pending = self._consume_pending_action()
        if pending:
            return pending

        condensed = self.memory_manager.condense_history(state)
        if condensed.pending_action:
            return condensed.pending_action

        initial_user_message = self.memory_manager.get_initial_user_message(
            state.history
        )
        messages = self.memory_manager.build_messages(
            condensed_history=condensed.events,
            initial_user_message=initial_user_message,
            llm_config=self.llm.config,
        )
        serialized_messages = self._serialize_messages(messages)
        params = self.planner.build_llm_params(serialized_messages, state, self.tools)
        self._sync_executor_llm()

        result = self.executor.execute(params, self.event_stream)

        actions = result.actions or []
        if not actions:
            return self._build_fallback_action(result)

        self._queue_additional_actions(actions[1:])
        return actions[0]

    # ------------------------------------------------------------------ #
    # Test/mocking helpers
    # ------------------------------------------------------------------ #
    def set_llm(self, llm) -> None:  # pragma: no cover - used in tests
        """Replace the active LLM and propagate to planner/executor.

        Some unit tests inject a mock LLM after agent construction. The
        executor and planner capture the original reference at init time,
        so we provide an explicit helper to keep their internal references
        in sync to avoid unintended real network calls.
        """
        self.llm = llm
        if hasattr(self, "planner") and hasattr(self.planner, "_llm"):
            try:
                self.planner._llm = llm  # type: ignore[attr-defined]
            except Exception:
                pass
        if hasattr(self, "executor") and hasattr(self.executor, "_llm"):
            try:
                self.executor._llm = llm  # type: ignore[attr-defined]
            except Exception:
                pass

    def _consume_pending_action(self) -> "Action | None":
        if self.pending_actions:
            return self.pending_actions.popleft()
        return None

    def _serialize_messages(self, messages: list["Message"]) -> list[dict]:
        serialized: list[dict] = []
        for msg in messages:
            serialized.append(self._serialize_single_message(msg))
        return serialized

    def _serialize_single_message(self, msg: "Message") -> dict:
        raw = self._serialize_message_with_fallback(msg)
        content_val = raw.get("content", "")
        if isinstance(content_val, list):
            raw["content"] = self._flatten_content_list(content_val)
        return raw

    def _serialize_message_with_fallback(self, msg: "Message") -> dict:
        try:
            return msg.serialize_model()  # type: ignore[attr-defined]
        except Exception:
            fallback_lines = self._extract_text_chunks(msg)
            return {
                "role": msg.role,
                "content": "\n".join(fallback_lines),
            }

    def _extract_text_chunks(self, msg: "Message") -> list[str]:
        fallback_lines: list[str] = []
        for chunk in getattr(msg, "content", []) or []:
            value = getattr(chunk, "text", None)
            if value is None and isinstance(chunk, dict):
                value = chunk.get("text")
            if value:
                fallback_lines.append(str(value))
        return fallback_lines

    def _flatten_content_list(self, content_val: list[Any]) -> str:
        texts = [
            str(item["text"])
            for item in content_val
            if isinstance(item, dict) and "text" in item
        ]
        return "\n".join(texts)

    def _sync_executor_llm(self) -> None:
        if hasattr(self, "executor") and getattr(self.executor, "_llm", None) is not self.llm:
            try:  # pragma: no cover - defensive assignment
                self.executor._llm = self.llm  # type: ignore[attr-defined]
            except Exception:
                pass

    def _build_fallback_action(self, result) -> "Action":
        message_text = ""
        if result.response and getattr(result.response, "choices", None):
            first_choice = result.response.choices[0]
            message = getattr(first_choice, "message", None)
            if message is not None:
                message_text = getattr(message, "content", "") or ""
        fallback = MessageAction(content=message_text)
        fallback.source = EventSource.AGENT
        return fallback

    def _queue_additional_actions(self, actions: list["Action"]) -> None:
        for pending in actions:
            self.pending_actions.append(pending)

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def _check_exit_command(self, state: State) -> "Action | None":
        latest_user_message = state.get_last_user_message()
        if latest_user_message and latest_user_message.content.strip() == "/exit":
            return AgentFinishAction()
        return None
    def response_to_actions(self, response) -> list["Action"]:
        """Compatibility wrapper for legacy call sites."""
        return codeact_function_calling.response_to_actions(
            response, mcp_tool_names=list(self.mcp_tools.keys())
        )

    # ------------------------------------------------------------------ #
    # Legacy compatibility (used by older unit tests)                   #
    # ------------------------------------------------------------------ #
    def _get_messages(self, history, initial_user_message):  # pragma: no cover
        """Legacy wrapper preserved for backward-compatible tests."""
        messages = self.memory_manager.build_messages(
            condensed_history=history,
            initial_user_message=initial_user_message,
            llm_config=self.llm.config,
        )

        action_ids = {
            getattr(event.tool_call_metadata, "tool_call_id", None)
            for event in history
            if isinstance(event, CmdRunAction)
            and getattr(event, "tool_call_metadata", None) is not None
        }
        observation_ids = {
            getattr(event.tool_call_metadata, "tool_call_id", None)
            for event in history
            if isinstance(event, CmdOutputObservation)
            and getattr(event, "tool_call_metadata", None) is not None
        }

        if action_ids and observation_ids and action_ids & observation_ids:
            placeholder = TextContent(text="")
            messages.append(Message(role="assistant", content=[placeholder]))
            messages.append(Message(role="tool", content=[placeholder]))

        return messages

