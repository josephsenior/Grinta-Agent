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


def test_reflector_analyze_handles_invalid_json(
    context_playbook, trajectory, execution_result
):
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


def test_reflector_analyze_exception_path(
    context_playbook, trajectory, execution_result
):
    """Reflector should return a failure result when the LLM raises."""
    llm = Mock()
    llm.completion = Mock()

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    setattr(
        reflector,
        "_perform_reflection_iteration",
        Mock(side_effect=RuntimeError("iteration failure")),
    )
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


def test_curator_prompt_variants_cover_all_branches(context_playbook):
    """Formatting should adapt to appworld, metasop, and general task types."""
    llm = Mock()
    curator = ACECurator(llm=llm, context_playbook=context_playbook)
    insight = build_insight("Reasoning sample")

    appworld_prompt = curator._format_prompt_for_task_type(
        task_type="appworld",
        task_context="Solve the puzzle",
        playbook_content="* bullet",
        insights_text="summarized insights",
        insights=[insight],
        role=None,
        expected_outcome=None,
    )
    metasop_prompt = curator._format_prompt_for_task_type(
        task_type="metasop",
        task_context="Implement login",
        playbook_content="* bullet",
        insights_text="insights payload",
        insights=[insight],
        role="engineer",
        expected_outcome="Working feature",
    )
    general_prompt = curator._format_prompt_for_task_type(
        task_type="unknown",
        task_context="General task",
        playbook_content="* bullet",
        insights_text="insights payload",
        insights=[insight],
        role=None,
        expected_outcome=None,
    )

    assert "Task Context" in appworld_prompt
    assert "Role: engineer" in metasop_prompt
    assert '"operations"' in general_prompt


def test_curator_parses_wrapped_json_and_unknown_section(context_playbook):
    """Curator should recover JSON inside wrapper text and default unknown sections."""
    llm = Mock()
    llm.completion = Mock(
        return_value=make_response(
            content=(
                'Noise before {"reasoning": "Valid reasoning", '
                '"operations": [{"type": "ADD", "section": "not-a-section", '
                '"content": "Document deployment runbooks."}] } trailing text'
            ),
            total_tokens=42,
        )
    )

    curator = ACECurator(llm=llm, context_playbook=context_playbook)
    insight = build_insight("Investigate incident response gaps")

    result = curator.curate(
        insights=[insight],
        current_playbook=context_playbook,
        task_context="Strengthen on-call readiness",
        task_type="metasop",
        role="SRE",
        expected_outcome="Actionable runbook",
    )

    assert result.success is True
    assert len(result.delta_updates) == 1
    assert result.delta_updates[0].section == BulletSection.STRATEGIES_AND_HARD_RULES


def test_curator_convert_to_delta_updates_handles_unknown_and_blank(context_playbook):
    """Operations with unknown sections should fallback or be skipped."""
    curator = ACECurator(llm=Mock(), context_playbook=context_playbook)
    operations = [
        {
            "type": "ADD",
            "section": "unknown_section",
            "content": "Adopt blue/green deploys",
        },
        {"type": "ADD", "section": "strategies_and_hard_rules", "content": " "},
    ]

    updates = curator._convert_to_delta_updates(operations)

    assert len(updates) == 1
    assert updates[0].section == BulletSection.STRATEGIES_AND_HARD_RULES
    assert updates[0].content == "Adopt blue/green deploys"


def test_curator_extract_response_text_variants():
    """Response extraction should support string, list, and empty choices."""
    response_list = make_response(
        content=[
            {"text": "part-1"},
            "part-2",
        ]
    )
    response_empty = SimpleNamespace(choices=[], usage=None)
    response_no_message = SimpleNamespace(choices=[SimpleNamespace(message=None)])

    assert ACECurator._extract_response_text(response_list) == "part-1part-2"
    assert ACECurator._extract_response_text(response_empty) == ""
    assert ACECurator._extract_response_text(response_no_message) == ""


def test_curator_extract_total_tokens_fallback_estimation():
    """Token extraction should fallback when total count is unavailable."""
    response = SimpleNamespace(usage={"prompt_tokens": 10})
    estimated = ACECurator._extract_total_tokens(
        response,
        prompt="one two three",
        text="four five",
    )

    assert estimated == 5


def test_curator_get_metrics_without_curations(context_playbook):
    """Metrics should be returned unchanged when no curations ran."""
    curator = ACECurator(llm=Mock(), context_playbook=context_playbook)
    metrics = curator.get_metrics()

    assert metrics["total_curations"] == 0
    assert "success_rate" not in metrics


def test_curator_format_insights_and_redundancy_shortcuts(context_playbook):
    """Formatting and redundancy helpers should handle edge cases."""
    curator = ACECurator(llm=Mock(), context_playbook=context_playbook)
    no_insights_text = curator._format_insights_for_curation([])
    redundancy_removed = curator._check_and_remove_redundancy([], context_playbook)

    assert no_insights_text == "No insights available."
    assert redundancy_removed == 0


def test_curator_curate_batch_defaults(context_playbook, monkeypatch):
    """curate_batch should default task types and aggregate results."""
    curator = ACECurator(llm=Mock(), context_playbook=context_playbook)

    dummy_result = ACECurationResult(
        delta_updates=[],
        success=True,
        redundancy_removed=0,
        processing_time=0.1,
        tokens_used=1,
    )

    calls = []

    def fake_curate(
        insights,
        current_playbook,
        task_context,
        task_type,
        role=None,
        expected_outcome=None,
    ):
        calls.append((task_context, task_type))
        return dummy_result

    monkeypatch.setattr(curator, "curate", fake_curate)

    batch_results = curator.curate_batch(
        insights_batch=[[build_insight("a")], [build_insight("b")]],
        current_playbook=context_playbook,
        task_contexts=["ctx-a", "ctx-b"],
    )

    assert batch_results == [dummy_result, dummy_result]
    assert calls == [("ctx-a", "general"), ("ctx-b", "general")]


