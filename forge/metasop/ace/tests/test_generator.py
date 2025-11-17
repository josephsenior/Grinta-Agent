"""Tests for ACEGenerator."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from forge.metasop.ace.context_playbook import BulletSection, ContextPlaybook
from forge.metasop.ace.generator import ACEGenerator
from forge.metasop.ace.models import ACEGenerationResult, ACETrajectory


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

    result = generator.generate(
        query="Validate user input for login flow", task_type="general"
    )

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
    initial_result = generator.generate(
        query="Validate user input for login", task_type="metasop", role="engineer"
    )

    # Mark the bullet as helpful to influence feedback prompt creation
    playbook.update_bullet(bullet_id="ctx-00000", helpful=True)

    feedback_result = generator.generate_with_feedback(
        query="Refined task",
        previous_result=initial_result,
        task_type="metasop",
        role="engineer",
    )

    assert feedback_result.success is True
    assert (
        feedback_result.trajectory.generation_metadata["feedback_incorporated"] is True
    )
    assert "Improved attempt" in feedback_result.trajectory.content

    assert feedback_result.tokens_used == 55

    metrics = generator.get_metrics()
    assert metrics["total_generations"] == 1
    assert metrics["successful_generations"] == 1


def test_generate_retry_then_success(monkeypatch, playbook):
    """Generator should retry after transient failure before succeeding."""
    llm = Mock()
    llm.completion = Mock(
        side_effect=[
            RuntimeError("temporary outage"),
            make_response("Recovered content"),
        ]
    )
    monkeypatch.setattr("time.sleep", lambda _: None)

    generator = ACEGenerator(llm=llm, context_playbook=playbook)
    result = generator.generate(
        query="Retry scenario", task_type="general", max_retries=2
    )

    assert result.success is True
    assert result.trajectory.content == "Recovered content"
    assert llm.completion.call_count == 2


def test_create_feedback_prompt_handles_helpful_and_harmful(playbook):
    """Feedback prompt should surface helpful and harmful bullets and respect role."""
    generator = ACEGenerator(llm=Mock(), context_playbook=playbook)
    bullet = playbook.bullets["ctx-00000"]
    bullet.helpful_count = 2
    bullet.harmful_count = 1
    helpful_prompt = generator._create_feedback_prompt(
        query="Task",
        helpful_bullets=[bullet],
        harmful_bullets=[],
        task_type="metasop",
        role="qa",
    )
    bullet.helpful_count = 0
    bullet.harmful_count = 3
    harmful_prompt = generator._create_feedback_prompt(
        query="Task",
        helpful_bullets=[],
        harmful_bullets=[bullet],
        task_type="general",
        role=None,
    )

    assert "HELPFUL STRATEGIES" in helpful_prompt
    assert "expert qa" in helpful_prompt
    assert "STRATEGIES TO AVOID" in harmful_prompt


def test_generate_with_feedback_failure_path(monkeypatch, playbook):
    """generate_with_feedback should surface failures and retain retry count."""
    generator = ACEGenerator(llm=Mock(), context_playbook=playbook)
    bullet = playbook.bullets["ctx-00000"]
    bullet.harmful_count = 5
    previous = ACEGenerationResult(
        trajectory=ACETrajectory(
            content="Prior attempt",
            task_type="general",
            used_bullet_ids=["ctx-00000"],
            playbook_content="",
            generation_metadata={},
        ),
        success=False,
        processing_time=0.1,
        tokens_used=10,
        retries=0,
    )
    monkeypatch.setattr(
        generator, "_generate_with_retries", Mock(side_effect=RuntimeError("boom"))
    )

    result = generator.generate_with_feedback(
        query="Retry with feedback",
        previous_result=previous,
        task_type="general",
        role=None,
    )

    assert result.success is False
    assert result.retries == 3


def test_generator_extract_total_tokens_fallback():
    """_extract_total_tokens should approximate counts when totals missing."""
    response = SimpleNamespace(usage={"prompt_tokens": 12})
    estimate = ACEGenerator._extract_total_tokens(
        response,
        prompt="one two",
        text="three four five",
    )
    assert estimate == 5


def test_generator_get_metrics_without_generations(playbook):
    """Metrics should remain pristine prior to any generation."""
    generator = ACEGenerator(llm=Mock(), context_playbook=playbook)
    metrics = generator.get_metrics()

    assert metrics["total_generations"] == 0
    assert "success_rate" not in metrics
