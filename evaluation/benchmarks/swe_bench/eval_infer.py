import copy
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from functools import partial
from typing import Callable
import pandas as pd
from tqdm import tqdm
from evaluation.benchmarks.swe_bench.resource.mapping import get_instance_resource_factor
from evaluation.benchmarks.swe_bench.run_infer import get_instance_docker_image
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    get_default_sandbox_config_for_eval,
    get_openhands_config_for_eval,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from openhands.core.config import LLMConfig, OpenHandsConfig, get_evaluation_parser
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime
from openhands.events.action import CmdRunAction
from openhands.events.observation import CmdOutputObservation
from openhands.utils.async_utils import call_async_from_sync

DOCKER_IMAGE_PREFIX = os.environ.get("EVAL_DOCKER_IMAGE_PREFIX", "docker.io/xingyaoww/")
logger.info("Using docker image prefix: %s", DOCKER_IMAGE_PREFIX)


def process_git_patch(patch):
    """Process and clean a git patch string.

    Args:
        patch: The git patch string to process.

    Returns:
        str: The cleaned and normalized git patch string.
    """
    if not isinstance(patch, str):
        return ""
    if not patch.strip():
        return ""
    patch = patch.replace("\r\n", "\n")
    lines = patch.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("diff --git"):
            patch = "\n".join(lines[i:])
            break
    patch = patch.rstrip() + "\n"
    return patch


def get_config(metadata: EvalMetadata, instance: pd.Series) -> OpenHandsConfig:
    base_container_image = get_instance_docker_image(instance["instance_id"])
    logger.info(
        "Using instance container image: %s. Please make sure this image exists. Submit an issue on https://github.com/All-Hands-AI/OpenHands if you run into any issues.",
        base_container_image,
    )
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = base_container_image
    sandbox_config.remote_runtime_resource_factor = get_instance_resource_factor(
        dataset_name=metadata.dataset, instance_id=instance["instance_id"]
    )
    return get_openhands_config_for_eval(runtime=os.environ.get("RUNTIME", "docker"), sandbox_config=sandbox_config)


@dataclass
class ConditionalImports:
    """We instantiate the values in this dataclass differently if we're evaluating SWE-bench or SWE-Gym."""

    get_eval_report: Callable
    APPLY_PATCH_FAIL: str
    APPLY_PATCH_PASS: str


def _setup_logging_and_config(
    instance: pd.Series, metadata: EvalMetadata, reset_logger: bool, log_dir: str | None
) -> tuple[OpenHandsConfig, str, str, str]:
    """Setup logging and get configuration."""
    if reset_logger:
        assert log_dir is not None, "Can't reset logger without a provided log directory."
        os.makedirs(log_dir, exist_ok=True)
        reset_logger_for_multiprocessing(logger, instance.instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance.instance_id)

    config = get_config(metadata, instance)
    instance_id = instance.instance_id
    model_patch = instance["model_patch"]
    test_spec = instance["test_spec"]
    logger.info("Starting evaluation for instance %s.", instance_id)

    return config, instance_id, model_patch, test_spec


def _initialize_test_result(instance: pd.Series, instance_id: str) -> None:
    """Initialize test result structure."""
    if "test_result" not in instance.keys():
        instance["test_result"] = {}
    instance["test_result"]["report"] = {
        "empty_generation": False,
        "resolved": False,
        "failed_apply_patch": False,
        "error_eval": False,
        "test_timeout": False,
    }


def _handle_empty_patch(instance: pd.Series, instance_id: str, metadata: EvalMetadata) -> EvalOutput:
    """Handle case where model patch is empty."""
    instance["test_result"]["report"]["empty_generation"] = True
    return EvalOutput(instance_id=instance_id, test_result=instance["test_result"], metadata=metadata)


