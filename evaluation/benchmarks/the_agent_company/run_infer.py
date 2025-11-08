import asyncio
import base64
import json
import os
import shutil
import tempfile
import yaml
from browsing import pre_login
from evaluation.utils.shared import get_default_sandbox_config_for_eval, get_FORGE_config_for_eval
from forge.controller.state.state import State
from forge.core.config import (
    LLMConfig,
    ForgeConfig,
    get_agent_config_arg,
    get_evaluation_parser,
    get_llm_config_arg,
)
from forge.core.config.agent_config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import CmdRunAction, MessageAction
from forge.events.observation import BrowserOutputObservation, CmdOutputObservation
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync


def get_config(
    base_container_image: str,
    task_short_name: str,
    mount_path_on_host: str,
    llm_config: LLMConfig,
    agent_config: AgentConfig | None,
) -> ForgeConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = base_container_image
    sandbox_config.enable_auto_lint = True
    sandbox_config.use_host_network = True
    config = get_FORGE_config_for_eval(
        max_iterations=100, sandbox_config=sandbox_config, workspace_mount_path=mount_path_on_host
    )
    config.save_trajectory_path = os.path.join(mount_path_on_host, f"traj_{task_short_name}.json")
    config.max_budget_per_task = 4
    config.set_llm_config(llm_config)
    if not agent_config:
        logger.info("Agent config not provided, using default settings")
        agent_config = AgentConfig(enable_prompt_extensions=False)
    config.set_agent_config(agent_config)
    return config


def load_dependencies(runtime: Runtime) -> list[str]:
    """Every task has a dependencies.yml file, which lists all the services that the.

    task depends on. This function loads the file and returns all dependent service names.
    """
    command = "cat /utils/dependencies.yml"
    action = CmdRunAction(command=command)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs: CmdOutputObservation = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    dependencies = yaml.safe_load(obs.content)
    if dependencies is None:
        dependencies = []
    return dependencies


def init_task_env(runtime: Runtime, hostname: str, env_llm_config: LLMConfig):
    command = f"SERVER_HOSTNAME={hostname} LITELLM_API_KEY={
        (
            env_llm_config.api_key.get_secret_value() if env_llm_config.api_key else None)} LITELLM_BASE_URL={
        env_llm_config.base_url} LITELLM_MODEL={
                env_llm_config.model} bash /utils/init.sh"
    action = CmdRunAction(command=command)
    action.set_hard_timeout(900)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0


def codeact_user_response(state: State) -> str:
    msg = "Please continue working on the task on whatever approach you think is suitable.\nIf you think you have solved the task, please finish the interaction.\nIMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n"
    if state.history:
        user_msgs = [event for event in state.history if isinstance(event, MessageAction) and event.source == "user"]
        if len(user_msgs) >= 2:
            return msg + "If you want to give up, run: <execute_bash> exit </execute_bash>.\n"
    return msg


def run_solver(
    runtime: Runtime,
    task_name: str,
    config: ForgeConfig,
    dependencies: list[str],
    save_final_state: bool,
    state_dir: str,
    save_screenshots: bool,
    screenshots_dir: str,
) -> State:
    instruction = "Complete the task in /instruction/task.md"
    if "gitlab" in dependencies:
        instruction += "\n\nGitlab username is 'root' and password is 'theagentcompany'"
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            sid=task_name,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=codeact_user_response,
        )
    )
    logger.info(state)
    if save_screenshots:
        screenshots_dir = os.path.join(screenshots_dir, task_name)
        os.makedirs(screenshots_dir, exist_ok=True)
        for image_id, obs in enumerate(state.history):
            if isinstance(obs, BrowserOutputObservation):
                image_data = base64.b64decode(obs.screenshot.replace("data:image/png;base64,", ""))
                with open(os.path.join(screenshots_dir, f"{image_id}.png"), "wb") as file:
                    file.write(image_data)
                if obs.set_of_marks:
                    som_image_data = base64.b64decode(obs.set_of_marks.replace("data:image/png;base64,", ""))
                    with open(os.path.join(screenshots_dir, f"{image_id}_som.png"), "wb") as file:
                        file.write(som_image_data)
    if save_final_state:
        os.makedirs(state_dir, exist_ok=True)
        with open(os.path.join(state_dir, f"state_{task_name}.json"), "w") as file:
            json.dump(str(state), file)
    return state


