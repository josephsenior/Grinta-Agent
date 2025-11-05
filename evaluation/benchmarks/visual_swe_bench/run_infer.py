import asyncio
import json
import os
import tempfile
from typing import Any
import pandas as pd
import toml
from datasets import load_dataset
import openhands.agenthub
from evaluation.benchmarks.swe_bench.resource.mapping import get_instance_resource_factor
from evaluation.utils.shared import (
    EvalException,
    EvalMetadata,
    EvalOutput,
    assert_and_raise,
    codeact_user_response,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_openhands_config_for_eval,
    is_fatal_evaluation_error,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
    update_llm_config_for_completions_logging,
)
from openhands.controller.state.state import State
from openhands.core.config import AgentConfig, OpenHandsConfig, get_evaluation_parser, get_llm_config_arg
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation, ErrorObservation
from openhands.events.serialization.event import event_to_dict
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync
from openhands.utils.shutdown_listener import sleep_if_should_continue

USE_HINT_TEXT = os.environ.get("USE_HINT_TEXT", "false").lower() == "true"
RUN_WITH_BROWSING = os.environ.get("RUN_WITH_BROWSING", "false").lower() == "true"
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}


def _get_swebench_workspace_dir_name(instance: pd.Series) -> str:
    return f"{instance.repo}__{instance.version}".replace("/", "__")


def get_instruction(instance: pd.Series, metadata: EvalMetadata):
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    instruction = f"<uploaded_files>\n/workspace/{workspace_dir_name}\n</uploaded_files>\nI've uploaded a python code repository in the directory {workspace_dir_name}. Consider the following issue description:\n\n<issue_description>\n{
        instance.problem_statement}\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Python environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script to reproduce the error and execute it with `python <filename.py>` using the BashTool, to confirm the error\n3. Edit the sourcecode of the repo to resolve the issue\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
        instance['base_commit']}. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n"
    if RUN_WITH_BROWSING:
        instruction += "<IMPORTANT!>\nYou SHOULD NEVER attempt to browse the web. </IMPORTANT!>\n"
    return instruction


DOCKER_IMAGE_PREFIX = os.environ.get("EVAL_DOCKER_IMAGE_PREFIX", "docker.io/xingyaoww/")
logger.info("Using docker image prefix: %s", DOCKER_IMAGE_PREFIX)


def get_instance_docker_image(instance_id: str, official_image: bool = False) -> str:
    image_name = f"sweb.eval.x86_64.{instance_id}"
    image_name = image_name.replace("__", "_s_")
    other_list = [
        "plotly__plotly.py-4083",
        "plotly__plotly.py-2600",
        "plotly__plotly.py-2591",
        "plotly__plotly.py-1966",
        "networkx__networkx-6503",
        "networkx__networkx-6098",
        "networkx__networkx-5616",
        "networkx__networkx-5354",
        "networkx__networkx-5058",
        "networkx__networkx-4378",
        "networkx__networkx-3764",
        "vega__altair-2785",
        "vega__altair-1092",
        "vega__altair-974",
        "vega__altair-830",
        "matplotlib__matplotlib-27754",
        "matplotlib__matplotlib-26926",
        "matplotlib__matplotlib-26788",
        "matplotlib__matplotlib-26586",
        "sympy__sympy-26941",
        "mwaskom__seaborn-3458",
        "mwaskom__seaborn-3454",
    ]
    if instance_id in other_list:
        return ("docker.io/luolin101/".rstrip("/") + "/" + image_name).lower()
    return (DOCKER_IMAGE_PREFIX.rstrip("/") + "/" + image_name).lower()