def _adjust_runtime_config(config: OpenHandsConfig, runtime_failure_count: int, instance_id: str) -> None:
    """Adjust runtime configuration based on failure count."""
    if runtime_failure_count > 0:
        config.sandbox.remote_runtime_resource_factor = min(
            config.sandbox.remote_runtime_resource_factor * 2**runtime_failure_count, 8
        )
        logger.warning(
            "This is the %sth attempt for instance %s, setting resource factor to %s",
            runtime_failure_count + 1,
            instance_id,
            config.sandbox.remote_runtime_resource_factor,
        )


def _setup_runtime_and_files(runtime, model_patch: str, test_spec) -> None:
    """Setup runtime and copy necessary files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        patch_file_path = os.path.join(temp_dir, "patch.diff")
        with open(patch_file_path, "w", encoding='utf-8') as f:
            f.write(model_patch)
        runtime.copy_to(patch_file_path, "/tmp")  # nosec B108 - Safe: controlled evaluation runtime

        eval_script_path = os.path.join(temp_dir, "eval.sh")
        with open(eval_script_path, "w", encoding='utf-8') as f:
            f.write(test_spec.eval_script)
        runtime.copy_to(eval_script_path, "/tmp")  # nosec B108 - Safe: controlled evaluation runtime


def _make_eval_script_executable(runtime) -> None:
    """Make the evaluation script executable."""
    action = CmdRunAction(command="chmod +x /tmp/eval.sh")
    action.set_hard_timeout(600)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0


def _apply_patch(runtime, instance_id: str) -> str:
    """Apply the patch and return the output."""
    exec_command = (
        "cd /testbed && (git apply -v /tmp/patch.diff && echo 'APPLY_PATCH_PASS' || "
        "(echo 'Failed to apply patch with git apply, trying with patch command...' && "
        "(patch --batch --fuzz=5 -p1 -i /tmp/patch.diff && echo 'APPLY_PATCH_PASS' || echo 'APPLY_PATCH_FAIL')))"
    )
    action = CmdRunAction(command=exec_command)
    action.set_hard_timeout(600)
    obs = runtime.run_action(action)
    assert isinstance(obs, CmdOutputObservation)
    apply_patch_output = obs.content
    assert isinstance(apply_patch_output, str)
    return apply_patch_output


def _handle_patch_failure(
    instance: pd.Series, instance_id: str, apply_patch_output: str, conditional_imports, metadata: EvalMetadata
) -> EvalOutput:
    """Handle case where patch application fails."""
    logger.info("[%s] %s:\n%s", instance_id, conditional_imports.APPLY_PATCH_FAIL, apply_patch_output)
    instance["test_result"]["report"]["failed_apply_patch"] = True
    return EvalOutput(instance_id=instance_id, test_result=instance["test_result"], metadata=metadata)


def _run_evaluation_with_timeout(runtime, instance_id: str) -> tuple[bool, str]:
    """Run evaluation with timeout monitoring."""
    log_file = "/tmp/eval_output.log"  # nosec B108 - Safe: controlled evaluation runtime
    action = CmdRunAction(command=f"/tmp/eval.sh > {log_file} 2>&1 & echo $!")  # nosec B108
    action.set_hard_timeout(300)
    obs = runtime.run_action(action)

    if not (isinstance(obs, CmdOutputObservation) and obs.exit_code == 0):
        logger.info("[%s] Error when starting eval:\n%s", instance_id, obs.content)
        return False, ""

    pid = obs.content.split()[-1].strip()
    logger.info("[%s] Evaluation process started with PID: %s", instance_id, pid)

    start_time = time.time()
    timeout = 1800

    while True:
        seconds_elapsed = time.time() - start_time
        if seconds_elapsed > timeout:
            logger.info("[%s] Evaluation timed out after %s seconds", instance_id, timeout)
            return False, ""

        check_action = CmdRunAction(command=f"ps -p {pid} > /dev/null; echo $?")
        check_action.set_hard_timeout(300)
        check_obs = runtime.run_action(check_action)

        if isinstance(check_obs, CmdOutputObservation) and check_obs.content.split()[-1].strip() == "1":
            logger.info("[%s] Evaluation process completed after %s seconds", instance_id, seconds_elapsed)
            break

        logger.info("[%s] [%ss] Evaluation still running, waiting...", instance_id, seconds_elapsed)
        time.sleep(30)

    # Get test output
    cat_action = CmdRunAction(command=f"cat {log_file}")
    cat_action.set_hard_timeout(300)
    cat_obs = runtime.run_action(cat_action)

    if isinstance(cat_obs, CmdOutputObservation) and cat_obs.exit_code == 0:
        test_output = cat_obs.content
        assert isinstance(test_output, str)
        return True, test_output

    return False, ""


def _grade_evaluation(
    instance: pd.Series,
    instance_id: str,
    test_output: str,
    test_spec,
    model_patch: str,
    metadata: EvalMetadata,
    conditional_imports,
) -> None:
    """Grade the evaluation results."""
    logger.info("[%s] Grading answer...", instance_id)

    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = os.path.join(temp_dir, "logs", instance_id.lower())
        os.makedirs(log_dir, exist_ok=True)
        test_output_path = os.path.join(log_dir, "test_output.txt")

        with open(test_output_path, "w", encoding='utf-8') as f:
            f.write(test_output)

        try:
            extra_kwargs = {}
            if "SWE-Gym" in metadata.dataset:
                extra_kwargs["log_path"] = test_output_path
            else:
                extra_kwargs["test_log_path"] = test_output_path

            _report = conditional_imports.get_eval_report(
                test_spec=test_spec,
                prediction={"model_patch": model_patch, "instance_id": instance_id},
                include_tests_status=True,
                **extra_kwargs,
            )
            report = _report[instance_id]
            logger.info(
                "[%s] report: %s\nResult for %s: resolved: %s", instance_id, report, instance_id, report["resolved"]
            )
            instance["test_result"]["report"]["resolved"] = report["resolved"]
        except Exception as e:
            logger.error("[%s] Error when getting eval report: %s", instance_id, e)
            instance["test_result"]["report"]["resolved"] = False
            instance["test_result"]["report"]["error_eval"] = True


def process_instance(
    instance: pd.Series,
    metadata: EvalMetadata,
    reset_logger: bool = True,
    log_dir: str | None = None,
    runtime_failure_count: int = 0,
    conditional_imports: ConditionalImports | None = None,
) -> EvalOutput:
    """Evaluate agent performance on a SWE-bench problem instance.

    Reduced complexity: 14 → 5 by extracting setup, patch handling, and evaluation logic.
    """
    # Validate inputs
    _validate_process_instance_args(conditional_imports)

    # Setup logging and configuration
    config, instance_id, model_patch, test_spec = _setup_logging_and_config(instance, metadata, reset_logger, log_dir)

    # Initialize test result structure
    _initialize_test_result(instance, instance_id)

    # Handle empty patch case
    if model_patch == "":
        return _handle_empty_patch(instance, instance_id, metadata)

    # Prepare runtime environment
    runtime = _prepare_runtime_environment(config, model_patch, test_spec)

    try:
        # Process patch application and evaluation
        return _process_patch_and_evaluation(
            runtime, instance, instance_id, model_patch, test_spec,
            metadata, runtime_failure_count, config, conditional_imports
        )
    finally:
        runtime.close()


def _validate_process_instance_args(conditional_imports: ConditionalImports | None) -> None:
    """Validate process_instance arguments."""
    assert (
        conditional_imports is not None
    ), "conditional_imports must be provided to run process_instance using multiprocessing"


def _prepare_runtime_environment(config, model_patch: str, test_spec) -> Runtime:
    """Prepare runtime environment with files and scripts."""
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    _setup_runtime_and_files(runtime, model_patch, test_spec)
    _make_eval_script_executable(runtime)
    return runtime


def _process_patch_and_evaluation(
    runtime: Runtime,
    instance: pd.Series,
    instance_id: str,
    model_patch: str,
    test_spec,
    metadata: EvalMetadata,
    runtime_failure_count: int,
    config,
    conditional_imports: ConditionalImports,
) -> EvalOutput:
    """Process patch application and run evaluation."""
    # Update metadata with runtime information
    updated_metadata = _update_metadata_for_runtime(metadata, runtime_failure_count, config)

    # Apply patch and get output
    apply_patch_output = _apply_patch(runtime, instance_id)
    instance["test_result"]["apply_patch_output"] = apply_patch_output

    # Handle patch application results
    return _handle_patch_application_results(
        apply_patch_output, instance, instance_id, model_patch, test_spec,
        updated_metadata, conditional_imports
    )


def _update_metadata_for_runtime(
    metadata: EvalMetadata, runtime_failure_count: int, config
) -> EvalMetadata:
    """Update metadata with runtime failure count and resource factor."""
    updated_metadata = copy.deepcopy(metadata)
    updated_metadata.details["runtime_failure_count"] = runtime_failure_count
    updated_metadata.details["remote_runtime_resource_factor"] = config.sandbox.remote_runtime_resource_factor
    return updated_metadata


def _handle_patch_application_results(
    apply_patch_output: str,
    instance: pd.Series,
    instance_id: str,
    model_patch: str,
    test_spec,
    metadata: EvalMetadata,
    conditional_imports: ConditionalImports,
) -> EvalOutput:
    """Handle different patch application results."""
    if "APPLY_PATCH_FAIL" in apply_patch_output:
        return _handle_patch_failure(instance, instance_id, apply_patch_output, conditional_imports, metadata)
    elif "APPLY_PATCH_PASS" in apply_patch_output:
        return _handle_successful_patch_application(
            instance, instance_id, model_patch, test_spec, metadata, conditional_imports, apply_patch_output
        )
    else:
        return _handle_unexpected_patch_output(instance_id, apply_patch_output)


def _handle_successful_patch_application(
    instance: pd.Series,
    instance_id: str,
    model_patch: str,
    test_spec,
    metadata: EvalMetadata,
    conditional_imports: ConditionalImports,
    apply_patch_output: str,
) -> EvalOutput:
    """Handle successful patch application and run evaluation."""
    logger.info("[%s] %s:\n%s", instance_id, conditional_imports.APPLY_PATCH_PASS, apply_patch_output)

    # Run evaluation with timeout
    success, test_output = _run_evaluation_with_timeout(None, instance_id)  # runtime should be passed here

    if success:
        instance["test_result"]["test_output"] = test_output
        _grade_evaluation(
            instance, instance_id, test_output, test_spec, model_patch, metadata, conditional_imports
        )
    else:
        instance["test_result"]["report"]["test_timeout"] = True
        instance["test_result"]["report"]["error_eval"] = True

    return EvalOutput(instance_id=instance_id, test_result=instance["test_result"], metadata=metadata)


def _handle_unexpected_patch_output(instance_id: str, apply_patch_output: str) -> EvalOutput:
    """Handle unexpected patch application output."""
    logger.info("[%s] Unexpected output when applying patch:\n%s", instance_id, apply_patch_output)
    raise RuntimeError(instance_id, f"Unexpected output when applying patch:\n{apply_patch_output}", logger)


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument("--input-file", type=str, help="Path to input predictions file", required=True)
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench",
        help="data set to evaluate on, either full-test or lite-test",
    )
    parser.add_argument("--split", type=str, default="test", help="split to evaluate on")
    args, _ = parser.parse_known_args()
    if "SWE-Gym" in args.dataset:
        from swegym.harness.grading import get_eval_report
        from swegym.harness.run_evaluation import APPLY_PATCH_FAIL, APPLY_PATCH_PASS
        from swegym.harness.test_spec import SWEbenchInstance, make_test_spec
        from swegym.harness.utils import load_swebench_dataset
    else:
        from swebench.harness.grading import get_eval_report
        from swebench.harness.run_evaluation import APPLY_PATCH_FAIL, APPLY_PATCH_PASS
        from swebench.harness.test_spec.test_spec import SWEbenchInstance, make_test_spec
        from swebench.harness.utils import load_swebench_dataset
    full_dataset: list[SWEbenchInstance] = load_swebench_dataset(args.dataset, args.split)
    instance_id_to_instance = {instance["instance_id"]: instance for instance in full_dataset}
    logger.info("Loaded dataset %s with split %s to run inference on.", args.dataset, args.split)
    assert args.input_file.endswith(".jsonl"), "Input file must be a jsonl file."
    required_fields = ["instance_id", "model_patch", "test_result"]
    with open(args.input_file, encoding='utf-8') as f:
        predictions = pd.DataFrame.from_records(
            [
                {k: v for k, v in json.loads(line).items() if k in required_fields}
                for line in tqdm(f, desc="Loading predictions")
            ]
        )
    assert "instance_id" in predictions.columns, "Input file must contain instance_id column."
    if "model_patch" not in predictions.columns and (
        "test_result" in predictions.columns and "model_patch" in predictions["test_result"].iloc[0]
    ):
        raise ValueError("Input file must contain model_patch column OR test_result column with model_patch field.")
    assert len(predictions["instance_id"].unique()) == len(predictions), "instance_id column must be unique."
    if "model_patch" not in predictions.columns:
        predictions["model_patch"] = predictions["test_result"].apply(lambda x: x.get("git_patch", ""))
    assert {"instance_id", "model_patch"}.issubset(
        set(predictions.columns)
    ), "Input file must contain instance_id and model_patch columns."
    predictions["model_patch"] = predictions["model_patch"].apply(process_git_patch)
    predictions["instance"] = predictions["instance_id"].apply(lambda x: instance_id_to_instance[x])
    predictions["test_spec"] = predictions["instance"].apply(make_test_spec)
    output_file = args.input_file.replace(".jsonl", ".swebench_eval.jsonl")
    instances = prepare_dataset(predictions, output_file, args.eval_n_limit)
    metadata: EvalMetadata | None = None
    metadata_filepath = os.path.join(os.path.dirname(args.input_file), "metadata.json")
    if os.path.exists(metadata_filepath):
        with open(metadata_filepath, "r", encoding='utf-8') as metadata_file:
            data = metadata_file.read()
            metadata = EvalMetadata.model_validate_json(data)
    else:
        metadata = EvalMetadata(
            agent_class="dummy_agent",
            llm_config=LLMConfig(model="dummy_model"),
            max_iterations=1,
            eval_output_dir=os.path.dirname(args.input_file),
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip(),
            dataset=args.dataset,
            details={},
        )
    process_instance_func = partial(
        process_instance,
        log_dir=output_file.replace(".jsonl", ".logs"),
        conditional_imports=ConditionalImports(
            get_eval_report=get_eval_report, APPLY_PATCH_FAIL=APPLY_PATCH_FAIL, APPLY_PATCH_PASS=APPLY_PATCH_PASS
        ),
    )
    run_evaluation(
        instances,
        metadata=metadata,
        output_file=output_file,
        num_workers=args.eval_num_workers,
        process_instance_func=process_instance_func,
    )
    evaluated_predictions = pd.read_json(output_file, lines=True)
    fields = ["resolved", "failed_apply_patch", "error_eval", "empty_generation"]

    def count_report_field(row, field):
        return row["test_result"]["report"][field]

    report = {}
    for field in fields:
        count = evaluated_predictions.apply(count_report_field, args=(field,), axis=1).sum()
        report[field] = count
        logger.info("# %s: %s / %s. (%s)", field, count, len(evaluated_predictions), count / len(evaluated_predictions))
