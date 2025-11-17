"""Implements evaluation of agents on HumanEvalFix from the HumanEvalPack benchmark introduced in.

"OctoPack: Instruction Tuning Code Large Language Models" (https://arxiv.org/abs/2308.07124).
Please see https://github.com/bigcode-project/bigcode-evaluation-harness/blob/main/bigcode_eval/tasks/humanevalpack.py
for the reference implementation used in the paper.

TODOs:
- Potentially support other HumanEvalPack datasets (Explain & Synthesize)
- Support other languages (currently only Python)
"""

import asyncio
import os
import tempfile
from typing import Any
import pandas as pd
from datasets import load_dataset
from evaluate import load
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    codeact_user_response,
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
from forge.core.config import ForgeConfig, get_llm_config_arg, parse_arguments
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import CmdRunAction, MessageAction
from forge.events.observation import CmdOutputObservation
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync

IMPORT_HELPER = {
    "python": [
        "import math",
        "import re",
        "import sys",
        "import copy",
        "import datetime",
        "import itertools",
        "import collections",
        "import heapq",
        "import statistics",
        "import functools",
        "import hashlib",
        "import numpy",
        "import numpy as np",
        "import string",
        "from typing import *",
        "from collections import *",
    ]
}
LANGUAGE_TO_TIMEOUT = {"python": 10}
LANGUAGE_TO_NUM_WORKERS = {"python": 4}
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}
AGENT_CLS_TO_INST_SUFFIX = {
    "CodeActAgent": 'When you think you have fixed the issue through code changes, please finish the interaction using the "finish" tool.\n'
}


def get_config(metadata: EvalMetadata) -> ForgeConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "python:3.12-bookworm"
    config = get_FORGE_config_for_eval(
        metadata=metadata, runtime="docker", sandbox_config=sandbox_config
    )
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    return config


def _get_instance_id(instance: pd.Series) -> str:
    return instance.instance_id.replace("/", "__")


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
    problem_statement = (
        instance.declaration + instance.buggy_solution + "\n" + instance.test
    )
    filename = f"{_get_instance_id(instance)}.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        host_script_path = os.path.join(tmpdir, filename)
        with open(host_script_path, "w", encoding="utf-8") as f:
            f.write(problem_statement)
        runtime.copy_to(host_script_path, "/workspace")
    action = CmdRunAction(command=f"ls /workspace/{_get_instance_id(instance)}.py")
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("%s BEGIN Runtime Completion Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    language = "python"
    timeout = 10
    code_metric = load("Muennighoff/code_eval_octopack")
    timeout = LANGUAGE_TO_TIMEOUT[language]
    num_workers = LANGUAGE_TO_NUM_WORKERS[language]
    python_imports = "\n".join(IMPORT_HELPER[language])
    action = CmdRunAction(command=f"cat /workspace/{_get_instance_id(instance)}.py")
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    function = obs.content.replace("\r\n", "\n")
    logger.info("Function: %s", function)
    function = [[python_imports + "\n" + function]]
    results, logs = code_metric.compute(
        references=[instance.test],
        predictions=function,
        language=language,
        timeout=timeout,
        num_workers=num_workers,
    )
    test_result = {
        "result": results,
        "metadata": {"logs": logs, "timeout": timeout, "num_workers": num_workers},
    }
    logger.info("%s END Runtime Completion Fn %s", "-" * 50, "-" * 50)
    return test_result


def process_instance(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True
) -> EvalOutput:
    config = get_config(metadata)
    sid = _get_instance_id(instance)
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance.instance_id)
    problem_statement = (
        instance.declaration + instance.buggy_solution + "\n" + instance.test
    )
    instruction = f"Please fix the function in {sid}.py such that all test cases pass.\nEnvironment has been set up for you to start working. You may assume all necessary tools are installed.\n\n# Problem Statement\n{problem_statement}\n\n"
    instruction += "IMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\nYou should NOT modify any existing test case files. If needed, you can add new test cases in a NEW file to reproduce the issue.\nYou SHOULD INCLUDE PROPER INDENTATION in your edit commands.\n"
    instruction += AGENT_CLS_TO_INST_SUFFIX[metadata.agent_class]
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance)
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN.get(
                metadata.agent_class
            ),
        )
    )
    if state is None:
        raise ValueError("State should not be None.")
    metrics = get_metrics(state)
    test_result = complete_runtime(runtime, instance)
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
    args = parse_arguments()
    dataset = load_dataset("bigcode/humanevalpack", "python")  # nosec B615 - Safe: evaluation benchmark dataset
    hefix_tests = dataset["test"].to_pandas()
    hefix_tests.rename(columns={"task_id": "instance_id"}, inplace=True)
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config,
        "humanevalfix-python",
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    instances = prepare_dataset(hefix_tests, output_file, args.eval_n_limit)
    run_evaluation(
        instances, metadata, output_file, args.eval_num_workers, process_instance
    )
