import json
import logging
import pprint
import sys

logger = logging.getLogger(__name__)


def extract_test_results(res_file_path: str) -> tuple[list[str], list[str]]:
    passed = []
    failed = []
    costs = []
    instance_ids = set()
    instances = []
    with open(res_file_path, "r", encoding="utf-8") as file:
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
                        "eval_script": data["eval_script"],
                        "eval_exit_code": data["eval_exit_code"],
                        "eval_output": data["eval_output"],
                        "accumulated_cost": data["metrics"]["accumulated_cost"],
                    }
                )
            costs.append(data["metrics"]["accumulated_cost"])
        instances.sort(key=lambda x: x["instance_id"])
        with open(res_file_path, "w", encoding="utf-8") as file:
            for instance in instances:
                file.write(json.dumps(instance) + "\n")
        return (passed, failed, costs)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error(
            "Usage: poetry run python summarise_results.py <path_to_output_jsonl_file>"
        )
        sys.exit(1)
    json_file_path = sys.argv[1]
    passed_tests, failed_tests, costs = extract_test_results(json_file_path)
    success_rate = len(passed_tests) / (len(passed_tests) + len(failed_tests))
    logger.info("PASSED TESTS:")
    pprint.pprint(passed_tests)
    logger.info("FAILED TESTS:")
    pprint.pprint(failed_tests)
    logger.info(
        "\nPassed %d tests, failed %d tests, success rate = %s, average cost = %s",
        len(passed_tests),
        len(failed_tests),
        success_rate,
        sum(costs) / len(costs) if costs else 0,
    )
