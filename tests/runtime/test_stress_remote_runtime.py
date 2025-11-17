"""Bash-related tests for the DockerRuntime, which connects to the ActionExecutor running in the sandbox.

Example usage:

```bash
export ALLHANDS_API_KEY="YOUR_API_KEY"
export RUNTIME=remote
export SANDBOX_REMOTE_RUNTIME_API_URL="https://runtime.staging.all-hands.dev"
poetry run pytest -vvxss tests/runtime/test_stress_remote_runtime.py
```

"""

import asyncio
import os
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock
import pandas as pd
import pytest
from conftest import TEST_IN_CI
from evaluation.utils.shared import (
    EvalException,
    EvalMetadata,
    EvalOutput,
    assert_and_raise,
    codeact_user_response,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from forge.agenthub import Agent
from forge.controller.state.state import State
from forge.core.config import AgentConfig, LLMConfig, ForgeConfig, SandboxConfig
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import (
    CmdRunAction,
    FileEditAction,
    FileWriteAction,
    MessageAction,
)
from forge.events.observation import CmdOutputObservation
from forge.events.serialization.event import event_to_dict
from forge.llm import LLM
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync

AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}


def get_config() -> ForgeConfig:
    config = ForgeConfig(
        run_as_Forge=False,
        runtime=os.environ.get("RUNTIME", "remote"),
        sandbox=SandboxConfig(
            base_container_image="python:3.11-bookworm",
            enable_auto_lint=True,
            use_host_network=False,
            timeout=300,
            api_key=os.environ.get("ALLHANDS_API_KEY", None),
            remote_runtime_api_url=os.environ.get(
                "SANDBOX_REMOTE_RUNTIME_API_URL", None
            ),
            keep_runtime_alive=False,
            remote_runtime_resource_factor=1,
        ),
        workspace_base=None,
        workspace_mount_path=None,
    )
    agent_config = AgentConfig(
        enable_jupyter=False, enable_browsing=False, enable_llm_editor=False
    )
    config.set_agent_config(agent_config)
    return config


