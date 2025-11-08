import asyncio
import copy
import json
import os
import tempfile
from typing import Any, Literal
import pandas as pd
import toml
from datasets import load_dataset
from jinja2 import Environment, FileSystemLoader
import forge.agenthub
from evaluation.benchmarks.swe_bench.binary_patch_utils import remove_binary_diffs, remove_binary_files_from_git
from evaluation.benchmarks.swe_bench.resource.mapping import get_instance_resource_factor
from evaluation.benchmarks.swe_bench.resource.swt_bench_constants import (
    MAP_REPO_TO_INSTALL,
    MAP_REPO_TO_TEST_FRAMEWORK_VERBOSE,
    MAP_VERSION_TO_INSTALL,
)
from evaluation.utils.shared import (
    EvalException,
    EvalMetadata,
    EvalOutput,
    assert_and_raise,
    check_maximum_retries_exceeded,
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
from forge.core.config import AgentConfig, ForgeConfig, get_evaluation_parser, get_llm_config_arg
from forge.core.config.condenser_config import NoOpCondenserConfig
from forge.core.config.utils import get_condenser_config_arg
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.critic import AgentFinishedCritic
from forge.events.action import CmdRunAction, FileReadAction, MessageAction
from forge.events.observation import CmdOutputObservation, ErrorObservation, FileReadObservation
from forge.events.serialization.event import event_from_dict, event_to_dict
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync
from forge.utils.shutdown_listener import sleep_if_should_continue

USE_HINT_TEXT = os.environ.get("USE_HINT_TEXT", "false").lower() == "true"
RUN_WITH_BROWSING = os.environ.get("RUN_WITH_BROWSING", "false").lower() == "true"
ENABLE_LLM_EDITOR = os.environ.get("ENABLE_LLM_EDITOR", "false").lower() == "true"
BenchMode = Literal["swe", "swt", "swt-ci"]
DATASET_TYPE = "SWE-bench"


def set_dataset_type(dataset_name: str) -> str:
    """Set dataset type based on dataset name."""
    global DATASET_TYPE
    name_lower = dataset_name.lower()
    if "swe-gym" in name_lower:
        DATASET_TYPE = "SWE-Gym"
    elif "swe-bench-live" in name_lower:
        DATASET_TYPE = "SWE-bench-Live"
    elif "swe-rebench" in name_lower:
        DATASET_TYPE = "SWE-rebench"
    elif "multimodal" in name_lower:
        DATASET_TYPE = "Multimodal"
    else:
        DATASET_TYPE = "SWE-bench"
    logger.info("Dataset type set to: %s", DATASET_TYPE)


AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}


def _get_swebench_workspace_dir_name(instance: pd.Series) -> str:
    if DATASET_TYPE == "SWE-bench-Live":
        return instance.instance_id
    else:
        return f"{instance.repo}__{instance.version}".replace("/", "__")


