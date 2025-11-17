from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from forge.audit.audit_logger import AuditLogger
from forge.audit.models import AuditEntry
from forge.events.action import ActionSecurityRisk, CmdRunAction, IPythonRunCellAction
from forge.events.action.files import FileEditAction
from forge.events.event import FileEditSource


def make_validation_result(
    *,
    allowed: bool = True,
    requires_review: bool = False,
    risk_level: ActionSecurityRisk = ActionSecurityRisk.LOW,
    blocked_reason: str | None = None,
    matched_patterns: list[str] | None = None,
) -> SimpleNamespace:
    """Create a lightweight validation result for tests."""
    return SimpleNamespace(
        allowed=allowed,
        requires_review=requires_review,
        risk_level=risk_level,
        blocked_reason=blocked_reason,
        matched_patterns=matched_patterns or [],
    )


def test_audit_entry_serialization_roundtrip():
    """AuditEntry should serialize to/from dictionaries while preserving enums."""
    original = AuditEntry(
        id="abc123",
        timestamp=datetime.now().replace(microsecond=0),
        session_id="session-1",
        iteration=5,
        action_type="CmdRunAction",
        action_content="pytest -q",
        risk_level=ActionSecurityRisk.HIGH,
        validation_result="blocked",
        execution_result="failed",
        blocked_reason="Dangerous command",
        filesystem_snapshot_id="snapshot-42",
        rollback_available=True,
        matched_risk_patterns=["rm -rf"],
        environment="production",
        agent_state="running",
    )

    as_dict = original.to_dict()
    # Ensure enums were converted to strings
    assert as_dict["risk_level"] == "HIGH"

    restored = AuditEntry.from_dict(json.loads(json.dumps(as_dict)))
    assert restored == original
    assert restored.risk_level is ActionSecurityRisk.HIGH


@pytest.mark.asyncio
async def test_log_action_and_read_entries(tmp_path):
    """AuditLogger should persist entries that can be read back."""
    logger = AuditLogger(str(tmp_path))
    action = CmdRunAction(command="pytest -q")
    validation_result = make_validation_result(risk_level=ActionSecurityRisk.MEDIUM)

    audit_id = await logger.log_action(
        session_id="session-1",
        iteration=1,
        action=action,
        validation_result=validation_result,
        timestamp=datetime.now(),
        execution_result="ok",
    )

    assert audit_id

    entries = logger.read_session_audit("session-1")
    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, AuditEntry)
    assert entry.id == audit_id
    assert entry.action_type == "CmdRunAction"
    assert entry.execution_result == "ok"
    assert entry.validation_result == "allowed"


@pytest.mark.asyncio
async def test_blocked_and_high_risk_queries(tmp_path):
    """Helper query methods should filter entries correctly."""
    logger = AuditLogger(str(tmp_path))

    # Blocked high-risk action
    await logger.log_action(
        session_id="session-2",
        iteration=1,
        action=CmdRunAction(command="rm -rf /"),
        validation_result=make_validation_result(
            allowed=False,
            risk_level=ActionSecurityRisk.HIGH,
            blocked_reason="Dangerous command",
        ),
        timestamp=datetime.now(),
    )

    # Allowed medium-risk action
    await logger.log_action(
        session_id="session-2",
        iteration=2,
        action=CmdRunAction(command="ls"),
        validation_result=make_validation_result(risk_level=ActionSecurityRisk.MEDIUM),
        timestamp=datetime.now(),
    )

    blocked = logger.get_blocked_actions("session-2")
    assert len(blocked) == 1
    assert blocked[0].blocked_reason == "Dangerous command"

    high_risk = logger.get_high_risk_actions("session-2")
    assert len(high_risk) == 1
    assert high_risk[0].action_content == "rm -rf /"


@pytest.mark.asyncio
async def test_export_audit_trail(tmp_path):
    """Audit logs should export to JSON using export_audit_trail."""
    logger = AuditLogger(str(tmp_path))
    await logger.log_action(
        session_id="session-3",
        iteration=3,
        action=CmdRunAction(command="echo 'hello'"),
        validation_result=make_validation_result(),
        timestamp=datetime.now(),
    )

    output_file = tmp_path / "audit.json"
    logger.export_audit_trail("session-3", str(output_file))

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["action_content"] == "echo 'hello'"


