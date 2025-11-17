import json
import logging
import multiprocessing as mp
import os
import pathlib
import signal
import subprocess
import time
import traceback
from contextlib import contextmanager
from inspect import signature
from typing import Any, Awaitable, Callable, TextIO
import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm
from forge.controller.state.state import State
from forge.core.config import LLMConfig, SandboxConfig
from forge.core.config.agent_config import AgentConfig
from forge.core.config.condenser_config import CondenserConfig, NoOpCondenserConfig
from forge.core.exceptions import (
    AgentRuntimeBuildError,
    AgentRuntimeDisconnectedError,
    AgentRuntimeError,
    AgentRuntimeNotFoundError,
    AgentRuntimeNotReadyError,
    AgentRuntimeTimeoutError,
    AgentRuntimeUnavailableError,
)
from forge.core.logger import get_console_handler
from forge.core.logger import forge_logger as logger
from forge.events.action import Action
from forge.events.action.message import MessageAction
from forge.events.event import Event
from forge.events.serialization.event import event_to_dict
from forge.events.utils import get_pairs_from_events
from forge.memory.condenser import get_condensation_metadata


class EvalMetadata(BaseModel):
    agent_class: str
    llm_config: LLMConfig
    agent_config: AgentConfig | None = None
    max_iterations: int
    eval_output_dir: str
    start_time: str
    git_commit: str
    dataset: str | None = None
    data_split: str | None = None
    details: dict[str, Any] | None = None
    condenser_config: CondenserConfig | None = None
    instruction_template_name: str | None = None


class EvalOutput(BaseModel):
    instance_id: str
    test_result: dict[str, Any]
    instruction: str | None = None
    metadata: EvalMetadata | None = None
    history: (
        list[dict[str, Any]] | list[tuple[dict[str, Any], dict[str, Any]]] | None
    ) = None
    metrics: dict[str, Any] | None = None
    error: str | None = None
    instance: dict[str, Any] | None = None


class EvalException(Exception):
    pass


class EvalTimeoutException(Exception):
    pass


@contextmanager
def timeout(seconds: int):
    """Context manager for timing out operations.

    Args:
        seconds: The timeout duration in seconds.

    Raises:
        EvalTimeoutException: If the operation times out.
    """

    def timeout_handler(signum, frame):
        raise EvalTimeoutException(f"Function timed out after {seconds} seconds")

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


def _build_encapsulation_string(encapsulate_solution: bool) -> str:
    """Build the encapsulation string if solution encapsulation is required."""
    if encapsulate_solution:
        return "Your final answer MUST be encapsulated within <solution> and </solution>.\nFor example: The answer to the question is <solution> 42 </solution>.\n"
    return ""


def _build_base_message(encapsulate_solution: bool) -> str:
    """Build the base message for the user response."""
    encaps_str = _build_encapsulation_string(encapsulate_solution)
    return f"Please continue working on the task on whatever approach you think is suitable.\nWhen you think you have solved the question, please use the finish tool and include your final answer in the message parameter of the finish tool.\n{encaps_str}IMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n"


def _check_for_parsed_answer(
    state: State, try_parse: Callable[[Action], str] | None
) -> bool:
    """Check if there's a parsed answer from the last action."""
    if try_parse is None:
        return False

    last_action = next(
        (event for event in reversed(state.history) if isinstance(event, Action)), None
    )
    if last_action is None:
        return False

    ans = try_parse(last_action)
    return ans is not None


def _should_add_give_up_message(state: State) -> bool:
    """Check if we should add the give-up message based on user message count."""
    if not state.history:
        return False

    user_msgs = [
        event
        for event in state.history
        if isinstance(event, MessageAction) and event.source == "user"
    ]
    return len(user_msgs) >= 2


def codeact_user_response(
    state: State,
    encapsulate_solution: bool = False,
    try_parse: Callable[[Action], str] | None = None,
) -> str:
    msg = _build_base_message(encapsulate_solution)

    if state.history:
        if _check_for_parsed_answer(state, try_parse):
            return "/exit"

        if _should_add_give_up_message(state):
            return (
                msg
                + 'If you want to give up, use the "finish" tool to finish the interaction.\n'
            )

    return msg


