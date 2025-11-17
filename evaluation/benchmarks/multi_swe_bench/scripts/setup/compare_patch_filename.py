"""This script compares gold patches with Forge-generated patches and check whether.

Forge found the right (set of) files to modify.
"""

import argparse
import json
import re


def extract_modified_files(patch):
    modified_files = set()
    file_pattern = re.compile("^diff --git a/(.*?) b/")
    for line in patch.split("\n"):
        if match := file_pattern.match(line):
            modified_files.add(match[1])
    return modified_files


def process_report(oh_output_file):
    succ = 0
    fail = 0
    for line in open(oh_output_file, encoding="utf-8"):
        line = json.loads(line)
        instance_id = line["instance_id"]
        gold_patch = line["swe_instance"]["patch"]
        generated_patch = line["git_patch"]
        gold_modified_files = extract_modified_files(gold_patch)
        assert len(gold_modified_files) == 1
        generated_modified_files = extract_modified_files(generated_patch)
        all_files_in_generated = gold_modified_files.issubset(generated_modified_files)
        if all_files_in_generated:
            succ += 1
        else:
            fail += 1
            print(
                f"{instance_id}: file mismatch, gold = {gold_modified_files}, generated = {generated_modified_files}"
            )
    print(
        f"\nSUMMARY: {succ} out of {
            succ + fail
        } instances found correct files to edit, success rate = {
            succ / float(succ + fail)
        }"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--oh_output_file", help="Path to the OH output file")
    args = parser.parse_args()
    process_report(args.oh_output_file)
