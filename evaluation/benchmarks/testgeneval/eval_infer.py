import os
import tempfile
import time
from functools import partial
import pandas as pd
from report_utils import (
    check_coverage,
    check_mutation,
    count_methods,
    get_lines_of_code,
)
from evaluation.benchmarks.testgeneval.compute_readability import compute_readability
from evaluation.benchmarks.testgeneval.constants import (
    COVERAGE_PREFIX,
    MUTATION_BUFFER,
    MUTATION_TEMPLATE,
    MUTATION_TIMEOUT,
    TESTS_SUFFIX,
)
from evaluation.benchmarks.testgeneval.metrics import (
    bleu,
    edit_sim,
    exact_match,
    rouge_l,
)
from evaluation.benchmarks.testgeneval.pygments_utils import tokenize_code
from evaluation.benchmarks.testgeneval.run_infer import get_instance_docker_image
from evaluation.benchmarks.testgeneval.test_filter import filter_tests
from evaluation.benchmarks.testgeneval.test_spec import (
    TestGenEvalInstance,
    TestSpec,
    make_test_spec,
)
from evaluation.benchmarks.testgeneval.utils import load_testgeneval_dataset
from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    get_FORGE_config_for_eval,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from forge.core.config import ForgeConfig, SandboxConfig, get_evaluation_parser
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime
from forge.events.action import CmdRunAction
from forge.events.observation import CmdOutputObservation
from forge.utils.async_utils import call_async_from_sync

DOCKER_IMAGE_PREFIX = os.environ.get("EVAL_DOCKER_IMAGE_PREFIX", "docker.io/kdjain/")
logger.info("Using docker image prefix: %s", DOCKER_IMAGE_PREFIX)


def get_config(instance: pd.Series) -> ForgeConfig:
    base_container_image = get_instance_docker_image(instance["instance_id_swebench"])
    assert base_container_image, (
        f"Invalid container image for instance {instance['instance_id_swebench']}."
    )
    logger.info("Using instance container image: %s.", base_container_image)
    sandbox_config = SandboxConfig(
        base_container_image=base_container_image,
        use_host_network=False,
        timeout=1800,
        api_key=os.environ.get("ALLHANDS_API_KEY"),
        remote_runtime_api_url=os.environ.get(
            "SANDBOX_REMOTE_RUNTIME_API_URL", "http://localhost:8000"
        ),
    )
    return get_FORGE_config_for_eval(
        sandbox_config=sandbox_config, runtime=os.environ.get("RUNTIME", "docker")
    )


def compute_lexical_metrics(pred_suite, gold_suite):
    """Compute lexical similarity metrics between predicted and gold test suites.

    Args:
        pred_suite: The predicted test suite string.
        gold_suite: The gold standard test suite string.

    Returns:
        dict: Dictionary containing various lexical metrics including LOC, methods,
              readability scores, BLEU, exact match, edit similarity, and ROUGE scores.
    """
    pred_loc = get_lines_of_code(pred_suite)
    gold_loc = get_lines_of_code(gold_suite)
    pred_methods = count_methods(pred_suite)
    gold_methods = count_methods(gold_suite)
    readability_pred = compute_readability(pred_suite)
    readability_gold = compute_readability(gold_suite)
    preds = tokenize_code(pred_suite)
    golds = tokenize_code(gold_suite)
    return {
        "pred_loc": pred_loc,
        "gold_loc": gold_loc,
        "pred_readability": readability_pred,
        "gold_readability": readability_gold,
        "pred_methods": pred_methods,
        "gold_methods": gold_methods,
        "bleu": bleu(preds, golds),
        "xmatch": exact_match(preds, golds),
        "edit_sim": edit_sim(preds, golds),
        "rouge_f": rouge_l(golds, preds)["f"],
        "rouge_p": rouge_l(golds, preds)["p"],
        "rouge_r": rouge_l(golds, preds)["r"],
    }