def cleanup():
    """Clean up child processes created during evaluation."""
    print("Cleaning up child processes...")
    for process in mp.active_children():
        print(f"Terminating child process: {process.name}")
        process.terminate()
        process.join()


def make_metadata(
    llm_config: LLMConfig,
    dataset_name: str,
    agent_class: str,
    max_iterations: int,
    eval_note: str | None,
    eval_output_dir: str,
    data_split: str | None = None,
    details: dict[str, Any] | None = None,
    agent_config: AgentConfig | None = None,
    condenser_config: CondenserConfig | None = None,
) -> EvalMetadata:
    model_name = llm_config.model.split("/")[-1]
    model_path = model_name.replace(":", "_").replace("@", "-")
    eval_note = f"_N_{eval_note}" if eval_note else ""
    eval_output_path = os.path.join(
        eval_output_dir,
        dataset_name,
        agent_class,
        f"{model_path}_maxiter_{max_iterations}{eval_note}",
    )
    pathlib.Path(eval_output_path).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.path.join(eval_output_path, "logs")).mkdir(
        parents=True, exist_ok=True
    )
    logger.info("Using evaluation output directory: %s", eval_output_path)
    metadata = EvalMetadata(
        agent_class=agent_class,
        llm_config=llm_config,
        agent_config=agent_config,
        max_iterations=max_iterations,
        eval_output_dir=eval_output_path,
        start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"])
        .decode("utf-8")
        .strip(),
        dataset=dataset_name,
        data_split=data_split,
        details=details,
        condenser_config=condenser_config or NoOpCondenserConfig(),
        instruction_template_name=os.environ.get("INSTRUCTION_TEMPLATE_NAME"),
    )
    metadata_json = metadata.model_dump_json()
    logger.info("Metadata: %s", metadata_json)
    with open(os.path.join(eval_output_path, "metadata.json"), "w") as f:
        f.write(metadata_json)
    return metadata


def prepare_dataset(
    dataset: pd.DataFrame,
    output_file: str,
    eval_n_limit: int,
    eval_ids: list[str] | None = None,
    skip_num: int | None = None,
):
    assert "instance_id" in dataset.columns, (
        "Expected 'instance_id' column in the dataset. You should define your own unique identifier for each instance and use it as the 'instance_id' column."
    )
    id_column = "instance_id"
    logger.info("Writing evaluation output to %s", output_file)

    finished_ids = _load_finished_instances(output_file, id_column)
    dataset = _filter_dataset_by_criteria(
        dataset, eval_ids, skip_num, eval_n_limit, id_column
    )
    new_dataset = _create_serializable_dataset(dataset, finished_ids, id_column)

    logger.info(
        "Finished instances: %s, Remaining instances: %s",
        len(finished_ids),
        len(new_dataset),
    )
    return pd.DataFrame(new_dataset)


def _load_finished_instances(output_file: str, id_column: str) -> set[str]:
    """Load finished instance IDs from output file."""
    finished_ids: set[str] = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                finished_ids.add(str(data[id_column]))
        logger.warning(
            "\nOutput file %s already exists. Loaded %s finished instances.",
            output_file,
            len(finished_ids),
        )
    return finished_ids


def _filter_dataset_by_criteria(
    dataset: pd.DataFrame,
    eval_ids: list[str] | None,
    skip_num: int | None,
    eval_n_limit: int,
    id_column: str,
) -> pd.DataFrame:
    """Filter dataset based on evaluation criteria."""
    if eval_ids:
        return _filter_by_specific_ids(dataset, eval_ids, id_column)
    elif skip_num and skip_num >= 0:
        return _filter_by_skip_and_limit(dataset, skip_num, eval_n_limit)
    elif eval_n_limit and eval_n_limit > 0:
        return _filter_by_limit_only(dataset, eval_n_limit)
    return dataset


def _filter_by_specific_ids(
    dataset: pd.DataFrame, eval_ids: list[str], id_column: str
) -> pd.DataFrame:
    """Filter dataset to specific instance IDs."""
    eval_ids_converted = [dataset[id_column].dtype.type(id) for id in eval_ids]
    dataset = dataset[dataset[id_column].isin(eval_ids_converted)]
    logger.info("Limiting evaluation to %s specific instances.", len(eval_ids))
    return dataset


