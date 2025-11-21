import asyncio
import copy
import os
import tempfile
from typing import Any
import pandas as pd
from datasets import load_dataset
from evaluation.benchmarks.aider_bench.helper import (
    FAKE_RESPONSES,
    INST_SUFFIXES,
    INSTRUCTIONS_ADDENDUM,
)
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    compatibility_for_eval_history_pairs,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_FORGE_config_for_eval,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from forge.controller.state.state import State
from forge.core.config import (
    ForgeConfig,
    get_llm_config_arg,
    load_from_toml,
    parse_arguments,
)
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import CmdRunAction, MessageAction
from forge.events.observation import CmdOutputObservation
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync

USE_UNIT_TESTS = os.environ.get("USE_UNIT_TESTS", "false").lower() == "true"
SKIP_NUM = os.environ.get("SKIP_NUM")
SKIP_NUM = (
    int(SKIP_NUM) if SKIP_NUM and SKIP_NUM.isdigit() and (int(SKIP_NUM) >= 0) else None
)


def get_config(metadata: EvalMetadata) -> ForgeConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "python:3.11-bookworm"
    config = get_FORGE_config_for_eval(
        metadata=metadata,
        sandbox_config=sandbox_config,
        runtime=os.environ.get("RUNTIME", "docker"),
    )
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    config_copy = copy.deepcopy(config)
    load_from_toml(config_copy)
    if "draft_editor" in config_copy.llms:
        config.set_llm_config(config_copy.llms["draft_editor"], "draft_editor")
    return config


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("\n%s BEGIN Runtime Initialization Fn %s\n", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    action = CmdRunAction(command="mkdir -p /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command="cd /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, f"{instance.instance_name}.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(instance.signature)
        runtime.copy_to(file_path, "/workspace")
        if USE_UNIT_TESTS:
            file_path = os.path.join(tmpdir, f"{instance.instance_name}_test.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(instance.test)
            runtime.copy_to(file_path, "/workspace")
    logger.info("\n%s END Runtime Initialization Fn %s\n", "-" * 50, "-" * 50)


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("\n%s BEGIN Runtime Completion Fn %s\n", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    script_name = f"{instance.instance_name}_test.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, script_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(instance.test)
        runtime.copy_to(file_path, "/workspace")
        logger.info("Running test file: %s", script_name)
    action = CmdRunAction(command=f"python3 -m unittest {script_name}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    exit_code = obs.exit_code if isinstance(obs, CmdOutputObservation) else 1
    logger.info("\n%s END Runtime Completion Fn %s\n", "-" * 50, "-" * 50)
    runtime.close()
    return {"test_output": obs.content, "exit_code": exit_code}


def process_instance(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True
) -> EvalOutput:
    config = get_config(metadata)
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, str(instance.instance_id), log_dir)
    else:
        logger.info(
            "\nStarting evaluation for instance %s.\n", str(instance.instance_id)
        )
    logger.info(instance)
    instruction = instance.instruction
    instruction += INSTRUCTIONS_ADDENDUM.format(
        signature_file=f"{instance.instance_name}.py"
    )
    if USE_UNIT_TESTS:
        logger.info(
            "\nInstruction to run test_file: %s_test.py\n", instance.instance_name
        )
        instruction += f"Use `python -m unittest {
            instance.instance_name
        }_test.py` to run the test_file and verify the correctness of your solution. DO NOT EDIT the test file.\n\n"
    instruction += "IMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\n"
    instruction += INST_SUFFIXES[metadata.agent_class]
    runtime: Runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance=instance)
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=FAKE_RESPONSES[metadata.agent_class],
        )
    )
    if state is None:
        raise ValueError("State should not be None.")
    return_val = complete_runtime(runtime, instance)
    exit_code = return_val["exit_code"]
    test_output = return_val["test_output"]
    errors = []
    test_cases = None
    if test_output.find("SyntaxError") != -1:
        errors += "SyntaxError"
    elif test_output.find("IndentationError") != -1:
        errors += "IndentationError"
    else:
        test_cases = test_output[: test_output.find("\r")]
    test_result = {"exit_code": exit_code, "test_cases": test_cases, "errors": errors}
    histories = compatibility_for_eval_history_pairs(state.history)
    metrics = get_metrics(state)
    return EvalOutput(
        instance_id=str(instance.instance_id),
        instance=instance.to_dict(),
        instruction=instruction,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
        test_result=test_result,
    )


if __name__ == "__main__":
    args = parse_arguments()
    dataset = load_dataset("RajMaheshwari/Exercism-Python")  # nosec B615 - Safe: evaluation benchmark dataset
    aider_bench_tests = dataset["train"].to_pandas()
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config,
        "AiderBench",
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    eval_ids = None
    if args.eval_ids:
        eval_ids = str(args.eval_ids).split(",")
        logger.info("\nUsing specific dataset IDs: %s\n", eval_ids)
    instances = prepare_dataset(
        aider_bench_tests,
        output_file,
        args.eval_n_limit,
        eval_ids=eval_ids,
        skip_num=SKIP_NUM,
    )
    run_evaluation(
        instances, metadata, output_file, args.eval_num_workers, process_instance
    )
