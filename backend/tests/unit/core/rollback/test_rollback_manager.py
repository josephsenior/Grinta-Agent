import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.core.rollback import rollback_manager
from forge.core.rollback.rollback_manager import Checkpoint, RollbackManager


class DummyProc(SimpleNamespace):
    def __init__(self, returncode=0, stdout="", stderr=""):
        super().__init__(returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "file.txt").write_text("content")

    # Patch git availability checks to simple responses by default
    monkeypatch.setattr(
        rollback_manager.subprocess,
        "run",
        lambda *args, **kwargs: DummyProc(returncode=1),
    )
    return ws


def test_load_checkpoints_handles_invalid_manifest(workspace, monkeypatch):
    checkpoints_dir = workspace / ".Forge" / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    (checkpoints_dir / "manifest.json").write_text("{invalid json")

    warnings = []
    monkeypatch.setattr(
        rollback_manager.logger, "warning", lambda msg: warnings.append(msg)
    )

    manager = RollbackManager(str(workspace))
    assert manager.checkpoints == []
    assert warnings


def test_load_checkpoints_success(workspace, monkeypatch):
    checkpoints_dir = workspace / ".Forge" / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_data = {
        "checkpoints": [
            {
                "id": "cp_existing",
                "timestamp": 1.0,
                "description": "existing",
                "checkpoint_type": "manual",
                "workspace_path": str(workspace),
                "metadata": {},
                "git_commit_sha": None,
                "file_snapshots": {},
            }
        ]
    }
    (checkpoints_dir / "manifest.json").write_text(json.dumps(checkpoint_data))

    manager = RollbackManager(str(workspace))
    assert manager.get_checkpoint("cp_existing") is not None


def test_check_git_available_success_and_failure(workspace, monkeypatch):
    def success_run(args, **kwargs):
        if args[:2] == ["git", "rev-parse"]:
            return DummyProc(returncode=0)
        return DummyProc(returncode=1)

    monkeypatch.setattr(rollback_manager.subprocess, "run", success_run)
    manager = RollbackManager(str(workspace))
    assert manager.git_available is True

    # Now simulate failure/exception path
    monkeypatch.setattr(
        rollback_manager.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError()),
    )
    assert manager._check_git_available() is False


def test_generate_checkpoint_id_format(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    checkpoint_id = manager._generate_checkpoint_id()
    assert checkpoint_id.startswith("cp_")


def test_create_checkpoint_creates_snapshot(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace), auto_cleanup=False)
    monkeypatch.setattr(
        RollbackManager, "_generate_checkpoint_id", lambda self: "cp_test"
    )

    checkpoint_id = manager.create_checkpoint("first")
    snapshot_file = manager.checkpoints_dir / "cp_test" / "file.txt"
    assert checkpoint_id == "cp_test"
    assert snapshot_file.exists()

    manifest = json.loads((manager.checkpoints_dir / "manifest.json").read_text())
    assert manifest["checkpoints"][0]["id"] == "cp_test"
    assert manager.list_checkpoints()[0]["id"] == "cp_test"
    assert manager.get_checkpoint("cp_test") is not None


