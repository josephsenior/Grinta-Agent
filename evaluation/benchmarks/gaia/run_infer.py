import asyncio
import copy
import functools
import os
import re
import shutil
import zipfile
import huggingface_hub
import pandas as pd
from datasets import load_dataset
from PIL import Image
from evaluation.benchmarks.gaia.scorer import question_scorer
from evaluation.benchmarks.gaia.utils import image_to_jpg_base64_url, image_to_png_base64_url
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
from forge.core.config import ForgeConfig, get_evaluation_parser, get_llm_config_arg, load_from_toml
from forge.core.config.utils import get_agent_config_arg
from forge.core.logger import forge_logger as logger
from forge.core.main import create_runtime, run_controller
from forge.events.action import AgentFinishAction, CmdRunAction, MessageAction
from forge.runtime.base import Runtime
from forge.utils.async_utils import call_async_from_sync

DATASET_CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {
    "CodeActAgent": functools.partial(codeact_user_response, encapsulate_solution=True)
}
AGENT_CLS_TO_INST_SUFFIX = {
    "CodeActAgent": "When you think you have solved the question, please use the finish tool and include your final answer in the message parameter of the finish tool. Your final answer MUST be encapsulated within <solution> and </solution>.\n"
}


def get_config(metadata: EvalMetadata) -> ForgeConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = "nikolaik/python-nodejs:python3.12-nodejs22"
    config = get_FORGE_config_for_eval(metadata=metadata, sandbox_config=sandbox_config, runtime="docker")
    config.set_llm_config(metadata.llm_config)
    if metadata.agent_config:
        config.set_agent_config(metadata.agent_config, metadata.agent_class)
    else:
        logger.info("Agent config not provided, using default settings")
        agent_config = config.get_agent_config(metadata.agent_class)
        agent_config.enable_prompt_extensions = False
    config_copy = copy.deepcopy(config)
    load_from_toml(config_copy)
    config.search_api_key = config_copy.search_api_key
    return config