def run_evaluator(runtime: Runtime, env_llm_config: LLMConfig, trajectory_path: str, result_path: str):
    command = f"LITELLM_API_KEY={
        (
            env_llm_config.api_key.get_secret_value() if env_llm_config.api_key else None)} LITELLM_BASE_URL={
        env_llm_config.base_url} LITELLM_MODEL={
                env_llm_config.model} DECRYPTION_KEY='theagentcompany is all you need' python_default /utils/eval.py --trajectory_path {trajectory_path} --result_path {result_path}"
    action = CmdRunAction(command=command)
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--task-image-name", type=str, default="ghcr.io/theagentcompany/example-image:1.0.0", help="Task image name"
    )
    parser.add_argument(
        "--outputs-path", type=str, default="./outputs", help="Folder path to save trajectories and evaluation results"
    )
    parser.add_argument(
        "--server-hostname",
        type=str,
        default="localhost",
        help="Server hostname, e.g. localhost to access the host machine from the container, assuming the task docker container is run with `--network host` flag",
    )
    parser.add_argument("--agent-llm-config", type=str, default=None, help="LLM config for agent")
    parser.add_argument(
        "--env-llm-config",
        type=str,
        default=None,
        help="LLM config for evaluation environment (NPC & llm-based evaluator)",
    )
    args, _ = parser.parse_known_args()
    agent_config: AgentConfig | None = None
    if args.agent_config:
        agent_config = get_agent_config_arg(args.agent_config)
    agent_llm_config: LLMConfig | None = None
    if args.agent_llm_config:
        agent_llm_config = get_llm_config_arg(args.agent_llm_config)
    if agent_llm_config is None:
        raise ValueError(f"Could not find LLM config for agent: --agent-llm-config {args.agent_llm_config}")
    if agent_llm_config.api_key is None:
        raise ValueError("LLM API key is not set for agent")
    env_llm_config: LLMConfig | None = None
    if args.env_llm_config:
        env_llm_config = get_llm_config_arg(args.env_llm_config)
    if env_llm_config is None:
        raise ValueError(
            f"Could not find LLM config for evaluation environment: --env-llm-config {args.env_llm_config}"
        )
    if env_llm_config.api_key is None:
        raise ValueError("LLM API key is not set for evaluation environment")
    task_short_name = args.task_image_name.split("/")[-1].split(":")[0]
    logger.info("Task image name is %s, short name is %s", args.task_image_name, task_short_name)
    if os.getenv("TMPDIR") and os.path.exists(os.getenv("TMPDIR")):
        temp_dir = os.path.abspath(os.getenv("TMPDIR"))
    else:
        temp_dir = tempfile.mkdtemp()
    config: ForgeConfig = get_config(
        args.task_image_name, task_short_name, temp_dir, agent_llm_config, agent_config
    )
    runtime: Runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    init_task_env(runtime, args.server_hostname, env_llm_config)
    dependencies = load_dependencies(runtime)
    logger.info("Service dependencies: %s", dependencies)
    try:
        pre_login(
            runtime,
            dependencies,
            save_screenshots=True,
            screenshots_dir=os.path.join(os.path.abspath(args.outputs_path), "screenshots"),
        )
    except Exception as e:
        logger.error("Failed to pre-login: %s", e)
        init_task_env(runtime, args.server_hostname, env_llm_config)
        pre_login(
            runtime,
            dependencies,
            save_screenshots=True,
            screenshots_dir=os.path.join(os.path.abspath(args.outputs_path), "screenshots"),
        )
    state = run_solver(
        runtime,
        task_short_name,
        config,
        dependencies,
        save_final_state=True,
        state_dir=os.path.abspath(args.outputs_path),
        save_screenshots=True,
        screenshots_dir=os.path.join(os.path.abspath(args.outputs_path), "screenshots"),
    )
    trajectory_path = f"/outputs/traj_{task_short_name}.json"
    result_path = f"/outputs/eval_{task_short_name}.json"
    run_evaluator(runtime, env_llm_config, trajectory_path, result_path)
    shutil.move(
        os.path.join(temp_dir, f"traj_{task_short_name}.json"),
        os.path.join(os.path.abspath(args.outputs_path), f"traj_{task_short_name}.json"),
    )
    shutil.move(
        os.path.join(temp_dir, f"eval_{task_short_name}.json"),
        os.path.join(os.path.abspath(args.outputs_path), f"eval_{task_short_name}.json"),
    )
