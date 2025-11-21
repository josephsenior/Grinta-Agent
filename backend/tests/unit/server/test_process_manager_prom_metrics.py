from __future__ import annotations

import time
from forge.server.routes.monitoring import _process_manager_prom_lines
from forge.runtime.utils.process_manager import (
    ProcessManager,
    get_process_manager_metrics_snapshot,
)


def test_process_manager_prometheus_lines():
    pm = ProcessManager()

    # Register 3 processes
    pm.register_process("python -m http.server", command_id="p1")
    pm.register_process("npm run dev", command_id="p2")
    pm.register_process("node server.js", command_id="p3")

    # Unregister one to simulate natural termination
    time.sleep(0.001)
    pm.unregister_process("p1")

    # Snapshot should reflect current state
    snap = get_process_manager_metrics_snapshot()
    assert snap["registered_total"] >= 3
    assert snap["active_processes"] >= 2
    assert snap["natural_terminations_total"] >= 1

    # Collect Prometheus lines directly without starting FastAPI app
    lines = _process_manager_prom_lines()

    assert any(l.startswith("forge_processmgr_active_processes ") for l in lines)
    assert any(l.startswith("forge_processmgr_registered_total ") for l in lines)
    assert any(
        l.startswith("forge_processmgr_natural_terminations_total ") for l in lines
    )
    assert any(l.startswith("forge_processmgr_cleanup_attempts_total ") for l in lines)
    assert any(l.startswith("forge_processmgr_cleanup_successes_total ") for l in lines)
    assert any(l.startswith("forge_processmgr_cleanup_failures_total ") for l in lines)
    assert any(
        l.startswith("forge_processmgr_forced_kill_attempts_total ") for l in lines
    )
    assert any(l.startswith("forge_processmgr_lifetime_ms_sum ") for l in lines)
    assert any(l.startswith("forge_processmgr_lifetime_ms_count ") for l in lines)