def _filter_by_skip_and_limit(
    dataset: pd.DataFrame, skip_num: int, eval_n_limit: int
) -> pd.DataFrame:
    """Filter dataset by skip number and limit."""
    skip_num = min(skip_num, len(dataset))
    dataset = dataset.iloc[skip_num:]
    logger.info(
        "Starting evaluation with skipping first %s instances (%s instances to run).",
        skip_num,
        len(dataset),
    )
    if eval_n_limit and eval_n_limit > 0:
        dataset = dataset.sample(
            min(eval_n_limit, len(dataset)), random_state=42, replace=False
        )
        logger.info(
            "Randomly sampling %s unique instances with random seed 42.", eval_n_limit
        )
    return dataset


def _filter_by_limit_only(dataset: pd.DataFrame, eval_n_limit: int) -> pd.DataFrame:
    """Filter dataset by limit only."""
    dataset = dataset.sample(
        min(eval_n_limit, len(dataset)), random_state=42, replace=False
    )
    logger.info(
        "Randomly sampling %s unique instances with random seed 42.", eval_n_limit
    )
    return dataset


def _create_serializable_dataset(
    dataset: pd.DataFrame, finished_ids: set[str], id_column: str
) -> list[dict]:
    """Create serializable dataset excluding finished instances."""

    def make_serializable(instance_dict: dict) -> dict:
        import numpy as np

        for k, v in instance_dict.items():
            if isinstance(v, np.ndarray):
                instance_dict[k] = v.tolist()
            elif isinstance(v, pd.Timestamp):
                instance_dict[k] = str(v)
            elif isinstance(v, dict):
                instance_dict[k] = make_serializable(v)
        return instance_dict

    return [
        make_serializable(instance.to_dict())
        for _, instance in dataset.iterrows()
        if str(instance[id_column]) not in finished_ids
    ]


def update_progress(result: EvalOutput, pbar: tqdm, output_fp: TextIO):
    """Update the progress bar and write the result to the output file."""
    pbar.update(1)
    pbar.set_description(f"Instance {result.instance_id}")
    pbar.set_postfix_str(f"Test Result: {str(result.test_result)[:300]}...")
    logger.info(
        "Finished evaluation for instance %s: %s...\n",
        result.instance_id,
        str(result.test_result)[:300],
    )
    output_fp.write(result.model_dump_json() + "\n")
    output_fp.flush()


def assert_and_raise(condition: bool, msg: str):
    """Raise an EvalException if the condition is not met.

    This will be used in conjunction with _process_instance_wrapper to handle retries. An EvalException should trigger a retry.
    """
    if not condition:
        raise EvalException(msg)


