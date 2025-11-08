"""Tests for ACEReflector and ACECurator."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from forge.metasop.ace.context_playbook import BulletSection, ContextPlaybook
from forge.metasop.ace.curator import ACECurator
from forge.metasop.ace.models import (
    ACECurationResult,
    ACEExecutionResult,
    ACEInsight,
    ACETrajectory,
)
from forge.metasop.ace.reflector import ACEReflector


def make_response(content, total_tokens=80):
    """Create a dummy completion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(total_tokens=total_tokens),
    )


@pytest.fixture
def context_playbook():
    playbook = ContextPlaybook(enable_grow_and_refine=False)
    playbook.add_bullet(
        content="Always validate user input for authentication flows.",
        section=BulletSection.STRATEGIES_AND_HARD_RULES,
        bullet_id="ctx-00000",
    )
    return playbook


@pytest.fixture
def trajectory():
    return ACETrajectory(
        content="Detailed reasoning steps for the task execution.",
        task_type="metasop",
        used_bullet_ids=["ctx-00000"],
        playbook_content="Existing playbook content",
        generation_metadata={"task": "Implement login"},
    )


@pytest.fixture
def execution_result():
    return ACEExecutionResult(
        success=True,
        output="Execution succeeded with valid output.",
        error=None,
        execution_time=0.4,
        tokens_used=25,
        cost=0.01,
        metadata={"expected_outcome": "Working login flow"},
    )


def test_reflector_analyze_success(context_playbook, trajectory, execution_result):
    """Reflector should extract insights and update playbook metrics."""
    llm = Mock()
    llm.completion = Mock(
        return_value=make_response(
            content='{"reasoning": "Deep reasoning", '
            '"error_identification": "None", '
            '"root_cause_analysis": "N/A", '
            '"correct_approach": "Continue current approach", '
            '"key_insight": "Document lessons learned", '
            '"bullet_tags": [{"id": "ctx-00000", "tag": "helpful"}]}',
        )
    )

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    result = reflector.analyze(
        trajectory=trajectory,
        execution_result=execution_result,
        ground_truth=None,
        used_bullet_ids=["ctx-00000"],
        task_type="metasop",
        role="engineer",
        max_iterations=2,
    )

    assert result.success is True
    assert len(result.insights) == 1
    assert context_playbook.bullets["ctx-00000"].helpful_count == 1

    metrics = reflector.get_metrics()
    assert metrics["total_reflections"] == 1
    assert metrics["iterative_refinements"] >= 0
    assert metrics["success_rate"] == 1.0


def test_reflector_analyze_handles_invalid_json(context_playbook, trajectory, execution_result):
    """Reflector should tolerate malformed responses without raising."""
    llm = Mock()
    llm.completion = Mock(return_value=make_response(content="invalid-response"))

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    result = reflector.analyze(
        trajectory=trajectory,
        execution_result=execution_result,
        used_bullet_ids=["ctx-00000"],
        task_type="general",
        max_iterations=1,
    )

    assert result.success is False
    assert result.insights == []


def test_reflector_analyze_exception_path(context_playbook, trajectory, execution_result):
    """Reflector should return a failure result when the LLM raises."""
    llm = Mock()
    llm.completion = Mock()

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    reflector._perform_reflection_iteration = Mock(side_effect=RuntimeError("iteration failure"))
    result = reflector.analyze(
        trajectory=trajectory,
        execution_result=execution_result,
        used_bullet_ids=["ctx-00000"],
        task_type="general",
        max_iterations=1,
    )

    assert result.success is False
    assert result.tokens_used == 0


def build_insight(reasoning: str) -> ACEInsight:
    """Helper to create ACEInsight instances for curator tests."""
    return ACEInsight(
        reasoning=reasoning,
        error_identification="",
        root_cause_analysis="",
        correct_approach="Apply standard solution",
        key_insight="Capture reusable knowledge",
        bullet_tags=[{"id": "ctx-00000", "tag": "helpful"}],
        success=True,
        confidence=0.8,
    )


def test_curator_curate_success(context_playbook):
    """Curator should convert insights into delta updates while avoiding redundancy."""
    llm = Mock()
    llm.completion = Mock(
        return_value=make_response(
            content='{"reasoning": "Add new guidance", "operations": ['
            '{"type": "ADD", "section": "strategies_and_hard_rules", "content": "Use feature flags for risky deployments."},'
            '{"type": "ADD", "section": "strategies_and_hard_rules", "content": "Always validate user input for authentication flows."}'
            "]}",
            total_tokens=90,
        )
    )

    curator = ACECurator(llm=llm, context_playbook=context_playbook)
    insight = build_insight("Refined execution walkthrough")

    result = curator.curate(
        insights=[insight],
        current_playbook=context_playbook,
        task_context="Implement feature rollout",
        task_type="general",
    )

    assert result.success is True
    assert len(result.delta_updates) == 1  # Redundant entry removed
    assert result.redundancy_removed >= 1

    metrics = curator.curation_metrics
    assert metrics["total_curations"] == 1
    assert metrics["successful_curations"] == 1
    assert metrics["delta_updates_generated"] == 1
    assert metrics["total_tokens"] >= result.tokens_used


def test_curator_handles_empty_insights(context_playbook):
    """Curator should short-circuit when no insights are provided."""
    llm = Mock()
    curator = ACECurator(llm=llm, context_playbook=context_playbook)

    result = curator.curate(
        insights=[],
        current_playbook=context_playbook,
        task_context="No insights task",
    )

    assert isinstance(result, ACECurationResult)
    assert result.success is True
    assert result.delta_updates == []
    assert result.tokens_used == 0


def test_curator_curate_parsing_failure(context_playbook):
    """Curator should return a failure result when JSON parsing fails."""
    llm = Mock()
    llm.completion = Mock(return_value=make_response(content="not-json"))

    curator = ACECurator(llm=llm, context_playbook=context_playbook)
    insight = build_insight("Insight requiring parsing fallback")

    result = curator.curate(
        insights=[insight],
        current_playbook=context_playbook,
        task_context="Parsing failure task",
        task_type="general",
    )

    assert result.success is False
    assert result.delta_updates == []


def test_curator_curate_exception(context_playbook):
    """Curator should handle unexpected exceptions from the LLM."""
    llm = Mock()
    llm.completion = Mock(side_effect=RuntimeError("LLM down"))

    curator = ACECurator(llm=llm, context_playbook=context_playbook)
    insight = build_insight("Exception scenario")

    result = curator.curate(
        insights=[insight],
        current_playbook=context_playbook,
        task_context="Exception task",
        task_type="general",
    )

    assert result.success is False
    assert result.tokens_used == 0

