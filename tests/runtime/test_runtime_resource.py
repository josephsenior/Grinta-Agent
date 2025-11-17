"""Stress tests for the DockerRuntime, which connects to the ActionExecutor running in the sandbox."""

import pytest
from conftest import _close_test_runtime, _load_runtime
from forge.core.logger import forge_logger as logger
from forge.events.action import CmdRunAction


def test_stress_docker_runtime(temp_dir, runtime_cls, repeat=1):
    pytest.skip("This test is flaky")
    runtime, config = _load_runtime(
        temp_dir,
        runtime_cls,
        docker_runtime_kwargs={
            "cpu_period": 100000,
            "cpu_quota": 100000,
            "mem_limit": "4G",
        },
    )
    action = CmdRunAction(
        command="sudo apt-get update && sudo apt-get install -y stress-ng"
    )
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    for _ in range(repeat):
        action = CmdRunAction(command="stress-ng --all 1 -t 30s")
        action.set_hard_timeout(120)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
    _close_test_runtime(runtime)