def log_skipped_maximum_retries_exceeded(instance, metadata, error, max_retries=5):
    """Log and skip the instance when maximum retries are exceeded.

    Args:
        instance: The instance that failed
        metadata: The evaluation metadata
        error: The error that occurred
        max_retries: The maximum number of retries that were attempted

    Returns:
        EvalOutput with the error information
    """
    from forge.core.logger import forge_logger as logger

    logger.exception(error)
    logger.error(
        "Maximum error retries reached for instance %s. Check maximum_retries_exceeded.jsonl, fix the issue and run evaluation again. Skipping this instance and continuing with others.",
        instance.instance_id,
    )
    if metadata and metadata.eval_output_dir:
        retries_file_path = os.path.join(
            metadata.eval_output_dir, "maximum_retries_exceeded.jsonl"
        )
        try:
            with open(retries_file_path, "a", encoding="utf-8") as f:
                import json

                error_entry = {
                    "instance_id": instance.instance_id,
                    "error": str(error),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                f.write(json.dumps(error_entry) + "\n")
            logger.info(
                "Added instance %s to %s", instance.instance_id, retries_file_path
            )
        except Exception as write_error:
            logger.error(
                "Failed to write to maximum_retries_exceeded.jsonl: %s", write_error
            )
    return EvalOutput(
        instance_id=instance.instance_id,
        test_result={},
        error=f"Maximum retries ({max_retries}) reached: {str(error)}",
        status="error",
    )


def check_maximum_retries_exceeded(eval_output_dir):
    """Check if maximum_retries_exceeded.jsonl exists and output a message."""
    from forge.core.logger import forge_logger as logger

    retries_file_path = os.path.join(eval_output_dir, "maximum_retries_exceeded.jsonl")
    if os.path.exists(retries_file_path):
        logger.info(
            "ATTENTION: Some instances reached maximum error retries and were skipped."
        )
        logger.info("These instances are listed in: %s", retries_file_path)
        logger.info(
            "Fix these instances and run evaluation again with EVAL_SKIP_MAXIMUM_RETRIES_EXCEEDED=false"
        )


def _process_instance_wrapper(
    process_instance_func: Callable[[pd.Series, EvalMetadata, bool], EvalOutput],
    instance: pd.Series,
    metadata: EvalMetadata,
    use_mp: bool,
    max_retries: int = 5,
    timeout_seconds: int | None = None,
) -> EvalOutput:
    """Wrap the process_instance_func to handle retries and errors."""
    runtime_failure_count = 0
    for attempt in range(max_retries + 1):
        try:
            kwargs = {}
            sig = signature(process_instance_func)
            if "runtime_failure_count" in sig.parameters:
                kwargs["runtime_failure_count"] = runtime_failure_count
            if timeout_seconds is not None:
                with timeout(timeout_seconds):
                    result = process_instance_func(instance, metadata, use_mp, **kwargs)
            else:
                result = process_instance_func(instance, metadata, use_mp, **kwargs)
            return result
        except EvalTimeoutException as e:
            error = f"Timeout after {timeout_seconds} seconds"
            stacktrace = traceback.format_exc()
            msg = (
                "-" * 10
                + "\n"
                + f"Timeout ({timeout_seconds} seconds) in instance [{
                    instance.instance_id
                }], Stopped evaluation for this instance."
                + "\n"
                + "-" * 10
            )
            logger.exception(e)
            return EvalOutput(
                instance_id=instance.instance_id, test_result={}, error=error
            )
        except Exception as e:
            error = str(e)
            stacktrace = traceback.format_exc()
            if attempt == max_retries:
                msg = (
                    "-" * 10
                    + "\n"
                    + f"Error in instance [{instance.instance_id}]: {error}. Stacktrace:\n{stacktrace}"
                    + "\n"
                    + f"[Encountered after {max_retries} retries. Please check the logs and report the issue.]"
                    + "-" * 10
                )
                skip_errors = (
                    os.environ.get(
                        "EVAL_SKIP_MAXIMUM_RETRIES_EXCEEDED", "false"
                    ).lower()
                    == "true"
                )
                if skip_errors:
                    return log_skipped_maximum_retries_exceeded(
                        instance, metadata, e, max_retries
                    )
                logger.exception(e)
                raise RuntimeError(
                    f"Maximum error retries reached for instance {instance.instance_id}"
                ) from e
            msg = (
                "-" * 10
                + "\n"
                + f"Error in instance [{instance.instance_id}]: {error}. Stacktrace:\n{stacktrace}"
                + "\n"
                + "-" * 10
                + f"[The above error occurred. Retrying... (attempt {attempt + 1} of {max_retries})]"
                + "-" * 10
                + "\n"
            )
            _error_str = type(e).__name__ + ": " + str(e)
            if is_fatal_runtime_error(_error_str):
                runtime_failure_count += 1
                msg += f"Runtime disconnected error detected for instance {
                    instance.instance_id
                }, runtime failure count: {runtime_failure_count}"
                msg += "\n" + "-" * 10 + "\n"
            logger.error(msg)
            time.sleep(5)


def _process_instance_wrapper_mp(args):
    """Wrapper for multiprocessing, especially for imap_unordered."""
    return _process_instance_wrapper(*args)