def get_instruction(instance: pd.Series, metadata: EvalMetadata) -> MessageAction:
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    mode = metadata.details["mode"]
    llm_model = metadata.llm_config.model
    if metadata.instruction_template_name:
        template_name = metadata.instruction_template_name
    elif mode.startswith("swt"):
        template_name = "swt.j2"
    elif mode == "swe":
        template_name = "swe_gpt4.j2" if "gpt-4.1" in llm_model else "swe_default.j2"
    else:
        logger.error("Unexpected evaluation mode: %s. Falling back to default.", mode)
        template_name = "swe_default.j2"
    logger.debug("Using instruction template file: %s", template_name)
    prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
    env = Environment(loader=FileSystemLoader(prompts_dir), autoescape=True)
    template = env.get_template(template_name)
    context = {
        "instance": instance,
        "workspace_dir_name": workspace_dir_name,
        "metadata": metadata,
        "test_instructions": (
            f"The following command can be used to run the tests: `{
                list(
                    MAP_REPO_TO_TEST_FRAMEWORK_VERBOSE[
                        instance.repo].values())[0]}`. Make sure they fail in the expected way.\n"
            if mode == "swt-ci"
            else ""
        ),
    }
    instruction = template.render(context)
    if RUN_WITH_BROWSING:
        instruction += "<IMPORTANT!>\nYou SHOULD NEVER attempt to browse the web. </IMPORTANT!>\n"
    if "image_assets" in instance:
        assets = json.loads(instance["image_assets"])
        assert "problem_statement" in assets, "problem_statement is required in image_assets"
        image_urls = assets["problem_statement"]
        return MessageAction(content=instruction, image_urls=image_urls)
    return MessageAction(content=instruction)


DEFAULT_DOCKER_IMAGE_PREFIX = os.environ.get("EVAL_DOCKER_IMAGE_PREFIX", "docker.io/xingyaoww/")
logger.info("Default docker image prefix: %s", DEFAULT_DOCKER_IMAGE_PREFIX)


def get_instance_docker_image(instance_id: str, swebench_official_image: bool = False) -> str:
    if swebench_official_image:
        if DATASET_TYPE == "SWE-bench":
            docker_image_prefix = "docker.io/swebench/"
        elif DATASET_TYPE == "SWE-bench-Live":
            docker_image_prefix = "docker.io/starryzhang/"
        elif DATASET_TYPE == "SWE-rebench":
            docker_image_prefix = "docker.io/swerebench/"
        repo, name = instance_id.split("__")
        image_name = f"{docker_image_prefix.rstrip('/')}/sweb.eval.x86_64.{repo}_1776_{name}:latest".lower()
        logger.debug("Using official SWE-Bench image: %s", image_name)
        return image_name
    else:
        docker_image_prefix = DEFAULT_DOCKER_IMAGE_PREFIX
        image_name = f"sweb.eval.x86_64.{instance_id}"
        image_name = image_name.replace("__", "_s_")
        return (docker_image_prefix.rstrip("/") + "/" + image_name).lower()


def get_config(instance: pd.Series, metadata: EvalMetadata) -> ForgeConfig:
    use_swebench_official_image = DATASET_TYPE != "SWE-Gym"
    base_container_image = get_instance_docker_image(
        instance["instance_id"], swebench_official_image=use_swebench_official_image
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
    config.set_llm_config(get_llm_config_arg("draft_editor"), "draft_editor")
    agent_config = AgentConfig(
        enable_jupyter=False,
        enable_browsing=RUN_WITH_BROWSING,
        enable_llm_editor=ENABLE_LLM_EDITOR,
        enable_mcp=False,
        condenser=metadata.condenser_config,
        enable_prompt_extensions=False,
    )
    config.set_agent_config(agent_config)
    return config


def initialize_runtime(runtime: Runtime, instance: pd.Series, metadata: EvalMetadata):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("-" * 30)
    logger.info("BEGIN Runtime Initialization Fn")
    logger.info("-" * 30)

    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    _configure_environment_variables(runtime, instance)
    _setup_workspace_directories(runtime)
    entry_script_path = _copy_instance_data_and_scripts(runtime, instance)
    _source_environment_scripts(runtime, entry_script_path)
    _setup_git_repository(runtime, workspace_dir_name)
    _run_setup_commands_if_needed(runtime, instance, metadata)
    _verify_python_interpreter(runtime)

    logger.info("-" * 30)
    logger.info("END Runtime Initialization Fn")
    logger.info("-" * 30)


def _configure_environment_variables(runtime: Runtime, instance: pd.Series) -> None:
    """Configure environment variables and git settings."""
    action = CmdRunAction(
        command=f"""echo 'export SWE_INSTANCE_ID={
            instance['instance_id']}' >> ~/.bashrc && echo 'export PIP_CACHE_DIR=~/.cache/pip' >> ~/.bashrc && echo "alias git='git --no-pager'" >> ~/.bashrc && git config --global core.pager "" && git config --global diff.binary false"""
    )
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to export SWE_INSTANCE_ID and configure git: {str(obs)}")

    action = CmdRunAction(command="export USER=$(whoami); echo USER=${USER} ")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to export USER: {str(obs)}")


def _setup_workspace_directories(runtime: Runtime) -> None:
    """Setup workspace directories."""
    action = CmdRunAction(command="mkdir -p /swe_util/eval_data/instances")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to create /swe_util/eval_data/instances: {str(obs)}")


def _copy_instance_data_and_scripts(runtime: Runtime, instance: pd.Series) -> str:
    """Copy instance data and setup scripts."""
    script_dir = os.path.dirname(__file__)
    swe_instance_json_name = "swe-bench-instance.json"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, swe_instance_json_name)
        with open(temp_file_path, "w", encoding='utf-8') as f:
            if not isinstance(instance, dict):
                json.dump([instance.to_dict()], f)
            else:
                json.dump([instance], f)
        runtime.copy_to(temp_file_path, "/swe_util/eval_data/instances/")

        entry_script_path = _get_entry_script_path()
        runtime.copy_to(str(os.path.join(script_dir, f"scripts/setup/{entry_script_path}")), "/swe_util/")

    return entry_script_path


def _get_entry_script_path() -> str:
    """Get the appropriate entry script path based on dataset type."""
    if DATASET_TYPE == "SWE-bench-Live":
        return "instance_swe_entry_live.sh"
    elif DATASET_TYPE == "SWE-rebench":
        return "instance_swe_entry_rebench.sh"
    else:
        return "instance_swe_entry.sh"


def _source_environment_scripts(runtime: Runtime, entry_script_path: str) -> None:
    """Source environment scripts."""
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

    action = CmdRunAction(command=f"source /swe_util/{entry_script_path}")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(obs.exit_code == 0, f"Failed to source /swe_util/{entry_script_path}: {str(obs)}")


def _setup_git_repository(runtime: Runtime, workspace_dir_name: str) -> None:
    """Setup git repository."""
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


def _run_setup_commands_if_needed(runtime: Runtime, instance: pd.Series, metadata: EvalMetadata) -> None:
    """Run setup commands if in swt-ci mode."""
    if metadata.details["mode"] == "swt-ci":
        setup_commands = _get_setup_commands(instance)
        for command in setup_commands:
            action = CmdRunAction(command=command)
            action.set_hard_timeout(600)
            logger.info(action, extra={"msg_type": "ACTION"})
            obs = runtime.run_action(action)
            logger.info(obs, extra={"msg_type": "OBSERVATION"})


def _get_setup_commands(instance: pd.Series) -> list[str]:
    """Get setup commands for the instance."""
    setup_commands = []
    if instance["repo"] in MAP_REPO_TO_INSTALL:
        setup_commands.append(MAP_REPO_TO_INSTALL[instance["repo"]])

    install = MAP_VERSION_TO_INSTALL.get(instance["repo"], {}).get(instance["version"], [])
    if "pre_install" in install:
        setup_commands.extend(iter(install["pre_install"]))
    if "install" in install:
        setup_commands.append(install["install"])

    return setup_commands


def _verify_python_interpreter(runtime: Runtime) -> None:
    """Verify Python interpreter is available."""
    if DATASET_TYPE not in ["Multimodal", "SWE-bench-Live"]:
        action = CmdRunAction(command="which python")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert_and_raise(
            obs.exit_code == 0 and "testbed" in obs.content,
            f"Expected to find python interpreter from testbed, but got: {str(obs)}",
        )


def _navigate_to_workspace(runtime: Runtime, workspace_dir_name: str) -> CmdOutputObservation:
    """Navigate to the workspace directory with retry logic."""
    action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    if obs.exit_code == -1:
        logger.info("The previous command is still running, trying to kill it...")
        action = CmdRunAction(command="C-c")
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})

    if obs.exit_code == -1:
        logger.info("The previous command is still running, trying to ctrl+z it...")
        action = CmdRunAction(command="C-z")
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        action = CmdRunAction(command=f"cd /workspace/{workspace_dir_name}")
        action.set_hard_timeout(600)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})

    return obs


def _setup_git_config(runtime: Runtime) -> None:
    """Setup git configuration."""
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
    """Remove nested git repositories."""
    action = CmdRunAction(command='find . -type d -name .git -not -path "./.git"')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0, f"Failed to find git repositories: {str(obs)}"
    )

    if git_dirs := [p for p in obs.content.strip().split("\n") if p]:
        for git_dir in git_dirs:
            action = CmdRunAction(command=f'rm -rf "{git_dir}"')
            action.set_hard_timeout(600)
            logger.info(action, extra={"msg_type": "ACTION"})
            obs = runtime.run_action(action)
            logger.info(obs, extra={"msg_type": "OBSERVATION"})
            assert_and_raise(
                isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
                f"Failed to remove git directory {git_dir}: {str(obs)}",
            )


def _stage_changes(runtime: Runtime) -> None:
    """Stage all changes and remove binary files."""
    action = CmdRunAction(command="git add -A")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(isinstance(obs, CmdOutputObservation) and obs.exit_code == 0, f"Failed to git add -A: {str(obs)}")

    action = CmdRunAction(command=remove_binary_files_from_git())
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0, f"Failed to remove binary files: {str(obs)}"
    )


def _generate_git_patch(runtime: Runtime, instance: pd.Series) -> str:
    """Generate git patch with retry logic."""
    n_retries = 0
    git_patch = None

    while n_retries < 5:
        action = CmdRunAction(command=f"git diff --no-color --cached {instance['base_commit']} > patch.diff")
        action.set_hard_timeout(max(300 + 100 * n_retries, 600))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        n_retries += 1

        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                git_patch = _read_patch_file(runtime, n_retries)
                if git_patch is not None:
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


def _read_patch_file(runtime: Runtime, n_retries: int) -> str | None:
    """Read the patch file with fallback for encoding issues."""
    action = FileReadAction(path="patch.diff")
    action.set_hard_timeout(max(300 + 100 * n_retries, 600))
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    if isinstance(obs, FileReadObservation):
        return obs.content
    elif isinstance(obs, ErrorObservation):
        assert "File could not be decoded as utf-8" in obs.content
        action = CmdRunAction(command="cat patch.diff")
        action.set_hard_timeout(max(300 + 100 * n_retries, 600))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        assert isinstance(obs, CmdOutputObservation) and obs.exit_code == 0
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        return obs.content
    else:
        assert_and_raise(False, f"Unexpected observation type: {str(obs)}")
        return None


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    _log_runtime_completion_start()

    # Setup workspace and navigation
    _setup_workspace_environment(runtime, instance)

    # Configure git and prepare repository
    _configure_git_environment(runtime)

    # Generate and process git patch
    git_patch = _generate_and_process_patch(runtime, instance)

    _log_runtime_completion_end()
    return {"git_patch": git_patch}


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


def _setup_workspace_environment(runtime: Runtime, instance: pd.Series) -> None:
    """Setup workspace environment and navigate to correct directory."""
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    obs = _navigate_to_workspace(runtime, workspace_dir_name)
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}",
    )


def _configure_git_environment(runtime: Runtime) -> None:
    """Configure git environment and prepare repository."""
    _setup_git_config(runtime)
    _cleanup_nested_git_repos(runtime)
    _stage_changes(runtime)


def _generate_and_process_patch(runtime: Runtime, instance: pd.Series) -> str:
    """Generate git patch and remove binary diffs."""
    git_patch = _generate_git_patch(runtime, instance)
    return remove_binary_diffs(git_patch)


def process_instance(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True, runtime_failure_count: int = 0
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
    metadata = copy.deepcopy(metadata)
    metadata.details["runtime_failure_count"] = runtime_failure_count
    metadata.details["remote_runtime_resource_factor"] = config.sandbox.remote_runtime_resource_factor
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    try:
        initialize_runtime(runtime, instance, metadata)
        message_action = get_instruction(instance, metadata)
        state: State | None = asyncio.run(
            run_controller(
                config=config,
                initial_user_action=message_action,
                runtime=runtime,
                fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[metadata.agent_class],
            )
        )
        if is_fatal_evaluation_error(state.last_error):
            raise EvalException("Fatal error detected: " + state.last_error)
        if DATASET_TYPE == "SWE-bench-Live":
            from evaluation.benchmarks.swe_bench.live_utils import complete_runtime as complete_runtime_fn
        else:
            complete_runtime_fn = complete_runtime
        return_val = complete_runtime_fn(runtime, instance)
        git_patch = return_val["git_patch"]
        logger.info("Got git diff for instance %s:\n--------\n%s\n--------", instance.instance_id, git_patch)
    finally:
        runtime.close()
    test_result = {"git_patch": git_patch}
    if state is None:
        raise ValueError("State should not be None.")
    histories = [event_to_dict(event) for event in state.history]
    metrics = get_metrics(state)
    instruction = message_action.content
    if message_action.image_urls:
        instruction += "\n\n<image_urls>" + "\n".join(message_action.image_urls) + "</image_urls>"
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
        with open(file_path, "r", encoding='utf-8') as file:
            data = toml.load(file)
            if "selected_ids" in data:
                selected_ids = data["selected_ids"]
                logger.info('Filtering %s tasks from "selected_ids"...', len(selected_ids))
                subset = dataset[dataset[filter_column].isin(selected_ids)]
                logger.info("Retained %s tasks after filtering", subset.shape[0])
                return subset
            if "selected_repos" in data:
                selected_repos = data["selected_repos"]
                if isinstance(selected_repos, str):
                    selected_repos = [selected_repos]
                assert isinstance(selected_repos, list)
                logger.info('Filtering %s tasks from "selected_repos"...', selected_repos)
                subset = dataset[dataset["repo"].isin(selected_repos)]
                logger.info("Retained %s tasks after filtering", subset.shape[0])
                return subset
    skip_ids = os.environ.get("SKIP_IDS", "").split(",")
    if len(skip_ids) > 0:
        logger.info('Filtering %s tasks from "SKIP_IDS"...', len(skip_ids))
        return dataset[~dataset[filter_column].isin(skip_ids)]
    return dataset


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench",
        help="data set to evaluate on, either full-test or lite-test",
    )
    parser.add_argument("--split", type=str, default="test", help="split to evaluate on")
    parser.add_argument(
        "--mode",
        type=str,
        default="swe",
        choices=["swe", "swt", "swt-ci"],
        help="mode to run the evaluation, either 'swe', 'swt', or 'swt-ci'",
    )
    args, _ = parser.parse_known_args()
    dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
    set_dataset_type(args.dataset)
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info("Loaded dataset %s with split %s: %s tasks", args.dataset, args.split, len(swe_bench_tests))
    if DATASET_TYPE == "SWE-Gym":
        with open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "split", "swegym_verified_instances.json"), "r"
        ) as f:
            swegym_verified_instances = json.load(f)
            swe_bench_tests = swe_bench_tests[swe_bench_tests["instance_id"].isin(swegym_verified_instances)]
        logger.info("%s tasks left after filtering for SWE-Gym verified instances", len(swe_bench_tests))
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.log_completions = True
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    condenser_name = os.environ.get("EVAL_CONDENSER")
    if condenser_name:
        condenser_config = get_condenser_config_arg(condenser_name)
        if condenser_config is None:
            raise ValueError(f"Could not find Condenser config: EVAL_CONDENSER={condenser_name}")
    else:
        condenser_config = NoOpCondenserConfig()
        logger.debug("No Condenser config provided via EVAL_CONDENSER, using NoOpCondenser.")
    details = {"mode": args.mode}
    _agent_cls = forge.agenthub.Agent.get_cls(args.agent_cls)
    dataset_descrption = args.dataset.replace("/", "__") + "-" + args.split.replace("/", "__")
    metadata = make_metadata(
        llm_config,
        dataset_descrption,
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
        details=details,
        condenser_config=condenser_config,
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    print(f"### OUTPUT FILE: {output_file} ###")
    ITERATIVE_EVAL_MODE = os.environ.get("ITERATIVE_EVAL_MODE", "false").lower() == "true"
    ITERATIVE_EVAL_MODE_MAX_ATTEMPTS = int(os.environ.get("ITERATIVE_EVAL_MODE_MAX_ATTEMPTS", "3"))
    if not ITERATIVE_EVAL_MODE:
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
    else:
        critic = AgentFinishedCritic()

        def get_cur_output_file_path(attempt: int) -> str:
            return f"{output_file.removesuffix('.jsonl')}.critic_attempt_{attempt}.jsonl"

        eval_ids = None
        for attempt in range(1, ITERATIVE_EVAL_MODE_MAX_ATTEMPTS + 1):
            cur_output_file = get_cur_output_file_path(attempt)
            logger.info(
                "Running evaluation with critic %s for attempt %s of %s.",
                critic.__class__.__name__,
                attempt,
                ITERATIVE_EVAL_MODE_MAX_ATTEMPTS,
            )
            if attempt > 1 and metadata.llm_config.temperature == 0:
                logger.info("Detected temperature is 0 for (>1) attempt %s. Setting temperature to 0.1...", attempt)
                metadata.llm_config.temperature = 0.1
            instances = prepare_dataset(swe_bench_tests, cur_output_file, args.eval_n_limit, eval_ids=eval_ids)
            if len(instances) > 0 and (
                not isinstance(instances["PASS_TO_PASS"][instances["PASS_TO_PASS"].index[0]], str)
            ):
                for col in ["PASS_TO_PASS", "FAIL_TO_PASS"]:
                    instances[col] = instances[col].apply(lambda x: str(x))
            logger.info("Evaluating %s instances for attempt %s...", len(instances), attempt)
            run_evaluation(
                instances,
                metadata,
                cur_output_file,
                args.eval_num_workers,
                process_instance,
                timeout_seconds=8 * 60 * 60,
                max_retries=5,
            )
            instances_failed = []
            logger.info(
                "Use critic %s to check %s instances for attempt %s...",
                critic.__class__.__name__,
                len(instances),
                attempt,
            )
            with open(cur_output_file, "r", encoding='utf-8') as f:
                for line in f:
                    instance = json.loads(line)
                    try:
                        history = [event_from_dict(event) for event in instance["history"]]
                        critic_result = critic.evaluate(history, instance["test_result"].get("git_patch", ""))
                        if not critic_result.success:
                            instances_failed.append(instance["instance_id"])
                    except Exception as e:
                        logger.error("Error loading history for instance %s: %s", instance["instance_id"], e)
                        instances_failed.append(instance["instance_id"])
            logger.info(
                "%s instances failed the current attempt %s: %s", len(instances_failed), attempt, instances_failed
            )
            eval_ids = instances_failed
            if len(instances_failed) == 0:
                break
        logger.info("Aggregating results from all attempts into the original output file...")
        fout = open(output_file, "w", encoding='utf-8')
        added_instance_ids = set()
        for attempt in reversed(range(1, ITERATIVE_EVAL_MODE_MAX_ATTEMPTS + 1)):
            cur_output_file = get_cur_output_file_path(attempt)
            if not os.path.exists(cur_output_file):
                logger.warning("Intermediate output file %s does not exist. Skipping...", cur_output_file)
                continue
            with open(cur_output_file, "r", encoding='utf-8') as f:
                for line in f:
                    instance = json.loads(line)
                    if (
                        instance["instance_id"] not in added_instance_ids
                        and instance["test_result"].get("git_patch", "").strip()
                    ):
                        fout.write(line)
                        added_instance_ids.add(instance["instance_id"])
            logger.info(
                "Aggregated instances from %s. Total instances added so far: %s",
                cur_output_file,
                len(added_instance_ids),
            )
        fout.close()
        logger.info("Done! Total %s instances added to %s", len(added_instance_ids), output_file)
        check_maximum_retries_exceeded(metadata.eval_output_dir)
