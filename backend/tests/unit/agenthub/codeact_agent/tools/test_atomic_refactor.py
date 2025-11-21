from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from forge.agenthub.codeact_agent.tools.atomic_refactor import AtomicRefactor


def _make_refactor(tmp_path: Path) -> AtomicRefactor:
    return AtomicRefactor(backup_root=str(tmp_path / "backups"))


def test_begin_transaction_creates_backup_dir(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    transaction = refactor.begin_transaction()
    assert transaction.transaction_id in refactor.active_transactions
    assert transaction.backup_dir is not None
    assert Path(transaction.backup_dir).exists()


def test_commit_modify_success(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "app.py"
    target.write_text("old", encoding="utf-8")

    refactor.add_file_edit(txn, str(target), "new content", operation="modify")
    result = refactor.commit(txn, validate=False)

    assert result.success is True
    assert target.read_text(encoding="utf-8") == "new content"
    assert Path(txn.backup_dir, "app.py").exists()


def test_commit_validation_failure_rolls_back(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "module.py"
    target.write_text("original", encoding="utf-8")

    refactor.add_file_edit(txn, str(target), "bad", operation="modify")

    def failing_validator(path: str, content: str) -> bool:
        return False

    result = refactor.commit(txn, validate=True, validator=failing_validator)
    assert result.success is False
    assert "Validation failed" in "\n".join(result.errors)

    # After a failed commit we can manually rollback to restore content.
    refactor.rollback(txn)
    assert target.read_text(encoding="utf-8") == "original"


def test_commit_rename_operation(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()

    old_path = tmp_path / "old.txt"
    new_path = tmp_path / "new.txt"
    old_path.write_text("data", encoding="utf-8")

    refactor.add_rename(txn, str(old_path), str(new_path))
    result = refactor.commit(txn, validate=False)

    assert result.success is True
    assert not old_path.exists()
    assert new_path.read_text(encoding="utf-8") == "data"


def test_rollback_after_commit(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    created = tmp_path / "created.txt"

    refactor.add_file_edit(txn, str(created), "hello", operation="create")
    refactor.commit(txn, validate=False)
    assert created.exists()

    rollback = refactor.rollback(txn)
    assert rollback.success is True
    assert not created.exists()


def test_delete_and_rollback_restore_file(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "to_delete.py"
    target.write_text("important", encoding="utf-8")

    refactor.add_file_edit(txn, str(target), "", operation="delete")
    refactor.commit(txn, validate=False)
    assert not target.exists()

    refactor.rollback(txn)
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "important"


def test_rename_rollback_restores_original(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    old_path = tmp_path / "component.py"
    new_path = tmp_path / "component_v2.py"
    old_path.write_text("content", encoding="utf-8")

    refactor.add_rename(txn, str(old_path), str(new_path))
    refactor.commit(txn, validate=False)
    assert new_path.exists()

    refactor.rollback(txn)
    assert old_path.exists()
    assert not new_path.exists()


def test_dry_run_detects_missing_file(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    refactor.add_file_edit(txn, str(tmp_path / "missing.py"), "x", operation="modify")

    result = refactor.dry_run(txn)
    assert result.success is False
    assert any("does not exist" in err for err in result.errors)


def test_dry_run_success(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "existing.py"
    target.write_text("old", encoding="utf-8")
    refactor.add_file_edit(txn, str(target), "new", operation="modify")
    result = refactor.dry_run(txn)
    assert result.success is True
    assert result.files_modified == 1


def test_dry_run_flags_unwritable_file(monkeypatch, tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "readonly.py"
    target.write_text("locked", encoding="utf-8")
    refactor.add_file_edit(txn, str(target), "new", operation="modify")

    def fake_access(path: str, mode: int) -> bool:
        if path == str(target):
            return False
        return True

    monkeypatch.setattr(os, "access", fake_access)
    result = refactor.dry_run(txn)
    assert result.success is False
    assert any("not writable" in err for err in result.errors)


def test_dry_run_flags_create_conflicts(monkeypatch, tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    existing = tmp_path / "dir" / "file.txt"
    existing.parent.mkdir()
    existing.write_text("exists", encoding="utf-8")
    refactor.add_file_edit(txn, str(existing), "new", operation="create")

    def fake_access(path: str, mode: int) -> bool:
        if path == str(existing.parent):
            return False
        return True

    monkeypatch.setattr(os, "access", fake_access)
    result = refactor.dry_run(txn)
    assert result.success is False
    joined = "\n".join(result.errors)
    assert "already exists" in joined
    assert "Directory is not writable" in joined


def test_cleanup_transaction_removes_backups(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    backup_dir = Path(txn.backup_dir)
    assert backup_dir.exists()

    refactor.cleanup_transaction(txn)
    assert not backup_dir.exists()
    assert txn.transaction_id not in refactor.active_transactions


def test_duplicate_commit_returns_error(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "file.txt"
    target.write_text("one", encoding="utf-8")
    refactor.add_file_edit(txn, str(target), "two", operation="modify")
    refactor.commit(txn, validate=False)

    second = refactor.commit(txn, validate=False)
    assert second.success is False
    assert "already committed" in second.message.lower()


def test_commit_after_rollback_returns_error(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "again.txt"
    target.write_text("orig", encoding="utf-8")
    refactor.add_file_edit(txn, str(target), "copy", operation="modify")
    refactor.rollback(txn)
    result = refactor.commit(txn, validate=False)
    assert result.success is False
    assert "rolled back" in result.message.lower()


def test_add_edit_after_finalize_raises(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    file_path = tmp_path / "file.txt"
    file_path.write_text("before", encoding="utf-8")
    refactor.add_file_edit(txn, str(file_path), "after")
    refactor.commit(txn, validate=False)

    with pytest.raises(ValueError):
        refactor.add_file_edit(txn, str(file_path), "again")

    refactor.rollback(txn)
    with pytest.raises(ValueError):
        refactor.add_rename(txn, str(file_path), str(file_path.with_suffix(".bak")))


def test_roll_back_twice_returns_error(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "double.txt"
    refactor.add_file_edit(txn, str(target), "data", operation="create")
    refactor.commit(txn, validate=False)
    first = refactor.rollback(txn)
    assert first.success is True
    second = refactor.rollback(txn)
    assert second.success is False
    assert "already rolled back" in second.message.lower()


def test_get_active_transactions(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    active_ids = {t.transaction_id for t in refactor.get_active_transactions()}
    assert txn.transaction_id in active_ids


def test_cleanup_warns_on_failure(monkeypatch, tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    def fake_rmtree(path):
        raise RuntimeError("nope")

    monkeypatch.setattr("shutil.rmtree", fake_rmtree)
    refactor.cleanup_transaction(txn)
    assert txn.transaction_id not in refactor.active_transactions


def test_commit_handles_unexpected_exception(tmp_path: Path, monkeypatch):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    target = tmp_path / "boom.py"
    target.write_text("old", encoding="utf-8")
    refactor.add_file_edit(txn, str(target), "new", operation="modify")

    def fail_apply(transaction, validate, validator):
        return [], ["simulated failure"]

    monkeypatch.setattr(
        refactor,
        "_apply_all_edits",
        fail_apply.__get__(refactor, type(refactor)),
    )
    result = refactor.commit(txn, validate=False)
    assert result.success is False
    assert "Transaction failed" in result.message


def test_commit_rename_without_source(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    old_path = tmp_path / "missing.txt"
    new_path = tmp_path / "new.txt"
    refactor.add_rename(txn, str(old_path), str(new_path))
    result = refactor.commit(txn, validate=False)
    assert result.success is True
    assert not new_path.exists()


def test_commit_delete_missing_file(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    refactor.add_file_edit(txn, str(tmp_path / "ghost.txt"), "", operation="delete")
    result = refactor.commit(txn, validate=False)
    assert result.success is True


def test_commit_create_then_validation_failure(tmp_path: Path):
    refactor = _make_refactor(tmp_path)
    txn = refactor.begin_transaction()
    created = tmp_path / "create_fail.txt"
    refactor.add_file_edit(txn, str(created), "new", operation="create")

    def validator(path, content):
        return False

    result = refactor.commit(txn, validate=True, validator=validator)
    assert result.success is False
    refactor.rollback(txn)
    assert not created.exists()



