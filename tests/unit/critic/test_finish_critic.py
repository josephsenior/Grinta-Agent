"""Tests for the basic critic implementations."""

from forge.critic.base import CriticResult
from forge.critic.finish_critic import AgentFinishedCritic
from forge.events.action.agent import AgentFinishAction, AgentThinkAction


def test_critic_result_success_threshold() -> None:
    """Boundary checks around the success property."""
    assert CriticResult(score=0.5, message="pass").success
    assert not CriticResult(score=0.49, message="fail").success


def test_agent_finished_critic_reports_success() -> None:
    """When the conversation ends with AgentFinishAction we get a perfect score."""
    critic = AgentFinishedCritic()
    events = [
        AgentThinkAction(thought="Working through the problem."),
        AgentFinishAction(final_thought="All set!"),
    ]

    result = critic.evaluate(events)

    assert result.score == 1
    assert result.message == "Agent finished."


def test_agent_finished_critic_rejects_empty_patch() -> None:
    """Empty git patch should short-circuit with score 0."""
    critic = AgentFinishedCritic()
    events = [AgentFinishAction(final_thought="All set!")]

    result = critic.evaluate(events, git_patch="   ")

    assert result.score == 0
    assert result.message == "Git patch is empty."


def test_agent_finished_critic_detects_missing_finish() -> None:
    """When the final meaningful event is not a finish action, score should be 0."""
    critic = AgentFinishedCritic()
    events = [AgentThinkAction(thought="Still working...")]

    result = critic.evaluate(events)

    assert result.score == 0
    assert result.message == "Agent did not finish."

