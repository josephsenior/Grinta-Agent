from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile
import types
import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class DummyLogger:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    setattr(logger_mod, "forge_logger", DummyLogger())

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.file_transaction",
    ROOT / "forge" / "runtime" / "utils" / "file_transaction.py",
)
assert spec and spec.loader
file_transaction = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.file_transaction"] = file_transaction
spec.loader.exec_module(file_transaction)
FileTransaction = file_transaction.FileTransaction
FileOperation = file_transaction.FileOperation
FileOperationType = file_transaction.FileOperationType


@pytest.mark.asyncio
async def test_write_and_commit(tmp_path):
    target = tmp_path / "file.txt"
    async with FileTransaction(SimpleNamespace()) as txn:
        await txn.write_file(str(target), "hello")
        await txn.commit()
    assert target.read_text(encoding="utf-8") == "hello"


@pytest.mark.asyncio
async def test_write_rollback_on_error(tmp_path):
    target = tmp_path / "file.txt"
    with pytest.raises(RuntimeError):
        async with FileTransaction(SimpleNamespace()) as txn:
            await txn.write_file(str(target), "temp")
            raise RuntimeError("boom")
    assert not target.exists()


@pytest.mark.asyncio
async def test_auto_commit_without_explicit_call(tmp_path):
    target = tmp_path / "auto.txt"
    txn = FileTransaction(SimpleNamespace())
    async with txn:
        await txn.write_file(str(target), "data")
    assert txn.committed is True
    assert target.read_text(encoding="utf-8") == "data"


@pytest.mark.asyncio
async def test_write_creates_backup(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    txn = FileTransaction(SimpleNamespace())
    txn.backup_dir = str(tmp_path / "backup")
    os.makedirs(txn.backup_dir, exist_ok=True)
    async with txn:
        await txn.write_file(str(target), "updated")
        backup_file = Path(txn.backup_dir) / target.name
        assert backup_file.read_text(encoding="utf-8") == "original"
        await txn.commit()
    assert target.read_text(encoding="utf-8") == "updated"


@pytest.mark.asyncio
async def test_edit_and_delete_rollback(tmp_path):
    edit_target = tmp_path / "edit.txt"
    delete_target = tmp_path / "delete.txt"
    edit_target.write_text("original", encoding="utf-8")
    delete_target.write_text("remove", encoding="utf-8")
    with pytest.raises(RuntimeError):
        async with FileTransaction(SimpleNamespace()) as txn:
            await txn.edit_file(str(edit_target), "modified")
            await txn.delete_file(str(delete_target))
            raise RuntimeError("fail")
    assert edit_target.read_text(encoding="utf-8") == "original"
    assert delete_target.read_text(encoding="utf-8") == "remove"


@pytest.mark.asyncio
async def test_edit_file_missing(tmp_path):
    target = tmp_path / "missing.txt"
    async with FileTransaction(SimpleNamespace()) as txn:
        with pytest.raises(FileNotFoundError):
            await txn.edit_file(str(target), "content")


@pytest.mark.asyncio
async def test_delete_file_missing(tmp_path):
    target = tmp_path / "missing.txt"
    async with FileTransaction(SimpleNamespace()) as txn:
        await txn.delete_file(str(target))
    assert not target.exists()


def test_rollback_write_operation_restores(tmp_path):
    file_path = tmp_path / "restore.txt"
    file_path.write_text("new", encoding="utf-8")
    txn = FileTransaction(SimpleNamespace())
    operation = FileOperation(
        operation_type=FileOperationType.WRITE,
        file_path=str(file_path),
        new_content="new",
        old_content="original",
        existed_before=True,
    )
    txn._rollback_write_operation(operation)
    assert file_path.read_text(encoding="utf-8") == "original"


def test_rollback_write_operation_removes_new_file(tmp_path):
    file_path = tmp_path / "new_file.txt"
    file_path.write_text("temp", encoding="utf-8")
    txn = FileTransaction(SimpleNamespace())
    operation = FileOperation(
        operation_type=FileOperationType.WRITE,
        file_path=str(file_path),
        new_content="temp",
        old_content=None,
        existed_before=False,
    )
    txn._rollback_write_operation(operation)
    assert not file_path.exists()


def test_rollback_edit_operation(tmp_path):
    file_path = tmp_path / "edit.txt"
    file_path.write_text("new", encoding="utf-8")
    txn = FileTransaction(SimpleNamespace())
    operation = FileOperation(
        operation_type=FileOperationType.EDIT,
        file_path=str(file_path),
        new_content="new",
        old_content="old",
        existed_before=True,
    )
    txn._rollback_edit_operation(operation)
    assert file_path.read_text(encoding="utf-8") == "old"


def test_rollback_delete_operation(tmp_path):
    file_path = tmp_path / "delete.txt"
    txn = FileTransaction(SimpleNamespace())
    operation = FileOperation(
        operation_type=FileOperationType.DELETE,
        file_path=str(file_path),
        old_content="restore",
        existed_before=True,
    )
    txn._rollback_delete_operation(operation)
    assert file_path.read_text(encoding="utf-8") == "restore"


def test_rollback_processes_operations_in_reverse(tmp_path):
    write_path = tmp_path / "write.txt"
    edit_path = tmp_path / "edit.txt"
    delete_path = tmp_path / "delete.txt"
    edit_path.write_text("new", encoding="utf-8")
    txn = FileTransaction(SimpleNamespace())
    txn.operations = [
        FileOperation(
            FileOperationType.WRITE,
            str(write_path),
            new_content="new",
            old_content="old",
            existed_before=True,
        ),
        FileOperation(
            FileOperationType.EDIT,
            str(edit_path),
            new_content="new",
            old_content="old",
            existed_before=True,
        ),
        FileOperation(
            FileOperationType.DELETE,
            str(delete_path),
            old_content="restore",
            existed_before=True,
        ),
    ]
    asyncio.run(txn.rollback())
    assert write_path.read_text(encoding="utf-8") == "old"
    assert edit_path.read_text(encoding="utf-8") == "old"
    assert delete_path.read_text(encoding="utf-8") == "restore"


@pytest.mark.asyncio
async def test_cleanup_backup_dir_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        file_transaction.shutil,
        "rmtree",
        lambda path: (_ for _ in ()).throw(OSError("fail")),
    )
    target = tmp_path / "cleanup.txt"
    async with FileTransaction(SimpleNamespace()) as txn:
        await txn.write_file(str(target), "content")
        await txn.commit()


