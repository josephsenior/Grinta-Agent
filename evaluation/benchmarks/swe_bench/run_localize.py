import asyncio
import json
import os
import tempfile
from typing import Any
import pandas as pd
import toml
from datasets import load_dataset
import forge.agenthub
from evaluation.benchmarks.swe_bench.resource.mapping import (
    get_instance_resource_factor,
)
from evaluation.utils.shared import (
    EvalException,
    EvalMetadata,
    EvalOutput,
    assert_and_raise,
    codeact_user_response,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_FORGE_config_for_eval,
    is_fatal_evaluation_error,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
    update_llm_config_for_completions_logging,
)
from forge.controller.state.state import State
from forge.core.config import (
    AgentConfig,
    ForgeConfig,
    get_evaluation_parser,
    get_llm_config_arg,
)
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import CmdRunAction, MessageAction
from forge.events.observation import CmdOutputObservation, ErrorObservation
from forge.events.serialization.event import event_to_dict
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync
from forge.utils.shutdown_listener import sleep_if_should_continue

USE_HINT_TEXT = os.environ.get("USE_HINT_TEXT", "false").lower() == "true"
RUN_WITH_BROWSING = os.environ.get("RUN_WITH_BROWSING", "false").lower() == "true"
INDEX_BASE_DIR = os.environ.get("INDEX_BASE_DIR", "")
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {
    "CodeActAgent": codeact_user_response,
    "LocAgent": codeact_user_response,
}


def _get_swebench_workspace_dir_name(instance: pd.Series) -> str:
    return f"{instance.repo}__{instance.version}".replace("/", "__")


def get_instruction(instance: pd.Series, metadata: EvalMetadata):
    """Generate instruction text for issue localization task.

    Args:
        instance: The SWE-bench instance containing problem statement and metadata.
        metadata: Evaluation metadata for the task.

    Returns:
        str: The formatted instruction text for the localization task.
    """
    _get_swebench_workspace_dir_name(instance)
    instruction = f"""\nConsider the following issue description:\n\n<issue_description>\n{
        instance.problem_statement
    }\n</issue_description>\n\nYour objective is to localize the specific files, classes or functions, and lines of code that need modification or contain key information to resolve the issue.\n\nFollow these steps to localize the issue:\n## Step 1: Categorize and Extract Key Problem Information\n - Classify the problem statement into the following categories:\n    Problem description, error trace, code to reproduce the bug, and additional context.\n - Identify modules in the "{
        instance.instance_id.split("_")[0]
    }" package mentioned in each category.\n - Use extracted keywords and line numbers to search for relevant code references for additional context.\n\n## Step 2: Locate Referenced Modules\n- Accurately determine specific modules\n    - Explore the repo to familiarize yourself with its structure.\n    - Analyze the described execution flow to identify specific modules or components being referenced.\n- Pay special attention to distinguishing between modules with similar names using context and described execution flow.\n- Output Format for collected relevant modules:\n    - Use the format: 'file_path:QualifiedName'\n    - E.g., for a function `calculate_sum` in the `MathUtils` class located in `src/helpers/math_helpers.py`, represent it as: 'src/helpers/math_helpers.py:MathUtils.calculate_sum'.\n\n## Step 3: Analyze and Reproducing the Problem\n- Clarify the Purpose of the Issue\n    - If expanding capabilities: Identify where and how to incorporate new behavior, fields, or modules.\n    - If addressing unexpected behavior: Focus on localizing modules containing potential bugs.\n- Reconstruct the execution flow\n    - Identify main entry points triggering the issue.\n    - Trace function calls, class interactions, and sequences of events.\n    - Identify potential breakpoints causing the issue.\n    Important: Keep the reconstructed flow focused on the problem, avoiding irrelevant details.\n\n## Step 4: Locate Areas for Modification\n- Locate specific files, functions, or lines of code requiring changes or containing critical information for resolving the issue.\n- Consider upstream and downstream dependencies that may affect or be affected by the issue.\n- If applicable, identify where to introduce new fields, functions, or variables.\n- Think Thoroughly: List multiple potential solutions and consider edge cases that could impact the resolution.\n\n## Output Format for Final Results:\nYour final output should list the locations requiring modification, wrapped with triple backticks ```\nEach location should include the file path, class name (if applicable), function name, or line numbers, ordered by importance.\nYour answer would better include about 5 files.\n\n### Examples:\n```\nfull_path1/file1.py\nline: 10\nclass: MyClass1\nfunction: my_function1\n\nfull_path2/file2.py\nline: 76\nfunction: MyClass2.my_function2\n\nfull_path3/file3.py\nline: 24\nline: 156\nfunction: my_function3\n```\n\nReturn just the location(s)\n\nNote: Your thinking should be thorough and so it's fine if it's very long.\n"""
    instruction += "IMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\nDon't include any lambda functions!\nYou should NOT modify any files!\n"
    if RUN_WITH_BROWSING:
        instruction += "\n<IMPORTANT!>\nYou SHOULD NEVER attempt to browse the web.\n</IMPORTANT!>\n"
    return instruction