def run_command(runtime, command, timeout=600):
    """Execute a command in the runtime environment.

    Args:
        runtime: The runtime environment to execute the command in.
        command: The command string to execute.
        timeout: Maximum execution time in seconds (default: 600).

    Returns:
        ActionObservation: The result of the command execution.
    """
    action = CmdRunAction(command=command)
    action.set_hard_timeout(timeout)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    return obs


def run_tests(runtime, instance, test_script, log_file="/tmp/test_output.log"):  # nosec B108 - Safe: controlled evaluation runtime
    action = CmdRunAction(command=f"bash {test_script} > {log_file} 2>&1 & echo $!")  # nosec B108
    action.set_hard_timeout(60)
    obs = runtime.run_action(action)
    assert isinstance(obs, CmdOutputObservation), "Failed to start test script."
    pid = obs.content.split()[-1].strip()
    logger.info("[%s] Test process started with PID: %s", instance.instance_id, pid)
    start_time = time.time()
    timeout = 1800
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            logger.info("[%s] Test process timed out.", instance.instance_id)
            instance["test_result"]["report"]["test_timeout"] = True
            break
        check_action = CmdRunAction(command=f"ps -p {pid} > /dev/null; echo $?")
        check_obs = runtime.run_action(check_action)
        if (
            isinstance(check_obs, CmdOutputObservation)
            and len(check_obs.content.split()) > 0
            and (check_obs.content.split()[-1].strip() == "1")
        ):
            logger.info("[%s] Test process completed.", instance.instance_id)
            break
        time.sleep(30)
    test_action = CmdRunAction(command=f"cat {log_file}")
    test_action.set_hard_timeout(300)
    test_obs = runtime.run_action(test_action)
    assert isinstance(test_obs, CmdOutputObservation), "Failed to retrieve test output."
    return (test_obs.exit_code, test_obs.content, elapsed_time)


def run_mutation_testing(
    runtime, instance, mutation_script, log_file="/tmp/mutation_output.log"
):  # nosec B108 - Safe: controlled evaluation runtime
    action = CmdRunAction(command=f"bash {mutation_script} > {log_file} 2>&1 & echo $!")  # nosec B108
    action.set_hard_timeout(60)
    obs = runtime.run_action(action)
    assert isinstance(obs, CmdOutputObservation), "Failed to start test script."
    pid = obs.content.split()[-1].strip()
    logger.info("[%s] Mutation process started with PID: %s", instance.instance_id, pid)
    start_time = time.time()
    timeout = 4000
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            logger.info("[%s] Mutation process timed out.", instance.instance_id)
            instance["test_result"]["report"]["mutation_timeout"] = True
            break
        check_action = CmdRunAction(command=f"ps -p {pid} > /dev/null; echo $?")
        check_obs = runtime.run_action(check_action)
        if (
            isinstance(check_obs, CmdOutputObservation)
            and len(check_obs.content.split()) > 0
            and (check_obs.content.split()[-1].strip() == "1")
        ):
            logger.info("[%s] Mutation process completed.", instance.instance_id)
            break
        time.sleep(30)
    assert isinstance(obs, CmdOutputObservation), "Failed to run mutation script."
    mutation_action = CmdRunAction(command=f"cat {log_file}")
    mutation_action.set_hard_timeout(300)
    mutation_obs = runtime.run_action(mutation_action)
    assert isinstance(mutation_obs, CmdOutputObservation), (
        "Failed to retrieve mutation output."
    )
    return (mutation_obs.exit_code, mutation_obs.content)


