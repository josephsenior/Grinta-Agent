import argparse
import json
import os
from collections import defaultdict
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("input_file", type=str)
args = parser.parse_args()
dirname = os.path.dirname(args.input_file)
instance_id_to_status = defaultdict(
    lambda: {
        "empty_generation": False,
        "resolved": False,
        "failed_apply_patch": False,
        "error_eval": False,
        "test_timeout": False,
    }
)
swebench_official_report_json = os.path.join(dirname, "report.json")
openhands_remote_report_jsonl = args.input_file.replace(".jsonl", ".swebench_eval.jsonl")
if os.path.exists(swebench_official_report_json):
    output_md_filepath = os.path.join(dirname, "README.md")
    with open(swebench_official_report_json, "r", encoding='utf-8') as f:
        report = json.load(f)
    output_md = f"# SWE-bench Report\nThis folder contains the evaluation results of the SWE-bench using the [official evaluation docker containerization](https://github.com/princeton-nlp/SWE-bench/blob/main/docs/20240627_docker/README.md#choosing-the-right-cache_level).\n\n## Summary\n- total instances: {
        report['total_instances']}\n- submitted instances: {
        report['submitted_instances']}\n- completed instances: {
            report['completed_instances']}\n- empty patch instances: {
                report['empty_patch_instances']}\n- resolved instances: {
                    report['resolved_instances']}\n- unresolved instances: {
                        report['unresolved_instances']}\n- error instances: {
                            report['error_instances']}\n"
    output_md += "\n## Resolved Instances\n"
    for instance_id in report["resolved_ids"]:
        instance_id_to_status[instance_id]["resolved"] = True
        output_md += f"- [{instance_id}](./eval_outputs/{instance_id}/run_instance.log)\n"
    output_md += "\n## Unresolved Instances\n"
    for instance_id in report["unresolved_ids"]:
        output_md += f"- [{instance_id}](./eval_outputs/{instance_id}/run_instance.log)\n"
    output_md += "\n## Error Instances\n"
    for instance_id in report["error_ids"]:
        instance_id_to_status[instance_id]["error_eval"] = True
        output_md += f"- [{instance_id}](./eval_outputs/{instance_id}/run_instance.log)\n"
    output_md += "\n## Empty Patch Instances\n"
    for instance_id in report["empty_patch_ids"]:
        instance_id_to_status[instance_id]["empty_generation"] = True
        output_md += f"- [{instance_id}](./eval_outputs/{instance_id}/run_instance.log)\n"
    output_md += "\n## Incomplete Instances\n"
    for instance_id in report["incomplete_ids"]:
        output_md += f"- [{instance_id}](./eval_outputs/{instance_id}/run_instance.log)\n"
    with open(output_md_filepath, "w", encoding='utf-8') as f:
        f.write(output_md)
