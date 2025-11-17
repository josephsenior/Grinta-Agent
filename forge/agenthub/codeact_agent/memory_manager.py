from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Optional, Tuple

from forge.core.logger import forge_logger as logger
from forge.core.message import Message, TextContent
from forge.events.action import MessageAction
from forge.memory.condenser import Condenser
from forge.memory.condenser.condenser import Condensation
from forge.memory.conversation_memory import ConversationMemory
from forge.memory.view import View

if TYPE_CHECKING:
    from forge.controller.state.state import State
    from forge.events.action import Action
    from forge.events.event import Event
    from forge.llm.llm_registry import LLMRegistry
    from forge.memory.enhanced_context_manager import EnhancedContextManager
    from forge.metasop.ace.ace_framework import ACEFramework
    from forge.utils.prompt import PromptManager
    from forge.core.config import AgentConfig


@dataclass
class CondensedHistory:
    events: list["Event"]
    pending_action: "Action | None"


class CodeActMemoryManager:
    """Owns conversation memory, condensation, context, and ACE integrations."""

    def __init__(
        self,
        config: "AgentConfig",
        llm_registry: "LLMRegistry",
    ) -> None:
        self._config = config
        self._llm_registry = llm_registry
        self.enhanced_context_manager: "EnhancedContextManager | None" = None
        self.conversation_memory: ConversationMemory | None = None
        self.condenser: Condenser | None = None
        self.ace_framework: "ACEFramework | None" = None

    # --------------------------------------------------------------------- #
    # Initialization
    # --------------------------------------------------------------------- #
    def initialize(self, prompt_manager: "PromptManager") -> None:
        """Initialize memory subsystems that depend on the prompt manager."""
        self.conversation_memory = ConversationMemory(self._config, prompt_manager)
        self._initialize_enhanced_context_manager()
        self._initialize_condenser()
        self._initialize_ace_framework()

    def _initialize_enhanced_context_manager(self) -> None:
        if not getattr(self._config, "enable_enhanced_context", False):
            self.enhanced_context_manager = None
            return

        try:
            from forge.memory.enhanced_context_manager import (
                EnhancedContextManager,
            )

            manager = EnhancedContextManager(
                short_term_window=getattr(self._config, "context_short_term_window", 5),
                working_memory_size=getattr(self._config, "context_working_size", 50),
                long_term_max_size=getattr(self._config, "context_long_term_size", 200),
                contradiction_threshold=getattr(
                    self._config, "context_contradiction_threshold", 0.7
                ),
            )

            persistence_path = getattr(
                self._config, "context_persistence_path", None
            )
            if persistence_path:
                try:
                    manager.load_from_file(persistence_path)
                    logger.info("Loaded enhanced context state from %s", persistence_path)
                except Exception as exc:  # pragma: no cover - log and continue
                    logger.debug("No existing context state to load: %s", exc)

            logger.info("Enhanced Context Manager initialized")
            self.enhanced_context_manager = manager
        except ImportError as exc:  # pragma: no cover - dependency guard
            logger.error("Failed to import Enhanced Context Manager: %s", exc)
            self.enhanced_context_manager = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize Enhanced Context Manager: %s", exc)
            self.enhanced_context_manager = None

    def _initialize_condenser(self) -> None:
        condenser_config = (
            getattr(self._config, "condenser_config", None)
            or getattr(self._config, "condenser", None)
        )
        if condenser_config is None:
            self.condenser = None
            return

        try:
            self.condenser = Condenser.from_config(
                condenser_config,
                self._llm_registry,
            )
            logger.debug("Using condenser: %s", type(self.condenser))
        except Exception as exc:  # pragma: no cover - condensation optional
            logger.warning("Failed to initialize condenser: %s", exc)
            self.condenser = None

    def _initialize_ace_framework(self) -> None:
        """Initialize ACE framework with smart enablement based on complexity."""
        enable_ace = getattr(self._config, "enable_ace", True)  # Default to True
        if not enable_ace:
            self.ace_framework = None
            return
        
        # Check if ACE should be auto-enabled based on complexity threshold
        # This will be checked later when we have the user message
        # For now, initialize if enabled in config

        try:
            from forge.metasop.ace import ACEConfig, ACEFramework, ContextPlaybook

            ace_config = ACEConfig(
                enable_ace=getattr(self._config, "enable_ace", True),  # Default to True
                max_bullets=getattr(self._config, "ace_max_bullets", 1000),
                multi_epoch=getattr(self._config, "ace_multi_epoch", True),
                num_epochs=getattr(self._config, "ace_num_epochs", 5),
                reflector_max_iterations=getattr(
                    self._config, "ace_reflector_max_iterations", 5
                ),
                enable_online_adaptation=getattr(
                    self._config, "ace_enable_online_adaptation", True
                ),
                playbook_persistence_path=getattr(
                    self._config, "ace_playbook_path", None
                ),
                min_helpfulness_threshold=getattr(
                    self._config, "ace_min_helpfulness_threshold", 0.0
                ),
                max_playbook_content_length=getattr(
                    self._config, "ace_max_playbook_content_length", 50
                ),
                enable_grow_and_refine=getattr(
                    self._config, "ace_enable_grow_and_refine", True
                ),
                cleanup_interval_days=getattr(
                    self._config, "ace_cleanup_interval_days", 30
                ),
                redundancy_threshold=getattr(
                    self._config, "ace_redundancy_threshold", 0.8
                ),
            )

            context_playbook = ContextPlaybook(
                max_bullets=ace_config.max_bullets,
                enable_grow_and_refine=ace_config.enable_grow_and_refine,
            )

            if ace_config.playbook_persistence_path:
                import json
                from pathlib import Path

                playbook_path = Path(ace_config.playbook_persistence_path).expanduser()
                if playbook_path.is_file():
                    try:
                        data = json.loads(playbook_path.read_text(encoding="utf-8"))
                        context_playbook.import_playbook(data)
                    except Exception as exc:  # pragma: no cover - best effort
                        logger.warning(
                            "Failed to load existing ACE playbook %s: %s",
                            playbook_path,
                            exc,
                        )

            self.ace_framework = ACEFramework(
                llm=self._llm_registry.get_active_llm(),
                context_playbook=context_playbook,
                config=ace_config,
            )
            logger.info("ACE framework initialized")
        except ImportError as exc:  # pragma: no cover - optional dependency
            logger.error("Failed to import ACE framework: %s", exc)
            self.ace_framework = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize ACE framework: %s", exc)
            self.ace_framework = None

    # --------------------------------------------------------------------- #
    # Context persistence / updates
    # --------------------------------------------------------------------- #
    def save_context_state(self) -> None:
        if not self.enhanced_context_manager:
            return

        persistence_path = getattr(self._config, "context_persistence_path", None)
        if not persistence_path:
            return

        try:
            self.enhanced_context_manager.save_to_file(persistence_path)
            logger.debug("Saved enhanced context state to %s", persistence_path)
        except Exception as exc:  # pragma: no cover - persistence best effort
            logger.warning("Failed to save context state: %s", exc)

    def update_context(self, state: "State") -> None:
        if not self.enhanced_context_manager:
            return

        try:
            events = state.history[-5:] if len(state.history) >= 5 else state.history
            for event in events:
                payload = {
                    "event_type": type(event).__name__,
                    "timestamp": getattr(event, "timestamp", None),
                    "content": str(event)[:500],
                }
                if hasattr(event, "action") and "file" in str(event.action).lower():
                    payload["has_decision"] = True
                self.enhanced_context_manager.add_to_short_term(payload)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to update context memory: %s", exc)

    # --------------------------------------------------------------------- #
    # History utilities
    # --------------------------------------------------------------------- #
    def condense_history(self, state: "State") -> CondensedHistory:
        history = getattr(state, "history", [])
        if not self.condenser:
            return CondensedHistory(list(history), None)

        condensation_result = self.condenser.condensed_history(state)
        if isinstance(condensation_result, View):
            return CondensedHistory(condensation_result.events, None)
        return CondensedHistory([], condensation_result.action)

    def get_initial_user_message(self, events: Iterable["Event"]) -> MessageAction:
        from forge.events.event import EventSource
        from forge.core.schemas import ActionType

        for event in events:
            try:
                source = getattr(event, "source", None)
                if source != EventSource.USER:
                    continue

                if isinstance(event, MessageAction):
                    return event

                if getattr(event, "action", None) == ActionType.MESSAGE and hasattr(
                    event, "content"
                ):
                    cloned = MessageAction(
                        content=str(getattr(event, "content", "")),
                        file_urls=getattr(event, "file_urls", None),
                        image_urls=getattr(event, "image_urls", None),
                        wait_for_response=bool(
                            getattr(event, "wait_for_response", False)
                        ),
                    )
                    cloned.source = source
                    if hasattr(event, "id"):
                        cloned.id = getattr(event, "id")
                    if hasattr(event, "timestamp"):
                        cloned.timestamp = getattr(event, "timestamp")
                    return cloned
            except Exception:
                continue
        raise ValueError("Initial user message not found")

    def build_messages(
        self,
        condensed_history: Iterable["Event"],
        initial_user_message: MessageAction,
        llm_config,
    ) -> list[Message]:
        if not self.conversation_memory:
            raise RuntimeError("Conversation memory is not initialized")

        events = list(condensed_history)
        messages = self.conversation_memory.process_events(
            condensed_history=events,
            initial_user_action=initial_user_message,
            max_message_chars=getattr(llm_config, "max_message_chars", None),
            vision_is_active=getattr(llm_config, "vision_is_active", False),
        )

        if not messages:
            return messages

        first_message = messages[0]
        for item in first_message.content:
            if isinstance(item, TextContent):
                item.cache_prompt = True
                break

        for message in reversed(messages):
            if message.role == "user":
                for item in message.content:
                    if isinstance(item, TextContent):
                        item.cache_prompt = True
                        break
                break

        return messages

    # --------------------------------------------------------------------- #
    # ACE context helpers
    # --------------------------------------------------------------------- #
    def get_ace_playbook_context(self, state: "State") -> Optional[str]:
        if not self.ace_framework:
            return None

        try:
            playbook_content = self.ace_framework.context_playbook.get_playbook_content(
                max_bullets=getattr(self._config, "ace_max_playbook_content_length", 50)
            )
            if not playbook_content or "No relevant strategies found" in playbook_content:
                return None

            return (
                "ACE PLAYBOOK:\n"
                f"{playbook_content}\n\n"
                "Instructions:\n"
                "1. Use relevant strategies from the playbook when applicable\n"
                "2. Apply domain-specific insights and patterns\n"
                "3. Follow verification checklists from the playbook\n"
                "4. Avoid common mistakes listed in the playbook\n"
                "5. Show your reasoning step-by-step\n"
                "6. Leverage tools and utilities mentioned in the playbook\n"
            )
        except Exception as exc:  # pragma: no cover - ACE optional
            logger.warning("Failed to get ACE playbook context: %s", exc)
            return None

