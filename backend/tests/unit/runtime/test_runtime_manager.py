from __future__ import annotations

import threading

from forge.runtime.runtime_manager import RuntimeManager, RuntimeServerInfo


def _make_server_info(port: int = 9000) -> RuntimeServerInfo:
    """Helper to construct a stub RuntimeServerInfo for tests."""
    dummy_thread = threading.Thread(target=lambda: None)
    exit_event = threading.Event()
    return RuntimeServerInfo(
        process=None,
        execution_server_port=port,
        vscode_port=port + 1,
        app_ports=[port + 2, port + 3],
        log_thread=dummy_thread,
        log_thread_exit_event=exit_event,
        temp_workspace=None,
        workspace_mount_path="/workspace",
    )


def test_add_and_acquire_warm_server() -> None:
    manager = RuntimeManager()
    info = _make_server_info()

    manager.add_warm_server("local", info, metadata={"env": "test"})

    assert manager.warm_count() == 1
    assert manager.warm_count("local") == 1
    assert manager.metrics_snapshot()["warm"]["local"] == 1

    acquired = manager.acquire_warm_server("local")
    assert acquired is info
    assert manager.warm_count("local") == 0


def test_register_and_deregister_running() -> None:
    manager = RuntimeManager()
    info = _make_server_info()

    manager.register_running("session-1", "local", info, metadata={"warm": "false"})

    assert manager.running_count() == 1
    assert manager.running_count("local") == 1
    assert manager.metrics_snapshot()["running"]["local"] == 1

    retrieved = manager.get_running("session-1")
    assert retrieved is info

    deregistered = manager.deregister_running("session-1")
    assert deregistered is info
    assert manager.running_count("local") == 0


def test_pop_all_warm_filters_by_kind() -> None:
    manager = RuntimeManager()
    local_a = _make_server_info(8000)
    local_b = _make_server_info(8100)
    docker = _make_server_info(8200)

    manager.add_warm_server("local", local_a)
    manager.add_warm_server("docker", docker)
    manager.add_warm_server("local", local_b)

    popped = manager.pop_all_warm("local")

    assert popped == [local_a, local_b]
    assert manager.warm_count("local") == 0
    assert manager.warm_count("docker") == 1
    remaining_snapshot = manager.metrics_snapshot()
    assert remaining_snapshot["warm"].get("local", 0) == 0
    assert remaining_snapshot["warm"].get("docker", 0) == 1

