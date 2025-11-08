"""Condenser that summarizes history via LLM-generated CondensationAction events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.config.condenser_config import LLMSummarizingCondenserConfig
from forge.core.message import Message, TextContent
from forge.events.action.agent import CondensationAction
from forge.events.observation.agent import AgentCondensationObservation
from forge.events.serialization.event import truncate_content
from forge.memory.condenser.condenser import Condensation, RollingCondenser
from forge.memory.view import View

if TYPE_CHECKING:
    from forge.llm.llm import LLM
    from forge.llm.llm_registry import LLMRegistry


class LLMSummarizingCondenser(RollingCondenser):
    """A condenser that summarizes forgotten events.

    Maintains a condensed history and forgets old events when it grows too large,
    keeping a special summarization event after the prefix that summarizes all previous summarizations
    and newly forgotten events.
    """

    def __init__(self, llm: LLM, max_size: int = 100, keep_first: int = 1, max_event_length: int = 10000) -> None:
        """Initialize the LLM-based summarizing condenser that summarizes forgotten events.
        
        This condenser maintains a rolling window of recent events and creates textual summaries
        of forgotten events using an LLM. It preserves a fixed prefix of initial events (keep_first),
        maintains one summary observation event after the prefix, fills the remainder with recent events,
        and forgets old non-summary events between prefix and tail.
        
        Args:
            llm: Language model instance for generating summaries of forgotten events.
            max_size: Maximum number of events before condensation is triggered. Must be >= 1.
                     Target condensation reduces this to max_size // 2 events (prefix + summary + tail).
            keep_first: Number of initial events to always preserve in the prefix.
                       Must be >= 0 and < max_size // 2 to leave room for summary and tail.
            max_event_length: Maximum character length for individual event content before truncation.
                             Prevents excessively large prompts when summarizing events (default 10000).
        
        Raises:
            ValueError: If keep_first >= max_size // 2, keep_first < 0, or max_size < 1.
        
        Side Effects:
            - Initializes parent RollingCondenser for event management
            - Sets truncation limit for content preprocessing in get_condensation()
        
        Notes:
            - Structure: [keep_first events] + [1 summary event] + [events_from_tail recent events]
            - Forgotten events are selected from view[keep_first:-events_from_tail]
            - Events are truncated to max_event_length before being included in LLM prompt
            - Summary prompt preserves TASK_TRACKING and maintains context-aware state
            - Examples: max_size=100, keep_first=1 → keep 1 first + 1 summary + ~48 recent events
        
        Example:
            >>> from forge.llm.llm import LLM
            >>> llm = get_llm_instance()  # doctest: +SKIP
            >>> condenser = LLMSummarizingCondenser(llm, max_size=100, keep_first=1, max_event_length=10000)
            >>> condenser.max_event_length
            10000

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
        super().__init__()

    def _truncate(self, content: str) -> str:
        """Truncate the content to fit within the specified maximum event length."""
        return truncate_content(content, max_chars=self.max_event_length)

    def get_condensation(self, view: View) -> Condensation:
        """Summarize middle of conversation using LLM while keeping initial/tail events."""
        head = view[: self.keep_first]
        target_size = self.max_size // 2
        events_from_tail = target_size - len(head) - 1
        summary_event = (
            view[self.keep_first]
            if isinstance(view[self.keep_first], AgentCondensationObservation)
            else AgentCondensationObservation("No events summarized")
        )
        forgotten_events = [
            event
            for event in view[self.keep_first: -events_from_tail]
            if not isinstance(event, AgentCondensationObservation)
        ]
        prompt = (
            'You are maintaining a context-aware state summary for an interactive agent.\nYou will be given a list of events corresponding to actions taken by the agent, and the most recent previous summary if one exists.\nIf the events being summarized contain ANY task-tracking, you MUST include a TASK_TRACKING section to maintain continuity.\nWhen referencing tasks make sure to preserve exact task IDs and statuses.\n\nTrack:\n\nUSER_CONTEXT: (Preserve essential user requirements, goals, and clarifications in concise form)\n\nTASK_TRACKING: {Active tasks, their IDs and statuses - PRESERVE TASK IDs}\n\nCOMPLETED: (Tasks completed so far, with brief results)\nPENDING: (Tasks that still need to be done)\nCURRENT_STATE: (Current variables, data structures, or relevant state)\n\nFor code-specific tasks, also include:\nCODE_STATE: {File paths, function signatures, data structures}\nTESTS: {Failing cases, error messages, outputs}\nCHANGES: {Code edits, variable updates}\nDEPS: {Dependencies, imports, external calls}\nVERSION_CONTROL_STATUS: {Repository state, current branch, PR status, commit history}\n\nPRIORITIZE:\n1. Adapt tracking format to match the actual task type\n2. Capture key user requirements and goals\n3. Distinguish between completed and pending tasks\n4. Keep all sections concise and relevant\n\nSKIP: Tracking irrelevant details for the current task type\n\nExample formats:\n\nFor code tasks:\nUSER_CONTEXT: Fix FITS card float representation issue\nCOMPLETED: Modified mod_float() in card.py, all tests passing\nPENDING: Create PR, update documentation\nCODE_STATE: mod_float() in card.py updated\nTESTS: test_format() passed\nCHANGES: str(val) replaces f"{val:.16G}"\nDEPS: None modified\nVERSION_CONTROL_STATUS: Branch: fix-float-precision, Latest commit: a1b2c3d\n\nFor other tasks:\nUSER_CONTEXT: Write 20 haikus based on coin flip results\nCOMPLETED: 15 haikus written for results [T,H,T,H,T,H,T,T,H,T,H,T,H,T,H]\nPENDING: 5 more haikus needed\nCURRENT_STATE: Last flip: Heads, Haiku count: 15/20'
            "\n\n"
        )
        summary_event_content = self._truncate(summary_event.message or "")
        prompt += f"<PREVIOUS SUMMARY>\n{summary_event_content}\n</PREVIOUS SUMMARY>\n"
        prompt += "\n\n"
        for forgotten_event in forgotten_events:
            event_content = self._truncate(str(forgotten_event))
            prompt += f"<EVENT id={forgotten_event.id}>\n{event_content}\n</EVENT>\n"
        prompt += "Now summarize the events using the rules above."
        messages = [Message(role="user", content=[TextContent(text=prompt)])]
        response = self.llm.completion(
            messages=self.llm.format_messages_for_llm(messages),
            extra_body={"metadata": self.llm_metadata},
        )
        summary = response.choices[0].message.content
        from forge.core.pydantic_compat import model_dump_with_options

        self.add_metadata("response", model_dump_with_options(response))
        self.add_metadata("metrics", self.llm.metrics.get())
        return Condensation(
            action=CondensationAction(
                forgotten_events_start_id=min(event.id for event in forgotten_events),
                forgotten_events_end_id=max(event.id for event in forgotten_events),
                summary=summary,
                summary_offset=self.keep_first,
            ),
        )

    def should_condense(self, view: View) -> bool:
        """Condense when total events exceed maximum allowed size."""
        return len(view) > self.max_size

    @classmethod
    def from_config(cls, config: "LLMSummarizingCondenserConfig", llm_registry: "LLMRegistry") -> "LLMSummarizingCondenser":
        """Instantiate summarizing condenser configured with registry-provided LLM."""
        llm_config = config.llm_config.model_copy()
        llm_config.caching_prompt = False
        llm = llm_registry.get_llm("condenser", llm_config)
        return LLMSummarizingCondenser(
            llm=llm,
            max_size=config.max_size,
            keep_first=config.keep_first,
            max_event_length=config.max_event_length,
        )


# Lazy registration to avoid circular imports
def _register_config():
    """Register LLMSummarizingCondenserConfig with the LLMSummarizingCondenser factory.
    
    Defers import of LLMSummarizingCondenserConfig to avoid circular dependency between
    condenser implementations and their configuration classes. Called at module load time
    to enable from_config() factory method to instantiate condensers from config objects.
    
    Side Effects:
        - Imports LLMSummarizingCondenserConfig from forge.core.config.condenser_config
        - Registers config class with LLMSummarizingCondenser.register_config() factory
    
    Notes:
        - Must be called at module level after LLMSummarizingCondenser class definition
        - Pattern reused across all condenser implementations
        - Avoids import-time circular dependency that would occur if config imported at top level

    """
    from forge.core.config.condenser_config import LLMSummarizingCondenserConfig
    LLMSummarizingCondenser.register_config(LLMSummarizingCondenserConfig)

_register_config()