DEFAULT_DOCKER_IMAGE_PREFIX = os.environ.get(
    "EVAL_DOCKER_IMAGE_PREFIX", "docker.io/xingyaoww/"
)
logger.info("Default docker image prefix: %s", DEFAULT_DOCKER_IMAGE_PREFIX)


def get_instance_docker_image(instance_id: str, official_image: bool = False) -> str:
    if official_image:
        docker_image_prefix = "docker.io/swebench/"
        repo, name = instance_id.split("__")
        image_name = f"sweb.eval.x86_64.{repo}_1776_{name}:latest"
        logger.warning("Using official SWE-Bench image: %s", image_name)
    else:
        docker_image_prefix = DEFAULT_DOCKER_IMAGE_PREFIX
        image_name = f"sweb.eval.x86_64.{instance_id}"
        image_name = image_name.replace("__", "_s_")
    return (docker_image_prefix.rstrip("/") + "/" + image_name).lower()


def get_config(instance: pd.Series, metadata: EvalMetadata) -> ForgeConfig:
    use_official_image = (
        "verified" in metadata.dataset.lower() or "lite" in metadata.dataset.lower()
    )
    base_container_image = get_instance_docker_image(
        instance["instance_id"], use_official_image
    )
    logger.info(
        "Using instance container image: %s. Please make sure this image exists. Submit an issue on https://github.com/All-Hands-AI/Forge if you run into any issues.",
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
    oh_aci_li_cmd = "/Forge/micromamba/bin/micromamba run -n Forge poetry run pip install Forge-aci[llama]"
    sandbox_config.runtime_extra_deps = oh_aci_li_cmd
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    sandbox_config.runtime_startup_env_vars = {
        "REPO_PATH": f"/workspace/{workspace_dir_name}/"
    }
    config = get_FORGE_config_for_eval(
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
        enable_mcp=os.environ.get("ENABLE_MCP", False),
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
            instance["instance_id"]
        }' >> ~/.bashrc && echo 'export PIP_CACHE_DIR=~/.cache/pip' >> ~/.bashrc && echo "alias git='git --no-pager'" >> ~/.bashrc"""
    )
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        obs.exit_code == 0, f"Failed to export SWE_INSTANCE_ID: {str(obs)}"
    )
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
    assert_and_raise(
        obs.exit_code == 0,
        f"Failed to create /swe_util/eval_data/instances: {str(obs)}",
    )
    swe_instance_json_name = "swe-bench-instance.json"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, swe_instance_json_name)
        with open(temp_file_path, "w", encoding="utf-8") as f:
            if not isinstance(instance, dict):
                json.dump([instance.to_dict()], f)
            else:
                json.dump([instance], f)
        runtime.copy_to(temp_file_path, "/swe_util/eval_data/instances/")
        runtime.copy_to(
            str(os.path.join(script_dir, "scripts/setup/instance_swe_entry.sh")),
            "/swe_util/",
        )
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
    assert_and_raise(
        obs.exit_code == 0,
        f"Failed to source /swe_util/instance_swe_entry.sh: {str(obs)}",
    )
    action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        obs.exit_code == 0,
        f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}",
    )
    action = CmdRunAction(command="git reset --hard")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to git reset --hard: {str(obs)}")
    action = CmdRunAction(
        command='for remote_name in $(git remote); do git remote remove "${remote_name}"; done'
    )
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to remove git remotes: {str(obs)}")
    action = CmdRunAction(command="mkdir _index_data/graph_index_v2.3")
    obs = runtime.run_action(action)
    graph_index_file_path = os.path.join(
        INDEX_BASE_DIR, "graph_index_v2.3", f"{instance['instance_id']}.pkl"
    )
    if INDEX_BASE_DIR and os.path.exists(graph_index_file_path):
        logger.info(
            "Copying graph index from %s to /workspace/%s/_index_data/graph_index_v2.3",
            graph_index_file_path,
            workspace_dir_name,
        )
        runtime.copy_to(
            graph_index_file_path,
            f"/workspace/{workspace_dir_name}/_index_data/graph_index_v2.3",
        )
        action = CmdRunAction(
            command=f"mv _index_data/graph_index_v2.3/{instance['instance_id']}.pkl _index_data/graph_index_v2.3/code_graph.pkl"
        )
        obs = runtime.run_action(action)
        bm25_index_dir = os.path.join(
            INDEX_BASE_DIR, "BM25_index", instance["instance_id"]
        )
        runtime.copy_to(
            bm25_index_dir,
            f"/workspace/{workspace_dir_name}/_index_data",
            recursive=True,
        )
        action = CmdRunAction(
            command=f"mv _index_data/{instance['instance_id']} _index_data/bm25_index"
        )
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert_and_raise(obs.exit_code == 0, f"Failed to mv file: {str(obs)}")
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


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("-" * 30)
    logger.info("BEGIN Runtime Completion Fn")
    logger.info("-" * 30)

    # Navigate to workspace directory
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    _navigate_to_workspace(runtime, workspace_dir_name)

    # Configure git settings
    _configure_git_settings(runtime)

    # Clean up nested git repositories
    _cleanup_nested_git_repos(runtime)

    # Stage all changes
    _stage_git_changes(runtime)

    # Get git patch with retry logic
    git_patch = _get_git_patch_with_retry(runtime, instance)

    logger.info("-" * 30)
    logger.info("END Runtime Completion Fn")
    logger.info("-" * 30)
    return {"git_patch": git_patch}