def get_config(instance: pd.Series, metadata: EvalMetadata) -> OpenHandsConfig:
    use_official_image = "verified" in metadata.dataset.lower() or "lite" in metadata.dataset.lower()
    base_container_image = get_instance_docker_image(instance["instance_id"], use_official_image)
    logger.info(
        "Using instance container image: %s. Please make sure this image exists. Submit an issue on https://github.com/All-Hands-AI/OpenHands if you run into any issues.",
        base_container_image,
    )
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = base_container_image
    sandbox_config.enable_auto_lint = True
    sandbox_config.use_host_network = False
    sandbox_config.platform = "linux/amd64"
    sandbox_config.remote_runtime_resource_factor = get_instance_resource_factor(
        dataset_name=metadata.dataset, instance_id=instance["instance_id"]
    )
    config = get_openhands_config_for_eval(
        metadata=metadata,
        enable_browser=RUN_WITH_BROWSING,
        runtime=os.environ.get("RUNTIME", "docker"),
        sandbox_config=sandbox_config,
    )
    config.set_llm_config(
        update_llm_config_for_completions_logging(
            metadata.llm_config, metadata.eval_output_dir, instance["instance_id"]
        )
    )
    agent_config = AgentConfig(
        enable_jupyter=False,
        enable_browsing=RUN_WITH_BROWSING,
        enable_llm_editor=False,
        condenser=metadata.condenser_config,
        enable_prompt_extensions=False,
    )
    config.set_agent_config(agent_config)
    return config


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("-" * 30)
    logger.info("BEGIN Runtime Initialization Fn")
    logger.info("-" * 30)
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    obs: CmdOutputObservation
    action = CmdRunAction(
        command=f"""echo 'export SWE_INSTANCE_ID={
            instance['instance_id']}' >> ~/.bashrc && echo 'export PIP_CACHE_DIR=~/.cache/pip' >> ~/.bashrc && echo "alias git='git --no-pager'" >> ~/.bashrc"""
    )
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to export SWE_INSTANCE_ID: {str(obs)}")
    action = CmdRunAction(command="export USER=$(whoami); echo USER=${USER} ")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to export USER: {str(obs)}")
    script_dir = os.path.dirname(__file__)
    action = CmdRunAction(command="mkdir -p /swe_util/eval_data/instances")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to create /swe_util/eval_data/instances: {str(obs)}")
    swe_instance_json_name = "swe-bench-instance.json"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, swe_instance_json_name)
        with open(temp_file_path, "w", encoding='utf-8') as f:
            if not isinstance(instance, dict):
                json.dump([instance.to_dict()], f)
            else:
                json.dump([instance], f)
        runtime.copy_to(temp_file_path, "/swe_util/eval_data/instances/")
        runtime.copy_to(str(os.path.join(script_dir, "scripts/setup/instance_swe_entry.sh")), "/swe_util/")
    action = CmdRunAction(command="cat ~/.bashrc")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to cat ~/.bashrc: {str(obs)}")
    action = CmdRunAction(command="source ~/.bashrc")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    if isinstance(obs, ErrorObservation):
        logger.error("Failed to source ~/.bashrc: %s", str(obs))
    assert_and_raise(obs.exit_code == 0, f"Failed to source ~/.bashrc: {str(obs)}")
    action = CmdRunAction(command="source /swe_util/instance_swe_entry.sh")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to source /swe_util/instance_swe_entry.sh: {str(obs)}")
    action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}")
    action = CmdRunAction(command="git reset --hard")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to git reset --hard: {str(obs)}")
    action = CmdRunAction(command='for remote_name in $(git remote); do git remote remove "${remote_name}"; done')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to remove git remotes: {str(obs)}")
    action = CmdRunAction(command="which python")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        obs.exit_code == 0 and "testbed" in obs.content,
        f"Expected to find python interpreter from testbed, but got: {str(obs)}",
    )
    logger.info("-" * 30)
    logger.info("END Runtime Initialization Fn")
    logger.info("-" * 30)


def _log_runtime_completion_start() -> None:
    """Log the start of runtime completion."""
    logger.info("-" * 30)
    logger.info("BEGIN Runtime Completion Fn")
    logger.info("-" * 30)


def _log_runtime_completion_end() -> None:
    """Log the end of runtime completion."""
    logger.info("-" * 30)
    logger.info("END Runtime Completion Fn")
    logger.info("-" * 30)


def _execute_command_with_timeout(runtime: Runtime, command: str, timeout: int = 600) -> CmdOutputObservation:
    """Execute a command with timeout and return the observation."""
    action = CmdRunAction(command=command)
    action.set_hard_timeout(timeout)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    return obs


