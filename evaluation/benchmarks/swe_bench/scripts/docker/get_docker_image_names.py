"""Get official docker image names for SWE-bench instances."""

import argparse
from datasets import load_dataset

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=str, default="princeton-nlp/SWE-bench")
parser.add_argument("--split", type=str, default="test")
parser.add_argument("--output", type=str, default="swebench_images.txt")
args = parser.parse_args()
SUPPORTED_DATASET = {
    "princeton-nlp/SWE-bench_Multimodal",
    "princeton-nlp/SWE-bench",
    "princeton-nlp/SWE-bench_Lite",
    "princeton-nlp/SWE-bench_Verified",
}
assert args.dataset in SUPPORTED_DATASET, f"Dataset {args.dataset} not supported"


def swebench_instance_id_to_docker_image_name(instance_id: str) -> str:
    repo, name = instance_id.split("__")
    return f"swebench/sweb.eval.x86_64.{repo}_1776_{name}:latest"


def swebench_multimodal_instance_id_to_docker_image_name(instance_id: str) -> str:
    repo, name = instance_id.split("__")
    return f"swebench/sweb.mm.eval.x86_64.{repo}_1776_{name}:latest"


dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
instance_ids = dataset["instance_id"]
print(f"Loading {len(instance_ids)} instances from {args.dataset} split {args.split}")
with open(args.output, "w", encoding='utf-8') as f:
    for instance_id in instance_ids:
        if args.dataset in [
            "princeton-nlp/SWE-bench",
            "princeton-nlp/SWE-bench_Lite",
            "princeton-nlp/SWE-bench_Verified",
        ]:
            f.write(swebench_instance_id_to_docker_image_name(instance_id) + "\n")
        else:
            f.write(swebench_multimodal_instance_id_to_docker_image_name(instance_id) + "\n")
print(f"Saved {len(instance_ids)} images to {args.output}")
