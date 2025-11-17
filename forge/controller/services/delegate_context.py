"""Delegate run-context contract helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from forge.controller.agent_controller import AgentController
    from forge.events import EventStream
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore


@dataclass(slots=True)
class DelegateRunContext:
    """Snapshot of the shared resources a delegate must inherit from its parent.

    Delegates today execute inside the parent controller's sandbox; they must
    reuse the same event stream, file store, metrics trackers, and iteration
    counters. Capturing the context up-front makes those invariants explicit
    and gives us a single choke point if/when we introduce isolated delegate
    runtimes in the future.
    """

    parent_id: str
    event_stream: "EventStream"
    conversation_stats: "ConversationStats | None"
    file_store: "FileStore | None"
    iteration_flag: Any | None
    inherits_runtime: bool = True

    @classmethod
    def capture(cls, controller: "AgentController") -> "DelegateRunContext":
        event_stream = getattr(controller, "event_stream", None)
        if event_stream is None:
            raise RuntimeError("Delegates require controller.event_stream to be set")
        state = getattr(controller, "state", None)
        iteration_flag = getattr(state, "iteration_flag", None) if state else None
        return cls(
            parent_id=getattr(controller, "id", "unknown"),
            event_stream=event_stream,
            conversation_stats=getattr(controller, "conversation_stats", None),
            file_store=getattr(controller, "file_store", None),
            iteration_flag=iteration_flag,
        )

    def attach(
        self, parent: "AgentController", delegate: "AgentController"
    ) -> None:
        """Validate + record the context on the delegate and parent."""

        self.validate(delegate)
        setattr(delegate, "delegate_run_context", self)
        setattr(parent, "delegate_run_context", self)

    def validate(self, delegate: "AgentController") -> None:
        """Ensure the delegate shares the parent's resources."""

        issues: list[str] = []
        if (
            self.inherits_runtime
            and getattr(delegate, "event_stream", None) is not self.event_stream
        ):
            issues.append("event_stream")
        if (
            self.conversation_stats is not None
            and getattr(delegate, "conversation_stats", None)
            is not self.conversation_stats
        ):
            issues.append("conversation_stats")
        if getattr(delegate, "file_store", None) is not self.file_store:
            issues.append("file_store")
        if self.iteration_flag is not None:
            delegate_state = getattr(delegate, "state", None)
            delegate_flag = getattr(delegate_state, "iteration_flag", None)
            if delegate_flag is not self.iteration_flag:
                issues.append("iteration_flag")
        if not getattr(delegate, "is_delegate", False):
            issues.append("delegate_flag")

        if issues:
            details = ", ".join(issues)
            logger.warning(
                "Delegate run context violation detected (%s); delegates are"
                " expected to reuse parent sandbox resources.",
                details,
            )
            raise RuntimeError(f"Delegate run context violated: {details}")


