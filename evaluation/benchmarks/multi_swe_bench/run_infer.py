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
from forge.core.config import (
    AgentConfig,
    ForgeConfig,
    get_evaluation_parser,
    get_llm_config_arg,
)
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import CmdRunAction, FileReadAction, MessageAction
from forge.events.observation import CmdOutputObservation, ErrorObservation
from forge.events.serialization.event import event_to_dict
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync
from forge.utils.shutdown_listener import sleep_if_should_continue

USE_HINT_TEXT = os.environ.get("USE_HINT_TEXT", "false").lower() == "true"
USE_INSTANCE_IMAGE = os.environ.get("USE_INSTANCE_IMAGE", "true").lower() == "true"
RUN_WITH_BROWSING = os.environ.get("RUN_WITH_BROWSING", "false").lower() == "true"
DOCKER_IMAGE_PREFIX = os.environ.get("EVAL_DOCKER_IMAGE_PREFIX", "")
LANGUAGE = os.environ.get("LANGUAGE", "python")
logger.info("Using docker image prefix: %s", DOCKER_IMAGE_PREFIX)
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": codeact_user_response}


def _get_swebench_workspace_dir_name(instance: pd.Series) -> str:
    return f"{instance.repo}__{instance.version}".replace("/", "__")


def get_instruction(instance: pd.Series, metadata: EvalMetadata):
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
    instructions = {
        "python": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a python code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Python environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script to reproduce the error and execute it with `python <filename.py>` using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "java": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a Java code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Java environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a Java class to reproduce the error and execute it by first compiling with `javac <classname>.java` and then running with `java <classname>` using the BashTool, to confirm the error\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script or class and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce class or script, and run them to make sure your fix handles these cases as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions or classes you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "go": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a Go code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Go environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script or a function to reproduce the error and execute it with `go run <filename.go>` using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "c": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a C code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development C environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script to reproduce the error by compiling your C code (for example, using `gcc <filename.c> -o <executable>`) and then running the executable using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "cpp": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a C++ code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development C++ environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create or adapt a small executable (e.g., a main file or a test driver) to reproduce the issue. Build and run it (for example, by using `g++ -o reproduce reproduce.cpp && ./reproduce` via the BashTool) to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "javascript": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a Javascript code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Javascript environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script to reproduce the error and execute it with `node <filename.js>` using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "typescript": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a Typescript code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Typescript environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a script to reproduce the error and execute it with `ts-node <filename.ts>` using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
        "rust": f"<uploaded_files>\n/workspace/{
            workspace_dir_name
        }\n</uploaded_files>\nI've uploaded a Rust code repository in the directory {
            workspace_dir_name
        }. Consider the following issue description:\n\n<issue_description>\n{
            instance.problem_statement
        }\n</issue_description>\n\nCan you help me implement the necessary changes to the repository so that the requirements specified in the <issue_description> are met?\nI've already taken care of all changes to any of the test files described in the <issue_description>. This means you DON'T have to modify the testing logic or any of the tests in any way!\nAlso the development Rust environment is already set up for you (i.e., all dependencies already installed), so you don't need to install other packages.\nYour task is to make the minimal changes to non-test files in the /workspace directory to ensure the <issue_description> is satisfied.\nFollow these steps to resolve the issue:\n1. As a first step, it might be a good idea to explore the repo to familiarize yourself with its structure.\n2. Create a reproduction script (or binary) that triggers the error and execute it with `cargo run --bin <filename>` using the BashTool, to confirm the error.\n3. Edit the sourcecode of the repo to resolve the issue.\n4. Rerun your reproduce script and confirm that the error is fixed!\n5. Think about edgecases, add comprehensive tests for them in your reproduce script, and run them to make sure your fix handles them as well.\n6. Once you are done with the initial implementation, please carefully re-read the problem description and check the difference between the current code and the base commit {
            instance['base_commit']
        }. Do you think that the issue has been completely and comprehensively solved? Write tests to check the correctness of the solution, specifically focusing on tests that may point out any remaining problems that are not yet solved. Run all of the tests in the repo and check if any of them fail, and if they do fix the code. Repeat this process of carefully reading the problem description and current implementation, testing, and fixing any problems until you are confident that the current implementation is correct. Find and run any tests in the repo that are related to:\n   - The issue you are fixing\n   - The files you modified\n   - The functions you changed\n   Make sure all these tests pass with your changes.\nYour thinking should be thorough and so it's fine if it's very long.\n",
    }
    instruction = instructions.get(LANGUAGE.lower())
    if instruction and RUN_WITH_BROWSING:
        instruction += (
            "<IMPORTANT!>\nYou SHOULD NEVER attempt to browse the web. </IMPORTANT!>\n"
        )
    return instruction


def get_instance_docker_image(instance: pd.Series):
    if LANGUAGE == "python":
        image_name = "sweb.eval.x86_64." + instance["instance_id"]
        image_name = image_name.replace("__", "_s_")
        return (DOCKER_IMAGE_PREFIX.rstrip("/") + "/" + image_name).lower()
    else:
        container_name = instance.get("repo", "").lower()
        container_name = container_name.replace("/", "_m_")
        instance_id = instance.get("instance_id", "")
        tag_suffix = instance_id.split("-")[-1] if instance_id else ""
        container_tag = f"pr-{tag_suffix}"
        return f"mswebench/{container_name}:{container_tag}"


