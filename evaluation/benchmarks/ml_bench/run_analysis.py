import json
import os
import pprint
import tqdm
from forge.core.config import get_evaluation_parser, get_llm_config_arg, load_FORGE_config
from forge.core.logger import forge_logger as logger
from forge.llm.llm import LLM

config = load_FORGE_config()


def extract_test_results(res_file_path: str) -> tuple[list[str], list[str]]:
    passed = []
    failed = []
    costs = []
    instance_ids = set()
    instances = []
    with open(res_file_path, "r", encoding='utf-8') as file:
        for line in file:
            data = json.loads(line.strip())
            success = data["metrics"]["success"]
            if data["instance_id"] in instance_ids:
                print(f"WARNING: Duplicate instance_id found: {data['instance_id']}")
                continue
            instance_ids.add(data["instance_id"])
            instances.append(data)
            if success:
                passed.append(
                    {
                        "instance_id": data["instance_id"],
                        "repo": data["repo"],
                        "instruction": data["instruction"],
                        "eval_script": data["eval_script"],
                        "eval_exit_code": data["eval_exit_code"],
                        "eval_output": data["eval_output"],
                        "accumulated_cost": data["metrics"]["accumulated_cost"],
                    }
                )
            else:
                failed.append(
                    {
                        "instance_id": data["instance_id"],
                        "repo": data["repo"],
                        "instruction": data["instruction"],
                        "metadata": data["metadata"],
                        "history": data["history"],
                        "eval_script": data["eval_script"],
                        "eval_exit_code": data["eval_exit_code"],
                        "eval_output": data["eval_output"],
                        "accumulated_cost": data["metrics"]["accumulated_cost"],
                    }
                )
            costs.append(data["metrics"]["accumulated_cost"])
        instances.sort(key=lambda x: x["instance_id"])
        with open(res_file_path, "w", encoding='utf-8') as file:
            for instance in instances:
                file.write(json.dumps(instance) + "\n")
        return (passed, failed, costs)


def classify_error(llm: LLM, failed_case: dict) -> str:
    prompt = f"\n    Please classify the error for the following failed case based on the history and eval_output:\n\n    Instruction:\n    {
        failed_case['instruction']}\n\n    Eval Script:\n    {
        failed_case['eval_script']}s\n\n    History:\n    {
            failed_case['history']}\n\n    Eval Output:\n    {
                failed_case['eval_output']}\n\n    The error categories are:\n    E1: Hallucination Errors - The model misinterpreted the user's intention, misplaced Python code and bash script, or generated random or irrelevant code.\n    E2: Lack of Knowledge or Information - The model lacks sufficient information or domain-specific knowledge to satisfy the user's requirements.\n    E3: Knowledge Manipulation - The model failed to integrate or manipulate information properly.\n    E4: Syntax Errors - The model generated code with syntax errors.\n    E5: Operational Error - The model gave up easily or exited without finishing the tasks.\n\n    Please provide only the error category (E1, E2, E3, E4, or E5) without any explanation.\n    "
    try:
        response = llm.completion(messages=[{"content": prompt, "role": "user"}])
        error_category = response.choices[0].message["content"]
    except Exception as e:
        logger.error("Failed to classify the error for the failed case: %s", failed_case["instance_id"])
        logger.error(e)
        error_category = input(
            failed_case["instruction"] + ": " + failed_case["eval_script"] + " - " + failed_case["eval_output"]
        )
    if error_category not in ["E1", "E2", "E3", "E4", "E5"]:
        raise ValueError(f"Invalid error category: {error_category}")
    return error_category


if __name__ == "__main__":
    parser = get_evaluation_parser()
    parser.add_argument(
        "--json_file_path", type=str, required=True, help="Path to the jsonl file containing the evaluation results"
    )
    args, _ = parser.parse_known_args()
    if args.llm_config:
        specified_llm_config = get_llm_config_arg(args.llm_config)
        specified_llm_config.modify_params = False
        if specified_llm_config:
            config.llm = specified_llm_config
    logger.info("Config for evaluation: %s", config)
    llm = LLM(llm_config=specified_llm_config)
    passed, new_failed, costs = extract_test_results(args.json_file_path)
    failed = []
    if os.path.exists(args.json_file_path.replace(".jsonl", "_failed.jsonl")):
        with open(args.json_file_path.replace(".jsonl", "_failed.jsonl"), "r") as file:
            failed.extend((json.loads(line.strip()) for line in file))
        logger.info(
            "Loaded %d failed cases from %s", len(failed), args.json_file_path.replace(".jsonl", "_failed.jsonl")
        )
    for failed_case in tqdm.tqdm(new_failed):
        if failed_case["instance_id"] in [case["instance_id"] for case in failed]:
            continue
        error_category = classify_error(llm, failed_case)
        failed_case["error_category"] = error_category
        failed.append(failed_case)
        with open(args.json_file_path.replace(".jsonl", "_failed.jsonl"), "a") as file:
            file.write(json.dumps(failed_case) + "\n")
    logger.info("Summary:")
    logger.info("Passed: %d", len(passed))
    logger.info("Failed: %d", len(failed))
    logger.info("Costs: %s", costs)
    logger.info("Failed cases:")
    error_categories = {}
    for case in failed:
        error_category = case["error_category"]
        if error_category not in error_categories:
            error_categories[error_category] = 0
        error_categories[error_category] += 1
    pprint.pprint(error_categories)
