"""Implements inference on JetBrains CI builds repair baselines.

Please see https://github.com/JetBrains-Research/lca-baselines/tree/main/ci-builds-repair
and https://huggingface.co/datasets/JetBrains-Research/lca-ci-builds-repair

TODOs:
- Add EXP_NAME
"""

import asyncio
import json
import os
from typing import Any
import pandas as pd
import ruamel.yaml
from datasets import load_dataset
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
)
from openhands.controller.state.state import State
from openhands.core.config import OpenHandsConfig, get_evaluation_parser, get_llm_config_arg, load_openhands_config
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync


def get_config(metadata: EvalMetadata) -> OpenHandsConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "python:3.12-bookworm"
    config = get_openhands_config_for_eval(metadata=metadata, runtime="docker", sandbox_config=sandbox_config)
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    return config


config = load_openhands_config()


def load_bench_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    yaml = ruamel.yaml.YAML(typ="rt")
    with open(config_path, "r", encoding='utf-8') as file:
        return yaml.load(file)


bench_config = load_bench_config()
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}
AGENT_CLS_TO_INST_SUFFIX = {
    "CodeActAgent": 'When you think you have completed the task, please finish the interaction using the "finish" tool.\n'
}


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("%s BEGIN Runtime Initialization Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    lca_path = bench_config["LCA_PATH"]
    lca_ci_path = os.path.join(lca_path, "lca-baselines", "ci-builds-repair", "ci-builds-repair-benchmark")
    repo_name = instance["repo_name"]
    repos_path = bench_config["repos_folder"]
    repo_owner = instance["repo_owner"]
    repo_path = os.path.join(repos_path, f"{repo_owner}__{repo_name}")
    model_name = bench_config["model_name"]
    action = CmdRunAction(command=f"mkdir {lca_path}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command=f"cd {lca_path}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    lca_repo_url = "https://github.com/juanmichelini/lca-baselines"
    action = CmdRunAction(command=f"git clone {lca_repo_url}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command=f"cd {lca_ci_path}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    action = CmdRunAction(command="git switch open-hands-integration")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    with open(config_path, "r", encoding='utf-8') as file:
        config_as_text = file.read()
    commandf = f"echo '{config_as_text}' > config.yaml"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    token_gh = bench_config["token_gh"]
    commandf = f"export TOKEN_GH={token_gh}"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    action = CmdRunAction(command="poetry install")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    commandf = f"poetry run python run_get_datapoint.py --model-name {model_name} --id {
        instance['id']} > branch_name.txt"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    if obs.exit_code != 0:
        print(f"run_get_datapoint.py failed at {instance['id']} with {obs.content}")
    assert obs.exit_code == 0
    commandf = "cat branch_name.txt"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    bench_config["user_branch_name"] = obs.content
    action = CmdRunAction(command=f"cd {repo_path}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)


def complete_runtime(runtime: Runtime, instance: pd.Series) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.
    """
    logger.info("%s BEGIN Runtime Completion Fn %s", "-" * 50, "-" * 50)
    obs: CmdOutputObservation
    model_name = bench_config["model_name"]
    lca_path = bench_config["LCA_PATH"]
    lca_ci_path = os.path.join(lca_path, "lca-baselines", "ci-builds-repair", "ci-builds-repair-benchmark")
    user_branch_name = bench_config["user_branch_name"]
    token_gh = bench_config["token_gh"]
    commandf = f"export TOKEN_GH={token_gh}"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    action = CmdRunAction(command=f"cd {lca_ci_path}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0
    commandf = f"poetry run python run_push_datapoint.py --id {
        instance['id']} --model-name {model_name} --user-branch-name {user_branch_name} > single_output.json"
    logger.info("Running push script: %s", commandf)
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    commandf = "cat single_output.json"
    action = CmdRunAction(command=commandf)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    result = json.loads(obs.content)
    logger.info("%s END Runtime Completion Fn %s", "-" * 50, "-" * 50)
    return result


def process_instance(instance: Any, metadata: EvalMetadata, reset_logger: bool = True):
    config = get_config(metadata)
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance["instance_id"], log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance["instance_id"])
    repo_name = instance["repo_name"]
    repo_workflow = instance["workflow_path"]
    repo_logs = instance["logs"]
    repos_path = bench_config["repos_folder"]
    repo_owner = instance["repo_owner"]
    repo_path = os.path.join(repos_path, f"{repo_owner}__{repo_name}")
    instruction_no_oracle = f"\n<uploaded_files>\n{repo_path}\n</uploaded_files>\n\nI've uploaded a python code repository in the directory {repo_path}, Consider the following issue:\n\n<issue_description>\nThe repository must pass the CI workflow {repo_workflow}.\nbut it gave the following error\n{repo_logs}\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Python environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the {repo_path} directory to ensure the <issue_description> is satisfied.\n\nFollow these phases to resolve the issue:\n\nPhase 1. READING: read the problem and reword it in clearer terms\n   1.1 If there are code or config snippets. Express in words any best practices or conventions in them.\n   1.2 Hightlight message errors, method names, variables, file names, stack traces, and technical details.\n   1.3 Explain the problem in clear terms.\n   1.4 Enumerate the steps to reproduce the problem.\n   1.5 Hightlight any best practices to take into account when testing and fixing the issue\n\nPhase 2. RUNNING: install and run the tests on the repository\n   2.1 Follow the readme\n   2.2 Install the environment and anything needed\n   2.2 Iterate and figure out how to run the tests\n\nPhase 3. EXPLORATION: find the files that are related to the problem and possible solutions\n   3.1 Use `grep` to search for relevant methods, classes, keywords and error messages.\n   3.2 Identify all files related to the problem statement.\n   3.3 Propose the methods and files to fix the issue and explain why.\n   3.4 From the possible file locations, select the most likely location to fix the issue.\n\nPhase 4. TEST CREATION: before implementing any fix, create a script to reproduce and verify the issue.\n   4.1 Look at existing test files in the repository to understand the test format/structure.\n   4.2 Create a minimal reproduction script that reproduces the located issue.\n   4.3 Run the reproduction script to confirm you are reproducing the issue.\n   4.4 Adjust the reproduction script as necessary.\n\nPhase 5. FIX ANALYSIS: state clearly the problem and how to fix it\n   5.1 State clearly what the problem is.\n   5.2 State clearly where the problem is located.\n   5.3 State clearly how the test reproduces the issue.\n   5.4 State clearly the best practices to take into account in the fix.\n   5.5 State clearly how to fix the problem.\n\nPhase 6. FIX IMPLEMENTATION: Edit the source code to implement your chosen solution.\n   6.1 Make minimal, focused changes to fix the issue.\n\nPhase 7. VERIFICATION: Test your implementation thoroughly.\n   7.1 Run your reproduction script to verify the fix works.\n   7.2 Add edge cases to your test script to ensure comprehensive coverage.\n   7.3 Run existing tests related to the modified code to ensure you haven't broken anything. Run any tests in the repository related to:\n     7.2.1 The issue you are fixing\n     7.2.2 The files you modified\n     7.2.3 The functions you changed\n   7.4 If any tests fail, revise your implementation until all tests pass\n\nPhase 8. REVIEW: Carefully re-read the problem description and compare your changes with the base commit {
        instance['sha_fail']}.\n   8.1 Ensure you've fully addressed all requirements.\n\nOnce all phases are done, announce: 'Agent Task Complete'.\nBe thorough in your exploration, testing, and reasoning. It's fine if your thinking process is lengthy - quality and completeness are more important than brevity.\n"
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance)
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction_no_oracle),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN.get(metadata.agent_class),
        )
    )
    assert state is not None
    metrics = get_metrics(state)
    test_result = complete_runtime(runtime, instance)
    histories = compatibility_for_eval_history_pairs(state.history)
    return EvalOutput(
        instance_id=instance["instance_id"],
        instruction=instruction_no_oracle,
        metadata=metadata,
        history=histories,
        test_result=test_result,
        metrics=metrics,
    )


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "-s", "--eval-split", type=str, default="test", choices=["test"], help="data split to evaluate on, must be test"
    )
    args, _ = parser.parse_known_args()
    data_split = args.eval_split
    bench = load_dataset(
        "JetBrains-Research/lca-ci-builds-repair", split=data_split
    ).to_pandas()  # nosec B615 - Safe: evaluation benchmark dataset
    bench = bench[bench["id"] != 126]
    bench = bench[bench["id"] != 145]
    bench["instance_id"] = bench["id"].astype(str)
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    metadata = make_metadata(
        llm_config,
        f"jetbrains-lca-ci--{data_split}",
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
    )
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    instances = prepare_dataset(bench, output_file, args.eval_n_limit)
    run_evaluation(instances, metadata, output_file, args.eval_num_workers, process_instance)
