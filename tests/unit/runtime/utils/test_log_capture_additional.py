from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.log_capture",
    ROOT / "forge" / "runtime" / "utils" / "log_capture.py",
)
assert spec and spec.loader
log_capture_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.log_capture"] = log_capture_mod
spec.loader.exec_module(log_capture_mod)

capture_logs = log_capture_mod.capture_logs


def _make_logger():
    logger = logging.getLogger("test.capture")
    # Ensure clean handlers and predictable level
    logger.handlers = [logging.NullHandler()]
    logger.setLevel(logging.INFO)
    return logger


@pytest.mark.asyncio
async def test_capture_logs_records_messages_and_restores_handlers():
    logger = _make_logger()
    original_handlers = list(logger.handlers)
    original_level = logger.level

    async with capture_logs(logger.name, level=logging.WARNING) as buffer:
        logger.warning("warning message")
        logger.error("error message")
        # INFO message should not be captured at WARNING level
        logger.info("info message")

    contents = buffer.getvalue()
    assert "warning message" in contents
    assert "error message" in contents
    assert "info message" not in contents
    assert logger.handlers == original_handlers
    assert logger.level == original_level


@pytest.mark.asyncio
async def test_capture_logs_restores_on_exception():
    logger = _make_logger()
    original_handlers = list(logger.handlers)
    original_level = logger.level

    class TestError(RuntimeError):
        pass

    with pytest.raises(TestError):
        async with capture_logs(logger.name, level=logging.DEBUG):
            logger.debug("debug message")
            raise TestError("boom")

    assert logger.handlers == original_handlers
    assert logger.level == original_level