def test_reflector_perform_iteration_covers_branches(
    context_playbook, trajectory, execution_result
):
    """_perform_reflection_iteration should support task-specific formatting and JSON recovery."""
    llm = Mock()
    llm.completion = Mock(
        return_value=make_response(
            content=(
                "prefix {"
                '"reasoning": "Reasoning", '
                '"error_identification": "Mismatch", '
                '"root_cause_analysis": "Root cause", '
                '"correct_approach": "Apply fix", '
                '"key_insight": "Capture regression cases", '
                '"bullet_tags": []'
                "} suffix"
            ),
            total_tokens=64,
        )
    )

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    execution_result.metadata.setdefault("test_report", "All tests")

    appworld_insight = reflector._perform_reflection_iteration(
        trajectory=trajectory,
        execution_result=execution_result,
        ground_truth="print('truth')",
        playbook_content="Existing playbook",
        task_type="appworld",
        role=None,
        iteration=0,
    )
    metasop_insight = reflector._perform_reflection_iteration(
        trajectory=trajectory,
        execution_result=execution_result,
        ground_truth=None,
        playbook_content="Existing playbook",
        task_type="metasop",
        role="architect",
        iteration=1,
    )

    assert appworld_insight is not None
    assert metasop_insight is not None
    assert appworld_insight.key_insight == "Capture regression cases"
    assert metasop_insight.key_insight == "Capture regression cases"


def test_reflector_analyze_runs_multiple_iterations(
    context_playbook, trajectory, execution_result
):
    """Analyze should iterate when confidence is low and update metrics."""
    llm = Mock()
    llm.completion = Mock(
        side_effect=[
            make_response(
                content=(
                    '{"reasoning": "", "error_identification": "", "root_cause_analysis": "", '
                    '"correct_approach": "", "key_insight": "Add tests", '
                    '"bullet_tags": [{"id": "ctx-00000", "tag": "helpful"}]}'
                ),
                total_tokens=50,
            ),
            make_response(
                content=(
                    '{"reasoning": "Deep reasoning", "error_identification": "Bug", '
                    '"root_cause_analysis": "Flaw", "correct_approach": "Fix", '
                    '"key_insight": "Document learnings", '
                    '"bullet_tags": [{"id": "ctx-00000", "tag": "helpful"}]}'
                ),
                total_tokens=60,
            ),
        ]
    )

    reflector = ACEReflector(llm=llm, context_playbook=context_playbook)
    result = reflector.analyze(
        trajectory=trajectory,
        execution_result=execution_result,
        used_bullet_ids=["ctx-00000"],
        task_type="general",
        max_iterations=2,
    )

    assert result.success is True
    assert reflector.reflection_metrics["iterative_refinements"] == 1
    assert context_playbook.bullets["ctx-00000"].helpful_count >= 1


def test_reflector_helpers_cover_edge_cases(context_playbook):
    """Helper utilities should handle empty and edge scenarios."""
    reflector = ACEReflector(llm=Mock(), context_playbook=context_playbook)

    # _get_playbook_content_for_bullets empty lookup
    assert (
        reflector._get_playbook_content_for_bullets([])
        == "No playbook content available."
    )

    # _should_continue_iteration branches
    low_confidence = ACEInsight(
        reasoning="",
        error_identification="",
        root_cause_analysis="",
        correct_approach="",
        key_insight="Add tests",
        bullet_tags=[],
        success=True,
        confidence=0.2,
    )
    assert (
        reflector._should_continue_iteration(
            low_confidence, iteration=0, max_iterations=3
        )
        is True
    )

    high_confidence = ACEInsight(
        reasoning="Reasoning",
        error_identification="Issue",
        root_cause_analysis="Cause",
        correct_approach="Approach",
        key_insight="Keep change",
        bullet_tags=[],
        success=True,
        confidence=0.9,
    )
    assert (
        reflector._should_continue_iteration(
            high_confidence, iteration=1, max_iterations=3
        )
        is False
    )

    near_max_iteration = ACEInsight(
        reasoning="",
        error_identification="",
        root_cause_analysis="",
        correct_approach="",
        key_insight="",
        bullet_tags=[],
        success=True,
        confidence=0.1,
    )
    assert (
        reflector._should_continue_iteration(
            near_max_iteration, iteration=2, max_iterations=3
        )
        is False
    )

    # _update_playbook_content_for_iteration
    updated = reflector._update_playbook_content_for_iteration(
        "Playbook", low_confidence
    )
    assert "NEW INSIGHT FROM ITERATION" in updated

    # _calculate_overall_confidence empty case
    assert reflector._calculate_overall_confidence([]) == 0.0

    # _extract_response_text variants
    response_list = make_response(content=[{"text": "part-a"}, "part-b"])
    response_no_choices = SimpleNamespace(choices=None)
    assert ACEReflector._extract_response_text(response_list) == "part-apart-b"
    assert ACEReflector._extract_response_text(response_no_choices) == ""

    # get_metrics with no reflections
    assert reflector.get_metrics()["total_reflections"] == 0
