"""Tests for the AgentFinishedCritic implementation."""

from __future__ import annotations

import pytest

from forge.critic.finish_critic import AgentFinishedCritic
from forge.events.action.agent import AgentFinishAction, AgentThinkAction


def make_events(*actions) -> list:
    """Helper to convert action inputs into event lists."""
    return list(actions)


@pytest.mark.parametrize(
    ("actions", "git_patch", "expected"),
    [
        (
            make_events(AgentThinkAction(thought="Working"), AgentFinishAction(final_thought="Done")),
            None,
            ("Agent finished.", 1),
        ),
        (
            make_events(AgentThinkAction(thought="Still running")),
            None,
            ("Agent did not finish.", 0),
        ),
        (
            make_events(AgentThinkAction(thought="Irrelevant")),
            "",
            ("Git patch is empty.", 0),
        ),
    ],
)
def test_agent_finished_critic_evaluate_returns_expected(actions, git_patch, expected) -> None:
    """Evaluate should score finish state and optional git patch correctly."""
    critic = AgentFinishedCritic()

    result = critic.evaluate(events=actions, git_patch=git_patch)

    expected_message, expected_score = expected
    assert result.message == expected_message
    assert result.score == expected_score


def test_agent_finished_critic_handles_no_action_events() -> None:
    """When no action events exist the critic should mark the run as unfinished."""
    critic = AgentFinishedCritic()
    result = critic.evaluate(events=[], git_patch=None)

    assert result.score == 0
    assert result.message == "Agent did not finish."


