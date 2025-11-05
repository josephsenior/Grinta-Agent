import asyncio
import os
from typing import Any
import pandas as pd
from datasets import load_dataset
from tqdm import tqdm
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    codeact_user_response,
    compatibility_for_eval_history_pairs,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_openhands_config_for_eval,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
    update_llm_config_for_completions_logging,
)
from openhands.controller.state.state import State
from openhands.core.config import OpenHandsConfig, get_evaluation_parser, get_llm_config_arg
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync

AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}
LOCAL_DATASET_PATH = os.path.join(os.path.dirname(__file__), "benchmark")


def format_task_dict(example, use_knowledge):
    task = {
        "instance_id": example["instance_id"],
        "task_inst": example["task_inst"],
        "dataset_path": "/benchmark/datasets/" + example["dataset_folder_tree"].split("\n")[0][4:],
        "dataset_folder_tree": example["dataset_folder_tree"],
        "dataset_preview": example["dataset_preview"],
        "pred_program_name": "pred_" + example["gold_program_name"],
    }
    if use_knowledge:
        task["task_inst"] += "\n" + str(example["domain_knowledge"])
    return task


def get_config(metadata: EvalMetadata, instance_id: str) -> OpenHandsConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "docker.io/xingyaoww/openhands-eval-scienceagentbench"
    config = get_openhands_config_for_eval(
        metadata=metadata, runtime=os.environ.get("RUNTIME", "docker"), sandbox_config=sandbox_config
    )
    config.set_llm_config(
        update_llm_config_for_completions_logging(metadata.llm_config, metadata.eval_output_dir, instance_id)
    )
    return config


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("%s BEGIN Runtime Initialization Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    action = CmdRunAction(command="mkdir -p /workspace/pred_programs")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command="mkdir -p /workspace/pred_results")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    dataset_name = instance["dataset_folder_tree"].split("\n")[0][4:].rstrip("/")
    dataset_dir = os.path.join(LOCAL_DATASET_PATH, "datasets", dataset_name)
    runtime.copy_to(dataset_dir, "/workspace/benchmark/datasets", recursive=True)
    action = CmdRunAction(command="cd /workspace/benchmark/datasets && ls")
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    assert dataset_name in obs.content
    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("%s BEGIN Runtime Completion Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    test_result = {}
    action = CmdRunAction(command="cd /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command=f"cat pred_programs/{instance.pred_program_name}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    if obs.exit_code == 0:
        test_result = {"program": obs.content}
    else:
        test_result = {"program": "ERROR"}
    logger.info("%s END Runtime Completion Fn %s", "-" * 50, "-" * 50)
    return test_result


def process_instance(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True) -> EvalOutput:
    instance_id = instance.instance_id.replace("/", "__")
    config = get_config(metadata, instance_id)
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance_id)
    instruction = f"You are an expert Python programming assistant that helps scientist users to write high-quality code to solve their tasks.\nGiven a user request, you are expected to write a complete program that accomplishes the requested task and save any outputs to `/workspace/pred_results/` in the correct format.\n\nHere's the user request you need to work on:\n{
        instance.task_inst}\n\nYou can access the dataset at `{
        instance.dataset_path}`. Here is the directory structure of the dataset:\n```\n{
            instance.dataset_folder_tree}\n```\nHere are some helpful previews for the dataset file(s):\n{
                instance.dataset_preview}\n\nPlease save your program as `/workspace/pred_programs/{
                    instance.pred_program_name}`.\nThen, please run the program to check and fix any errors.\nPlease do NOT run the program in the background.\nIf the program uses some packages that are incompatible, please figure out alternative implementations and do NOT restart the environment.\n\n"
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance)
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN.get(metadata.agent_class),
        )
    )
    test_result = complete_runtime(runtime, instance)
    if state is None:
        raise ValueError("State should not be None.")
    metrics = get_metrics(state)
    histories = compatibility_for_eval_history_pairs(state.history)
    return EvalOutput(
        instance_id=instance.instance_id,
        instruction=instruction,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
        test_result=test_result,
    )


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--use-knowledge",
        type=str,
        default="false",
        choices=["true", "false"],
        help="use expert-provided knowledge or not",
    )
    args, _ = parser.parse_known_args()
    sab_dataset = load_dataset(
        "osunlp/ScienceAgentBench", split="validation"
    )  # nosec B615 - Safe: evaluation benchmark dataset
    dataset_processed = [format_task_dict(example, args.use_knowledge == "true") for example in tqdm(sab_dataset)]
    dataset = pd.DataFrame(dataset_processed)
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config, "ScienceAgentBench", args.agent_cls, args.max_iterations, args.eval_note, args.eval_output_dir
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    dataset["instance_id"] = dataset["instance_id"].apply(str)
    instances = prepare_dataset(dataset, output_file, args.eval_n_limit)
    run_evaluation(instances, metadata, output_file, args.eval_num_workers, process_instance)