def run_evaluation(
    dataset: pd.DataFrame,
    metadata: EvalMetadata | None,
    output_file: str,
    num_workers: int,
    process_instance_func: Callable[
        [pd.Series, EvalMetadata, bool], Awaitable[EvalOutput]
    ],
    max_retries: int = 5,
    timeout_seconds: int | None = None,
):
    use_multiprocessing = num_workers > 1
    if metadata is not None:
        logger.info(
            "Evaluation started with Agent %s:\nmodel %s, max iterations %s.\n",
            metadata.agent_class,
            metadata.llm_config.model,
            metadata.max_iterations,
        )
    else:
        logger.warning("Running evaluation without metadata.")
        logger.info("Evaluation started with %s workers.", num_workers)
    total_instances = len(dataset)
    pbar = tqdm(total=total_instances, desc="Instances processed")
    with open(output_file, "a", encoding="utf-8") as output_fp:
        try:
            if use_multiprocessing:
                with mp.Pool(num_workers) as pool:
                    args_iter = (
                        (
                            process_instance_func,
                            instance,
                            metadata,
                            True,
                            max_retries,
                            timeout_seconds,
                        )
                        for _, instance in dataset.iterrows()
                    )
                    results = pool.imap_unordered(
                        _process_instance_wrapper_mp, args_iter
                    )
                    for result in results:
                        update_progress(result, pbar, output_fp)
            else:
                for _, instance in dataset.iterrows():
                    result = _process_instance_wrapper(
                        process_instance_func=process_instance_func,
                        instance=instance,
                        metadata=metadata,
                        use_mp=False,
                        max_retries=max_retries,
                    )
                    update_progress(result, pbar, output_fp)
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt received. Cleaning up...\n")
            cleanup()
    logger.info("\nEvaluation finished.\n")
    if metadata and metadata.eval_output_dir:
        check_maximum_retries_exceeded(metadata.eval_output_dir)


def reset_logger_for_multiprocessing(
    logger: logging.Logger, instance_id: str, log_dir: str
):
    """Reset the logger for multiprocessing.

    Save logs to a separate file for each process, instead of trying to write to the
    same file/console from multiple processes.
    """
    log_file = os.path.join(log_dir, f"instance_{instance_id}.log")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    console_handler = get_console_handler(log_level=logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            f"Instance {instance_id} - %(asctime)s - %(levelname)s - %(message)s"
        )
    )
    logger.addHandler(console_handler)
    logger.info(
        'Starting evaluation for instance %s.\nHint: run "tail -f %s" to see live logs in a separate shell',
        instance_id,
        log_file,
    )
    console_handler.setLevel(logging.WARNING)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)


def update_llm_config_for_completions_logging(
    llm_config: LLMConfig, eval_output_dir: str, instance_id: str
) -> LLMConfig:
    """Update the LLM config for logging completions."""
    if llm_config.log_completions:
        llm_config.log_completions_folder = os.path.join(
            eval_output_dir, "llm_completions", instance_id
        )
        logger.info(
            "Logging LLM completions for instance %s to %s",
            instance_id,
            llm_config.log_completions_folder,
        )
    return llm_config


def compatibility_for_eval_history_pairs(
    history: list[Event],
) -> list[tuple[dict, dict]]:
    """Convert event history to compatible format for evaluation.

    Args:
        history: List of events to convert.

    Returns:
        list[tuple[dict, dict]]: List of action-observation pairs as dictionaries.
    """
    return [
        (event_to_dict(action), event_to_dict(observation))
        for action, observation in get_pairs_from_events(history)
    ]


def is_fatal_evaluation_error(error: str | None) -> bool:
    """The AgentController class overrides last error for certain exceptions.

    We want to ensure those exeption do not overlap with fatal exceptions defined here
    This is because we do a comparisino against the stringified error.
    """
    if not error:
        return False
    FATAL_EXCEPTIONS = [
        AgentRuntimeError,
        AgentRuntimeBuildError,
        AgentRuntimeTimeoutError,
        AgentRuntimeUnavailableError,
        AgentRuntimeNotReadyError,
        AgentRuntimeDisconnectedError,
        AgentRuntimeNotFoundError,
        ConnectionError,
    ]
    if any((exception.__name__ in error for exception in FATAL_EXCEPTIONS)):
        logger.error("Fatal evaluation error detected: %s", error)
        return True
    return False


