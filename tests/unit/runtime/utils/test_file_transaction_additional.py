import importlib
import sys
import types
from types import SimpleNamespace

import pytest
if "tenacity.stop.stop_base" not in sys.modules:
    stub_tenacity = types.ModuleType("tenacity.stop.stop_base")
    stub_tenacity.StopBase = type("StopBase", (), {})
    sys.modules["tenacity.stop.stop_base"] = stub_tenacity



@pytest.fixture()
def file_transaction_module(monkeypatch):
    original_logger = sys.modules.get("forge.core.logger")
    stub_logger = types.ModuleType("forge.core.logger")

    class DummyLogger:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    stub_logger.forge_logger = DummyLogger()
    monkeypatch.setitem(sys.modules, "forge.core.logger", stub_logger)

    module = importlib.import_module("forge.runtime.utils.file_transaction")
    yield module

    sys.modules.pop("forge.runtime.utils.file_transaction", None)
    if original_logger is not None:
        sys.modules["forge.core.logger"] = original_logger
    else:
        sys.modules.pop("forge.core.logger", None)


@pytest.mark.asyncio
async def test_file_transaction_write_and_commit(tmp_path, file_transaction_module):
    runtime = SimpleNamespace()
    target = tmp_path / "file.txt"

    async with file_transaction_module.FileTransaction(runtime) as txn:
        await txn.write_file(str(target), "hello")
        await txn.commit()

    assert target.read_text(encoding="utf-8") == "hello"


@pytest.mark.asyncio
async def test_file_transaction_rollback_write(tmp_path, file_transaction_module):
    runtime = SimpleNamespace()
    target = tmp_path / "file.txt"

    with pytest.raises(RuntimeError):
        async with file_transaction_module.FileTransaction(runtime) as txn:
            await txn.write_file(str(target), "temp")
            raise RuntimeError("boom")

    assert not target.exists()


@pytest.mark.asyncio
async def test_file_transaction_rollback_edit_and_delete(tmp_path, file_transaction_module):
    runtime = SimpleNamespace()
    edit_target = tmp_path / "edit.txt"
    delete_target = tmp_path / "delete.txt"
    edit_target.write_text("original", encoding="utf-8")
    delete_target.write_text("remove", encoding="utf-8")

    with pytest.raises(RuntimeError):
        async with file_transaction_module.FileTransaction(runtime) as txn:
            await txn.edit_file(str(edit_target), "modified")
            await txn.delete_file(str(delete_target))
            raise RuntimeError("fail")

    assert edit_target.read_text(encoding="utf-8") == "original"
    assert delete_target.read_text(encoding="utf-8") == "remove"