def get_config(instance: pd.Series, metadata: EvalMetadata) -> ForgeConfig:
    if USE_INSTANCE_IMAGE:
        base_container_image = get_instance_docker_image(instance)
        logger.info(
            "Using instance container image: %s. Please make sure this image exists. Submit an issue on https://github.com/All-Hands-AI/Forge if you run into any issues.",
            base_container_image,
        )
    else:
        SWE_BENCH_CONTAINER_IMAGE = "ghcr.io/opendevin/eval-swe-bench:full-v1.2.1"
        base_container_image = SWE_BENCH_CONTAINER_IMAGE
        logger.info("Using swe-bench container image: %s", base_container_image)
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
    REPO_NAME = instance["repo"].split("/")[-1]
    action = CmdRunAction(
        command=f"""echo 'export SWE_INSTANCE_ID={
            instance["instance_id"]
        }' >> ~/.bashrc && echo 'export PIP_CACHE_DIR=~/.cache/pip' >> ~/.bashrc && echo "alias git='git --no-pager'" >> ~/.bashrc && echo 'export REPO_NAME={
            REPO_NAME
        }' >> ~/.bashrc"""
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
    if USE_INSTANCE_IMAGE:
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
    else:
        action = CmdRunAction(command="source /swe_util/swe_entry.sh")
        action.set_hard_timeout(1800)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert_and_raise(
            obs.exit_code == 0, f"Failed to source /swe_util/swe_entry.sh: {str(obs)}"
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
    obs: CmdOutputObservation
    workspace_dir_name = _get_swebench_workspace_dir_name(instance)
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
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to cd to /workspace/{workspace_dir_name}: {str(obs)}",
    )
    action = CmdRunAction(command='git config --global core.pager ""')
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f'Failed to git config --global core.pager "": {str(obs)}',
    )
    action = CmdRunAction(command="git add -A")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to git add -A: {str(obs)}",
    )
    action = CmdRunAction(
        command='\n        for file in $(git status --porcelain | grep -E "^(M| M|\\?\\?|A| A)" | cut -c4-); do\n            if [ -f "$file" ] && (file "$file" | grep -q "executable" || git check-attr binary "$file" | grep -q "binary: set"); then\n                git rm -f "$file" 2>/dev/null || rm -f "$file"\n                echo "Removed: $file"\n            fi\n        done\n        '
    )
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert_and_raise(
        isinstance(obs, CmdOutputObservation) and obs.exit_code == 0,
        f"Failed to remove binary files: {str(obs)}",
    )
    n_retries = 0
    git_patch = None
    while n_retries < 5:
        action = CmdRunAction(
            command=f"git diff --no-color --cached {instance['base_commit']} > patch.diff"
        )
        action.set_hard_timeout(max(300 + 100 * n_retries, 600))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        n_retries += 1
        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                break
            logger.info("Failed to get git diff, retrying...")
            sleep_if_should_continue(10)
        elif isinstance(obs, ErrorObservation):
            logger.error("Error occurred: %s. Retrying...", obs.content)
            sleep_if_should_continue(10)
        else:
            assert_and_raise(False, f"Unexpected observation type: {str(obs)}")
    action = FileReadAction(path="patch.diff")
    action.set_hard_timeout(max(300 + 100 * n_retries, 600))
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    git_patch = obs.content
    assert_and_raise(git_patch is not None, "Failed to get git diff (None)")
    logger.info("-" * 30)
    logger.info("END Runtime Completion Fn")
    logger.info("-" * 30)
    return {"git_patch": git_patch}


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

    def remove_binary_diffs(patch_text):
        lines = patch_text.splitlines()
        cleaned_lines = []
        block = []
        is_binary_block = False
        for line in lines:
            if line.startswith("diff --git "):
                if block and (not is_binary_block):
                    cleaned_lines.extend(block)
                block = [line]
                is_binary_block = False
            elif "Binary files" in line:
                is_binary_block = True
                block.append(line)
            else:
                block.append(line)
        if block and (not is_binary_block):
            cleaned_lines.extend(block)
        return "\n".join(cleaned_lines)

    git_patch = remove_binary_diffs(git_patch)
    test_result = {"git_patch": git_patch}
    if state is None:
        raise ValueError("State should not be None.")
    histories = [event_to_dict(event) for event in state.history]
    metrics = get_metrics(state)
    output = EvalOutput(
        instance_id=instance.instance_id,
        instruction=instruction,
        instance=instance.to_dict(),
        test_result=test_result,
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
    )
    return output


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
    dataset = load_dataset("json", data_files=args.dataset)  # nosec B615 - Safe: evaluation benchmark dataset
    dataset = dataset[args.split]
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info(
        "Loaded dataset %s with split %s: %s tasks",
        args.dataset,
        args.split,
        len(swe_bench_tests),
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
    print(f"### OUTPUT FILE: {output_file} ###")
    instances = prepare_dataset(swe_bench_tests, output_file, args.eval_n_limit)
    if len(instances) > 0 and (
        not isinstance(
            instances["FAIL_TO_PASS"][instances["FAIL_TO_PASS"].index[0]], str
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
        timeout_seconds=120 * 60,
        max_retries=5,
    )
    check_maximum_retries_exceeded(metadata.eval_output_dir)
