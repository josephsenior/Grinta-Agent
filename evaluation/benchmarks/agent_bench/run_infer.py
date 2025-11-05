import asyncio
import os
import re
import tempfile
from typing import Any
import pandas as pd
from datasets import load_dataset
from evaluation.benchmarks.agent_bench.helper import FAKE_RESPONSES, INST_SUFFIXES, compare_results, create_sh_file
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    compatibility_for_eval_history_pairs,
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
from openhands.events.action import AgentFinishAction, CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync


def get_config(metadata: EvalMetadata) -> OpenHandsConfig:
    config = get_openhands_config_for_eval(metadata=metadata)
    config.sandbox.base_container_image = "python:3.12-slim"
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    return config


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("%s BEGIN Runtime Initialization Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    action = CmdRunAction(command="mkdir -p /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command="cd /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    init_cmd = instance.init
    if init_cmd is not None:
        script_name = f"{instance.instance_id}_init.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            host_script_path = os.path.join(tmpdir, script_name)
            create_sh_file(host_script_path, init_cmd)
            runtime.copy_to(host_script_path, "/workspace")
        logger.info("Running init script: %s", script_name)
        action = CmdRunAction(command=f"chmod +x ./{script_name} && ./{script_name}")
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    _log_runtime_completion_start()

    agent_answer = _get_agent_answer(runtime, instance)
    final_ans = _get_final_answer(runtime, instance)

    _log_runtime_completion_end()
    return {"final_ans": final_ans, "agent_answer": agent_answer}


def _log_runtime_completion_start() -> None:
    """Log the start of runtime completion."""
    logger.info("%s BEGIN Runtime Completion Fn %s", "-" * 50, "-" * 50)


def _log_runtime_completion_end() -> None:
    """Log the end of runtime completion."""
    logger.info("%s END Runtime Completion Fn %s", "-" * 50, "-" * 50)


def _get_agent_answer(runtime: Runtime, instance: pd.Series) -> str | None:
    """Get agent answer by running the agent result command."""
    get_agent_result_cmd = instance.get_agent_result
    if get_agent_result_cmd is None:
        return None

    return _run_script_command(runtime, get_agent_result_cmd, "get_agent_result.sh")


def _get_final_answer(runtime: Runtime, instance: pd.Series) -> str | None:
    """Get final answer from ground truth or by running ground truth command."""
    if instance.ground_truth is not None:
        return instance.ground_truth

    get_ground_truth_cmd = instance.get_ground_truth
    if get_ground_truth_cmd is None:
        return None

    return _run_script_command(runtime, get_ground_truth_cmd, "get_ground_truth.sh")


def _run_script_command(runtime: Runtime, command: str, script_name: str) -> str:
    """Run a script command and return its output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        host_script_path = os.path.join(tmpdir, script_name)
        create_sh_file(host_script_path, command)
        runtime.copy_to(host_script_path, "/workspace")
        logger.info("Running %s cmd: %s", script_name, script_name)

    action = CmdRunAction(command=f"chmod +x ./{script_name} && ./{script_name}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    if script_name == "get_agent_result.sh":
        assert obs.exit_code == 0

    return obs.content


def _setup_logging(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool) -> None:
    """Setup logging for the evaluation instance."""
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance.instance_id)


def _build_instruction(instance: pd.Series, metadata: EvalMetadata) -> str:
    """Build the instruction string for the agent."""
    instruction = f"Please fix the following issue.\nIMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\nPlease encapsulate your final answer (answer ONLY) within <solution> and </solution>.\nFor example: The answer to the question is <solution> 42 </solution>.\n# Problem \n{
        instance.description}\n\n"
    instruction += (
        "IMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\n"
    )
    instruction += INST_SUFFIXES[metadata.agent_class]
    return instruction


def _run_agent_evaluation(config, instruction: str, metadata: EvalMetadata, runtime: Runtime) -> State:
    """Run the agent evaluation and return the state."""
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
    return state


def _extract_raw_answer_from_agent_events(state: State) -> str:
    """Extract raw answer from agent events in state history."""
    for event in reversed(state.history):
        if event.source == "agent":
            if isinstance(event, AgentFinishAction) or (
                not isinstance(event, MessageAction) and isinstance(event, CmdRunAction)
            ):
                return event.thought
            elif isinstance(event, MessageAction):
                return event.content
    return ""


def _parse_solution_from_answer(raw_ans: str) -> str:
    """Parse solution from raw answer using regex."""
    agent_answer = re.findall("<solution>(.*?)</solution>", raw_ans, re.DOTALL)
    if len(agent_answer) == 0:
        logger.warning("Failed to parse model answer: %s", raw_ans)
        return raw_ans
    return agent_answer[0]


def _extract_agent_answer_from_history(state: State) -> str:
    """Extract agent answer from the state history."""
    logger.info("Retrieving agent answer from history.")

    raw_ans = _extract_raw_answer_from_agent_events(state)
    return _parse_solution_from_answer(raw_ans)


def _create_eval_output(
    instance: pd.Series, metadata: EvalMetadata, instruction: str, state: State, agent_answer: str, final_ans: str
) -> EvalOutput:
    """Create the final evaluation output."""
    comparison_method = instance.comparison_method
    logger.info(
        "Final message: %s | Ground truth: %s | Comparison method: %s", agent_answer, final_ans, comparison_method
    )

    test_result = compare_results(comparison_method, agent_answer, final_ans)
    histories = compatibility_for_eval_history_pairs(state.history)
    metrics = get_metrics(state)

    return EvalOutput(
        instance_id=instance.instance_id,
        instance=instance.to_dict(),
        instruction=instruction,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
        test_result={
            "agent_answer": agent_answer,
            "final_answer": final_ans,
            "check_method": comparison_method,
            "result": test_result,
        },
    )


def process_instance(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True) -> EvalOutput:
    """Process a single evaluation instance."""
    config = get_config(metadata)

    # Setup logging
    _setup_logging(instance, metadata, reset_logger)

    # Build instruction
    instruction = _build_instruction(instance, metadata)

    # Setup runtime
    runtime: Runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance=instance)

    # Run agent evaluation
    state = _run_agent_evaluation(config, instruction, metadata, runtime)

    # Complete runtime and get results
    return_val = complete_runtime(runtime, instance)
    agent_answer = return_val["agent_answer"]
    final_ans = return_val["final_ans"]

    # Extract agent answer if not provided
    if agent_answer is None:
        agent_answer = _extract_agent_answer_from_history(state)

    # Create and return evaluation output
    return _create_eval_output(instance, metadata, instruction, state, agent_answer, final_ans)


if __name__ == "__main__":
    args = parse_arguments()
    dataset = load_dataset("iFurySt/AgentBench")  # nosec B615 - Safe: evaluation benchmark dataset
    agent_bench_tests = dataset["osbench"].to_pandas()
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config, "AgentBench-OS", args.agent_cls, args.max_iterations, args.eval_note, args.eval_output_dir
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    instances = prepare_dataset(agent_bench_tests, output_file, args.eval_n_limit)
    run_evaluation(instances, metadata, output_file, args.eval_num_workers, process_instance)