def _navigate_to_workspace(runtime: Runtime, workspace_dir_name: str) -> CmdOutputObservation:
    """Navigate to the workspace directory with retry logic."""
    obs = _execute_command_with_timeout(runtime, f"cd /workspace/{workspace_dir_name}")

    if obs.exit_code == -1:
        logger.info("The previous command is still running, trying to kill it...")
        _execute_command_with_timeout(runtime, "C-c")
        obs = _execute_command_with_timeout(runtime, f"cd /workspace/{workspace_dir_name}")

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}",
    )
    return obs


def _setup_git_configuration(runtime: Runtime) -> None:
    """Set up git configuration."""
    obs = _execute_command_with_timeout(runtime, 'git config --global core.pager ""')
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f'Failed to git config --global core.pager "": {str(obs)}',
    )


def _cleanup_nested_git_repos(runtime: Runtime) -> None:
    """Find and remove nested git repositories."""
    obs = _execute_command_with_timeout(runtime, 'find . -type d -name .git -not -path "./.git"')
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0, f"Failed to find git repositories: {str(obs)}"
    )

    git_dirs = [p for p in obs.content.strip().split("\n") if p]
    for git_dir in git_dirs:
        obs = _execute_command_with_timeout(runtime, f'rm -rf "{git_dir}"')
        assert_and_raise(
            isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
            f"Failed to remove git directory {git_dir}: {str(obs)}",
        )


def _stage_all_changes(runtime: Runtime) -> None:
    """Stage all changes with git add -A."""
    obs = _execute_command_with_timeout(runtime, "git add -A")
    assert_and_raise(isinstance(obs, CmdOutputObservation) and obs.exit_code == 0, f"Failed to git add -A: {str(obs)}")


def _get_git_patch_with_retry(runtime: Runtime, base_commit: str) -> str:
    """Get git patch with retry logic."""
    n_retries = 0
    git_patch = None

    while n_retries < 5:
        timeout = max(300 + 100 * n_retries, 600)
        obs = _execute_command_with_timeout(runtime, f"git diff --no-color --cached {base_commit}", timeout)
        n_retries += 1

        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                git_patch = obs.content.strip()
                break
            else:
                logger.info("Failed to get git diff, retrying...")
                sleep_if_should_continue(10)
        elif isinstance(obs, ErrorObservation):
            logger.error("Error occurred: %s. Retrying...", obs.content)
            sleep_if_should_continue(10)
        else:
            assert_and_raise(False, f"Unexpected observation type: {str(obs)}")

    assert_and_raise(git_patch is not None, "Failed to get git diff (None)")
    return git_patch


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    _log_runtime_completion_start()

    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    _navigate_to_workspace(runtime, workspace_dir_name)
    _setup_git_configuration(runtime)
    _cleanup_nested_git_repos(runtime)
    _stage_all_changes(runtime)
    git_patch = _get_git_patch_with_retry(runtime, instance["base_commit"])

    _log_runtime_completion_end()
    return {"git_patch": git_patch}


def _setup_logging_and_config(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool, runtime_failure_count: int
) -> tuple[OpenHandsConfig, Runtime]:
    """Set up logging and configuration for the instance."""
    config = get_config(instance, metadata)

    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance.instance_id)

    if runtime_failure_count > 0:
        config.sandbox.remote_runtime_resource_factor = min(
            config.sandbox.remote_runtime_resource_factor * 2**runtime_failure_count, 8
        )
        logger.warning(
            "This is the %sth attempt for instance %s, setting resource factor to %s",
            runtime_failure_count + 1,
            instance.instance_id,
            config.sandbox.remote_runtime_resource_factor,
        )

    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    return config, runtime


def _run_agent_controller(
    config: OpenHandsConfig, instance: pd.Series, metadata: EvalMetadata, runtime: Runtime
) -> State:
    """Run the agent controller and return the state."""
    initialize_runtime(runtime, instance)
    instruction = get_instruction(instance, metadata)
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[metadata.agent_class],
        )
    )

    if is_fatal_evaluation_error(state.last_error):
        raise EvalException("Fatal error detected: " + state.last_error)

    if state is None:
        raise ValueError("State should not be None.")

    return state


