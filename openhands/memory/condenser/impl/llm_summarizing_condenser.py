from __future__ import annotations

from typing import TYPE_CHECKING

from openhands.core.config.condenser_config import LLMSummarizingCondenserConfig
from openhands.core.message import Message, TextContent
from openhands.events.action.agent import CondensationAction
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.events.serialization.event import truncate_content
from openhands.memory.condenser.condenser import Condensation, RollingCondenser
from openhands.memory.view import View

if TYPE_CHECKING:
    from openhands.llm.llm import LLM
    from openhands.llm.llm_registry import LLMRegistry


class LLMSummarizingCondenser(RollingCondenser):
    """A condenser that summarizes forgotten events.

    Maintains a condensed history and forgets old events when it grows too large,
    keeping a special summarization event after the prefix that summarizes all previous summarizations
    and newly forgotten events.
    """

    def __init__(self, llm: LLM, max_size: int = 100, keep_first: int = 1, max_event_length: int = 10000) -> None:
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
        from openhands.core.pydantic_compat import model_dump_with_options

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
        return len(view) > self.max_size

    @classmethod
    def from_config(cls, config: "LLMSummarizingCondenserConfig", llm_registry: "LLMRegistry") -> "LLMSummarizingCondenser":
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
    from openhands.core.config.condenser_config import LLMSummarizingCondenserConfig
    LLMSummarizingCondenser.register_config(LLMSummarizingCondenserConfig)

_register_config()