def test_cleanup_old_checkpoints_removes_extra(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    ids = (str(i) for i in range(3))
    monkeypatch.setattr(
        RollbackManager, "_generate_checkpoint_id", lambda self: next(ids)
    )

    manager = RollbackManager(str(workspace), max_checkpoints=1)
    manager.create_checkpoint("first")
    manager.create_checkpoint("second")

    assert len(manager.checkpoints) == 1
    remaining = manager.checkpoints[0].id
    assert (manager.checkpoints_dir / remaining).exists()


def test_create_git_snapshot_success(workspace, monkeypatch):
    order = []

    def fake_run(args, **kwargs):
        cmd = tuple(args)
        order.append(cmd)
        if cmd[:2] == ("git", "add"):
            return DummyProc(returncode=0)
        if cmd[:2] == ("git", "commit"):
            return DummyProc(returncode=0)
        if cmd[:2] == ("git", "rev-parse"):
            return DummyProc(returncode=0, stdout="abc123\n")
        return DummyProc(returncode=1)

    monkeypatch.setattr(rollback_manager.subprocess, "run", fake_run)
    manager = RollbackManager(str(workspace))
    manager.git_available = True

    sha = manager._create_git_snapshot()
    assert sha == "abc123"
    assert any(cmd[:2] == ("git", "add") for cmd in order)


def test_create_git_snapshot_failure_returns_none(workspace, monkeypatch):
    def fake_run(args, **kwargs):
        if args[:2] == ["git", "commit"]:
            return DummyProc(returncode=1, stderr="fail")
        return DummyProc(returncode=0)

    monkeypatch.setattr(rollback_manager.subprocess, "run", fake_run)
    manager = RollbackManager(str(workspace))
    manager.git_available = True

    assert manager._create_git_snapshot() is None


def test_create_git_snapshot_logs_warning(workspace, monkeypatch):
    def raising_run(*args, **kwargs):
        raise RuntimeError("git broken")

    warnings = []
    monkeypatch.setattr(rollback_manager.subprocess, "run", raising_run)
    monkeypatch.setattr(
        rollback_manager.logger, "warning", lambda msg: warnings.append(msg)
    )
    manager = RollbackManager(str(workspace))
    manager.git_available = True

    assert manager._create_git_snapshot() is None
    assert warnings


def test_create_git_snapshot_skips_when_git_unavailable(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    manager.git_available = False
    assert manager._create_git_snapshot() is None


def test_create_file_snapshot_logs_error(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    monkeypatch.setattr(
        rollback_manager.shutil,
        "copy2",
        lambda *a, **k: (_ for _ in ()).throw(OSError("copy failed")),
    )
    errors = []
    monkeypatch.setattr(
        rollback_manager.logger, "error", lambda msg: errors.append(msg)
    )

    snapshots = manager._create_file_snapshot("cp_error")
    assert snapshots == {}
    assert errors


def test_rollback_to_file_snapshot(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))

    checkpoint = Checkpoint(
        id="cp1",
        timestamp=1.0,
        description="snapshot",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha=None,
        file_snapshots={"file.txt": "saved"},
    )

    manager.checkpoints = [checkpoint]
    snapshot_dir = manager.checkpoints_dir / "cp1"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "file.txt").write_text("old")

    extra_dir = workspace / "folder"
    extra_dir.mkdir()
    (extra_dir / "temp.txt").write_text("temp")

    assert manager.rollback_to("cp1") is True
    assert (workspace / "file.txt").read_text() == "old"
    assert not extra_dir.exists()


def test_rollback_to_uses_git_path(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    checkpoint = Checkpoint(
        id="cp_git",
        timestamp=1.0,
        description="git",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha="sha",
        file_snapshots={},
    )
    manager.checkpoints = [checkpoint]
    manager.git_available = True

    monkeypatch.setattr(RollbackManager, "_try_git_rollback", lambda self, cp: True)
    assert manager.rollback_to("cp_git") is True


def test_rollback_to_handles_exception(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    checkpoint = Checkpoint(
        id="cp_exc",
        timestamp=1.0,
        description="exc",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha=None,
        file_snapshots={},
    )
    manager.checkpoints = [checkpoint]
    monkeypatch.setattr(
        RollbackManager,
        "_try_git_rollback",
        lambda self, cp: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    errors = []
    monkeypatch.setattr(
        rollback_manager.logger, "error", lambda msg: errors.append(msg)
    )

    assert manager.rollback_to("cp_exc") is False
    assert errors


def test_rollback_to_missing_checkpoint_returns_false(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    assert manager.rollback_to("missing") is False


def test_try_git_rollback_success(workspace, monkeypatch):
    def fake_run(args, **kwargs):
        if args[:2] == ["git", "reset"]:
            return DummyProc(returncode=0)
        return DummyProc(returncode=0)

    monkeypatch.setattr(rollback_manager.subprocess, "run", fake_run)
    manager = RollbackManager(str(workspace))
    manager.git_available = True
    checkpoint = Checkpoint(
        id="cp_git",
        timestamp=1.0,
        description="git",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha="abc",
        file_snapshots={},
    )

    assert manager._try_git_rollback(checkpoint) is True


def test_try_git_rollback_failure_logs_warning(workspace, monkeypatch):
    def failing_run(args, **kwargs):
        if args[:2] == ["git", "reset"]:
            return DummyProc(returncode=1, stderr="nope")
        return DummyProc(returncode=0)

    warnings = []
    monkeypatch.setattr(rollback_manager.subprocess, "run", failing_run)
    monkeypatch.setattr(
        rollback_manager.logger, "warning", lambda msg: warnings.append(msg)
    )

    manager = RollbackManager(str(workspace))
    manager.git_available = True
    checkpoint = Checkpoint(
        id="cp_git",
        timestamp=1.0,
        description="git",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha="abc",
        file_snapshots={},
    )

    assert manager._try_git_rollback(checkpoint) is False
    assert warnings


def test_try_file_based_rollback_missing_snapshot(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    result = manager._try_file_based_rollback("missing")
    assert result is False


def test_delete_checkpoint_removes_directory(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    checkpoint = Checkpoint(
        id="cp_delete",
        timestamp=1.0,
        description="del",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha=None,
        file_snapshots={},
    )
    manager.checkpoints = [checkpoint]
    snapshot_dir = manager.checkpoints_dir / "cp_delete"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "file.txt").write_text("data")

    assert manager.delete_checkpoint("cp_delete") is True
    assert not snapshot_dir.exists()


def test_delete_checkpoint_missing_returns_false(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    assert manager.delete_checkpoint("none") is False


def test_get_latest_checkpoint(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    now = 100.0
    older = Checkpoint(
        id="old",
        timestamp=now - 10,
        description="old",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha=None,
        file_snapshots={},
    )
    newer = Checkpoint(
        id="new",
        timestamp=now,
        description="new",
        checkpoint_type="manual",
        workspace_path=str(workspace),
        metadata={},
        git_commit_sha=None,
        file_snapshots={},
    )
    manager.checkpoints = [older, newer]
    assert manager.get_latest_checkpoint().id == "new"


def test_get_latest_checkpoint_none(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    assert manager.get_latest_checkpoint() is None


def test_save_checkpoints_logs_error(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: False)
    manager = RollbackManager(str(workspace))
    manager.checkpoints = []

    def failing_open(*args, **kwargs):
        raise OSError("cannot write")

    errors = []
    monkeypatch.setattr("builtins.open", failing_open)
    monkeypatch.setattr(
        rollback_manager.logger, "error", lambda msg: errors.append(msg)
    )

    manager._save_checkpoints()
    assert errors


def test_create_checkpoint_skips_git_when_disabled(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: True)
    manager = RollbackManager(str(workspace), auto_cleanup=False)
    monkeypatch.setattr(
        RollbackManager, "_generate_checkpoint_id", lambda self: "cp_nogit"
    )
    monkeypatch.setattr(
        RollbackManager,
        "_create_git_snapshot",
        lambda self: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    checkpoint_id = manager.create_checkpoint("desc", use_git=False)
    assert checkpoint_id == "cp_nogit"


def test_create_checkpoint_with_git_snapshot(workspace, monkeypatch):
    monkeypatch.setattr(RollbackManager, "_check_git_available", lambda self: True)
    manager = RollbackManager(str(workspace), auto_cleanup=False)
    manager.git_available = True
    monkeypatch.setattr(
        RollbackManager, "_generate_checkpoint_id", lambda self: "cp_git"
    )
    monkeypatch.setattr(RollbackManager, "_create_git_snapshot", lambda self: "sha123")

    checkpoint_id = manager.create_checkpoint("with git")
    checkpoint = manager.get_checkpoint(checkpoint_id)
    assert checkpoint.git_commit_sha == "sha123"
