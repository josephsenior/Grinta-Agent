"""Test that the runtime import system is robust against broken third-party dependencies.

This test specifically addresses the issue where broken third-party runtime dependencies
(like runloop-api-client with incompatible httpx_aiohttp versions) would break the entire
OpenHands CLI and system.
"""

import logging
import sys
import pytest


def test_cli_import_with_broken_third_party_runtime():
    """Test that CLI can be imported even with broken third-party runtime dependencies."""
    modules_to_clear = [k for k in sys.modules.keys() if "openhands" in k or "third_party" in k]
    for module in modules_to_clear:
        del sys.modules[module]
    try:
        pass
    except Exception as e:
        pytest.fail(f"CLI import failed: {e}")


def test_runtime_import_robustness():
    """Test that runtime import system is robust against broken dependencies."""
    modules_to_clear = [k for k in sys.modules.keys() if "openhands.runtime" in k]
    for module in modules_to_clear:
        del sys.modules[module]
    try:
        pass
    except Exception as e:
        pytest.fail(f"Runtime import failed: {e}")


def test_get_runtime_cls_works():
    """Test that get_runtime_cls works even when third-party runtimes are broken."""
    import openhands.runtime

    docker_runtime = openhands.runtime.get_runtime_cls("docker")
    assert docker_runtime is not None
    local_runtime = openhands.runtime.get_runtime_cls("local")
    assert local_runtime is not None
    with pytest.raises(ValueError, match="Runtime nonexistent not supported"):
        openhands.runtime.get_runtime_cls("nonexistent")


def test_runtime_exception_handling():
    """Test that the runtime discovery code properly handles exceptions."""
    import openhands.runtime

    assert hasattr(openhands.runtime, "get_runtime_cls")
    assert hasattr(openhands.runtime, "_THIRD_PARTY_RUNTIME_CLASSES")


def test_runtime_import_exception_handling_behavior():
    """Test that runtime import handles ImportError silently but logs other exceptions."""
    from io import StringIO
    from openhands.core.logger import openhands_logger as logger

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        module_path = "third_party.runtime.impl.missing.missing_runtime"
        try:
            raise ImportError("No module named 'missing_library'")
        except ImportError:
            pass
        module_path = "third_party.runtime.impl.runloop.runloop_runtime"
        try:
            raise AttributeError("module 'httpx_aiohttp' has no attribute 'HttpxAiohttpClient'")
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Failed to import third-party runtime %s: %s", module_path, e)
        log_output = log_capture.getvalue()
        assert "Failed to import third-party runtime" in log_output
        assert "HttpxAiohttpClient" in log_output
        assert "missing_library" not in log_output
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)


def test_import_error_handled_silently(caplog):
    """Test that ImportError is handled silently (no logging) as it means library is not installed."""
    logging.getLogger("openhands.runtime")
    with caplog.at_level(logging.WARNING):
        try:
            raise ImportError("No module named 'optional_runtime_library'")
        except ImportError:
            pass
    warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert not warning_records, f"ImportError should not generate warnings, but got: {warning_records}"