@pytest.mark.asyncio
async def test_write_backup_failure(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    original_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if str(path) == str(backup_dir / target.name) and "w" in mode:
            raise OSError("backup fail")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    async with FileTransaction(SimpleNamespace()) as txn:
        txn.backup_dir = str(backup_dir)
        await txn.write_file(str(target), "updated")
        await txn.commit()
    assert target.read_text(encoding="utf-8") == "updated"


@pytest.mark.asyncio
async def test_write_failure_logs_and_raises(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.parent.mkdir(exist_ok=True)
    original_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if str(path) == str(target) and "w" in mode:
            raise OSError("write fail")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    async with FileTransaction(SimpleNamespace()) as txn:
        with pytest.raises(OSError):
            await txn.write_file(str(target), "data")


@pytest.mark.asyncio
async def test_edit_backup_failure(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    original_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if str(path) == str(backup_dir / target.name) and "w" in mode:
            raise OSError("backup fail")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    async with FileTransaction(SimpleNamespace()) as txn:
        txn.backup_dir = str(backup_dir)
        with pytest.raises(OSError):
            await txn.edit_file(str(target), "modified")
    assert target.read_text(encoding="utf-8") == "original"


@pytest.mark.asyncio
async def test_edit_failure_raises(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    original_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if str(path) == str(target) and "w" in mode:
            raise OSError("edit fail")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    async with FileTransaction(SimpleNamespace()) as txn:
        with pytest.raises(OSError):
            await txn.edit_file(str(target), "modified")
    assert target.read_text(encoding="utf-8") == "original"


@pytest.mark.asyncio
async def test_delete_backup_failure(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    original_open = builtins.open
    backup_path: list[Path] = []

    def fake_open(path, mode="r", *args, **kwargs):
        if backup_path and str(path) == str(backup_path[0]) and "w" in mode:
            raise OSError("backup fail")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    async with FileTransaction(SimpleNamespace()) as txn:
        backup_path.append(Path(txn.backup_dir) / target.name)
        await txn.delete_file(str(target))
    assert not target.exists()


@pytest.mark.asyncio
async def test_delete_failure_raises(tmp_path, monkeypatch):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    monkeypatch.setattr(
        file_transaction.os,
        "remove",
        lambda path: (_ for _ in ()).throw(OSError("delete fail")),
    )
    async with FileTransaction(SimpleNamespace()) as txn:
        with pytest.raises(OSError):
            await txn.delete_file(str(target))
    assert target.exists()


def test_rollback_handles_exceptions(tmp_path, monkeypatch):
    txn = FileTransaction(SimpleNamespace())
    txn.operations = [
        FileOperation(
            FileOperationType.WRITE,
            str(tmp_path / "a.txt"),
            new_content="",
            old_content="",
            existed_before=True,
        ),
    ]
    monkeypatch.setattr(
        txn,
        "_rollback_write_operation",
        lambda op: (_ for _ in ()).throw(OSError("fail")),
    )
    asyncio.run(txn.rollback())