elif os.path.exists(openhands_remote_report_jsonl):
    output_md_filepath = args.input_file.replace(".jsonl", ".swebench_eval.md")
    instance_ids = set()
    eval_instance_ids = set()
    n_instances = 0
    with open(args.input_file, "r", encoding='utf-8') as f:
        for line in tqdm(f, desc="Counting instances in original file"):
            data = json.loads(line)
            instance_ids.add(data["instance_id"])
            n_instances += 1
    print(f"Total instances in original file: {n_instances}")
    n_eval_instances = 0
    with open(openhands_remote_report_jsonl, "r", encoding='utf-8') as f:
        for line in tqdm(f, desc="Processing eval report"):
            data = json.loads(line)
            instance_id = data["instance_id"]
            eval_instance_ids.add(instance_id)
            n_eval_instances += 1
            instance_id_to_status[instance_id] = data["test_result"]["report"]
    print(f"Total instances in eval report: {n_eval_instances}")
    assert len(instance_ids) == n_instances, "Duplicate instance ids found in original output"
    assert len(eval_instance_ids) == n_eval_instances, "Duplicate instance ids found in eval report"
    stats = {"total": len(instance_ids), "resolved": 0, "empty_patch": 0, "error": 0}
    resolved_ids = []
    unresolved_ids = []
    error_ids = []
    empty_patch_ids = []
    timeout_ids = []
    with open(args.input_file, "r", encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            instance_id = data["instance_id"]
            report = instance_id_to_status[instance_id]
            if report.get("resolved", False):
                stats["resolved"] += 1
                resolved_ids.append(instance_id)
            else:
                unresolved_ids.append(instance_id)
            if report.get("empty_generation", False):
                stats["empty_patch"] += 1
                empty_patch_ids.append(instance_id)
            if report.get("error_eval", False):
                stats["error"] += 1
                error_ids.append(instance_id)
            if report.get("test_timeout", False):
                timeout_ids.append(instance_id)

    def _instance_id_to_log_path(instance_id):
        path = f"{args.input_file.replace('.jsonl', '.swebench_eval.logs')}/instance_{instance_id}.log"
        return os.path.relpath(path, start=dirname)

    output_md = f"# SWE-bench Report\nThis folder contains the evaluation results of the SWE-bench using the [official evaluation docker containerization](https://github.com/princeton-nlp/SWE-bench/blob/main/docs/20240627_docker/README.md#choosing-the-right-cache_level).\n\n## Summary\n- submitted instances: {
        stats['total']}\n- empty patch instances: {
        stats['empty_patch']}\n- resolved instances: {
            stats['resolved']}\n- unresolved instances: {
                len(unresolved_ids)}\n- error instances: {
                    stats['error']}\n"
    output_md += "\n## Resolved Instances\n"
    for instance_id in resolved_ids:
        instance_id_to_status[instance_id]["resolved"] = True
        output_md += f"- [{instance_id}]({_instance_id_to_log_path(instance_id)})\n"
    output_md += "\n## Unresolved Instances\n"
    for instance_id in unresolved_ids:
        output_md += f"- [{instance_id}]({_instance_id_to_log_path(instance_id)})\n"
    output_md += "\n## Error Instances\n"
    for instance_id in error_ids:
        instance_id_to_status[instance_id]["error_eval"] = True
        output_md += f"- [{instance_id}]({_instance_id_to_log_path(instance_id)})\n"
    output_md += "\n## Empty Patch Instances\n"
    for instance_id in empty_patch_ids:
        instance_id_to_status[instance_id]["empty_generation"] = True
        output_md += f"- [{instance_id}]({_instance_id_to_log_path(instance_id)})\n"
    output_md += "\n## Incomplete Instances\n"
    for instance_id in timeout_ids:
        output_md += f"- [{instance_id}]({_instance_id_to_log_path(instance_id)})\n"
    with open(output_md_filepath, "w", encoding='utf-8') as f:
        f.write(output_md)
else:
    print(
        f"No report file found: Both {swebench_official_report_json} and {openhands_remote_report_jsonl} do not exist."
    )
exit()
needs_update = False
with open(args.input_file, "r", encoding='utf-8') as infile:
    for line in tqdm(infile, desc="Checking for changes"):
        data = json.loads(line)
        instance_id = data["instance_id"]
        current_report = data.get("report", {})
        new_report = instance_id_to_status[instance_id]
        if current_report != new_report:
            needs_update = True
            break
if not needs_update:
    print("No updates detected. Skipping file update.")
    exit()
if os.path.exists(f"{args.input_file}.bak"):
    conf = input("Existing backup file found. Do you want to overwrite it? (y/n)")
    if conf != "y":
        exit()
    os.remove(f"{args.input_file}.bak")
os.rename(args.input_file, f"{args.input_file}.bak")
with open(f"{args.input_file}.bak", "r", encoding='utf-8') as infile, open(args.input_file, "w", encoding='utf-8') as outfile:
    for line in tqdm(infile, desc="Updating output file"):
        data = json.loads(line)
        instance_id = data["instance_id"]
        data["report"] = instance_id_to_status[instance_id]
        outfile.write(json.dumps(data) + "\n")
