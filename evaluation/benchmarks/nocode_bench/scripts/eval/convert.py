import argparse
import json
import logging
from forge.core.io import print_json_stdout

logger = logging.getLogger(__name__)


def main(output_jsonl: str):
    with open(output_jsonl, "r", encoding='utf-8') as f:
        for line in f:
            try:
                output = json.loads(line)
                pred = {
                    "instance_id": output["instance_id"],
                    "model_name_or_path": output["metadata"]["llm_config"]["model"],
                    "model_patch": output["test_result"]["git_patch"],
                }
            except Exception as e:
                logger.exception("Error while reading output of instance: %s", e)
                continue
            print_json_stdout(pred)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_jsonl", type=str, required=True, help="Path to the prediction file (.../outputs.jsonl)"
    )
    args = parser.parse_args()
    main(args.output_jsonl)
