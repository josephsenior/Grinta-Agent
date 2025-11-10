import pytest
from datetime import datetime


def test_decision_tracking_and_anchors(tmp_path):
    from forge.memory.enhanced_context_manager import (
        DecisionType,
        EnhancedContextManager,
    )

    manager = EnhancedContextManager(short_term_window=2, working_memory_size=3, long_term_max_size=4)
    decision = manager.track_decision(
        description="Use PostgreSQL",
        rationale="Better relational support",
        decision_type=DecisionType.TECHNICAL,
        context="database discussion",
        alternatives=["SQLite"],
        confidence=0.8,
        anchor=True,
    )
    assert decision.decision_id in manager.decisions
    assert manager.anchors

    anchor = manager.create_anchor("Keep migrations", "requirement", importance=0.9)
    retrieved = manager.get_anchor(anchor.anchor_id)
    assert retrieved.access_count == 1
    assert manager.get_all_anchors(min_importance=0.8)

    manager.add_to_short_term({"content": "step1", "has_anchor": True})
    manager.add_to_short_term({"content": "step2"})
    manager.add_to_short_term({"content": "step3", "has_decision": True, "access_count": 5})

    short = manager.get_all_memory()["short_term"]
    assert len(short) == 2  # one promoted

    manager.add_to_working_memory({"content": "recent", "has_anchor": True})
    manager.add_to_long_term({"content": "historical"})
    stats = manager.get_stats()
    assert stats["total_decisions"] == 1

    for tier in manager.get_all_memory().values():
        for item in tier:
            if "timestamp" in item:
                item["timestamp"] = "2025-01-01T00:00:00"

    file_path = tmp_path / "memory.json"
    manager.save_to_file(str(file_path))

    new_manager = EnhancedContextManager()
    new_manager.load_from_file(str(file_path))
    assert new_manager.decisions
    assert new_manager.anchors


def test_contradiction_detection_and_context():
    from forge.memory.enhanced_context_manager import EnhancedContextManager, DecisionType

    manager = EnhancedContextManager()
    manager.track_decision(
        description="Enable feature X",
        rationale="user request",
        decision_type=DecisionType.FUNCTIONAL,
        context="planning",
    )
    manager.create_anchor("Feature X must remain enabled", "constraint", importance=0.9)

    contradiction, description = manager.detect_contradiction(
        "We should not enable feature X because feature X is problematic",
        "planning",
    )
    assert contradiction is False

    manager.add_to_short_term({"detail": "First", "has_anchor": True})
    manager.add_to_working_memory({"detail": "Second"})
    manager.add_to_long_term({"detail": "Third"})

    for tier in manager.get_all_memory().values():
        for item in tier:
            if "timestamp" in item:
                item["timestamp"] = "2025-01-01T00:00:00"

    context = manager.get_relevant_context("feature")
    assert context["anchors"]
    assert context["decisions"]
    assert isinstance(context["memory"], list)


def test_decision_queries_and_search():
    from forge.memory.enhanced_context_manager import DecisionType, EnhancedContextManager

    manager = EnhancedContextManager()
    decision = manager.track_decision(
        description="Adopt REST API",
        rationale="Consistency",
        decision_type=DecisionType.ARCHITECTURAL,
        context="api design",
    )
    assert manager.get_decision(decision.decision_id) is decision
    assert manager.get_decisions_by_type(DecisionType.ARCHITECTURAL)[0] is decision
    assert manager.search_decisions("rest")


def test_anchor_filtering_and_memory_search():
    from forge.memory.enhanced_context_manager import EnhancedContextManager

    manager = EnhancedContextManager(short_term_window=1, working_memory_size=1, long_term_max_size=2)
    anchor = manager.create_anchor("Critical requirement", "requirement", importance=0.6)
    assert manager.get_anchors_by_category("requirement")[0] is anchor
    manager.short_term_memory = [{"message": "short", "timestamp": "2025-01-01T00:00:00", "tier": "short_term"}]
    manager.working_memory = [{"message": "working", "tier": "working"}]
    manager.long_term_memory = [{"message": "long", "timestamp": "2025-01-01T00:00:00", "access_count": 0}]
    results = manager.search_memory("message")
    assert results


def test_promote_and_cleanup_long_term():
    from forge.memory.enhanced_context_manager import EnhancedContextManager

    manager = EnhancedContextManager(working_memory_size=2, long_term_max_size=2)
    manager.working_memory = [
        {"has_anchor": True, "access_count": 5},
        {"has_decision": True},
        {"access_count": 10},
    ]
    manager._promote_to_long_term()
    assert manager.long_term_memory
    assert manager.stats["promotions_to_long_term"] > 0

    manager.long_term_memory.extend(
        [
            {"timestamp": datetime.now(), "access_count": 0},
            {"timestamp": datetime.now(), "access_count": 1},
        ]
    )
    manager._cleanup_long_term()
    assert len(manager.long_term_memory) >= 1


def test_get_relevant_context_flags():
    from forge.memory.enhanced_context_manager import DecisionType, EnhancedContextManager

    manager = EnhancedContextManager()
    manager.create_anchor("Keep context", "requirement", importance=0.9)
    manager.track_decision(
        description="Use Celery",
        rationale="Background tasks",
        decision_type=DecisionType.WORKFLOW,
        context="task queue",
    )
    manager.short_term_memory = [{"info": "task details", "timestamp": "2025-01-01T00:00:00", "tier": "short_term"}]
    manager.working_memory = []
    manager.long_term_memory = []
    context = manager.get_relevant_context("task", include_anchors=False, include_decisions=False)
    assert context["anchors"] == []
    assert context["decisions"] == []
    assert context["memory"]


def test_load_from_file_handles_missing(tmp_path):
    from forge.memory.enhanced_context_manager import EnhancedContextManager

    manager = EnhancedContextManager()
    missing_path = tmp_path / "missing.json"
    manager.load_from_file(str(missing_path))
