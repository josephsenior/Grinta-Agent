"""Tests for system stats utilities."""

import time
from unittest.mock import patch
import psutil
from backend.runtime.utils.system_stats import (
    get_system_info,
    get_system_stats,
    update_last_execution_time,
)


def _validate_cpu_stats(stats):
    """Validate CPU statistics."""
    assert isinstance(stats["cpu_percent"], float)
    assert 0 <= stats["cpu_percent"] <= 100 * psutil.cpu_count()


def _validate_memory_stats(stats):
    """Validate memory statistics."""
    assert isinstance(stats["memory"], dict)
    assert set(stats["memory"].keys()) == {"rss", "vms", "percent"}
    assert isinstance(stats["memory"]["rss"], int)
    assert isinstance(stats["memory"]["vms"], int)
    assert isinstance(stats["memory"]["percent"], float)
    assert stats["memory"]["rss"] > 0
    assert stats["memory"]["vms"] > 0
    assert 0 <= stats["memory"]["percent"] <= 100


def _validate_disk_stats(stats):
    """Validate disk statistics."""
    assert isinstance(stats["disk"], dict)
    assert set(stats["disk"].keys()) == {"total", "used", "free", "percent"}
    assert isinstance(stats["disk"]["total"], int)
    assert isinstance(stats["disk"]["used"], int)
    assert isinstance(stats["disk"]["free"], int)
    assert isinstance(stats["disk"]["percent"], float)
    assert stats["disk"]["total"] > 0
    assert stats["disk"]["used"] >= 0
    assert stats["disk"]["free"] >= 0
    assert 0 <= stats["disk"]["percent"] <= 100
    assert stats["disk"]["used"] + stats["disk"]["free"] <= stats["disk"]["total"]


def _validate_io_stats(stats):
    """Validate I/O statistics."""
    assert isinstance(stats["io"], dict)
    assert set(stats["io"].keys()) == {"read_bytes", "write_bytes"}
    assert isinstance(stats["io"]["read_bytes"], int)
    assert isinstance(stats["io"]["write_bytes"], int)
    assert stats["io"]["read_bytes"] >= 0
    assert stats["io"]["write_bytes"] >= 0


def _validate_basic_stats_structure(stats):
    """Validate basic structure of system statistics."""
    assert isinstance(stats, dict)
    assert set(stats.keys()) == {"cpu_percent", "memory", "disk", "io"}


def test_get_system_stats():
    """Test that get_system_stats returns valid system statistics."""
    stats = get_system_stats()

    # Validate basic structure
    _validate_basic_stats_structure(stats)

    # Validate each component
    _validate_cpu_stats(stats)
    _validate_memory_stats(stats)
    _validate_disk_stats(stats)
    _validate_io_stats(stats)


def test_get_system_stats_stability():
    """Test that get_system_stats can be called multiple times without errors."""
    for _ in range(3):
        stats = get_system_stats()
        assert isinstance(stats, dict)
        assert stats["cpu_percent"] >= 0


def test_get_system_info():
    """Test that get_system_info returns valid system information."""
    with patch("backend.runtime.utils.system_stats.get_system_stats") as mock_get_stats:
        mock_get_stats.return_value = {"cpu_percent": 10.0}
        info = get_system_info()
        assert isinstance(info, dict)
        assert set(info.keys()) == {"uptime", "idle_time", "resources"}
        assert isinstance(info["uptime"], float)
        assert isinstance(info["idle_time"], float)
        assert info["uptime"] > 0
        assert info["idle_time"] >= 0
        assert info["resources"] == {"cpu_percent": 10.0}
        mock_get_stats.assert_called_once()


def test_update_last_execution_time():
    """Test that update_last_execution_time updates the last execution time."""
    initial_info = get_system_info()
    initial_idle_time = initial_info["idle_time"]
    time.sleep(0.1)
    update_last_execution_time()
    updated_info = get_system_info()
    updated_idle_time = updated_info["idle_time"]
    assert updated_idle_time < initial_idle_time
    assert updated_idle_time < 0.1


def test_idle_time_increases_without_updates():
    """Test that idle_time increases when no updates are made."""
    update_last_execution_time()
    initial_info = get_system_info()
    initial_idle_time = initial_info["idle_time"]
    time.sleep(0.2)
    updated_info = get_system_info()
    updated_idle_time = updated_info["idle_time"]
    assert updated_idle_time > initial_idle_time
    assert updated_idle_time >= 0.2


@patch("time.time")
def test_idle_time_calculation(mock_time):
    """Test that idle_time is calculated correctly."""
    mock_time.side_effect = [100.0, 100.0, 110.0]
    import importlib
    import backend.runtime.utils.system_stats

    importlib.reload(forge.runtime.utils.system_stats)
    from backend.runtime.utils.system_stats import get_system_info

    info = get_system_info()
    assert info["uptime"] == 10.0
    assert info["idle_time"] == 10.0