def grade_test_output(
    test_suite: str, instance: pd.Series, test_output: str, test_spec: TestSpec, runtime
):
    """Two-pass test grading with short-circuiting:.

    1. Run all tests to identify passing/failing tests
    2. If no failing tests, evaluate coverage immediately
    3. Otherwise, run only passing tests for coverage analysis.
    """
    unit_test_output, coverage_output = ("", "")
    if TESTS_SUFFIX in test_output:
        unit_test_output = test_output.split(TESTS_SUFFIX)[0]
    if not unit_test_output:
        return (
            False,
            0,
            "",
            "",
            {
                "total_tests": 0,
                "passing_tests": 0,
                "failing_tests": 0,
                "any_pass": False,
                "all_pass": False,
                "passing_test_names": [],
                "failing_test_names": [],
            },
        )
    logger.info("Calling filter unit tests")
    filtered_content, passing_tests, failing_tests = filter_tests(
        test_suite, unit_test_output, test_spec.repo
    )
    total_tests = len(passing_tests) + len(failing_tests)
    test_stats = {
        "total_tests": total_tests,
        "passing_tests": len(passing_tests),
        "failing_tests": len(failing_tests),
        "any_pass": len(passing_tests) > 0,
        "all_pass": len(failing_tests) == 0 and total_tests > 0,
        "passing_test_names": passing_tests,
        "failing_test_names": failing_tests,
    }
    if not passing_tests:
        return (False, 0, unit_test_output, coverage_output, test_stats)
    if not failing_tests:
        coverage = 0
        cov_success = False
        if COVERAGE_PREFIX in test_output:
            coverage_output = test_output.split(COVERAGE_PREFIX)[1]
            _, coverage = check_coverage(coverage_output, test_spec.code_file)
            cov_success = True
        return (cov_success, coverage, unit_test_output, coverage_output, test_stats)
    cov_success = False
    coverage = 0
    if filtered_content:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_suite_path = os.path.join(temp_dir, "test_suite.py")
            with open(test_suite_path, "w", encoding="utf-8") as f:
                f.write(filtered_content)
            runtime.copy_to(test_suite_path, "/tmp")  # nosec B108 - Safe: controlled evaluation runtime
        run_command(runtime, f"cp /tmp/test_suite.py /testbed/{test_spec.test_file}")  # nosec B108
        _, test_output_second_pass, _ = run_tests(runtime, instance, "/tmp/test.sh")  # nosec B108
        coverage, coverage_output, unit_test_output = (0, "", test_output_second_pass)
        if COVERAGE_PREFIX in test_output_second_pass:
            coverage_output = test_output_second_pass.split(COVERAGE_PREFIX)[1]
            unit_test_output = test_output_second_pass.split(TESTS_SUFFIX)[0]
            _, coverage = check_coverage(coverage_output, test_spec.code_file)
            cov_success = True
    return (cov_success, coverage, unit_test_output, coverage_output, test_stats)


def process_instance(
    instance: pd.Series,
    metadata: EvalMetadata,
    reset_logger: bool = True,
    log_dir: str | None = None,
) -> EvalOutput:
    """Evaluate agent performance on a TestGenEval problem instance."""
    # Initialize logging
    _initialize_logging(reset_logger, log_dir, instance.instance_id)

    # Initialize configuration and instance
    config = get_config(instance)
    _initialize_test_result(instance)

    # Handle empty test suite
    if _is_empty_test_suite(instance):
        return EvalOutput(
            instance_id=instance.instance_id, test_result=instance["test_result"]
        )

    # Compute lexical metrics if not skipped
    _compute_lexical_metrics_if_needed(instance)

    # Run test evaluation
    return _run_test_evaluation(instance, config)


def _initialize_logging(
    reset_logger: bool, log_dir: str | None, instance_id: str
) -> None:
    """Initialize logging for the evaluation."""
    if reset_logger:
        assert log_dir is not None, (
            "Can't reset logger without a provided log directory."
        )
        os.makedirs(log_dir, exist_ok=True)
        reset_logger_for_multiprocessing(logger, instance_id, log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance_id)


def _initialize_test_result(instance: pd.Series) -> None:
    """Initialize test result structure."""
    instance_id = instance.instance_id
    logger.info("Starting evaluation for instance %s.", instance_id)

    instance["test_result"]["id"] = instance_id
    instance["test_result"]["report"] = _create_report_template()
    instance["test_result"]["lexical"] = _create_lexical_template()