def is_fatal_runtime_error(error: str | None) -> bool:
    if not error:
        return False
    FATAL_RUNTIME_ERRORS = [
        AgentRuntimeTimeoutError,
        AgentRuntimeUnavailableError,
        AgentRuntimeDisconnectedError,
        AgentRuntimeNotFoundError,
    ]
    if any((exception.__name__ in error for exception in FATAL_RUNTIME_ERRORS)):
        logger.error("Fatal runtime error detected: %s", error)
        return True
    return False


def get_metrics(state: State) -> dict[str, Any]:
    """Extract metrics for evaluations.

    Prefer ConversationStats (source of truth) and fall back to state.metrics for
    backward compatibility.
    """
    metrics: dict[str, Any]
    try:
        if getattr(state, "conversation_stats", None):
            combined = state.conversation_stats.get_combined_metrics()
            metrics = combined.get()
        elif getattr(state, "metrics", None):
            metrics = state.metrics.get()
        else:
            metrics = {}
    except Exception:
        metrics = state.metrics.get() if getattr(state, "metrics", None) else {}
    metrics["condenser"] = get_condensation_metadata(state)
    return metrics


def get_default_sandbox_config_for_eval() -> SandboxConfig:
    return SandboxConfig(
        use_host_network=False,
        timeout=300,
        api_key=os.environ.get("ALLHANDS_API_KEY", None),
        runtime_startup_env_vars={"NO_CHANGE_TIMEOUT_SECONDS": "30"},
        remote_runtime_api_url=os.environ.get("SANDBOX_REMOTE_RUNTIME_API_URL"),
        keep_runtime_alive=False,
        remote_runtime_init_timeout=3600,
        remote_runtime_api_timeout=120,
        remote_runtime_enable_retries=True,
        remote_runtime_class="sysbox",
    )


def get_FORGE_config_for_eval(
    metadata: EvalMetadata | None = None,
    sandbox_config: SandboxConfig | None = None,
    runtime: str | None = None,
    max_iterations: int | None = None,
    default_agent: str | None = None,
    enable_browser: bool = False,
    workspace_base: str | None = None,
    workspace_mount_path: str | None = None,
):
    """Create an ForgeConfig with common patterns used across evaluation scripts.

    This function provides a standardized way to create Forge configurations
    for evaluation runs, with sensible defaults that match the patterns used in
    most run_infer.py scripts. Individual evaluation scripts can override specific
    attributes as needed.

    Args:
        metadata: EvalMetadata containing agent class, max iterations, etc.
        sandbox_config: Custom sandbox config. If None, uses get_default_sandbox_config_for_eval()
        runtime: Runtime type. If None, uses environment RUNTIME or 'docker'
        max_iterations: Max iterations for the agent. If None, uses metadata.max_iterations
        default_agent: Agent class name. If None, uses metadata.agent_class
        enable_browser: Whether to enable browser functionality
        workspace_base: Workspace base path. Defaults to None
        workspace_mount_path: Workspace mount path. Defaults to None

    Returns:
        ForgeConfig: Configured for evaluation with eval-specific overrides applied
    """
    from forge.core.config.FORGE_config import ForgeConfig as _OHConfig

    if sandbox_config is None:
        sandbox_config = get_default_sandbox_config_for_eval()
    if metadata is not None:
        if max_iterations is None:
            max_iterations = metadata.max_iterations
        if default_agent is None:
            default_agent = metadata.agent_class
    if runtime is None:
        runtime = os.environ.get("RUNTIME", "docker")
    if default_agent is None:
        default_agent = "CodeActAgent"
    if max_iterations is None:
        max_iterations = 50
    eval_store = os.path.abspath(os.path.join(os.getcwd(), ".eval_sessions"))
    config = _OHConfig(
        default_agent=default_agent,
        run_as_Forge=False,
        runtime=runtime,
        max_iterations=max_iterations,
        enable_browser=enable_browser,
        sandbox=sandbox_config,
        workspace_base=workspace_base,
        workspace_mount_path=workspace_mount_path,
        file_store="local",
        file_store_path=eval_store,
    )
    return config
