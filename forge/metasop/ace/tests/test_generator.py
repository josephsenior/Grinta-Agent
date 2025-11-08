"""Tests for ACEGenerator."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from forge.metasop.ace.context_playbook import BulletSection, ContextPlaybook
from forge.metasop.ace.generator import ACEGenerator


def make_response(content, total_tokens=42):
    """Create a dummy completion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(total_tokens=total_tokens),
    )


@pytest.fixture
def playbook():
    playbook = ContextPlaybook(enable_grow_and_refine=False)
    playbook.add_bullet(
        content="Prioritize security and validate all user input.",
        section=BulletSection.STRATEGIES_AND_HARD_RULES,
        bullet_id="ctx-00000",
    )
    return playbook


def test_generate_success(playbook):
    """Generator should produce a successful trajectory with metrics updates."""
    llm = Mock()
    llm.completion = Mock(return_value=make_response("Step 1\nStep 2"))

    generator = ACEGenerator(llm=llm, context_playbook=playbook)

    result = generator.generate(query="Validate user input for login flow", task_type="general")

    assert result.success is True
    assert result.trajectory.content.startswith("Step 1")
    assert result.trajectory.used_bullet_ids == ["ctx-00000"]

    metrics = generator.get_metrics()
    assert metrics["total_generations"] == 1
    assert metrics["successful_generations"] == 1
    assert metrics["total_tokens"] > 0


def test_generate_failure_after_retries(playbook):
    """Generator should handle repeated LLM failures gracefully."""
    llm = Mock()
    llm.completion = Mock(side_effect=RuntimeError("LLM failure"))

    generator = ACEGenerator(llm=llm, context_playbook=playbook)

    result = generator.generate(query="Cause failure", task_type="general")

    assert result.success is False
    assert result.trajectory.content == ""
    assert result.retries == 3

    metrics = generator.get_metrics()
    assert metrics["total_generations"] == 1
    assert metrics["failed_generations"] == 1


def test_generate_with_feedback(playbook):
    """Generator should incorporate feedback from previous attempts."""
    llm = Mock()
    llm.completion = Mock(
        side_effect=[
            make_response("Initial attempt content."),
            make_response(
                [
                    {"text": "Improved "},
                    {"text": "attempt with feedback."},
                ],
                total_tokens=55,
            ),
        ]
    )

    generator = ACEGenerator(llm=llm, context_playbook=playbook)
    initial_result = generator.generate(query="Validate user input for login", task_type="metasop", role="engineer")

    # Mark the bullet as helpful to influence feedback prompt creation
    playbook.update_bullet(bullet_id="ctx-00000", helpful=True)

    feedback_result = generator.generate_with_feedback(
        query="Refined task",
        previous_result=initial_result,
        task_type="metasop",
        role="engineer",
    )

    assert feedback_result.success is True
    assert feedback_result.trajectory.generation_metadata["feedback_incorporated"] is True
    assert "Improved attempt" in feedback_result.trajectory.content

    assert feedback_result.tokens_used == 55

    metrics = generator.get_metrics()
    assert metrics["total_generations"] == 1
    assert metrics["successful_generations"] == 1