def _create_report_template() -> dict[str, Any]:
    """Create template for test report."""
    return {
        "test_output": "",
        "empty_generation": False,
        "error_eval": False,
        "all_tests_pass": False,
        "tests_pass": False,
        "test_timeout": False,
        "mutation_timeout": False,
        "coverage_success": False,
        "mutation_success": False,
        "coverage": 0,
        "mutation_score": 0,
        "mutation_error_interval": -1,
        "num_mutants": -1,
    }


def _create_lexical_template() -> dict[str, Any]:
    """Create template for lexical metrics."""
    return {
        "pred_loc": -1,
        "gold_loc": -1,
        "pred_readability": -1,
        "gold_readability": -1,
        "pred_methods": -1,
        "gold_methods": -1,
        "bleu": -1,
        "xmatch": -1,
        "edit_sim": -1,
        "rouge_f": -1,
        "rouge_p": -1,
        "rouge_r": -1,
    }


def _is_empty_test_suite(instance: pd.Series) -> bool:
    """Check if test suite is empty."""
    if instance["test_suite"] == "" or instance["test_suite"] is None:
        instance["test_result"]["report"]["empty_generation"] = True
        return True
    return False


def _compute_lexical_metrics_if_needed(instance: pd.Series) -> None:
    """Compute lexical metrics if not skipped."""
    if not args.skip_lexical:
        lexical_metrics = compute_lexical_metrics(
            instance["test_suite"], instance["instance"]["test_src"]
        )
        instance["test_result"]["lexical"] = lexical_metrics


def _run_test_evaluation(instance: pd.Series, config) -> EvalOutput:
    """Run the actual test evaluation."""
    test_suite = instance["test_suite"]
    test_spec: TestSpec = instance["test_spec"]

    # Create and connect runtime
    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)

    try:
        # Setup test files
        _setup_test_files(runtime, test_suite, test_spec)

        # Run tests and get results
        test_results = _execute_tests(runtime, instance, test_suite, test_spec)

        # Update instance with test results
        _update_test_results(instance, test_results)

        # Run mutation testing if applicable
        _run_mutation_testing_if_applicable(runtime, instance, test_spec, test_results)

        return EvalOutput(
            instance_id=instance.instance_id, test_result=instance["test_result"]
        )

    except Exception as e:
        logger.error("Error processing instance %s: %s", instance.instance_id, e)
        raise RuntimeError(instance.instance_id, "Unexpected output...", logger) from e
    finally:
        runtime.close()


