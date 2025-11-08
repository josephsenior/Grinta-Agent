from pathlib import Path

import pytest


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