def _navigate_to_workspace(runtime: Runtime, workspace_dir_name: str) -> None:
    """Navigate to the workspace directory with error handling."""
    action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    # Handle case where command is still running
    if obs.exit_code == -1:
        logger.info("The previous command is still running, trying to kill it...")
        action = CmdRunAction(command="C-c")
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})

        # Retry navigation
        action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}",
    )


def _configure_git_settings(runtime: Runtime) -> None:
    """Configure git settings for the runtime."""
    action = CmdRunAction(command='git config --global core.pager ""')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f'Failed to git config --global core.pager "": {str(obs)}',
    )


def _cleanup_nested_git_repos(runtime: Runtime) -> None:
    """Clean up nested git repositories in the workspace."""
    action = CmdRunAction(command='find . -type d -name .git -not -path "./.git"')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to find git repositories: {str(obs)}",
    )

    # Remove nested git directories
    if git_dirs := [p for p in obs.content.strip().split("\n") if p]:
        for git_dir in git_dirs:
            _remove_git_directory(runtime, git_dir)


def _remove_git_directory(runtime: Runtime, git_dir: str) -> None:
    """Remove a specific git directory."""
    action = CmdRunAction(command=f'rm -rf "{git_dir}"')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to remove git directory {git_dir}: {str(obs)}",
    )