def _setup_test_files(runtime, test_suite: str, test_spec: TestSpec) -> None:
    """Setup test files in the runtime environment."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write test suite file
        test_suite_path = os.path.join(temp_dir, "test_suite.py")
        with open(test_suite_path, "w", encoding="utf-8") as f:
            f.write(test_suite)
        runtime.copy_to(test_suite_path, "/tmp")  # nosec B108

        # Write test script
        test_script_path = os.path.join(temp_dir, "test.sh")
        with open(test_script_path, "w", encoding="utf-8") as f:
            f.write(test_spec.test_script)
        runtime.copy_to(test_script_path, "/tmp")  # nosec B108

        # Write mutation script
        mutation_script_path = os.path.join(temp_dir, "mutation.sh")
        with open(mutation_script_path, "w", encoding="utf-8") as f:
            f.write(test_spec.mutation_script)
        runtime.copy_to(mutation_script_path, "/tmp")  # nosec B108


def _execute_tests(
    runtime, instance: pd.Series, test_suite: str, test_spec: TestSpec
) -> dict[str, Any]:
    """Execute the test suite and return results."""
    # Make scripts executable
    run_command(runtime, "chmod +x /tmp/test.sh /tmp/mutation.sh")  # nosec B108
    run_command(runtime, f"cp /tmp/test_suite.py /testbed/{test_spec.test_file}")  # nosec B108

    # Run tests
    _, test_output, test_time = run_tests(runtime, instance, "/tmp/test.sh")  # nosec B108

    # Grade test output
    coverage_success, coverage, unit_test_output, coverage_output, test_stats = (
        grade_test_output(test_suite, instance, test_output, test_spec, runtime)
    )

    return {
        "test_output": test_output,
        "test_time": test_time,
        "coverage_success": coverage_success,
        "coverage": coverage,
        "unit_test_output": unit_test_output,
        "coverage_output": coverage_output,
        "test_stats": test_stats,
    }


def _update_test_results(instance: pd.Series, test_results: dict[str, Any]) -> None:
    """Update instance with test results."""
    instance["test_result"]["report"].update(
        {
            "test_output": test_results["unit_test_output"],
            "tests_pass": test_results["test_stats"]["any_pass"],
            "all_tests_pass": test_results["test_stats"]["all_pass"],
            "coverage_success": test_results["coverage_success"],
            "coverage": test_results["coverage"]
            if test_results["coverage_success"]
            else 0,
            "test_stats": test_results["test_stats"],
        }
    )


def _run_mutation_testing_if_applicable(
    runtime, instance: pd.Series, test_spec: TestSpec, test_results: dict[str, Any]
) -> None:
    """Run mutation testing if conditions are met."""
    if (
        not args.skip_mutation
        and test_results["coverage_success"]
        and test_results["test_stats"]["any_pass"]
        and (test_results["coverage"] > 0)
    ):
        _execute_mutation_testing(
            runtime, instance, test_spec, test_results["test_time"]
        )


def _execute_mutation_testing(
    runtime, instance: pd.Series, test_spec: TestSpec, test_time: float
) -> None:
    """Execute mutation testing."""
    mutation_timeout = max(10, 1.5 * test_time)
    mutation_toml = MUTATION_TEMPLATE.format(
        test_cmd=test_spec.test_cmd,
        source_fp=test_spec.code_file,
        timeout=mutation_timeout,
    )

    # Write mutation TOML file
    with tempfile.TemporaryDirectory() as temp_dir:
        mutation_toml_path = os.path.join(temp_dir, "mutation.toml")
        with open(mutation_toml_path, "w", encoding="utf-8") as f:
            f.write(mutation_toml)
        runtime.copy_to(mutation_toml_path, "/tmp")  # nosec B108

    # Run mutation testing
    run_command(runtime, "cp /tmp/mutation.toml /testbed/mutation.toml")  # nosec B108
    mutation_code, mutation_output = run_mutation_testing(
        runtime, instance, "/tmp/mutation.sh"
    )  # nosec B108

    # Process mutation results
    if mutation_output and mutation_code == 0:
        _process_mutation_results(instance, mutation_output)


def _process_mutation_results(instance: pd.Series, mutation_output: str) -> None:
    """Process mutation testing results."""
    mutation_success, num_mutants, mutation_score, mutation_confidence_interval = (
        check_mutation(mutation_output)
    )

    instance["test_result"]["report"]["num_mutants"] = num_mutants
    instance["test_result"]["report"]["mutation_success"] = mutation_success
    instance["test_result"]["report"]["mutation_score"] = mutation_score
    instance["test_result"]["report"]["mutation_error_interval"] = (
        mutation_confidence_interval
    )


def count_and_log_fields(evaluated_predictions, fields, key):
    """Count and log the sum of specified fields in the evaluated predictions,.

    ignoring fields with a value of -1. If all values for a field are -1,
    return -1.

    :param evaluated_predictions: DataFrame containing evaluation results
    :param fields: List of field names to count
    :param key: Key to access the field values ('report' or 'lexical')
    """

    def count_field(row, field):
        value = row["test_result"][key][field]
        return value if value != -1 else None

    for field in fields:
        valid_values = evaluated_predictions.apply(
            count_field, args=(field,), axis=1
        ).dropna()
        if valid_values.empty:
            logger.info("# %s: -1 (All values are -1)", field)
        else:
            count = valid_values.sum()
            length = len(valid_values)
            logger.info("# %s: %s. (%s)", field, length, count / length)


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--input-file", type=str, required=True, help="Path to input predictions file"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="kjain14/testgeneval",
        help="Dataset to evaluate on",
    )
    parser.add_argument(
        "--split", type=str, default="test", help="Split to evaluate on"
    )
    parser.add_argument(
        "--skip_mutation", action="store_true", help="Skip mutation testing"
    )
    parser.add_argument(
        "--skip_lexical", action="store_true", help="Skip lexical metrics"
    )
    parser.add_argument(
        "--mutation_timeout",
        type=int,
        default=MUTATION_TIMEOUT,
        help="Mutation timeout",
    )
    parser.add_argument(
        "--mutation_buffer", type=int, default=MUTATION_BUFFER, help="Mutation buffer"
    )
    args, _ = parser.parse_known_args()
    dataset: list[TestGenEvalInstance] = load_testgeneval_dataset(
        args.dataset, args.split
    )
    logger.info(
        "Loaded dataset %s with split %s to run inference on.", args.dataset, args.split
    )
    assert args.input_file.endswith(".jsonl"), "Input file must be a jsonl file."
    predictions = pd.read_json(args.input_file, lines=True)
    assert "instance_id" in predictions.columns, (
        "Input file must contain instance_id column."
    )
    if "test_suite" not in predictions.columns and (
        "test_result" in predictions.columns
        and "test_suite" in predictions["test_result"].iloc(0)
    ):
        raise ValueError(
            "Input file must contain test_suite column OR test_result column with test_suite field."
        )
    if "instance_id_swebench" not in predictions.columns:
        predictions["instance_id_swebench"] = predictions["instance"].apply(
            lambda x: x["instance_id_swebench"]
        )
    if "instance_id" not in predictions.columns and "instance_id" in predictions[
        "instance"
    ].iloc(0):
        raise ValueError(
            "Input file must contain id column OR instance column with id field."
        )
    if "instance_id" not in predictions.columns:
        predictions["instance_id"] = predictions["instance"].apply(
            lambda x: x["instance_id"]
        )
    if "test_suite" not in predictions.columns:
        predictions["test_suite"] = predictions["test_result"].apply(
            lambda x: x["test_suite"]
        )
    assert len(predictions["instance_id"].unique()) == len(predictions), (
        "instance_id column must be unique."
    )
    assert {"instance_id_swebench", "test_suite", "instance_id"}.issubset(
        set(predictions.columns)
    ), "Input file must contain id, instance_id and test_suite columns."
    predictions["test_spec"] = predictions["instance"].apply(
        lambda x: make_test_spec(x, args.mutation_timeout, args.mutation_buffer)
    )
    output_file = args.input_file.replace(".jsonl", ".testgeneval.jsonl")
    instances = prepare_dataset(predictions, output_file, args.eval_n_limit)
    metadata: EvalMetadata | None = None
    metadata_filepath = os.path.join(os.path.dirname(args.input_file), "metadata.json")
    if os.path.exists(metadata_filepath):
        with open(metadata_filepath, "r", encoding="utf-8") as metadata_file:
            data = metadata_file.read()
            metadata = EvalMetadata.model_validate_json(data)
    process_instance_func = partial(
        process_instance, log_dir=output_file.replace(".jsonl", ".logs")
    )
    run_evaluation(
        instances,
        metadata=None,
        output_file=output_file,
        num_workers=args.eval_num_workers,
        process_instance_func=process_instance_func,
    )
    evaluated_predictions = pd.read_json(output_file, lines=True)
    report_fields = [
        "coverage",
        "mutation_score",
        "tests_pass",
        "all_tests_pass",
        "empty_generation",
        "coverage_success",
        "test_timeout",
        "error_eval",
    ]
    lexical_fields = [
        "pred_loc",
        "gold_loc",
        "pred_methods",
        "gold_methods",
        "bleu",
        "xmatch",
        "edit_sim",
        "rouge_f",
        "rouge_p",
        "rouge_r",
    ]
    count_and_log_fields(evaluated_predictions, report_fields, key="report")
    count_and_log_fields(evaluated_predictions, lexical_fields, key="lexical")
