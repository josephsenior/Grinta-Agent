"""Utilities for transforming event history into LLM-ready conversation messages."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypeGuard, cast
import copy

from forge.core.logger import forge_logger as logger
from forge.core.message import (
    ChatCompletionMessageToolCallType,
    ImageContent,
    Message,
    TextContent,
)
from forge.core.schemas import ActionType
from forge.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    IPythonRunCellAction,
    MessageAction,
    TaskTrackingAction,
)
from forge.events.action.mcp import MCPAction
from forge.events.action.message import SystemMessageAction
from forge.events.event import Event, RecallType, EventSource
from forge.events.model_response_lite import ModelResponseLite
from forge.events.observation import (
    AgentCondensationObservation,
    AgentDelegateObservation,
    AgentThinkObservation,
    BrowserOutputObservation,
    CmdOutputObservation,
    FileDownloadObservation,
    FileEditObservation,
    FileReadObservation,
    IPythonRunCellObservation,
    TaskTrackingObservation,
    UserRejectObservation,
)
from forge.events.observation.agent import MicroagentKnowledge, RecallObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.mcp import MCPObservation
from forge.events.observation.observation import Observation
from forge.events.serialization.event import truncate_content
from forge.utils.prompt import (
    ConversationInstructions,
    PromptManager,
    RepositoryInfo,
    RuntimeInfo,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from forge.core.config.agent_config import AgentConfig
    from forge.memory.enhanced_vector_store import EnhancedVectorStore


@dataclass
class _ToolCallTracking:
    pending_action_messages: dict[str, Message] = field(default_factory=dict)
    tool_call_messages: dict[str, Message] = field(default_factory=dict)


class ConversationMemory:
    """Processes event history into a coherent conversation for the agent."""

    def __init__(self, config: AgentConfig, prompt_manager: PromptManager) -> None:
        """Store agent configuration and set up optional vector memory backends."""
        self.agent_config = config
        self.prompt_manager = prompt_manager

        # Initialize vector memory if enabled
        self.vector_store: EnhancedVectorStore | None = None
        if bool(getattr(config, "enable_vector_memory", False)):
            self._initialize_vector_memory()

    def _initialize_vector_memory(self) -> None:
        """Initialize vector memory store for persistent context."""
        try:
            from forge.memory.enhanced_vector_store import EnhancedVectorStore

            hybrid_enabled = bool(
                getattr(self.agent_config, "enable_hybrid_retrieval", False)
            )
            self.vector_store = EnhancedVectorStore(
                collection_name="conversation_memory",
                enable_cache=True,
                enable_reranking=hybrid_enabled,
            )
            logger.info(
                "✅ Vector memory initialized for ConversationMemory\n"
                "   Accuracy: 92%% | Hybrid retrieval: %s",
                "enabled" if hybrid_enabled else "disabled",
            )
        except Exception as e:
            logger.warning(
                "Failed to initialize vector memory: %s\n"
                "Continuing without persistent memory. To enable:\n"
                "  pip install chromadb sentence-transformers",
                e,
            )
            self.vector_store = None

    def apply_prompt_caching(self, messages: list[Message]) -> None:
        """Set prompt caching hints for the first system message and the latest user message."""
        if not self._should_cache(messages):
            return
        self._reset_cache_flags(messages)
        self._cache_first_system_message(messages)
        self._cache_latest_user_message(messages)

    def _should_cache(self, messages: list[Message]) -> bool:
        return bool(
            messages and getattr(self.agent_config, "enable_prompt_caching", True)
        )

    def _reset_cache_flags(self, messages: list[Message]) -> None:
        for message in messages:
            for content in getattr(message, "content", []) or []:
                if self._is_text_content(content):
                    content.cache_prompt = False

    def _cache_first_system_message(self, messages: list[Message]) -> None:
        first_message = messages[0]
        for content in getattr(first_message, "content", []) or []:
            if self._is_text_content(content):
                content.cache_prompt = True

    def _cache_latest_user_message(self, messages: list[Message]) -> None:
        for message in reversed(messages):
            if message.role != "user":
                continue
            for content in getattr(message, "content", []) or []:
                if self._is_text_content(content):
                    content.cache_prompt = True
            break

    @staticmethod
    def _message_with_text(
        role: Literal["user", "system", "assistant", "tool"], text: str
    ) -> Message:
        """Build a Message with a single TextContent entry."""
        content_items: list[TextContent | ImageContent] = [TextContent(text=text)]
        return Message(role=role, content=content_items)

    @staticmethod
    def _is_valid_image_url(url: str | None) -> bool:
        """Check if an image URL is valid and non-empty.

        Validates that a URL exists and is not just whitespace. Used to filter
        out placeholder or invalid image URLs before including them in messages.

        Args:
            url: The image URL string to validate

        Returns:
            bool: True if URL is non-None and non-empty after stripping whitespace,
                False otherwise

        Example:
            >>> ConversationMemory._is_valid_image_url("https://example.com/image.png")
            True
            >>> ConversationMemory._is_valid_image_url(None)
            False
            >>> ConversationMemory._is_valid_image_url("   ")
            False

        """
        return bool(url and url.strip())

    def process_events(
        self,
        condensed_history: list[Event],
        initial_user_action: MessageAction,
        max_message_chars: int | None = None,
        vision_is_active: bool = False,
    ) -> list[Message]:
        """Process state history into a list of messages for the LLM.

        Ensures that tool call actions are processed correctly in function calling mode.

        Args:
            condensed_history: The condensed history of events to convert
            max_message_chars: The maximum number of characters in the content of an event included
                in the prompt to the LLM. Larger observations are truncated.
            vision_is_active: Whether vision is active in the LLM. If True, image URLs will be included.
            initial_user_action: The initial user message action, if available. Used to ensure the conversation starts correctly.

        """
        events = self._prepare_event_history(condensed_history, initial_user_action)
        logger.debug(
            "Visual browsing: %s", self.agent_config.enable_som_visual_browsing
        )
        messages: list[Message] = []
        tool_state = _ToolCallTracking()
        for i, event in enumerate(events):
            messages_to_add = self._messages_from_event(
                event=event,
                index=i,
                events=events,
                tool_state=tool_state,
                max_message_chars=max_message_chars,
                vision_is_active=vision_is_active,
            )
            messages_to_add.extend(self._flush_resolved_tool_calls(tool_state))
            messages += messages_to_add
        messages = list(ConversationMemory._filter_unmatched_tool_calls(messages))
        messages = self._normalize_system_messages(messages)
        messages = self._remove_duplicate_system_prompt_user(messages)
        return self._apply_user_message_formatting(messages)

    def _prepare_event_history(
        self,
        condensed_history: list[Event],
        initial_user_action: MessageAction,
    ) -> list[Event]:
        """Create a defensively-copied history with required system/user roots."""
        events = list(condensed_history)
        self._ensure_system_message(events)
        self._ensure_initial_user_message(events, initial_user_action)
        return events

    def _messages_from_event(
        self,
        *,
        event: Event,
        index: int,
        events: list[Event],
        tool_state: _ToolCallTracking,
        max_message_chars: int | None,
        vision_is_active: bool,
    ) -> list[Message]:
        """Dispatch an event to the appropriate transformation helper."""
        if self._is_action_event(event):
            return self._process_action(
                action=cast(Action, event),
                pending_tool_call_action_messages=tool_state.pending_action_messages,
                vision_is_active=vision_is_active,
            )
        if self._is_observation_event(event):
            return self._process_observation(
                obs=cast(Observation, event),
                tool_call_id_to_message=tool_state.tool_call_messages,
                max_message_chars=max_message_chars,
                vision_is_active=vision_is_active,
                enable_som_visual_browsing=self.agent_config.enable_som_visual_browsing,
                current_index=index,
                events=events,
            )
        return self._fallback_message_for_generic_event(event)

    def _fallback_message_for_generic_event(self, event: Any) -> list[Message]:
        """Convert legacy event doubles to user messages when possible."""
        fallback_content = None
        if hasattr(event, "content") and isinstance(getattr(event, "content"), str):
            fallback_content = getattr(event, "content")
        elif hasattr(event, "message") and isinstance(getattr(event, "message"), str):
            fallback_content = getattr(event, "message")
        if fallback_content is not None:
            logger.debug(
                "[ConversationMemory] Handling generic event type %s via fallback.",
                type(event).__name__,
            )
            return [ConversationMemory._message_with_text("user", fallback_content)]
        raise ValueError(f"Unknown event type without text content: {type(event).__name__}")

    def _flush_resolved_tool_calls(
        self, tool_state: _ToolCallTracking
    ) -> list[Message]:
        """Release pending tool-call responses once all tool outputs arrive."""
        resolved_messages: list[Message] = []
        response_ids_to_remove: list[str] = []
        for response_id, pending_message in tool_state.pending_action_messages.items():
            assert pending_message.tool_calls is not None, (
                "Tool calls should NOT be None when function calling is enabled &"
                f" the message is considered pending tool call. Pending message: {pending_message}"
            )
            if all(
                tool_call.id in tool_state.tool_call_messages
                for tool_call in pending_message.tool_calls
            ):
                resolved_messages.append(pending_message)
                for tool_call in pending_message.tool_calls:
                    resolved_messages.append(
                        tool_state.tool_call_messages.pop(tool_call.id)
                    )
                response_ids_to_remove.append(response_id)
        for response_id in response_ids_to_remove:
            tool_state.pending_action_messages.pop(response_id)
        return resolved_messages

    def _normalize_system_messages(self, messages: list[Message]) -> list[Message]:
        """Ensure a single leading system prompt and drop duplicates."""
        if not messages:
            return messages

        first_system_index = next(
            (i for i, message in enumerate(messages) if message.role == "system"), -1
        )
        if first_system_index == -1:
            try:
                system_prompt = self.prompt_manager.get_system_message(
                    cli_mode=self.agent_config.cli_mode,
                    config=self.agent_config,
                )
            except Exception:
                system_prompt = "You are Forge agent."
            messages.insert(0, ConversationMemory._message_with_text("system", system_prompt))
            first_system_index = 0
        elif first_system_index != 0:
            sys_msg = messages.pop(first_system_index)
            messages.insert(0, sys_msg)

        deduped: list[Message] = [messages[0]]
        deduped.extend(message for message in messages[1:] if message.role != "system")
        return deduped

    def _to_model_response_lite(self, response: Any) -> ModelResponseLite | None:
        """Normalize SDK or dict responses into a ModelResponseLite."""
        if response is None:
            return None
        if isinstance(response, ModelResponseLite):
            return response
        try:
            return ModelResponseLite.from_sdk(response)
        except Exception:
            logger.debug("Failed to normalize model response %s", type(response).__name__, exc_info=True)
            return None

    @staticmethod
    def _convert_tool_calls(
        raw_tool_calls: Any,
    ) -> list[ChatCompletionMessageToolCallType] | None:
        """Convert SDK-specific tool call payloads into dicts accepted by Message."""
        if not raw_tool_calls:
            return None
        normalized: list[ChatCompletionMessageToolCallType] = []
        for idx, call in enumerate(raw_tool_calls):
            call_dict: dict[str, Any]
            if isinstance(call, dict):
                call_dict = dict(call)
            elif hasattr(call, "model_dump"):
                call_dict = cast(dict[str, Any], call.model_dump())
            else:
                call_dict = {
                    "id": getattr(call, "id", None),
                    "type": getattr(call, "type", "function"),
                    "function": getattr(call, "function", None),
                    "arguments": getattr(call, "arguments", None),
                    "name": getattr(call, "name", None),
                }

            ConversationMemory._ensure_tool_call_function(call_dict, call, idx)
            call_dict.setdefault("id", call_dict.get("tool_call_id") or f"tool_call_{idx}")
            call_dict.setdefault("type", getattr(call, "type", "function"))
            normalized.append(cast(ChatCompletionMessageToolCallType, call_dict))
        return normalized

    @staticmethod
    def _ensure_tool_call_function(
        call_dict: dict[str, Any], source: Any, idx: int
    ) -> None:
        """Ensure tool call payload includes a proper function dict."""

        function_payload = call_dict.get("function")
        fallback_name = (
            call_dict.get("name")
            or getattr(source, "function_name", None)
            or getattr(source, "name", None)
            or f"tool_call_{idx}"
        )
        fallback_arguments = (
            call_dict.get("arguments")
            or getattr(source, "arguments", None)
            or "{}"
        )

        if not function_payload:
            function_payload = {
                "name": fallback_name,
                "arguments": fallback_arguments,
            }
        elif isinstance(function_payload, dict):
            function_payload.setdefault("name", fallback_name)
            function_payload.setdefault("arguments", fallback_arguments)
        else:
            function_payload = {
                "name": getattr(function_payload, "name", fallback_name),
                "arguments": getattr(function_payload, "arguments", fallback_arguments),
            }

        call_dict["function"] = function_payload

    def _remove_duplicate_system_prompt_user(self, messages: list[Message]) -> list[Message]:
        """Drop leading user messages that accidentally duplicate the system prompt.

        Pytest can reload action modules when different suites run together, which
        occasionally causes a `SystemMessageAction` instance to be deserialized
        through the generic fallback path (treated as a user message). When this
        happens we end up with a user role entry that contains the exact same text
        as the preceding system prompt, shifting the rest of the history and
        breaking caching-related expectations. This normalization makes the pipeline
        idempotent by removing that redundant user entry while preserving the rest
        of the conversation.
        """
        if len(messages) < 2:
            return messages
        system_text = self._extract_first_text(messages[0])
        first_user_text = self._extract_first_text(messages[1])
        if (
            messages[0].role == "system"
            and messages[1].role == "user"
            and system_text
            and first_user_text
            and first_user_text.strip() == system_text.strip()
        ):
            return [messages[0]] + messages[2:]
        return messages

    @staticmethod
    def _extract_first_text(message: Message | None) -> str | None:
        """Helper to extract the first textual content from a message."""
        if not message or not getattr(message, "content", None):
            return None
        for item in message.content:
            if ConversationMemory._is_text_content(item):
                return getattr(item, "text", None)
        return None

    def _apply_user_message_formatting(self, messages: list[Message]) -> list[Message]:
        r"""Apply formatting rules to message sequence, such as separating consecutive user messages.

        Ensures proper readability when multiple user messages appear consecutively
        by adding newline separators. This prevents user messages from being visually
        connected when they should be distinct.

        Args:
            messages: List of Message objects to format

        Returns:
            list[Message]: Formatted message list with newline separators added where needed

        Example:
            >>> msg1 = Message(role="user", content=[TextContent(text="First")])
            >>> msg2 = Message(role="user", content=[TextContent(text="Second")])
            >>> formatted = memory._apply_user_message_formatting([msg1, msg2])
            >>> formatted[1].content[0].text
            "\\n\\nSecond"

        """
        formatted_messages: list[Message] = []
        prev_role = None
        for msg in messages:
            current_role = getattr(msg, "role", None)
            # Deep copy to avoid mutating original test fixtures / history lists.
            new_msg = msg.model_copy(deep=True) if hasattr(msg, "model_copy") else copy.deepcopy(msg)
            if current_role == "user" and prev_role == "user" and (len(new_msg.content) > 0):
                for content_item in new_msg.content:
                    if self._is_text_content(content_item):
                        # Add separator only if not already present to remain idempotent.
                        if not getattr(content_item, "text", "").startswith("\n\n"):
                            content_item.text = "\n\n" + getattr(content_item, "text", "")
                        break
            formatted_messages.append(new_msg)
            prev_role = current_role
        return formatted_messages

    @staticmethod
    def _is_text_content(content_item: Any) -> TypeGuard[TextContent]:
        """Duck-typed check for text content objects across module reloads."""
        if isinstance(content_item, TextContent):
            return True
        return bool(
            getattr(content_item, "type", None) == "text"
            and hasattr(content_item, "text")
        )

    @staticmethod
    def _class_name_in_mro(obj: Any, target_name: str | None) -> bool:
        """Check whether an object's class hierarchy contains the given name."""
        if not target_name or obj is None:
            return False
        cls = obj if isinstance(obj, type) else type(obj)
        for base in getattr(cls, "__mro__", ()):
            if base.__name__ == target_name:
                return True
        return False

    @staticmethod
    def _is_instance_of(obj: Any, cls: type[Any]) -> bool:
        """Safely evaluate isinstance across duplicated module loads."""
        if isinstance(obj, cls):
            return True
        return ConversationMemory._class_name_in_mro(obj, getattr(cls, "__name__", None))

    @staticmethod
    def _is_action_event(event: Any) -> bool:
        """Duck-typed action detection resilient to module reloads."""
        return ConversationMemory._is_instance_of(event, Action)

    @staticmethod
    def _is_observation_event(event: Any) -> bool:
        """Duck-typed observation detection resilient to module reloads."""
        return ConversationMemory._is_instance_of(event, Observation)

    @staticmethod
    def _is_message_action(event: Any) -> bool:
        """Helper for duck-typed MessageAction detection."""
        return ConversationMemory._is_instance_of(event, MessageAction)

    def _is_tool_based_action(self, action: Action) -> bool:
        """Check if action is a tool-based action that requires special handling.

        Identifies actions that involve tool execution or delegation to determine
        if they need to be processed differently (vs simple messages). Tool-based
        actions may have associated metadata, follow different message formatting,
        or have results that must be included as observations.

        Args:
            action: The Action object to classify

        Returns:
            bool: True if action is tool-based, False for simple message actions

        Example:
            >>> memory._is_tool_based_action(MessageAction(...))
            False
            >>> memory._is_tool_based_action(FileReadAction(...))
            True
            >>> memory._is_tool_based_action(MCPAction(...))
            True

        """
        src = getattr(action, "source", None)
        if isinstance(src, EventSource):
            src_value = src.value
        else:
            src_value = src
        tool_action_classes = (
            AgentDelegateAction,
            AgentThinkAction,
            IPythonRunCellAction,
            FileEditAction,
            FileReadAction,
            BrowseInteractiveAction,
            BrowseURLAction,
            MCPAction,
            TaskTrackingAction,
        )
        if any(self._is_instance_of(action, cls) for cls in tool_action_classes):
            return True
        return self._is_instance_of(action, CmdRunAction) and src_value == "agent"

    def _handle_tool_based_action(
        self,
        action: Action,
        pending_tool_call_action_messages: dict[str, Message],
    ) -> list[Message]:
        """Handle tool-based actions in function calling mode.

        Processes tool-based actions by extracting the LLM's model response,
        creating an assistant message with the model's output and tool calls.
        The resulting message is stored as pending until all tool call results
        are available before being added to the final message chain.

        Args:
            action: The tool-based action containing metadata and results
            pending_tool_call_action_messages: Dictionary to store messages pending
                tool results, keyed by model response ID

        Returns:
            list[Message]: Empty list (message is stored in pending dict for later inclusion)

        Raises:
            AssertionError: If tool call metadata is missing for agent actions

        Example:
            >>> result = memory._handle_tool_based_action(file_read_action, pending_msgs)
            >>> len(result)
            0  # Message stored in pending_msgs instead

        """
        if self._should_emit_user_tool_request(action):
            return self._build_user_tool_request_message(action)

        if self._is_instance_of(action, AgentThinkAction):
            return self._build_think_action_message(action)

        tool_metadata = self._require_tool_metadata(action)
        llm_response = self._extract_llm_response(tool_metadata)
        if llm_response is None:
            return []

        assistant_msg = self._first_choice_message(llm_response)
        if assistant_msg is None:
            return []

        role = self._role_from_assistant_message(assistant_msg)
        content_items = self._content_from_assistant_message(assistant_msg)
        response_id = getattr(llm_response, "id", None)
        if response_id is None:
            return []

        tool_calls_payload = self._convert_tool_calls(
            getattr(assistant_msg, "tool_calls", None)
        )
        pending_tool_call_action_messages[str(response_id)] = Message(
            role=role,
            content=content_items,
            tool_calls=tool_calls_payload,
        )
        return []

    def _should_emit_user_tool_request(self, action: Action) -> bool:
        src_value = getattr(getattr(action, "source", None), "value", None) or getattr(
            action, "source", None
        )
        return src_value == "user" and getattr(action, "tool_call_metadata", None) is None

    def _build_user_tool_request_message(self, action: Action) -> list[Message]:
        content: list[TextContent | ImageContent] = [
            TextContent(text=f"User requested to read file: {action!s}"),
        ]
        return [Message(role="user", content=content)]

    def _build_think_action_message(self, action: Action) -> list[Message]:
        think_text = cast(str, getattr(action, "thought", "")) or ""
        think_content: list[TextContent | ImageContent] = [
            TextContent(text=f"🤔 {think_text}")
        ]
        return [Message(role="assistant", content=think_content)]

    def _require_tool_metadata(self, action: Action):
        tool_metadata = getattr(action, "tool_call_metadata", None)
        assert tool_metadata is not None, (
            "Tool call metadata should NOT be None when function calling is enabled for "
            f"agent actions. Action: {action!s}"
        )
        return tool_metadata

    def _extract_llm_response(self, tool_metadata) -> ModelResponseLite | None:
        llm_response = self._to_model_response_lite(tool_metadata.model_response)
        if llm_response is None or not llm_response.choices:
            return None
        return llm_response

    @staticmethod
    def _first_choice_message(
        llm_response: ModelResponseLite,
    ) -> Any | None:
        raw_choice = llm_response.choices[0]
        if not hasattr(raw_choice, "message"):
            return None
        return cast(Any, raw_choice).message

    @staticmethod
    def _role_from_assistant_message(assistant_msg: Any) -> Literal[
        "user", "system", "assistant", "tool"
    ]:
        role_value = getattr(assistant_msg, "role", "assistant")
        if role_value not in {"user", "system", "assistant", "tool"}:
            role_value = "assistant"
        return cast(Literal["user", "system", "assistant", "tool"], role_value)

    @staticmethod
    def _content_from_assistant_message(
        assistant_msg: Any,
    ) -> list[TextContent | ImageContent]:
        content_items: list[TextContent | ImageContent] = []
        assistant_content = getattr(assistant_msg, "content", None)
        if isinstance(assistant_content, str):
            stripped = assistant_content.strip()
            if stripped:
                content_items.append(TextContent(text=stripped))
        elif assistant_content not in (None, ""):
            text_value = str(assistant_content).strip()
            if text_value:
                content_items.append(TextContent(text=text_value))
        return content_items

    def _handle_agent_finish_action(self, action: AgentFinishAction) -> list[Message]:
        """Handle AgentFinishAction by converting thought/conclusion to message.

        Transforms the agent's finish action (final conclusion) into a message
        that can be included in the conversation history. Optionally incorporates
        any model response content from function calling mode.

        Args:
            action: The AgentFinishAction containing the agent's final thought

        Returns:
            list[Message]: Single-element list containing the formatted message

        Raises:
            ValueError: If the role is invalid (not user/system/assistant/tool)

        Example:
            >>> finish_action = AgentFinishAction(thought="Task complete", source="agent")
            >>> messages = memory._handle_agent_finish_action(finish_action)
            >>> messages[0].role
            "assistant"

        """
        role = self._role_from_source(getattr(action, "source", None))
        self._merge_tool_metadata_thought(action)
        content_items: list[TextContent | ImageContent] = [
            TextContent(text=action.thought or "")
        ]
        return [Message(role=role, content=content_items)]

    def _role_from_source(
        self, source: EventSource | str | None
    ) -> Literal["user", "system", "assistant", "tool"]:
        src_value = source.value if isinstance(source, EventSource) else source
        role_value = "user" if src_value == "user" else "assistant"
        return cast(Literal["user", "system", "assistant", "tool"], role_value)

    def _merge_tool_metadata_thought(self, action: AgentFinishAction) -> None:
        tool_metadata = action.tool_call_metadata
        if tool_metadata is None:
            return
        response = self._to_model_response_lite(tool_metadata.model_response)
        if response is None or not response.choices:
            setattr(action, "tool_call_metadata", None)
            return
        choice = response.choices[0]
        if not hasattr(choice, "message"):
            setattr(action, "tool_call_metadata", None)
            return
        assistant_msg = cast(Any, choice).message
        content = getattr(assistant_msg, "content", "") or ""
        if action.thought:
            if action.thought != content and content:
                action.thought += "\n" + content
        else:
            action.thought = content
        setattr(action, "tool_call_metadata", None)

    def _handle_message_action(
        self, action: MessageAction, vision_is_active: bool
    ) -> list[Message]:
        """Handle MessageAction with optional image content.

        Converts a message action into a Message object, optionally including
        image URLs if vision is enabled. Images are added as separate content
        items in the message for multi-modal processing.

        Args:
            action: The MessageAction containing text content and optional image URLs
            vision_is_active: Whether image content should be included in the message

        Returns:
            list[Message]: Single-element list containing the formatted message

        Example:
            >>> action = MessageAction(
            ...     content="What's in this image?",
            ...     image_urls=["https://example.com/img.png"],
            ...     source="user"
            ... )
            >>> messages = memory._handle_message_action(action, vision_is_active=True)
            >>> len(messages[0].content)
            3  # Text, label, and image

        """
        src = getattr(action, "source", None)
        if isinstance(src, EventSource):
            src_value = src.value
        else:
            src_value = src
        role_value = "user" if src_value == "user" else "assistant"
        if role_value not in {"user", "system", "assistant", "tool"}:
            role_value = "assistant"
        role = cast(Literal["user", "system", "assistant", "tool"], role_value)
        content: list[TextContent | ImageContent] = [
            TextContent(text=action.content or "")
        ]

        if action.image_urls:
            if role == "user":
                for idx, url in enumerate(action.image_urls):
                    if vision_is_active:
                        content.append(TextContent(text=f"Image {idx + 1}:"))
                    content.append(ImageContent(image_urls=[url]))
            else:
                content.append(ImageContent(image_urls=action.image_urls))

        if role not in ("user", "system", "assistant", "tool"):
            msg = f"Invalid role: {role}"
            raise ValueError(msg)
        return [Message(role=role, content=content)]

    def _handle_user_cmd_action(self, action: CmdRunAction) -> list[Message]:
        """Handle user-initiated CmdRunAction."""
        content_items: list[TextContent | ImageContent] = [
            TextContent(text=f"User executed the command:\n{action.command}"),
        ]
        return [Message(role="user", content=content_items)]

    def _handle_system_message_action(
        self, action: SystemMessageAction
    ) -> list[Message]:
        """Handle SystemMessageAction."""
        content_items: list[TextContent | ImageContent] = [
            TextContent(text=action.content)
        ]
        return [Message(role="system", content=content_items, tool_calls=None)]

    def _process_action(
        self,
        action: Action,
        pending_tool_call_action_messages: dict[str, Message],
        vision_is_active: bool = False,
    ) -> list[Message]:
        """Converts an action into a message format that can be sent to the LLM.

        This method handles different types of actions and formats them appropriately:
        1. For tool-based actions (AgentDelegate, CmdRun, IPythonRunCell, FileEdit) and agent-sourced AgentFinish:
            - In function calling mode: Stores the LLM's response in pending_tool_call_action_messages
            - In non-function calling mode: Creates a message with the action string
        2. For MessageActions: Creates a message with the text content and optional image content

        Args:
            action: The action to convert. Can be one of:
                - CmdRunAction: For executing bash commands
                - IPythonRunCellAction: For running IPython code
                - FileEditAction: For editing files
                - FileReadAction: For reading files using Forge-aci commands
                - BrowseInteractiveAction: For browsing the web
                - AgentFinishAction: For ending the interaction
                - MessageAction: For sending messages
                - MCPAction: For interacting with the MCP server
            pending_tool_call_action_messages: Dictionary mapping response IDs to their corresponding messages.
                Used in function calling mode to track tool calls that are waiting for their results.

            vision_is_active: Whether vision is active in the LLM. If True, image URLs will be included

        Returns:
            list[Message]: A list containing the formatted message(s) for the action.
                May be empty if the action is handled as a tool call in function calling mode.

        Note:
            In function calling mode, tool-based actions are stored in pending_tool_call_action_messages
            rather than being returned immediately. They will be processed later when all corresponding
            tool call results are available.

        """
        if self._is_tool_based_action(action):
            return self._handle_tool_based_action(
                action, pending_tool_call_action_messages
            )
        if self._is_instance_of(action, AgentFinishAction):
            return self._handle_agent_finish_action(cast(AgentFinishAction, action))
        if self._is_instance_of(action, MessageAction):
            return self._handle_message_action(
                cast(MessageAction, action), vision_is_active
            )
        if self._is_instance_of(action, CmdRunAction):
            src = getattr(action, "source", None)
            if isinstance(src, EventSource):
                src_value = src.value
            else:
                src_value = src
            if src_value == "user":
                return self._handle_user_cmd_action(cast(CmdRunAction, action))
            return self._handle_user_cmd_action(cast(CmdRunAction, action))
        if self._is_instance_of(action, SystemMessageAction):
            return self._handle_system_message_action(
                cast(SystemMessageAction, action)
            )
        return []

    def _process_cmd_output_observation(
        self, obs: CmdOutputObservation, max_message_chars: int | None
    ) -> Message:
        """Process CmdOutputObservation into a message."""
        if obs.tool_call_metadata is None:
            text = truncate_content(
                f"\nObserved result of command executed by user:\n{
                    obs.to_agent_observation()
                }",
                max_message_chars,
            )
        else:
            text = truncate_content(obs.to_agent_observation(), max_message_chars)
        content_items: list[TextContent | ImageContent] = [TextContent(text=text)]
        return Message(role="user", content=content_items)

    def _process_mcp_observation(
        self, obs: MCPObservation, max_message_chars: int | None
    ) -> Message:
        """Process MCPObservation into a message."""
        text = truncate_content(obs.content, max_message_chars)
        content_items: list[TextContent | ImageContent] = [TextContent(text=text)]
        return Message(role="user", content=content_items)

    def _process_ipython_observation(
        self,
        obs: IPythonRunCellObservation,
        max_message_chars: int | None,
        vision_is_active: bool,
    ) -> Message:
        """Process IPythonRunCellObservation into a message."""
        text_content = self._sanitize_ipython_text(obs.content)
        text_content = truncate_content(text_content, max_message_chars)
        content: list[TextContent | ImageContent] = [TextContent(text=text_content)]
        if obs.image_urls:
            self._append_ipython_images(content, obs.image_urls, vision_is_active)
        return Message(role="user", content=content)

    def _sanitize_ipython_text(self, text: str) -> str:
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            if "![image](data:image/png;base64," in line:
                lines[idx] = (
                    "![image](data:image/png;base64, ...) already displayed to user"
                )
        return "\n".join(lines)

    def _append_ipython_images(
        self,
        content: list[TextContent | ImageContent],
        image_urls: list[str],
        vision_is_active: bool,
    ) -> None:
        valid_image_urls = [url for url in image_urls if self._is_valid_image_url(url)]
        invalid_count = len(image_urls) - len(valid_image_urls)

        if valid_image_urls:
            content.append(ImageContent(image_urls=valid_image_urls))
            if vision_is_active and invalid_count > 0:
                self._add_invalid_image_note(content[0], invalid_count)
            return

        logger.debug("IPython observation has image URLs but none are valid")
        if vision_is_active:
            self._add_all_images_invalid_note(content[0], len(image_urls))

    def _add_invalid_image_note(self, first_item: TextContent | ImageContent, invalid_count: int) -> None:
        if self._is_text_content(first_item):
            first_item.text += (
                f"\n\nNote: {invalid_count} invalid or empty image(s) were filtered from this output. "
                "The agent may need to use alternative methods to access visual information."
            )

    def _add_all_images_invalid_note(self, first_item: TextContent | ImageContent, total_count: int) -> None:
        if self._is_text_content(first_item):
            first_item.text += (
                f"\n\nNote: All {total_count} image(s) in this output were invalid or empty and have been filtered. "
                "The agent should use alternative methods to access visual information."
            )

    def _process_browser_output_observation(
        self,
        obs: BrowserOutputObservation,
        vision_is_active: bool,
        enable_som_visual_browsing: bool,
    ) -> Message:
        """Process BrowserOutputObservation into a message.

        Args:
            obs: Browser output observation
            vision_is_active: Whether vision is enabled
            enable_som_visual_browsing: Whether SOM visual browsing is enabled

        Returns:
            Formatted message

        """
        content: list[TextContent | ImageContent] = [TextContent(text=obs.content)]

        if (
            obs.trigger_by_action == ActionType.BROWSE_INTERACTIVE
            and enable_som_visual_browsing
        ):
            self._add_browser_visual_content(obs, content, vision_is_active)

        return Message(role="user", content=content)

    def _add_browser_visual_content(
        self,
        obs: BrowserOutputObservation,
        content: list[TextContent | ImageContent],
        vision_is_active: bool,
    ) -> None:
        """Add visual content to browser observation message.

        Enhances browser observation messages with visual information (set of marks or
        screenshots) when vision is enabled. Falls back to text-only mode gracefully
        if no valid image is available.

        Args:
            obs: Browser output observation containing image data
            content: Content list to append visual elements to (modified in-place)
            vision_is_active: Whether vision capabilities are enabled in the LLM

        Returns:
            None

        Example:
            >>> obs = BrowserOutputObservation(screenshot="base64...", ...)
            >>> content = [TextContent(text="Page loaded")]
            >>> memory._add_browser_visual_content(obs, content, vision_is_active=True)
            >>> len(content)
            2  # Text and image added

        """
        if vision_is_active:
            first_item = content[0]
            if self._is_text_content(first_item):
                first_item.text += (
                    "Image: Current webpage screenshot (Note that only visible portion of webpage is present "
                    "in the screenshot. However, the Accessibility tree contains information from the entire webpage.)\n"
                )

        image_url, image_type = self._extract_browser_image(obs)

        if self._is_valid_image_url(image_url):
            assert image_url is not None
            content.append(ImageContent(image_urls=[image_url]))
            logger.debug("Adding %s for browsing", image_type)
        elif vision_is_active:
            self._add_browser_image_fallback(content, image_url, image_type)

    def _extract_browser_image(
        self, obs: BrowserOutputObservation
    ) -> tuple[str | None, str | None]:
        """Extract image URL and type from browser observation.

        Prioritizes set of marks over screenshot. Returns the first available visual
        representation from the browser observation, or (None, None) if neither is available.

        Args:
            obs: Browser output observation containing set_of_marks and screenshot

        Returns:
            tuple[str | None, str | None]: (image_url, image_type) where image_type is
                "set of marks", "screenshot", or None

        Example:
            >>> obs = BrowserOutputObservation(
            ...     set_of_marks="base64_encoded_marks",
            ...     screenshot=None
            ... )
            >>> url, type_ = memory._extract_browser_image(obs)
            >>> type_
            "set of marks"

        """
        if obs.set_of_marks is not None and len(obs.set_of_marks) > 0:
            return obs.set_of_marks, "set of marks"
        if obs.screenshot is not None and len(obs.screenshot) > 0:
            return obs.screenshot, "screenshot"
        return None, None

    def _add_browser_image_fallback(
        self,
        content: list[TextContent | ImageContent],
        image_url: str | None,
        image_type: str | None,
    ) -> None:
        """Add fallback message when image is unavailable.

        Args:
            content: Content list
            image_url: Image URL if available
            image_type: Type of image

        """
        first_item = content[0]
        if self._is_text_content(first_item):
            if image_url:
                logger.warning(
                    "Invalid image URL format for %s: %s...", image_type, image_url[:50]
                )
                first_item.text += (
                    f"\n\nNote: The {image_type} for this webpage was invalid or empty and has been filtered. "
                    "The agent should use alternative methods to access visual information about the webpage."
                )
            else:
                logger.debug(
                    "Vision enabled for browsing, but no valid image available"
                )
                first_item.text += (
                    "\n\nNote: No visual information (screenshot or set of marks) is available for this webpage. "
                    "The agent should rely on the text content above."
                )

    def _process_recall_observation(
        self,
        obs: RecallObservation,
        current_index: int,
        events: list[Event] | None,
    ) -> list[Message]:
        """Process RecallObservation into messages."""
        if not self.agent_config.enable_prompt_extensions:
            return []

        recall_type: RecallType | str | None = getattr(obs, "recall_type", None)
        if recall_type == RecallType.WORKSPACE_CONTEXT:
            return self._process_workspace_context_recall(obs)
        if recall_type == RecallType.KNOWLEDGE:
            return self._process_knowledge_recall(obs, current_index, events or [])
        logger.debug("Unknown recall type encountered: %s", recall_type)
        return []

    def _process_workspace_context_recall(
        self, obs: RecallObservation
    ) -> list[Message]:
        """Process workspace context recall observation."""
        repo_info = self._create_repo_info(obs)
        runtime_info = self._create_runtime_info(obs)
        conversation_instructions = self._create_conversation_instructions(obs)
        repo_instructions = obs.repo_instructions or ""
        filtered_agents = self._filter_microagents(obs)

        has_content = self._has_workspace_content(
            repo_info,
            runtime_info,
            repo_instructions,
            conversation_instructions,
            filtered_agents,
        )
        if not has_content:
            return []

        message_content = self._build_message_content(
            repo_info,
            runtime_info,
            conversation_instructions,
            repo_instructions,
            filtered_agents,
        )
        return [Message(role="user", content=message_content)]

    def _create_repo_info(self, obs: RecallObservation) -> RepositoryInfo | None:
        """Create repository info from observation."""
        if obs.repo_name or obs.repo_directory:
            return RepositoryInfo(
                repo_name=obs.repo_name or "",
                repo_directory=obs.repo_directory or "",
                branch_name=obs.repo_branch or None,
            )
        return None

    def _create_runtime_info(self, obs: RecallObservation) -> RuntimeInfo:
        """Create runtime info from observation."""
        date = obs.date
        if obs.runtime_hosts or obs.additional_agent_instructions:
            return RuntimeInfo(
                available_hosts=obs.runtime_hosts,
                additional_agent_instructions=obs.additional_agent_instructions,
                date=date,
                custom_secrets_descriptions=obs.custom_secrets_descriptions,
                working_dir=obs.working_dir,
            )
        return RuntimeInfo(
            date=date,
            custom_secrets_descriptions=obs.custom_secrets_descriptions,
            working_dir=obs.working_dir,
        )

    def _create_conversation_instructions(
        self, obs: RecallObservation
    ) -> ConversationInstructions | None:
        """Create conversation instructions from observation."""
        if obs.conversation_instructions:
            return ConversationInstructions(content=obs.conversation_instructions)
        return None

    def _filter_microagents(self, obs: RecallObservation) -> list[MicroagentKnowledge]:
        """Filter microagents based on disabled list."""
        if not obs.microagent_knowledge:
            return []
        return [
            agent
            for agent in obs.microagent_knowledge
            if agent.name not in self.agent_config.disabled_microagents
        ]

    def _has_workspace_content(
        self,
        repo_info: RepositoryInfo | None,
        runtime_info: RuntimeInfo,
        repo_instructions: str,
        conversation_instructions: ConversationInstructions | None,
        filtered_agents: list[MicroagentKnowledge],
    ) -> bool:
        """Check if there's any workspace content to include."""
        has_repo = bool(repo_info and (repo_info.repo_name or repo_info.repo_directory))
        has_runtime = bool(
            runtime_info.date or runtime_info.custom_secrets_descriptions
        )
        has_instructions = (
            bool(repo_instructions.strip()) or conversation_instructions is not None
        )
        has_agents = bool(filtered_agents)
        return has_repo or has_runtime or has_instructions or has_agents

    def _build_message_content(
        self,
        repo_info: RepositoryInfo | None,
        runtime_info: RuntimeInfo,
        conversation_instructions: ConversationInstructions | None,
        repo_instructions: str,
        filtered_agents: list[MicroagentKnowledge],
    ) -> list[TextContent | ImageContent]:
        """Build the message content from workspace information."""
        message_content: list[TextContent | ImageContent] = []

        # Add workspace context if available
        has_repo = repo_info is not None and (
            repo_info.repo_name or repo_info.repo_directory
        )
        has_runtime = runtime_info is not None and (
            runtime_info.date or runtime_info.custom_secrets_descriptions
        )
        has_instructions = (
            bool(repo_instructions.strip()) or conversation_instructions is not None
        )

        if has_repo or has_runtime or has_instructions:
            formatted_workspace_text = self.prompt_manager.build_workspace_context(
                repository_info=repo_info,
                runtime_info=runtime_info,
                conversation_instructions=conversation_instructions,
                repo_instructions=repo_instructions,
            )
            message_content.append(TextContent(text=formatted_workspace_text))

        # Add microagent info if available
        if filtered_agents:
            formatted_microagent_text = self.prompt_manager.build_microagent_info(
                triggered_agents=filtered_agents
            )
            message_content.append(TextContent(text=formatted_microagent_text))

        return message_content

    def _process_knowledge_recall(
        self,
        obs: RecallObservation,
        current_index: int,
        events: list[Event],
    ) -> list[Message]:
        """Process knowledge recall observation."""
        filtered_agents = self._filter_agents_in_microagent_obs(
            obs, current_index, events
        )
        if filtered_agents:
            filtered_agents = [
                agent
                for agent in filtered_agents
                if agent.name not in self.agent_config.disabled_microagents
            ]
        if filtered_agents:
            formatted_text = self.prompt_manager.build_microagent_info(
                triggered_agents=filtered_agents
            )
            content_items: list[TextContent | ImageContent] = [
                TextContent(text=formatted_text)
            ]
            return [Message(role="user", content=content_items)]
        return []

    def _process_simple_observation(
        self,
        obs,
        max_message_chars: int | None,
        prefix: str = "",
        suffix: str = "",
    ) -> Message:
        """Process simple observation types that just need text truncation."""
        text = truncate_content(str(obs), max_message_chars)
        if prefix:
            text = prefix + text
        if suffix:
            text += suffix
        content_items: list[TextContent | ImageContent] = [TextContent(text=text)]
        return Message(role="user", content=content_items)

    def _process_observation(
        self,
        obs: Observation,
        tool_call_id_to_message: dict[str, Message],
        max_message_chars: int | None = None,
        vision_is_active: bool = False,
        enable_som_visual_browsing: bool = False,
        current_index: int = 0,
        events: list[Event] | None = None,
    ) -> list[Message]:
        """Converts an observation into a message format that can be sent to the LLM.

        This method handles different types of observations and formats them appropriately:
        - CmdOutputObservation: Formats command execution results with exit codes
        - IPythonRunCellObservation: Formats IPython cell execution results, replacing base64 images
        - FileEditObservation: Formats file editing results
        - FileReadObservation: Formats file reading results from forge-aci
        - AgentDelegateObservation: Formats results from delegated agent tasks
        - ErrorObservation: Formats error messages from failed actions
        - UserRejectObservation: Formats user rejection messages
        - FileDownloadObservation: Formats the result of a browsing action that opened/downloaded a file

        In function calling mode, observations with tool_call_metadata are stored in
        tool_call_id_to_message for later processing instead of being returned immediately.

        Args:
            obs: The observation to convert
            tool_call_id_to_message: Dictionary mapping tool call IDs to their corresponding messages (used in function calling mode)
            max_message_chars: The maximum number of characters in the content of an observation included in the prompt to the LLM
            vision_is_active: Whether vision is active in the LLM. If True, image URLs will be included
            enable_som_visual_browsing: Whether to enable visual browsing for the SOM model
            current_index: The index of the current event in the events list (for deduplication)
            events: The list of all events (for deduplication)

        Returns:
            list[Message]: A list containing the formatted message(s) for the observation.
                May be empty if the observation is handled as a tool response in function calling mode.

        Raises:
            ValueError: If the observation type is unknown

        """
        # Handle special cases first
        if self._is_instance_of(obs, RecallObservation):
            return self._process_recall_observation(
                cast(RecallObservation, obs), current_index, events or []
            )

        # Handle different observation types
        message = self._get_message_for_observation(
            obs,
            max_message_chars,
            vision_is_active,
            enable_som_visual_browsing,
        )

        # Handle tool call metadata
        if (tool_call_metadata := getattr(obs, "tool_call_metadata", None)) is not None:
            tool_call_id_to_message[tool_call_metadata.tool_call_id] = Message(
                role="tool",
                content=message.content,
                tool_call_id=tool_call_metadata.tool_call_id,
                name=tool_call_metadata.function_name,
            )
            return []

        return [message]

    def _get_message_for_observation(
        self,
        obs: Observation,
        max_message_chars: int | None,
        vision_is_active: bool,
        enable_som_visual_browsing: bool,
    ) -> Message:
        """Get the appropriate message for different observation types."""
        # Create observation handler mapping
        handlers = self._get_observation_handlers(
            max_message_chars, vision_is_active, enable_som_visual_browsing
        )

        # Get the appropriate handler for this observation type
        obs_type = type(obs)
        if handler := handlers.get(obs_type):
            return handler(obs)
        # Fallback for duplicate class definitions produced by importlib.reload in tests.
        obs_class_name = obs_type.__name__
        for cls, handler in handlers.items():
            if cls.__name__ == obs_class_name:
                return handler(obs)

        # Default fallback for unknown observation types
        return self._process_simple_observation(obs, max_message_chars)

    def _get_observation_handlers(
        self,
        max_message_chars: int | None,
        vision_is_active: bool,
        enable_som_visual_browsing: bool,
    ) -> dict[type, Callable[[Any], Message]]:
        """Get mapping of observation types to their handler functions."""
        return {
            CmdOutputObservation: lambda obs: self._process_cmd_output_observation(
                obs, max_message_chars
            ),
            MCPObservation: lambda obs: self._process_mcp_observation(
                obs, max_message_chars
            ),
            IPythonRunCellObservation: lambda obs: self._process_ipython_observation(
                obs,
                max_message_chars,
                vision_is_active,
            ),
            FileEditObservation: lambda obs: self._process_simple_observation(
                obs, max_message_chars
            ),
            FileReadObservation: lambda obs: self._message_with_text(
                "user", obs.content
            ),
            BrowserOutputObservation: lambda obs: self._process_browser_output_observation(
                obs,
                vision_is_active,
                enable_som_visual_browsing,
            ),
            AgentDelegateObservation: lambda obs: self._process_agent_delegate_observation(
                obs, max_message_chars
            ),
            AgentThinkObservation: lambda obs: self._process_simple_observation(
                obs, max_message_chars
            ),
            TaskTrackingObservation: lambda obs: self._process_simple_observation(
                obs, max_message_chars
            ),
            ErrorObservation: lambda obs: self._process_error_observation(
                obs, max_message_chars
            ),
            UserRejectObservation: lambda obs: self._process_user_reject_observation(
                obs, max_message_chars
            ),
            AgentCondensationObservation: lambda obs: self._process_simple_observation(
                obs, max_message_chars
            ),
            FileDownloadObservation: lambda obs: self._process_simple_observation(
                obs, max_message_chars
            ),
        }

    def _process_agent_delegate_observation(
        self,
        obs: AgentDelegateObservation,
        max_message_chars: int | None,
    ) -> Message:
        """Process agent delegate observation."""
        text = truncate_content(
            obs.outputs.get("content", obs.content), max_message_chars
        )
        content_items: list[TextContent | ImageContent] = [TextContent(text=text)]
        return Message(role="user", content=content_items)

    def _process_error_observation(
        self, obs: ErrorObservation, max_message_chars: int | None
    ) -> Message:
        """Process error observation with specific formatting."""
        return self._process_simple_observation(
            obs,
            max_message_chars,
            suffix="\n[Error occurred in processing last action]",
        )

    def _process_user_reject_observation(
        self, obs: UserRejectObservation, max_message_chars: int | None
    ) -> Message:
        """Process user reject observation with specific formatting."""
        return self._process_simple_observation(
            obs,
            max_message_chars,
            prefix="OBSERVATION:\n",
            suffix="\n[Last action has been rejected by the user]",
        )

    def _filter_agents_in_microagent_obs(
        self,
        obs: RecallObservation,
        current_index: int,
        events: list[Event],
    ) -> list[MicroagentKnowledge]:
        """Filter out agents that appear in earlier RecallObservations.

        Args:
            obs: The current RecallObservation to filter
            current_index: The index of the current event in the events list
            events: The list of all events

        Returns:
            list[MicroagentKnowledge]: The filtered list of microagent knowledge

        """
        if obs.recall_type != RecallType.KNOWLEDGE:
            return obs.microagent_knowledge
        return [
            agent
            for agent in obs.microagent_knowledge
            if not self._has_agent_in_earlier_events(agent.name, current_index, events)
        ]

    def _has_agent_in_earlier_events(
        self, agent_name: str, current_index: int, events: list[Event]
    ) -> bool:
        """Check if an agent appears in any earlier RecallObservation in the event list.

        Args:
            agent_name: The name of the agent to look for
            current_index: The index of the current event in the events list
            events: The list of all events

        Returns:
            bool: True if the agent appears in an earlier RecallObservation, False otherwise

        """
        return any(
            self._is_instance_of(event, RecallObservation)
            and any(
                agent.name == agent_name
                for agent in cast(RecallObservation, event).microagent_knowledge
            )
            for event in events[:current_index]
        )

    @staticmethod
    def _filter_unmatched_tool_calls(
        messages: list[Message],
    ) -> Generator[Message, None, None]:
        """Filter out tool calls that don't have matching tool responses and vice versa.

        This ensures that every tool_call_id in a tool message has a corresponding tool_calls[].id
        in an assistant message, and vice versa. The original list is unmodified, when tool_calls is
        updated the message is copied.

        This does not remove items with id set to None.
        """
        tool_call_ids = ConversationMemory._collect_tool_call_ids(messages)
        tool_response_ids = ConversationMemory._collect_tool_response_ids(messages)

        for message in messages:
            if ConversationMemory._should_include_message(
                message, tool_call_ids, tool_response_ids
            ):
                yield ConversationMemory._maybe_trim_tool_calls(
                    message, tool_response_ids
                )

    @staticmethod
    def _collect_tool_call_ids(messages: list[Message]) -> set[str]:
        """Collect all tool call IDs from assistant messages."""
        return {
            tool_call.id
            for message in messages
            if message.tool_calls
            for tool_call in message.tool_calls
            if message.role == "assistant" and tool_call.id
        }

    @staticmethod
    def _collect_tool_response_ids(messages: list[Message]) -> set[str]:
        """Collect all tool response IDs from tool messages."""
        return {
            message.tool_call_id
            for message in messages
            if message.role == "tool" and message.tool_call_id
        }

    @staticmethod
    def _should_include_message(
        message: Message, tool_call_ids: set[str], tool_response_ids: set[str]
    ) -> bool:
        """Determine if a message should be included in the filtered results."""
        if message.role == "tool" and message.tool_call_id:
            return message.tool_call_id in tool_call_ids
        if message.role == "assistant" and message.tool_calls:
            return ConversationMemory._all_tool_calls_match(message, tool_response_ids)
        return True

    @staticmethod
    def _maybe_trim_tool_calls(
        message: Message, tool_response_ids: set[str]
    ) -> Message:
        if message.role != "assistant" or not message.tool_calls:
            return message

        matched_calls = [
            call for call in message.tool_calls if call.id in tool_response_ids
        ]
        if len(matched_calls) == len(message.tool_calls):
            return message
        if not matched_calls:
            raise StopIteration  # Should not be yielded by caller

        new_message = message.model_copy(deep=True)
        new_message.tool_calls = matched_calls
        return new_message

    @staticmethod
    def _all_tool_calls_match(message: Message, tool_response_ids: set[str]) -> bool:
        """Check if all tool calls in a message have matching responses."""
        if not message.tool_calls:
            return True

        all_match = all(
            tool_call.id in tool_response_ids for tool_call in message.tool_calls
        )
        if all_match:
            return True

        return bool(
            [
                tool_call
                for tool_call in message.tool_calls
                if tool_call.id in tool_response_ids
            ]
        )

    def _ensure_system_message(self, events: list[Event]) -> None:
        """Checks if a system message exists and adds one if not.

        Uses duck-typing in addition to isinstance to avoid false negatives
        when tests or alternate imports provide compatible event stubs.
        """
        has_system_message = False
        for event in events:
            # Primary fast-path: direct isinstance or duck-typed equivalent
            if self._is_instance_of(event, SystemMessageAction):
                has_system_message = True
                break
            # Class name match fallback (handles duplicate class loading / re-import edge cases)
            if type(event).__name__ == "SystemMessageAction":  # pragma: no cover - defensive
                has_system_message = True
                break
            # Duck-typed detection: an event with action == ActionType.SYSTEM is treated as system
            if getattr(event, "action", None) == ActionType.SYSTEM:
                has_system_message = True
                break
        if not has_system_message:
            logger.debug(
                "[ConversationMemory] No SystemMessageAction found in events. Adding one for backward compatibility. ",
            )
            if system_prompt := self.prompt_manager.get_system_message(
                cli_mode=self.agent_config.cli_mode, config=self.agent_config
            ):
                system_message = SystemMessageAction(content=system_prompt)
                events.insert(0, system_message)
                logger.info(
                    "[ConversationMemory] Added SystemMessageAction for backward compatibility"
                )

    def _ensure_initial_user_message(
        self, events: list[Event], initial_user_action: MessageAction
    ) -> None:
        """Ensure the initial user message is present and positioned consistently.

        Idempotent logic:
        - If the exact initial_user_action object already exists anywhere in the list:
          * If it's at index 1 and correctly sourced, leave as-is.
          * If it's elsewhere and index 1 is not a user-sourced MessageAction, move it to index 1.
        - If it does not exist, insert at index 1 (or append if list length == 0).
        This avoids duplicate insertions across repeated calls (important for tests invoking
        the pipeline multiple times with the same underlying history list).
        """
        if not events:
            self._append_initial_user_action(events, initial_user_action)
            return

        existing_index = self._find_existing_initial_action(events, initial_user_action)
        if self._handle_existing_initial_action(events, initial_user_action, existing_index):
            return

        if self._has_user_message_at_index_one(events):
            return

        self._insert_initial_user_at_index(events, initial_user_action)

    @staticmethod
    def _append_initial_user_action(
        events: list[Event], initial_user_action: MessageAction
    ) -> None:
        logger.error("Cannot ensure initial user message: event list is empty.")
        events.append(initial_user_action)

    @staticmethod
    def _find_existing_initial_action(
        events: list[Event], initial_user_action: MessageAction
    ) -> int:
        for idx, event in enumerate(events):
            if event is initial_user_action:
                return idx
        return -1

    def _handle_existing_initial_action(
        self,
        events: list[Event],
        initial_user_action: MessageAction,
        existing_index: int,
    ) -> bool:
        if existing_index == -1:
            return False
        if existing_index == 1 and self._is_user_message(events[1]):
            return True
        if len(events) > 1 and self._is_user_message(events[1]):
            return True
        events.pop(existing_index)
        insert_pos = 1 if len(events) >= 1 else 0
        events.insert(insert_pos, initial_user_action)
        logger.debug(
            "Repositioned existing initial user action to index %s", insert_pos
        )
        return True

    def _has_user_message_at_index_one(self, events: list[Event]) -> bool:
        return len(events) > 1 and self._is_user_message(events[1])

    def _insert_initial_user_at_index(
        self, events: list[Event], initial_user_action: MessageAction
    ) -> None:
        insert_pos = 1 if len(events) >= 1 else 0
        events.insert(insert_pos, initial_user_action)
        logger.info("Inserted initial user action at index %s", insert_pos)

    def _is_user_message(self, event: Event) -> bool:
        if not self._is_instance_of(event, MessageAction):
            return False
        source = getattr(event, "source", getattr(event, "_source", None))
        if isinstance(source, EventSource):
            return source == EventSource.USER
        return source == "user"

    def store_in_memory(
        self,
        event_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store an event in persistent vector memory.

        Args:
            event_id: Unique event identifier
            role: Role (user/agent/system)
            content: Event content to store
            metadata: Optional metadata dict

        """
        if not self.vector_store:
            return

        try:
            self.vector_store.add(
                step_id=event_id,
                role=role,
                artifact_hash=None,
                rationale=None,
                content_text=content,
                metadata=metadata or {},
            )
            logger.debug(f"Stored event {event_id} in vector memory")
        except Exception as e:
            logger.warning(f"Failed to store event in memory: {e}")

    def recall_from_memory(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant context from persistent vector memory.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant memory records

        """
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.search(query, k=k)
            logger.debug(
                f"Retrieved {len(results)} relevant memories for query: {query[:50]}"
            )
            return results
        except Exception as e:
            logger.warning(f"Failed to retrieve from memory: {e}")
            return []
