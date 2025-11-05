import asyncio
import json
import os
from typing import TYPE_CHECKING
import pandas as pd
from datasets import load_dataset
from litellm import completion as litellm_completion
import openhands.agenthub
from evaluation.benchmarks.swe_bench.run_infer import (
    AgentFinishedCritic,
    complete_runtime,
    filter_dataset,
    get_config,
    initialize_runtime,
)
from evaluation.benchmarks.swe_bench.run_infer import get_instruction as base_get_instruction
from evaluation.utils.shared import (
    EvalException,
    EvalMetadata,
    EvalOutput,
    get_metrics,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from openhands.controller.state.state import State
from openhands.core.config import get_evaluation_parser, get_llm_config_arg
from openhands.core.config.condenser_config import NoOpCondenserConfig
from openhands.core.config.utils import get_condenser_config_arg
from openhands.core.logger import openhands_logger as logger

if TYPE_CHECKING:
    from openhands.core.config import OpenHandsConfig
    from openhands.runtime.base import Runtime
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import MessageAction
from openhands.events.serialization.event import event_from_dict, event_to_dict
from openhands.utils.async_utils import call_async_from_sync

USE_HINT_TEXT = os.environ.get("USE_HINT_TEXT", "false").lower() == "true"
USE_INSTANCE_IMAGE = os.environ.get("USE_INSTANCE_IMAGE", "false").lower() == "true"
RUN_WITH_BROWSING = os.environ.get("RUN_WITH_BROWSING", "false").lower() == "false"


class FakeUser:

    def __init__(self, issue, hints, files):
        self.system_message = f"""\n        You are a GitHub user reporting an issue. Here are the details of your issue and environment:\n\n        Issue: {issue}\n\n        Hints: {hints}\n\n        Files relative to your current directory: {files}\n\n        Your task is to respond to questions from a coder who is trying to solve your issue. The coder has a summarized version of the issue you have. Follow these rules:\n        1. If the coder asks a question that is directly related to the information in the issue you have, provide that information.\n        2. Always stay in character as a user reporting an issue, not as an AI assistant.\n        3. Keep your responses concise and to the point.\n        4. The coder has limited turns to solve the issue. Do not interact with the coder beyond 3 turns.\n\n        Respond with "I don't have that information" if the question is unrelated or you're unsure.\n        """
        self.chat_history = [{"role": "system", "content": self.system_message}]
        self.turns = 0
        self.llm_config = get_llm_config_arg("llm.fake_user")

    def generate_reply(self, question):
        if self.turns > 3:
            return "Please continue working on the task. Do NOT ask for more help."
        self.chat_history.append({"role": "user", "content": question.content})
        response = litellm_completion(
            model=self.llm_config.model,
            messages=self.chat_history,
            api_key=self.llm_config.api_key.get_secret_value(),
            temperature=self.llm_config.temperature,
            base_url=self.llm_config.base_url,
        )
        reply = response.choices[0].message.content
        self.chat_history.append({"role": "assistant", "content": reply})
        self.turns += 1
        return reply


fake_user = None


def get_fake_user_response(state: State) -> str:
    global fake_user
    if not fake_user:
        return "Please continue working on the task."
    if last_agent_message := state.get_last_agent_message():
        return fake_user.generate_reply(last_agent_message)
    return "Please continue working on the task."


AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {"CodeActAgent": get_fake_user_response}


def get_instruction(instance: pd.Series, metadata: EvalMetadata) -> MessageAction:
    instance_copy = instance.copy()
    instance_copy.problem_statement = f"{instance.problem_statement}\n\nHints:\nThe user has not provided all the necessary details about the issue, and there are some hidden details that are helpful. Please ask the user specific questions using non-code commands to gather the relevant information that the user has to help you solve the issue. Ensure you have all the details you require to solve the issue."
    return base_get_instruction(instance_copy, metadata)


def process_instance(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True) -> EvalOutput:
    config = get_config(instance, metadata)
    _setup_fake_user(instance)
    _setup_logging(instance, metadata, reset_logger)

    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)

    try:
        initialize_runtime(runtime, instance, metadata)
        message_action = get_instruction(instance, metadata)
        state = _run_agent_controller(config, message_action, runtime, metadata)
        _validate_agent_state(state)
        return_val = complete_runtime(runtime, instance)
        git_patch = return_val["git_patch"]
        logger.info("Got git diff for instance %s:\n--------\n%s\n--------", instance.instance_id, git_patch)
    finally:
        runtime.close()

    return _create_eval_output(instance, metadata, message_action, state, git_patch)


def _setup_fake_user(instance: pd.Series) -> None:
    """Setup fake user for interactive evaluation."""
    global fake_user
    original_issue = instance.original_issue
    issue = str(original_issue)
    fake_user = FakeUser(issue=issue, hints=instance.hints_text, files=instance.files)


def _setup_logging(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool) -> None:
    """Setup logging for the instance."""
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance.instance_id)


def _run_agent_controller(
    config: OpenHandsConfig, message_action: MessageAction, runtime: Runtime, metadata: EvalMetadata
) -> State | None:
    """Run the agent controller and return the state."""
    return asyncio.run(
        run_controller(
            config=config,
            initial_user_action=message_action,
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[metadata.agent_class],
        )
    )


def _validate_agent_state(state: State | None) -> None:
    """Validate the agent state and handle fatal errors."""
    if (
        state
        and state.last_error
        and ("fatal error during agent execution" in state.last_error)
        and ("stuck in a loop" not in state.last_error)
    ):
        raise EvalException("Fatal error detected: " + state.last_error)


def _create_eval_output(
    instance: pd.Series, metadata: EvalMetadata, message_action: MessageAction, state: State | None, git_patch: str
) -> EvalOutput:
    """Create the evaluation output."""
    if state is None:
        raise ValueError("State should not be None.")

    test_result = {"git_patch": git_patch}
    histories = [event_to_dict(event) for event in state.history]
    metrics = get_metrics(state)
    instruction = _build_instruction_with_images(message_action)

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


def _build_instruction_with_images(message_action: MessageAction) -> str:
    """Build instruction string with image URLs if present."""
    instruction = message_action.content
    if message_action.image_urls:
        instruction += "\n\n<image_urls>" + "\n".join(message_action.image_urls) + "</image_urls>"
    return instruction


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument("--dataset", type=str, default="cmu-lti/interactive-swe", help="dataset to evaluate on")
    parser.add_argument("--split", type=str, default="test", help="split to evaluate on")
    args, _ = parser.parse_known_args()
    dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info("Loaded dataset %s with split %s: %s tasks", args.dataset, args.split, len(swe_bench_tests))
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
    details = {"mode": "interact"}
    _agent_cls = openhands.agenthub.Agent.get_cls(args.agent_cls)
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