def test_extract_action_content_variants(tmp_path):
    """_extract_action_content should tailor content to action type."""
    logger = AuditLogger(str(tmp_path))

    cmd_content = logger._extract_action_content(CmdRunAction(command="npm test"))
    assert cmd_content == "npm test"

    ipy_content = logger._extract_action_content(
        IPythonRunCellAction(code="print('x')")
    )
    assert ipy_content == "print('x')"

    file_action = FileEditAction(
        path="README.md",
        content="update",
        impl_source=FileEditSource.LLM_BASED_EDIT,
    )
    assert logger._extract_action_content(file_action) == "Edit README.md"

    class UnknownAction:
        def __str__(self) -> str:
            return "fallback"

    fallback = logger._extract_action_content(UnknownAction())
    assert fallback == "fallback"

    # Ensure truncation for very long content
    long_action = CmdRunAction(command="a" * 2000)
    truncated = logger._extract_action_content(long_action)
    assert truncated.startswith("a" * 1000)
    assert truncated.endswith("... (truncated)")


def test_read_session_audit_handles_missing_file(tmp_path):
    """read_session_audit should return an empty list for missing logs."""
    logger = AuditLogger(str(tmp_path))
    assert logger.read_session_audit("missing") == []


@pytest.mark.asyncio
async def test_log_action_marks_requires_review(tmp_path):
    """log_action should translate requires_review state."""
    logger = AuditLogger(str(tmp_path))
    await logger.log_action(
        session_id="session-rr",
        iteration=10,
        action=CmdRunAction(command="touch file"),
        validation_result=make_validation_result(requires_review=True),
        timestamp=datetime.now(),
    )

    entries = logger.read_session_audit("session-rr")
    assert entries[0].validation_result == "requires_review"


def test_get_session_log_file_sanitizes_name(tmp_path):
    """Session IDs with path separators should be sanitized for filenames."""
    logger = AuditLogger(str(tmp_path))
    path_with_slash = logger._get_session_log_file("team/session\\name")
    assert path_with_slash.name == "session_team_session_name.jsonl"
    assert path_with_slash.exists()


def test_read_session_audit_handles_corrupt_lines(tmp_path):
    """Corrupt entries should be skipped rather than crashing."""
    logger = AuditLogger(str(tmp_path))
    log_file = logger._get_session_log_file("messy")
    valid_entry = AuditEntry(
        id="1",
        timestamp=datetime.utcnow(),
        session_id="messy",
        iteration=1,
        action_type="Cmd",
        action_content="ls",
        risk_level=ActionSecurityRisk.LOW,
        validation_result="allowed",
    ).to_dict()
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(valid_entry, f)
        f.write("\nnot-json\n")

    entries = logger.read_session_audit("messy")
    assert len(entries) == 1


def test_read_session_audit_ignores_blank_lines(tmp_path):
    """Blank lines should be skipped without attempting to parse JSON."""
    logger = AuditLogger(str(tmp_path))
    log_file = logger._get_session_log_file("blank")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n")  # blank line

    assert logger.read_session_audit("blank") == []


@pytest.mark.asyncio
async def test_write_entry_handles_errors(monkeypatch, tmp_path):
    """_write_entry should swallow IO errors and log instead of raising."""
    logger = AuditLogger(str(tmp_path))

    def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(logger, "_get_session_log_file", boom)
    entry = SimpleNamespace(to_dict=lambda: {})

    await logger._write_entry("session", entry)


def test_read_session_audit_returns_empty_for_missing_path(monkeypatch, tmp_path):
    """If the log file is absent, read_session_audit should return an empty list."""
    logger = AuditLogger(str(tmp_path))
    missing_path = tmp_path / "nonexistent.jsonl"

    monkeypatch.setattr(logger, "_get_session_log_file", lambda _sid: missing_path)

    assert logger.read_session_audit("whatever") == []


def test_read_session_audit_handles_exceptions(monkeypatch, tmp_path):
    """Exceptions when opening files should be swallowed."""
    logger = AuditLogger(str(tmp_path))

    def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(logger, "_get_session_log_file", boom)
    assert logger.read_session_audit("boom") == []


def test_audit_entry_from_dict_without_conversions():
    """from_dict should handle pre-parsed values without touching them."""
    dt = datetime.now()
    data = {
        "id": "id1",
        "timestamp": dt,
        "session_id": "s",
        "iteration": 1,
        "action_type": "Cmd",
        "action_content": "ls",
        "risk_level": ActionSecurityRisk.LOW,
        "validation_result": "allowed",
    }
    entry = AuditEntry.from_dict(data.copy())
    assert entry.timestamp is dt
    assert entry.risk_level is ActionSecurityRisk.LOW


def test_export_audit_trail_handles_exception(monkeypatch, tmp_path):
    """export_audit_trail should swallow exceptions."""
    logger = AuditLogger(str(tmp_path))

    def boom(*args, **kwargs):
        raise RuntimeError("export error")

    monkeypatch.setattr(logger, "read_session_audit", boom)

    logger.export_audit_trail("session", str(tmp_path / "out.json"))