@pytest.mark.skipif(
    TEST_IN_CI, reason="This test should only be run locally, not in CI."
)
def test_stress_remote_runtime_eval(n_eval_workers: int = 64):
    """Mimic evaluation setting to test remote runtime in a multi-processing setting."""

    def _initialize_runtime(runtime: Runtime):
        """Initialize the runtime for the agent.

        This function is called before the runtime is used to run the agent.
        """
        logger.info("-" * 30)
        logger.info("BEGIN Runtime Initialization Fn")
        logger.info("-" * 30)
        obs: CmdOutputObservation
        action = CmdRunAction(command="export USER=$(whoami); echo USER=${USER} ")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert_and_raise(obs.exit_code == 0, f"Failed to export USER: {str(obs)}")
        action = CmdRunAction(command="mkdir -p /dummy_dir")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert_and_raise(obs.exit_code == 0, f"Failed to create /dummy_dir: {str(obs)}")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, "dummy_file")
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write("dummy content")
            runtime.copy_to(temp_file_path, "/dummy_dir/")
        logger.info("-" * 30)
        logger.info("END Runtime Initialization Fn")
        logger.info("-" * 30)

    def _process_instance(
        instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True
    ) -> EvalOutput:
        config = get_config()
        if reset_logger:
            log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
            reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
        else:
            logger.info("Starting evaluation for instance %s.", instance.instance_id)
        runtime = create_runtime(config, headless_mode=True)
        call_async_from_sync(runtime.connect)
        try:
            _initialize_runtime(runtime)
            instruction = "dummy instruction"
            agent = Agent.get_cls(metadata.agent_class)(
                llm=LLM(config=metadata.llm_config),
                config=config.get_agent_config(metadata.agent_class),
            )

            def next_command(*args, **kwargs):
                return CmdRunAction(command="ls -lah")

            agent.step = MagicMock(side_effect=next_command)
            state: State | None = asyncio.run(
                run_controller(
                    config=config,
                    initial_user_action=MessageAction(content=instruction),
                    runtime=runtime,
                    fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[
                        metadata.agent_class
                    ],
                    agent=agent,
                )
            )
            if (
                state.last_error
                and "fatal error during agent execution" in state.last_error
                and ("stuck in a loop" not in state.last_error)
            ):
                raise EvalException("Fatal error detected: " + state.last_error)
        finally:
            runtime.close()
        test_result = {}
        if state is None:
            raise ValueError("State should not be None.")
        histories = [event_to_dict(event) for event in state.history]
        metrics = state.metrics.get() if state.metrics else None
        output = EvalOutput(
            instance_id=instance.instance_id,
            instruction=instruction,
            instance=instance.to_dict(),
            test_result=test_result,
            metadata=metadata,
            history=histories,
            metrics=metrics,
            error=state.last_error if state and state.last_error else None,
        )
        return output

    llm_config = LLMConfig()
    metadata = make_metadata(
        llm_config,
        "dummy_dataset_descrption",
        "CodeActAgent",
        max_iterations=10,
        eval_note="dummy_eval_note",
        eval_output_dir="./dummy_eval_output_dir",
        details={},
    )
    dummy_instance = pd.DataFrame(
        {"instance_id": [f"dummy_instance_{i}" for i in range(300)]}
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    instances = prepare_dataset(
        dummy_instance, output_file, eval_n_limit=len(dummy_instance)
    )
    run_evaluation(instances, metadata, output_file, n_eval_workers, _process_instance)


@pytest.mark.skipif(
    TEST_IN_CI, reason="This test should only be run locally, not in CI."
)
def _setup_stress_test_runtime():
    """Setup runtime for stress testing."""
    config = get_config()
    runtime = create_runtime(config, headless_mode=True)
    call_async_from_sync(runtime.connect)
    return runtime


def _collect_system_memory_stats(runtime, i):
    """Collect system memory statistics."""
    mem_action = CmdRunAction(
        'free -k | grep "Mem:" | awk \'{printf "Total: %8.1f MB, Used: %8.1f MB, Free: %8.1f MB, Available: %8.1f MB\\n", $2/1024, $3/1024, $4/1024, $7/1024}\''
    )
    mem_obs = runtime.run_action(mem_action)
    assert mem_obs.exit_code == 0
    logger.info("System memory usage (iteration %s): %s", i, mem_obs.content.strip())

    iteration_stats = {"iteration": i, "timestamp": time.time()}
    mem_parts = mem_obs.content.strip().split(",")
    for part in mem_parts:
        key, value = part.strip().split(":")
        iteration_stats[f"memory_{key.lower()}"] = float(
            value.replace("MB", "").strip()
        )

    return iteration_stats


def _collect_process_memory_stats(runtime, i):
    """Collect process memory statistics."""
    # Top 5 memory-consuming processes
    mem_action = CmdRunAction(
        "ps aux | awk '{printf \"%8.1f MB  %s\\n\", $6/1024, $0}' | sort -nr | head -n 5"
    )
    mem_obs = runtime.run_action(mem_action)
    assert mem_obs.exit_code == 0
    _top_processes = [i.strip() for i in mem_obs.content.strip().split("\n")]
    logger.info(
        "Top 5 memory-consuming processes (iteration %s):\n%s",
        i,
        "- " + "\n- ".join(_top_processes),
    )

    iteration_stats = {"top_processes": _top_processes}

    # Tmux memory usage
    mem_action = CmdRunAction(
        "ps aux | awk '{printf \"%8.1f MB  %s\\n\", $6/1024, $0}' | sort -nr | grep \"/usr/bin/tmux\" | grep -v grep | awk '{print $1}'"
    )
    mem_obs = runtime.run_action(mem_action)
    assert mem_obs.exit_code == 0
    logger.info("Tmux memory usage (iteration %s): %s KB", i, mem_obs.content.strip())
    try:
        iteration_stats["tmux_memory_mb"] = float(mem_obs.content.strip())
    except (ValueError, AttributeError):
        iteration_stats["tmux_memory_mb"] = None

    # Action execution server memory usage
    mem_action = CmdRunAction(
        'ps aux | awk \'{printf "%8.1f MB  %s\\n", $6/1024, $0}\' | sort -nr | grep "action_execution_server" | grep "/Forge/poetry" | grep -v grep | awk \'{print $1}\''
    )
    mem_obs = runtime.run_action(mem_action)
    assert mem_obs.exit_code == 0
    logger.info(
        "Action execution server memory usage (iteration %s): %s MB",
        i,
        mem_obs.content.strip(),
    )
    try:
        iteration_stats["action_server_memory_mb"] = float(mem_obs.content.strip())
    except (ValueError, AttributeError):
        iteration_stats["action_server_memory_mb"] = None

    return iteration_stats


def _test_interactive_command(runtime):
    """Test interactive command execution."""
    action = CmdRunAction(
        'read -p "Do you want to continue? [Y/n] " answer; if [[ $answer == "Y" ]]; then echo "Proceeding with operation..."; echo "Operation completed successfully!"; else echo "Operation cancelled."; exit 1; fi'
    )
    obs = runtime.run_action(action)
    assert "Do you want to continue?" in obs.content
    assert obs.exit_code == -1

    action = CmdRunAction("Y", is_input=True)
    obs = runtime.run_action(action)
    assert "Proceeding with operation..." in obs.content
    assert "Operation completed successfully!" in obs.content
    assert obs.exit_code == 0
    assert "[The command completed with exit code 0.]" in obs.metadata.suffix


def _test_timeout_handling(runtime, i):
    """Test timeout handling with long-running command."""
    action = CmdRunAction(
        f"""export i={i}; for j in $(seq 1 100); do echo "Line $j - Iteration $i - $(printf '%1000s' | tr " " "*")"; sleep 1; done"""
    )
    action.set_hard_timeout(2)
    obs = runtime.run_action(action)
    assert obs.exit_code == -1
    assert f"Line 1 - Iteration {i}" in obs.content

    # Test that previous command is still running
    obs = runtime.run_action(CmdRunAction("ls"))
    assert obs.exit_code == -1
    assert "The previous command is still running" in obs.metadata.suffix

    # Cancel the running command
    obs = runtime.run_action(CmdRunAction("C-c", is_input=True))
    assert obs.exit_code == 130

    # Verify we can run new commands
    obs = runtime.run_action(CmdRunAction("ls"))
    assert obs.exit_code == 0


def _run_stress_iteration(runtime, i):
    """Run a single stress test iteration."""
    start_time = time.time()

    # Collect memory statistics
    iteration_stats = _collect_system_memory_stats(runtime, i)
    process_stats = _collect_process_memory_stats(runtime, i)
    iteration_stats.update(process_stats)

    # Test interactive command
    _test_interactive_command(runtime)

    # Test timeout handling
    _test_timeout_handling(runtime, i)

    duration = time.time() - start_time
    iteration_stats["duration"] = duration
    logger.info("Completed iteration %s in %s seconds", i, duration)

    return iteration_stats


def test_stress_remote_runtime_long_output_with_soft_and_hard_timeout():
    """Stress test for the remote runtime."""
    runtime = _setup_stress_test_runtime()
    try:
        datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        for i in range(10):
            _run_stress_iteration(runtime, i)
    finally:
        runtime.close()


@pytest.mark.skipif(
    TEST_IN_CI, reason="This test should only be run locally, not in CI."
)
def test_stress_runtime_memory_limits():
    """Test runtime behavior under resource constraints."""
    config = get_config()
    if config.runtime == "docker":
        config.sandbox.docker_runtime_kwargs = {
            "cpu_period": 100000,
            "cpu_quota": 100000,
            "mem_limit": "4G",
            "memswap_limit": "0",
            "mem_swappiness": 0,
            "oom_kill_disable": False,
        }
    config.sandbox.runtime_startup_env_vars = {
        "RUNTIME_MAX_MEMORY_GB": "3",
        "RUNTIME_MEMORY_MONITOR": "true",
    }
    try:
        runtime = create_runtime(config, headless_mode=True)
        call_async_from_sync(runtime.connect)
        action = CmdRunAction(
            command="sudo apt-get update && sudo apt-get install -y stress-ng"
        )
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        action = CmdRunAction(
            command="stress-ng --vm 1 --vm-bytes 6G --timeout 1m --metrics"
        )
        action.set_hard_timeout(120)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "aborted early, out of system resources" in obs.content
        assert obs.exit_code == 3
    finally:
        runtime.close()


@pytest.mark.skipif(
    TEST_IN_CI, reason="This test should only be run locally, not in CI."
)
def test_stress_runtime_memory_limits_with_repeated_file_edit():
    """Test runtime behavior under resource constraints with repeated file edits."""
    config = get_config()
    if config.runtime == "docker":
        config.sandbox.docker_runtime_kwargs = {
            "cpu_period": 100000,
            "cpu_quota": 100000,
            "mem_limit": "4G",
            "memswap_limit": "0",
            "mem_swappiness": 0,
            "oom_kill_disable": False,
        }
    config.sandbox.runtime_startup_env_vars = {
        "RUNTIME_MAX_MEMORY_GB": "3",
        "RUNTIME_MEMORY_MONITOR": "true",
    }
    try:
        runtime = create_runtime(config, headless_mode=True)
        call_async_from_sync(runtime.connect)
        test_file = "/tmp/test_file.txt"  # nosec B108 - Safe: test file
        base_content = "".join((f"content_{i:03d}\n" for i in range(1000)))
        write_action = FileWriteAction(path=test_file, content=base_content)
        obs = runtime.run_action(write_action)
        for i in range(1000):
            edit_action = FileEditAction(
                command="str_replace",
                path=test_file,
                old_str=f"content_{i:03d}",
                new_str=f"-content_{i:03d}",
            )
            obs = runtime.run_action(edit_action)
            assert f"The file {test_file} has been edited" in obs.content, (
                f"Edit failed at iteration {i}"
            )
            logger.info("finished iteration %s", i)
        action = FileEditAction(command="view", path=test_file)
        obs = runtime.run_action(action)
        assert "-content_999" in obs.content, "Final content verification failed"
        logger.info("Final file content verified successfully")
    finally:
        runtime.close()