def _setup_workspace(runtime: Runtime) -> None:
    """Setup the workspace directory."""
    action = CmdRunAction(command="mkdir -p /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0


def _handle_zip_file(runtime: Runtime, instance: pd.Series, metadata) -> None:
    """Handle zip file extraction."""
    instance["file_name"].split(".")[-1]
    src_file = os.path.join(DATASET_CACHE_DIR, "2023", metadata.data_split, instance["file_name"])
    assert os.path.exists(src_file)

    temp_dir = os.path.join(DATASET_CACHE_DIR, "2023", metadata.data_split, "tmp_file")
    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(src_file, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    dest_file = "/workspace"
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            runtime.copy_to(os.path.join(root, file), dest_file)

    shutil.rmtree(temp_dir)


def _handle_regular_file(runtime: Runtime, instance: pd.Series, metadata) -> None:
    """Handle regular file copying."""
    extension_name = instance["file_name"].split(".")[-1]
    src_file = os.path.join(DATASET_CACHE_DIR, "2023", metadata.data_split, instance["file_name"])
    assert os.path.exists(src_file)

    dest_file = "/workspace"
    runtime.copy_to(src_file, dest_file)

    action = CmdRunAction(command=f"mv /workspace/{instance['file_name']} /workspace/file.{extension_name}")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0


def _handle_file_upload(runtime: Runtime, instance: pd.Series, metadata) -> None:
    """Handle file upload based on file type."""
    if instance["file_name"] != "":
        assert metadata.data_split is not None
        extension_name = instance["file_name"].split(".")[-1]

        if extension_name == "zip":
            _handle_zip_file(runtime, instance, metadata)
        elif extension_name not in ["jpg", "png"]:
            _handle_regular_file(runtime, instance, metadata)


def _setup_environment(runtime: Runtime) -> None:
    """Setup the environment with necessary tools."""
    action = CmdRunAction(command="cd /workspace")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    action = CmdRunAction(command="apt-get update && apt-get install -y ffmpeg && apt-get install -y ffprobe")
    runtime.run_action(action)


def initialize_runtime(runtime: Runtime, instance: pd.Series):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    """
    logger.info("%s BEGIN Runtime Initialization Fn %s", "-" * 50, "-" * 50)

    # Setup workspace
    _setup_workspace(runtime)

    # Handle file upload
    _handle_file_upload(runtime, instance, metadata)

    # Setup environment
    _setup_environment(runtime)

    logger.info("%s END Runtime Initialization Fn %s", "-" * 50, "-" * 50)


def _setup_logging(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool) -> None:
    """Setup logging for the evaluation instance."""
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, "infer_logs")
        reset_logger_for_multiprocessing(logger, instance["instance_id"], log_dir)
    else:
        logger.info("Starting evaluation for instance %s.", instance["instance_id"])


def _prepare_file_handling(instance: pd.Series) -> tuple[str | None, str | None]:
    """Prepare file handling for the instance."""
    if instance["file_name"] != "":
        extension_name = instance["file_name"].split(".")[-1]
        dest_file = os.path.join("/workspace", f"file.{extension_name}")
        return dest_file, extension_name
    return None, None


def _build_base_instruction(instance: pd.Series) -> str:
    """Build the base instruction for the task."""
    return "You have one question to answer. It is paramount that you provide a correct answer.\nGive it all you can: I know for a fact that you have access to all the relevant tools to solve it and find the correct answer (the answer does not exist). Failure or 'I cannot answer' or 'None found' will not be tolerated, success will be rewarded.\nYou must make sure you find the correct answer! You MUST strictly follow the task-specific formatting instructions for your final answer.\nHere is the task:\n{task_question}\n".format(
        task_question=instance["Question"]
    )


def _get_zip_file_instruction(instance: pd.Series, metadata: EvalMetadata) -> str:
    """Get instruction text for zip file contents."""
    filenames = []
    src_file = os.path.join(DATASET_CACHE_DIR, "2023", metadata.data_split, instance["file_name"])
    with zipfile.ZipFile(src_file, "r") as zip_ref:
        filenames = zip_ref.namelist()
    filenames = [f"/workspace/{file}" for file in filenames]
    filenames = ", ".join(filenames)
    return f"To solve this task you will have to use the attached files provided in the workspace at locations: {filenames}\n\n"


def _handle_image_file(instance: pd.Series, metadata: EvalMetadata, extension_name: str) -> tuple[str, list]:
    """Handle image file processing and return instruction addition and image URLs."""
    src_file = os.path.join(DATASET_CACHE_DIR, "2023", metadata.data_split, instance["file_name"])
    instruction_addition = "Image: To solve this task you will have to use the image shown below.\n\n"
    image = Image.open(src_file)

    if extension_name == "jpg":
        image_urls = [image_to_jpg_base64_url(image)]
    else:
        image_urls = [image_to_png_base64_url(image)]

    return instruction_addition, image_urls


def _add_file_instructions(
    instruction: str, dest_file: str | None, extension_name: str | None, instance: pd.Series, metadata: EvalMetadata
) -> tuple[str, list]:
    """Add file-specific instructions to the main instruction."""
    image_urls = []

    if dest_file:
        if extension_name not in ["jpg", "png", "zip"]:
            instruction += f"To solve this task you will have to use the attached file provided in the workspace at location: {dest_file}\n\n"
        elif extension_name == "zip":
            instruction += _get_zip_file_instruction(instance, metadata)
        else:
            instruction_addition, image_urls = _handle_image_file(instance, metadata, extension_name)
            instruction += instruction_addition

    return instruction, image_urls


def _add_standard_instructions(instruction: str, metadata: EvalMetadata) -> str:
    """Add standard instructions to the main instruction."""
    instruction += "IMPORTANT: When seeking information from a website, REFRAIN from arbitrary URL navigation. You should utilize the designated search engine tool with precise keywords to obtain relevant URLs or use the specific website's search interface. DO NOT navigate directly to specific URLs as they may not exist.\n\nFor example: if you want to search for a research paper on Arxiv, either use the search engine tool with specific keywords or navigate to arxiv.org and then use its interface.\n"
    instruction += "IMPORTANT: You should NEVER ask for Human Help.\n"
    instruction += "IMPORTANT: Please encapsulate your final answer (answer ONLY) within <solution> and </solution>. Your answer will be evaluated using string matching approaches so it important that you STRICTLY adhere to the output formatting instructions specified in the task (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)\n"
    instruction += "For example: The answer to the question is <solution> 42 </solution>.\n"
    instruction += "IMPORTANT: Your final answer should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. If you are asked for a number, express it numerically (i.e., with digits rather than words), do not use commas, and do not include units such as $ or percent signs unless specified otherwise. If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities). If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string.\n"
    instruction += AGENT_CLS_TO_INST_SUFFIX.get(metadata.agent_class, "")
    return instruction


def _extract_model_answer(state: State) -> str:
    """Extract model answer from state history."""
    model_answer_raw = ""
    for event in reversed(state.history):
        if event.source == "agent":
            if isinstance(event, AgentFinishAction):
                model_answer_raw = event.final_thought
                break
            elif isinstance(event, CmdRunAction):
                model_answer_raw = event.thought
                break
            elif isinstance(event, MessageAction):
                model_answer_raw = event.content
                break

    model_answer = re.findall("<solution>(.*?)</solution>", model_answer_raw)
    if len(model_answer) != 0:
        return model_answer[0]
    logger.warning("Failed to parse model answer: %s", model_answer_raw)
    return model_answer_raw


def _create_eval_output(
    instance: pd.Series, metadata: EvalMetadata, state: State, model_answer: str, model_answer_raw: str
) -> EvalOutput:
    """Create the final evaluation output."""
    logger.info("Final message: %s | Ground truth: %s", model_answer, instance["Final answer"])
    score = question_scorer(model_answer=model_answer, ground_truth=instance["Final answer"])
    test_result = {
        "score": score,
        "model_answer_raw": model_answer_raw,
        "model_answer": model_answer,
        "ground_truth": instance["Final answer"],
    }
    metrics = get_metrics(state)
    histories = compatibility_for_eval_history_pairs(state.history)

    return EvalOutput(
        instance_id=instance["instance_id"],
        instance=instance.to_dict(),
        instruction=instance["Question"],
        metadata=metadata,
        history=histories,
        metrics=metrics,
        error=state.last_error if state and state.last_error else None,
        test_result=test_result,
    )


def process_instance(instance: pd.Series, metadata: EvalMetadata, reset_logger: bool = True) -> EvalOutput:
    """Process a single evaluation instance."""
    config = get_config(metadata)
    _setup_logging(instance, metadata, reset_logger)
    dest_file, extension_name = _prepare_file_handling(instance)

    instruction = _build_base_instruction(instance)
    logger.info("Instruction: %s", instruction)
    instruction, image_urls = _add_file_instructions(instruction, dest_file, extension_name, instance, metadata)
    instruction = _add_standard_instructions(instruction, metadata)
    logger.info("Instruction:\n%s", instruction, extra={"msg_type": "OBSERVATION"})

    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance)

    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction, image_urls=image_urls),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN[metadata.agent_class],
        )
    )

    if state is None:
        raise ValueError("State should not be None.")

    model_answer = _extract_model_answer(state)
    output = _create_eval_output(instance, metadata, state, model_answer, model_answer)

    runtime.close()
    return output


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument("--level", type=str, help="gaia level to evaluate, eg. 2023_level1")
    parser.add_argument("--data-split", type=str, help="data split to evaluate, eg. test", default="validation")
    args, _ = parser.parse_known_args()
    agent_config = None
    if args.agent_config:
        agent_config = get_agent_config_arg(args.agent_config)
    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f"Could not find LLM config: --llm_config {args.llm_config}")
    toml_config = ForgeConfig()
    load_from_toml(toml_config)
    metadata = make_metadata(
        llm_config=llm_config,
        dataset_name="gaia",
        agent_class=args.agent_cls,
        max_iterations=args.max_iterations,
        eval_note=args.eval_note,
        eval_output_dir=args.eval_output_dir,
        data_split=args.data_split,
        details={"gaia-level": args.level, "mcp-servers": ["tavily"] if toml_config.search_api_key else []},
        agent_config=agent_config,
    )
    dataset = load_dataset("gaia-benchmark/GAIA", args.level)  # nosec B615 - Safe: evaluation benchmark dataset
    huggingface_hub.snapshot_download(
        "gaia-benchmark/GAIA", repo_type="dataset", local_dir=DATASET_CACHE_DIR
    )  # nosec B615 - Safe: evaluation dataset download
    gaia_tests = dataset[metadata.data_split].to_pandas()
    gaia_tests.rename(columns={"task_id": "instance_id"}, inplace=True)
    output_file = os.path.join(metadata.eval_output_dir, "output.jsonl")
    prepared_dataset = prepare_dataset(gaia_tests, output_file, args.eval_n_limit)
    run_evaluation(
        dataset=prepared_dataset,
        metadata=metadata,
        output_file=output_file,
        num_workers=args.eval_num_workers,
        process_instance_func=process_instance,
    )
