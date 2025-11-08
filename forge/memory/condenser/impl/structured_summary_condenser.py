"""Condenser that converts history into structured summaries using template-driven rules."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from forge.core.config.condenser_config import StructuredSummaryCondenserConfig
from forge.core.logger import forge_logger as logger
from forge.core.message import Message, TextContent
from forge.events.action.agent import CondensationAction
from forge.events.observation.agent import AgentCondensationObservation
from forge.events.serialization.event import truncate_content
from forge.memory.condenser.condenser import Condensation, RollingCondenser
from forge.memory.view import View

if TYPE_CHECKING:
    from forge.llm.llm import LLM
    from forge.llm.llm_registry import LLMRegistry


class StateSummary(BaseModel):
    """A structured representation summarizing the state of the agent and the task."""

    user_context: str = Field(
        default="",
        description="Essential user requirements, goals, and clarifications in concise form.",
    )
    completed_tasks: str = Field(default="", description="List of tasks completed so far with brief results.")
    pending_tasks: str = Field(default="", description="List of tasks that still need to be done.")
    current_state: str = Field(
        default="",
        description="Current variables, data structures, or other relevant state information.",
    )
    files_modified: str = Field(default="", description="List of files that have been created or modified.")
    function_changes: str = Field(default="", description="List of functions that have been created or modified.")
    data_structures: str = Field(default="", description="List of key data structures in use or modified.")
    tests_written: str = Field(
        default="",
        description="Whether tests have been written for the changes. True, false, or unknown.",
    )
    tests_passing: str = Field(
        default="",
        description="Whether all tests are currently passing. True, false, or unknown.",
    )
    failing_tests: str = Field(default="", description="List of names or descriptions of any failing tests.")
    error_messages: str = Field(default="", description="List of key error messages encountered.")
    branch_created: str = Field(
        default="",
        description="Whether a branch has been created for this work. True, false, or unknown.",
    )
    branch_name: str = Field(default="", description="Name of the current working branch if known.")
    commits_made: str = Field(default="", description="Whether any commits have been made. True, false, or unknown.")
    pr_created: str = Field(default="", description="Whether a pull request has been created. True, false, or unknown.")
    pr_status: str = Field(
        default="",
        description="Status of any pull request: 'draft', 'open', 'merged', 'closed', or 'unknown'.",
    )
    dependencies: str = Field(
        default="",
        description="List of dependencies or imports that have been added or modified.",
    )
    other_relevant_context: str = Field(
        default="",
        description="Any other important information that doesn't fit into the categories above.",
    )

    @classmethod
    def tool_description(cls) -> dict[str, Any]:
        """Description of a tool whose arguments are the fields of this class.

        Can be given to an LLM to force structured generation.
        """
        properties = {}
        for field_name, field in cls.model_fields.items():
            description = field.description or ""
            properties[field_name] = {"type": "string", "description": description}
        return {
            "type": "function",
            "function": {
                "name": "create_state_summary",
                "description": "Creates a comprehensive summary of the current state of the interaction to preserve context when history grows too large. You must include non-empty values for user_context, completed_tasks, and pending_tasks.",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": [
                        "user_context",
                        "completed_tasks",
                        "pending_tasks"],
                },
            },
        }

    def __str__(self) -> str:
        """Format the state summary in a clear way for Claude 3.7 Sonnet."""
        sections = [
            "# State Summary",
            "## Core Information",
            f"**User Context**: {self.user_context}",
            f"**Completed Tasks**: {self.completed_tasks}",
            f"**Pending Tasks**: {self.pending_tasks}",
            f"**Current State**: {self.current_state}",
            "## Code Changes",
            f"**Files Modified**: {self.files_modified}",
            f"**Function Changes**: {self.function_changes}",
            f"**Data Structures**: {self.data_structures}",
            f"**Dependencies**: {self.dependencies}",
            "## Testing Status",
            f"**Tests Written**: {self.tests_written}",
            f"**Tests Passing**: {self.tests_passing}",
            f"**Failing Tests**: {self.failing_tests}",
            f"**Error Messages**: {self.error_messages}",
            "## Version Control",
            f"**Branch Created**: {self.branch_created}",
            f"**Branch Name**: {self.branch_name}",
            f"**Commits Made**: {self.commits_made}",
            f"**PR Created**: {self.pr_created}",
            f"**PR Status**: {self.pr_status}",
            "## Additional Context",
            f"**Other Relevant Context**: {self.other_relevant_context}",
        ]
        return "\n\n".join(sections)


class StructuredSummaryCondenser(RollingCondenser):
    """A condenser that summarizes forgotten events.

    Maintains a condensed history and forgets old events when it grows too large. Uses structured generation via function-calling to produce summaries that replace forgotten events.
    """

    def __init__(self, llm: LLM, max_size: int = 100, keep_first: int = 1, max_event_length: int = 10000) -> None:
        """Initialize a structured summarizing condenser using LLM function calling.
        
        This condenser uses an LLM with function calling capability to generate structured
        state summaries (StateSummary objects) that replace forgotten events. Unlike free-form
        text summarization, structured summaries enforce consistent categorization across
        multiple dimensions (user context, tasks, code changes, version control status, etc.),
        making the preserved context more queryable and reliable for downstream processing.
        
        Args:
            llm: Language model instance with active function calling capability.
                 Will raise ValueError if is_function_calling_active() returns False.
            max_size: Maximum number of events before condensation is triggered. Must be >= 1.
                     Target condensation reduces this to max_size // 2 events.
            keep_first: Number of initial events to always preserve in prefix.
                       Must be >= 0 and < max_size // 2 to leave room for summary and tail.
            max_event_length: Maximum character length for individual event content before truncation.
                             Prevents excessively large prompts when summarizing events (default 10000).
        
        Raises:
            ValueError: If keep_first >= max_size // 2, keep_first < 0, max_size < 1,
                       or if LLM doesn't have function calling enabled.
        
        Side Effects:
            - Validates LLM function calling capability via is_function_calling_active()
            - Initializes parent RollingCondenser for event management
        
        Notes:
            - Structure: [keep_first events] + [1 summary event] + [events_from_tail recent events]
            - Structured output: StateSummary with 22 fields for comprehensive state tracking
            - Function calling: Uses StateSummary.tool_description() to enforce structured output
            - Forgotten events: Selected from view[keep_first:-events_from_tail], excluding summary events
            - Examples: max_size=100, keep_first=1 → keep 1 first + 1 summary + ~48 recent events
        
        Example:
            >>> from forge.llm.llm import LLM
            >>> llm = get_llm_with_function_calling()  # doctest: +SKIP
            >>> condenser = StructuredSummaryCondenser(llm, max_size=100, keep_first=1)
            >>> condenser.max_size
            100

        """
        if keep_first >= max_size // 2:
            msg = f"keep_first ({keep_first}) must be less than half of max_size ({max_size})"
            raise ValueError(msg)
        if keep_first < 0:
            msg = f"keep_first ({keep_first}) cannot be negative"
            raise ValueError(msg)
        if max_size < 1:
            msg = f"max_size ({max_size}) cannot be non-positive"
            raise ValueError(msg)
        self.max_size = max_size
        self.keep_first = keep_first
        self.max_event_length = max_event_length
        self.llm = llm
        if not self.llm.is_function_calling_active():
            msg = "LLM must support function calling to use StructuredSummaryCondenser"
            raise ValueError(msg)
        super().__init__()

    def _truncate(self, content: str) -> str:
        """Truncate the content to fit within the specified maximum event length."""
        return truncate_content(content, max_chars=self.max_event_length)

    def get_condensation(self, view: View) -> Condensation:
        """Generate condensation from view by summarizing forgotten events."""
        # Prepare view sections
        _head, forgotten_events, summary_event = self._prepare_view_sections(view)

        # Build prompt for LLM
        prompt = self._build_condensation_prompt(summary_event, forgotten_events)

        # Get summary from LLM
        summary = self._get_llm_summary(prompt)

        # Create condensation result
        return self._create_condensation_result(forgotten_events, summary)

    def _prepare_view_sections(self, view: View) -> tuple[list, list, AgentCondensationObservation]:
        """Prepare view sections: head, forgotten events, and summary event."""
        head = view[: self.keep_first]
        target_size = self.max_size // 2
        events_from_tail = target_size - len(head) - 1

        # Get or create summary event
        summary_event = (
            view[self.keep_first]
            if isinstance(view[self.keep_first], AgentCondensationObservation)
            else AgentCondensationObservation("No events summarized")
        )

        # Get forgotten events (exclude summary events)
        forgotten_events = [
            event
            for event in view[self.keep_first: -events_from_tail]
            if not isinstance(event, AgentCondensationObservation)
        ]

        return head, forgotten_events, summary_event

    def _build_condensation_prompt(self, summary_event: AgentCondensationObservation, forgotten_events: list) -> str:
        """Build the prompt for LLM condensation."""
        base_prompt = (
            "You are maintaining a context-aware state summary for an interactive software agent. This summary is critical because it:\n"
            "1. Preserves essential context when conversation history grows too large\n"
            "2. Prevents lost work when the session length exceeds token limits\n"
            "3. Helps maintain continuity across multiple interactions\n\n"
            "You will be given:\n"
            "- A list of events (actions taken by the agent)\n"
            "- The most recent previous summary (if one exists)\n\n"
            "Capture all relevant information, especially:\n"
            "- User requirements that were explicitly stated\n"
            "- Work that has been completed\n"
            "- Tasks that remain pending\n"
            "- Current state of code, variables, and data structures\n"
            "- The status of any version control operations\n\n")

        # Add previous summary
        summary_event_content = self._truncate(summary_event.message or "")
        base_prompt += f"<PREVIOUS SUMMARY>\n{summary_event_content}\n</PREVIOUS SUMMARY>\n\n"

        # Add forgotten events
        for forgotten_event in forgotten_events:
            event_content = self._truncate(str(forgotten_event))
            base_prompt += f"<EVENT id={forgotten_event.id}>\n{event_content}\n</EVENT>\n"

        return base_prompt

    def _get_llm_summary(self, prompt: str) -> StateSummary:
        """Get summary from LLM using tool calling."""
        messages = [Message(role="user", content=[TextContent(text=prompt)])]

        response = self.llm.completion(
            messages=self.llm.format_messages_for_llm(messages),
            tools=[StateSummary.tool_description()],
            tool_choice={"type": "function", "function": {"name": "create_state_summary"}},
        )

        # Parse response
        summary = self._parse_llm_response(response)

        # Add metadata
        self._add_response_metadata(response)

        return summary

    def _parse_llm_response(self, response) -> StateSummary:
        """Parse LLM response to extract StateSummary."""
        try:
            message = response.choices[0].message
            if not hasattr(message, "tool_calls") or not message.tool_calls:
                msg = "No tool calls found in response"
                raise ValueError(msg)

            summary_tool_call = next(
                (tool_call for tool_call in message.tool_calls if tool_call.function.name == "create_state_summary"),
                None,
            )
            if not summary_tool_call:
                msg = "create_state_summary tool call not found"
                raise ValueError(msg)

            args_json = summary_tool_call.function.arguments
            args_dict = json.loads(args_json)
            return StateSummary.model_validate(args_dict)

        except (ValueError, AttributeError, KeyError, json.JSONDecodeError) as e:
            logger.warning("Failed to parse summary tool call: %s. Using empty summary.", e)
            return StateSummary()

    def _add_response_metadata(self, response) -> None:
        """Add response metadata to condenser."""
        from forge.core.pydantic_compat import model_dump_with_options

        self.add_metadata("response", model_dump_with_options(response))
        self.add_metadata("metrics", self.llm.metrics.get())

    def _create_condensation_result(self, forgotten_events: list, summary: StateSummary) -> Condensation:
        """Create the final condensation result."""
        return Condensation(
            action=CondensationAction(
                forgotten_events_start_id=min(event.id for event in forgotten_events),
                forgotten_events_end_id=max(event.id for event in forgotten_events),
                summary=str(summary),
                summary_offset=self.keep_first,
            ),
        )

    def should_condense(self, view: View) -> bool:
        """Condense when the conversation length exceeds the configured max size."""
        return len(view) > self.max_size

    @classmethod
    def from_config(
        cls,
        config: "StructuredSummaryCondenserConfig",
        llm_registry: LLMRegistry,
    ) -> StructuredSummaryCondenser:
        """Instantiate structured summary condenser with configured LLM and limits."""
        llm_config = config.llm_config.model_copy()
        llm_config.caching_prompt = False
        llm = llm_registry.get_llm("condenser", llm_config)
        return StructuredSummaryCondenser(
            llm=llm,
            max_size=config.max_size,
            keep_first=config.keep_first,
            max_event_length=config.max_event_length,
        )


# Lazy registration to avoid circular imports
def _register_config():
    """Register StructuredSummaryCondenserConfig with the StructuredSummaryCondenser factory.
    
    Defers import of StructuredSummaryCondenserConfig to avoid circular dependency between
    condenser implementations and their configuration classes. Called at module load time
    to enable from_config() factory method to instantiate condensers from config objects.
    
    Side Effects:
        - Imports StructuredSummaryCondenserConfig from forge.core.config.condenser_config
        - Registers config class with StructuredSummaryCondenser.register_config() factory
    
    Notes:
        - Must be called at module level after StructuredSummaryCondenser class definition
        - Pattern reused across all condenser implementations
        - Avoids import-time circular dependency that would occur if config imported at top level

    """
    from forge.core.config.condenser_config import StructuredSummaryCondenserConfig
    StructuredSummaryCondenser.register_config(StructuredSummaryCondenserConfig)

_register_config()
