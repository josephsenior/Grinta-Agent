"""Budget and bandwidth monitoring utilities for MetaSOP."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from forge.core.logger import forge_logger as logger

from .metrics import record_event

if TYPE_CHECKING:
    from forge.metasop.models import SopStep, StepResult
    from forge.metasop.event_service import MetaSOPEVentService


class BudgetStatus(str, Enum):
    """Represents current budget state after an update."""

    OK = "ok"
    SOFT_LIMIT = "soft_limit"
    HARD_LIMIT = "hard_limit"


class BudgetMonitorService:
    """Tracks token consumption vs. configured soft/hard budgets."""

    def __init__(
        self,
        event_service: "MetaSOPEVentService",
        *,
        default_soft_limit: int = 0,
        default_hard_limit: int = 0,
    ) -> None:
        self._event_service = event_service
        self._default_soft_limit = max(0, int(default_soft_limit))
        self._default_hard_limit = max(0, int(default_hard_limit))

        self.soft_limit = self._default_soft_limit
        self.hard_limit = self._default_hard_limit
        self.consumed_tokens = 0
        self._soft_warning_emitted = False
        self._hard_limit_reached = False

    # ------------------------------------------------------------------ #
    # Lifecycle helpers
    # ------------------------------------------------------------------ #
    def configure_run(self, soft_limit: int, hard_limit: int) -> None:
        """Configure limits for the upcoming orchestration run."""

        self.soft_limit = max(0, int(soft_limit or self._default_soft_limit))
        self.hard_limit = max(0, int(hard_limit or self._default_hard_limit))
        self.reset()

    def reset(self) -> None:
        """Reset counters for a new orchestration run."""

        self.consumed_tokens = 0
        self._soft_warning_emitted = False
        self._hard_limit_reached = False

    # ------------------------------------------------------------------ #
    # Recording helpers
    # ------------------------------------------------------------------ #
    def record_step_result(
        self, step: "SopStep", result: "StepResult"
    ) -> BudgetStatus:
        """Record token usage for a step result and return current status."""

        tokens = self._extract_tokens(result)
        if tokens <= 0:
            return BudgetStatus.OK

        self.consumed_tokens += tokens
        status = BudgetStatus.OK

        record_event(
            {
                "metric": "budget_update",
                "step_id": getattr(step, "id", None),
                "role": getattr(step, "role", None),
                "tokens": tokens,
                "consumed_tokens": self.consumed_tokens,
                "soft_limit": self.soft_limit or None,
                "hard_limit": self.hard_limit or None,
            }
        )

        if self.hard_limit and self.consumed_tokens >= self.hard_limit:
            status = BudgetStatus.HARD_LIMIT
            if not self._hard_limit_reached:
                self._emit_budget_event("budget_hard_limit_exceeded", step)
                self._hard_limit_reached = True
        elif (
            self.soft_limit
            and self.consumed_tokens >= self.soft_limit
            and not self._soft_warning_emitted
        ):
            status = BudgetStatus.SOFT_LIMIT
            self._soft_warning_emitted = True
            self._emit_budget_event("budget_soft_limit_reached", step)

        return status

    # ------------------------------------------------------------------ #
    # State helpers
    # ------------------------------------------------------------------ #
    @property
    def hard_limit_reached(self) -> bool:
        return self._hard_limit_reached

    def remaining_soft_budget(self) -> int | None:
        if not self.soft_limit:
            return None
        return max(0, self.soft_limit - self.consumed_tokens)

    def remaining_hard_budget(self) -> int | None:
        if not self.hard_limit:
            return None
        return max(0, self.hard_limit - self.consumed_tokens)

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    def _emit_budget_event(self, event_type: str, step: "SopStep") -> None:
        payload = {
            "type": event_type,
            "step_id": getattr(step, "id", None),
            "role": getattr(step, "role", None),
            "consumed_tokens": self.consumed_tokens,
            "soft_limit": self.soft_limit or None,
            "hard_limit": self.hard_limit or None,
        }
        try:
            self._event_service.emit_event(payload)
        except Exception:  # pragma: no cover - defensive logging
            logger.debug("Failed to emit budget event", exc_info=True)

    def _extract_tokens(self, result: "StepResult") -> int:
        """Extract token usage from step result fallbacks."""

        if tokens := self._tokens_from_trace(result):
            return tokens
        if tokens := self._tokens_from_artifact(result):
            return tokens
        if tokens := self._tokens_from_cost(result):
            return tokens
        return 0

    def _tokens_from_trace(self, result: "StepResult") -> int | None:
        trace = getattr(result, "trace", None)
        if not trace:
            return None
        total = getattr(trace, "total_tokens", None)
        if total:
            return int(total)
        prompt = getattr(trace, "prompt_tokens", 0) or 0
        completion = getattr(trace, "completion_tokens", 0) or 0
        combined = prompt + completion
        return int(combined) if combined else None

    def _tokens_from_artifact(self, result: "StepResult") -> int | None:
        artifact = getattr(result, "artifact", None)
        content = getattr(artifact, "content", None)
        if not (artifact and isinstance(content, dict)):
            return None
        meta: dict[str, Any] = content.get("__trace_meta__") or {}
        total = meta.get("total_tokens")
        if total:
            return int(total)
        prompt = meta.get("prompt_tokens") or 0
        completion = meta.get("completion_tokens") or 0
        combined = prompt + completion
        return int(combined) if combined else None

    @staticmethod
    def _tokens_from_cost(result: "StepResult") -> int | None:
        token_cost = getattr(result, "token_cost", None)
        if isinstance(token_cost, (int, float)):
            return int(token_cost)
        return None


__all__ = ["BudgetMonitorService", "BudgetStatus"]

