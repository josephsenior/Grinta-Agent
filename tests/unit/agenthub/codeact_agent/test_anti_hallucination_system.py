"""Tests for the AntiHallucinationSystem safeguards."""

from __future__ import annotations

import pytest

from forge.agenthub.codeact_agent.anti_hallucination_system import (
    AntiHallucinationSystem,
    FileOperationContext,
)
from forge.events.action import CmdRunAction, FileEditAction, MessageAction


class DummyState:
    """Placeholder state object; current implementation doesn't inspect it."""

    view = []


def test_should_enforce_tools_detects_action_commands() -> None:
    system = AntiHallucinationSystem()
    choice = system.should_enforce_tools("Please create a new file", DummyState())
    assert choice == "required"
    assert system.stats["strict_mode_activations"] == 1


def test_should_enforce_tools_allows_question() -> None:
    system = AntiHallucinationSystem()
    choice = system.should_enforce_tools("Why is the sky blue?", DummyState(), strict_mode=False)
    assert choice == "auto"
    assert system.stats["strict_mode_activations"] == 0


def test_should_enforce_tools_pending_operations_force_required() -> None:
    system = AntiHallucinationSystem()
    system.pending_file_operations.append(FileOperationContext("edit", ["foo.py"]))
    choice = system.should_enforce_tools("What's next?", DummyState(), strict_mode=False)
    assert choice == "required"


def test_inject_verification_commands_tracks_operations() -> None:
    system = AntiHallucinationSystem()
    actions = [FileEditAction(path="src/app.py"), MessageAction("Done")]
    enhanced = system.inject_verification_commands(actions, turn=1)

    assert len(enhanced) == 3  # edit action, verification command, original message
    assert isinstance(enhanced[1], CmdRunAction)
    assert system.pending_file_operations[0].file_paths == ["src/app.py"]
    assert system.stats["verifications_injected"] == 1


def test_validate_response_detects_hallucination() -> None:
    system = AntiHallucinationSystem()
    ok, error = system.validate_response("I created the file `src/new_file.py`.", [])
    assert ok is False
    assert "HALLUCINATION PREVENTED" in error
    assert system.stats["hallucinations_prevented"] == 1


def test_validate_response_accepts_when_tools_called() -> None:
    system = AntiHallucinationSystem()
    ok, error = system.validate_response(
        "I created the file `src/new_file.py`.",
        [FileEditAction(path="src/new_file.py")],
    )
    assert ok is True
    assert error is None


def test_extract_file_operation_claims_variations() -> None:
    system = AntiHallucinationSystem()
    text = (
        "I created the file `src/app.py` and I've updated src/utils/helpers.py. "
        "Then I wrote to `docs/readme.md`."
    )
    claims = system._extract_file_operation_claims(text)
    # Should capture unique claims with actual file paths
    assert any("src/app.py" in claim for claim in claims)
    assert any("src/utils/helpers.py" in claim for claim in claims)
    assert any("docs/readme.md" in claim for claim in claims)


def test_mark_and_cleanup_operations() -> None:
    system = AntiHallucinationSystem()
    system.pending_file_operations = [
        FileOperationContext("edit", ["a.py"], False, 1),
        FileOperationContext("edit", ["b.py"], False, 4),
    ]
    system.mark_operation_verified("a.py")
    assert system.pending_file_operations[0].verified is True

    system.cleanup_old_operations(current_turn=5, max_age=3)
    # Operation started at turn 1 should be removed (age 4 > 3)
    assert len(system.pending_file_operations) == 1
    assert system.pending_file_operations[0].file_paths == ["b.py"]


def test_get_stats_includes_pending_counts() -> None:
    system = AntiHallucinationSystem()
    system.pending_file_operations.append(FileOperationContext("edit", ["file.py"], False, 0))
    stats = system.get_stats()
    assert stats["pending_operations"] == 1
    assert stats["unverified_operations"] == 1

