import asyncio
import json
import os
from typing import Any
import gymnasium as gym
import pandas as pd
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    compatibility_for_eval_history_pairs,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_openhands_config_for_eval,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from openhands.controller.state.state import State
from openhands.core.config import OpenHandsConfig, get_llm_config_arg, parse_arguments
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import BrowseInteractiveAction, CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation
from openhands.runtime.base import Runtime
from openhands.runtime.browser.browser_env import BROWSER_EVAL_GET_GOAL_ACTION, BROWSER_EVAL_GET_REWARDS_ACTION
from openhands.utils.async_utils import call_async_from_sync

SUPPORTED_AGENT_CLS = {"BrowsingAgent"}


def get_config(metadata: EvalMetadata, env_id: str) -> OpenHandsConfig:
    base_url = os.environ.get("WEBARENA_BASE_URL", None)
    openai_api_key = os.environ.get("OPENAI_API_KEY", None)
    assert base_url is not None, "WEBARENA_BASE_URL must be set"
    assert openai_api_key is not None, "OPENAI_API_KEY must be set"
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "python:3.12-bookworm"
    sandbox_config.browsergym_eval_env = env_id
    sandbox_config.runtime_startup_env_vars = {
        "BASE_URL": base_url,
        "OPENAI_API_KEY": openai_api_key,
        "SHOPPING": f"{base_url}:7770/",
        "SHOPPING_ADMIN": f"{base_url}:7780/admin",
        "REDDIT": f"{base_url}:9999",
        "GITLAB": f"{base_url}:8023",
        "WIKIPEDIA": f"{base_url}:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing",
        "MAP": f"{base_url}:3000",
        "HOMEPAGE": f"{base_url}:4399",
    }
    config = get_openhands_config_for_eval(metadata=metadata, runtime="docker", sandbox_config=sandbox_config)
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    return config


def initialize_runtime(runtime: Runtime) -> dict:
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("%s BEGIN Runtime Initialization Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    action = CmdRunAction(command="mkdir -p /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = BrowseInteractiveAction(browser_actions=BROWSER_EVAL_GET_GOAL_ACTION)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    goal = obs.content
    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)
    return goal


def complete_runtime(runtime: Runtime) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("%s BEGIN Runtime Completion Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    action = BrowseInteractiveAction(browser_actions=BROWSER_EVAL_GET_REWARDS_ACTION)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    logger.info("%s END Runtime Completion Fn %s", "-" * 50, "-" * 50)
    return {"rewards": json.loads(obs.content)}


def process_instance(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True):
    env_id = instance.instance_id
    config = get_config(metadata, env_id)
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, env_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", env_id)
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    task_str = initialize_runtime(runtime)
    state: State | None = asyncio.run(
        run_controller(config=config, initial_user_action=MessageAction(content=task_str), runtime=runtime)
    )
    if state is None:
        raise ValueError("State should not be None.")
    metrics = get_metrics(state)
    instruction = next((event.content for event in state.history if isinstance(event, MessageAction)), "")
    return_val = complete_runtime(runtime)
    logger.info("Return value from complete_runtime: %s", return_val)
    reward = max(return_val["rewards"])
    histories = compatibility_for_eval_history_pairs(state.history)
    return EvalOutput(
        instance_id=env_id,
        instruction=instruction,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
        test_result={"reward": reward},
    )


if __name__ == "__main__":
    args = parse_arguments()
    dataset = pd.DataFrame(
        {"instance_id": [id for id in gym.envs.registry.keys() if id.startswith("browsergym/webarena")]}
    )
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config, args.dataset_name, args.agent_cls, args.max_iterations, args.eval_note, args.eval_output_dir
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    instances = prepare_dataset(dataset, output_file, args.eval_n_limit)
    run_evaluation(instances, metadata, output_file, args.eval_num_workers, process_instance)