def _get_git_patch_from_runtime(runtime: Runtime, instance: pd.Series) -> str:
    """Get git patch from runtime completion."""
    return_val = complete_runtime(runtime, instance)
    git_patch = return_val["git_patch"]
    logger.info("Got git diff for instance %s:\n--------\n%s\n--------", instance.instance_id, git_patch)
    return git_patch


def _create_eval_output(
    instance: pd.Series, instruction: str, state: State, git_patch: str, metadata: EvalMetadata
) -> EvalOutput:
    """Create the evaluation output."""
    test_result = {"git_patch": git_patch}
    histories = [event_to_dict(event) for event in state.history]
    metrics = get_metrics(state)
    return EvalOutput(
        instance_id=instance.instance_id,
        instruction=instruction,
        instance=instance.to_dict(),
        test_result=test_result,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
    )


def process_instance(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True, runtime_failure_count: int = 0
) -> EvalOutput:
    config, runtime = _setup_logging_and_config(instance, metadata, reset_logger, runtime_failure_count)

    try:
        state = _run_agent_controller(config, instance, metadata, runtime)
        git_patch = _get_git_patch_from_runtime(runtime, instance)
        return _create_eval_output(instance, get_instruction(instance, metadata), state, git_patch, metadata)
    finally:
        runtime.close()


def filter_dataset(dataset: pd.DataFrame, filter_column: str) -> pd.DataFrame:
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding='utf-8') as file:
            data = toml.load(file)
            if "selected_ids" in data:
                selected_ids = data["selected_ids"]
                logger.info('Filtering %s tasks from "selected_ids"...', len(selected_ids))
                subset = dataset[dataset[filter_column].isin(selected_ids)]
                logger.info("Retained %s tasks after filtering", subset.shape[0])
                return subset
    skip_ids = os.environ.get("SKIP_IDS", "").split(",")
    if len(skip_ids) > 0:
        logger.info('Filtering %s tasks from "SKIP_IDS"...', len(skip_ids))
        return dataset[~dataset[filter_column].isin(skip_ids)]
    return dataset


SWEGYM_EXCLUDE_IDS = [
    "dask__dask-10422",
    "pandas-dev__pandas-50548",
    "pandas-dev__pandas-53672",
    "pandas-dev__pandas-54174",
    "pandas-dev__pandas-55518",
    "pandas-dev__pandas-58383",
    "pydata__xarray-6721",
    "pytest-dev__pytest-10081",
    "pytest-dev__pytest-7236",
]
if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench",
        help="data set to evaluate on, either full-test or lite-test",
    )
    parser.add_argument("--split", type=str, default="test", help="split to evaluate on")
    args, _ = parser.parse_known_args()
    dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info("Loaded dataset %s with split %s: %s tasks", args.dataset, args.split, len(swe_bench_tests))
    if "SWE-Gym" in args.dataset:
        swe_bench_tests = swe_bench_tests[~swe_bench_tests["instance_id"].isin(SWEGYM_EXCLUDE_IDS)]
        logger.info("%s tasks left after excluding SWE-Gym excluded tasks", len(swe_bench_tests))
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.log_completions = True
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    details = {}
    _agent_cls = openhands.agenthub.Agent.get_cls(args.agent_cls)
    dataset_descrption = args.dataset.replace("/", "__") + "-" + args.split.replace("/", "__")
    metadata = make_metadata(
        llm_config,
        dataset_descrption,
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
        details=details,
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    print(f"### OUTPUT FILE: {output_file} ###")
    instances = prepare_dataset(swe_bench_tests, output_file, args.eval_n_limit)
    if len(instances) > 0 and (not isinstance(instances["PASS_TO_PASS"][instances["PASS_TO_PASS"].index[0]], str)):
        for col in ["PASS_TO_PASS", "FAIL_TO_PASS"]:
            instances[col] = instances[col].apply(lambda x: str(x))
    run_evaluation(
        instances,
        metadata,
        output_file,
        args.eval_num_workers,
        process_instance,
        timeout_seconds=8 * 60 * 60,
        max_retries=5,
    )
