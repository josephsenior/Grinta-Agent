"""Tests for base critic abstractions."""

from __future__ import annotations

from forge.critic.base import BaseCritic, CriticResult


class DummyCritic(BaseCritic):
    """Concrete implementation for exercising BaseCritic."""

    def __init__(self) -> None:
        self.invocations: list[tuple[list, str | None]] = []

    def evaluate(self, events: list, git_patch: str | None = None) -> CriticResult:
        """Record inputs and return deterministic success."""
        # Call the abstract method's default implementation to cover the base class stub.
        super().evaluate(events, git_patch)
        self.invocations.append((events, git_patch))
        return CriticResult(score=1.0, message="Looks good.")


def test_critic_result_success_thresholds() -> None:
    """CriticResult.success should respect the 0.5 success threshold."""
    assert CriticResult(score=0.5, message="pass").success is True
    assert CriticResult(score=0.49, message="fail").success is False


def test_base_critic_subclass_evaluate_records_inputs() -> None:
    """Concrete subclass should inherit the abstract protocol."""
    critic = DummyCritic()
    result = critic.evaluate(events=["event-1"], git_patch="diff")

    assert result.score == 1.0
    assert result.message == "Looks good."
    assert critic.invocations == [(["event-1"], "diff")]