def _stage_git_changes(runtime: Runtime) -> None:
    """Stage all changes in the git repository."""
    action = CmdRunAction(command="git add -A")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to git add -A: {str(obs)}",
    )


def _get_git_patch_with_retry(runtime: Runtime, instance: pd.Series) -> str:
    """Get git patch with retry logic for robustness."""
    n_retries = 0
    git_patch = None

    while n_retries < 5:
        action = CmdRunAction(
            command=f"git diff --no-color --cached {instance['base_commit']}"
        )
        action.set_hard_timeout(max(300 + 100 * n_retries, 600))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        n_retries += 1

        if _handle_git_diff_observation(obs):
            git_patch = obs.content.strip()
            break

        sleep_if_should_continue(10)

    assert_and_raise(git_patch is not None, "Failed to get git diff (None)")
    return git_patch


def _handle_git_diff_observation(obs) -> bool:
    """Handle git diff observation and return True if successful."""
    if isinstance(obs, CmdOutputObservation):
        if obs.exit_code == 0:
            return True
        else:
            logger.info("Failed to get git diff, retrying...")
            return False
    elif isinstance(obs, ErrorObservation):
        logger.error("Error occurred: %s. Retrying...", obs.content)
        return False
    else:
        assert_and_raise(False, f"Unexpected observation type: {str(obs)}")
        return False


def process_instance(
    instance: pd.Series,
    metadata: EvalMetadata,
    reset_logger: bool = True,
    runtime_failure_count: int = 0,
) -> EvalOutput:
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
    try:
        initialize_runtime(runtime, instance)
        instruction = get_instruction(instance, metadata)
        state: State | None = asyncio.run(
            run_controller(
                config=config,
                initial_user_action=MessageAction(content=instruction),
                runtime=runtime,
                fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[
                    metadata.agent_class
                ],
            )
        )
        if is_fatal_evaluation_error(state.last_error):
            raise EvalException("Fatal error detected: " + state.last_error)
        return_val = complete_runtime(runtime, instance)
        git_patch = return_val["git_patch"]
        logger.info(
            "Got git diff for instance %s:\n--------\n%s\n--------",
            instance.instance_id,
            git_patch,
        )
    finally:
        runtime.close()
    test_result = {"git_patch": git_patch}
    if state is None:
        raise ValueError("State should not be None.")
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


def filter_dataset(dataset: pd.DataFrame, filter_column: str) -> pd.DataFrame:
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            data = toml.load(file)
            if "selected_ids" in data:
                selected_ids = data["selected_ids"]
                logger.info(
                    'Filtering %s tasks from "selected_ids"...', len(selected_ids)
                )
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
    parser.add_argument(
        "--split", type=str, default="test", help="split to evaluate on"
    )
    args, _ = parser.parse_known_args()
    dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info(
        "Loaded dataset %s with split %s: %s tasks",
        args.dataset,
        args.split,
        len(swe_bench_tests),
    )
    if "SWE-Gym" in args.dataset:
        swe_bench_tests = swe_bench_tests[
            ~swe_bench_tests["instance_id"].isin(SWEGYM_EXCLUDE_IDS)
        ]
        logger.info(
            "%s tasks left after excluding SWE-Gym excluded tasks", len(swe_bench_tests)
        )
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.log_completions = True
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    details = {}
    _agent_cls = forge.agenthub.Agent.get_cls(args.agent_cls)
    dataset_descrption = (
        args.dataset.replace("/", "__") + "-" + args.split.replace("/", "__")
    )
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
    logger.info("### OUTPUT FILE: %s ###", output_file)
    instances = prepare_dataset(swe_bench_tests, output_file, args.eval_n_limit)
    if len(instances) > 0 and (
        not isinstance(
            instances["PASS_TO_PASS"][instances["PASS_TO_PASS"].index[0]], str
        )
    ):
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
