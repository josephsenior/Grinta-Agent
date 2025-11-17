import argparse
import copy
import difflib
import json
import logging
import os

logger = logging.getLogger(__name__)


def insert_line_in_string(input_string, new_str, insert_line):
    """Inserts a new line into a string at the specified line number.

    :param input_string: The original string.
    :param new_str: The string to insert.
    :param insert_line: The line number at which to insert (1-based index).
    :return: The modified string.
    """
    file_text = input_string.expandtabs()
    new_str = new_str.expandtabs()
    file_text_lines = file_text.split("\n")
    new_str_lines = new_str.split("\n")
    new_file_text_lines = (
        file_text_lines[:insert_line] + new_str_lines + file_text_lines[insert_line:]
    )
    return "\n".join(new_file_text_lines)


def print_string_diff(original, modified):
    """Prints the differences between two strings line by line.

    :param original: The original string.
    :param modified: The modified string.
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="original",
        tofile="modified",
        lineterm="",
    )
    logger.info("".join(diff))


def _process_tool_call(tool_call: dict, test_suite: str) -> str:
    """Process a single tool call and return updated test suite."""
    tool_call_dict = eval(tool_call["function"]["arguments"])  # nosec B307 - Safe: parsing controlled evaluation output
    if tool_call_dict is None or tool_call_dict == {}:
        return test_suite

    command = tool_call_dict["command"]

    if command == "create":
        return tool_call_dict["file_text"]

    if command != "str_replace" and command != "insert" and "coverage" not in command:
        logger.info("%s", command)

    if command == "insert":
        return insert_line_in_string(
            test_suite, tool_call_dict["new_str"], tool_call_dict["insert_line"]
        )
    elif command == "str_replace":
        if test_suite.count(tool_call_dict["old_str"]) == 1:
            return test_suite.replace(
                tool_call_dict["old_str"], tool_call_dict["new_str"]
            )

    return test_suite


def _process_json_file(file_path: str, test_suite: str) -> str:
    """Process a single JSON file and return updated test suite."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                tool_calls = data["response"]["choices"][0]["message"]["tool_calls"]
                if tool_calls is not None:
                    for tool_call in tool_calls:
                        test_suite = _process_tool_call(tool_call, test_suite)
            except Exception:
                logger.exception("Error while processing tool_calls")
    except Exception as e:
        logger.exception("Error loading %s", file_path)
        logger.error("  Error loading %s: %s", file_path, e)

    return test_suite


def _process_subdirectory(
    subdir: str, subdir_path: str, metadata: dict, preds_objs: dict, final_output: dict
) -> None:
    """Process a single subdirectory and update final_output."""
    if not os.path.isdir(subdir_path):
        return

    logger.info("Processing subdirectory: %s", subdir)
    i = 0
    test_suite = preds_objs.get(subdir, "")

    for file in sorted(os.listdir(subdir_path)):
        if not file.endswith(".json"):
            continue

        metadata_copy = copy.deepcopy(metadata)
        file_path = os.path.join(subdir_path, file)
        test_suite = _process_json_file(file_path, test_suite)

        metadata_copy["test_result"]["test_suite"] = test_suite
        if i < 25:
            final_output[i].append(metadata_copy)
            i += 1

    # Fill remaining slots with the last metadata
    for j in range(i, 24):
        final_output[j].append(metadata_copy)

    # Add original test suite as the last entry
    metadata_orig = copy.deepcopy(metadata)
    orig_test_suite = metadata["test_result"]["test_suite"]
    metadata_orig["test_result"]["test_suite"] = orig_test_suite
    final_output[24].append(metadata_orig)


def _write_output_files(output_dir: str, final_output: dict) -> None:
    """Write all output files to disk."""
    for i in range(25):
        output_file = os.path.join(output_dir, f"output_{i}.jsonl")
        with open(output_file, "w", encoding="utf-8") as f:
            for metadata in final_output[i]:
                f.write(json.dumps(metadata) + "\n")


def parse_json_files(root_dir, output_dir, metadata_objs, preds_objs):
    """Parse JSON files and generate output files."""
    final_output = {i: [] for i in range(25)}

    for subdir in sorted(os.listdir(root_dir)):
        subdir_path = os.path.join(root_dir, subdir)
        metadata = metadata_objs[subdir]
        _process_subdirectory(subdir, subdir_path, metadata, preds_objs, final_output)

    _write_output_files(output_dir, final_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse JSON file")
    parser.add_argument("--root_dir", type=str, help="Root directory", required=True)
    parser.add_argument(
        "--output_dir", type=str, help="Output directory", required=True
    )
    parser.add_argument(
        "--starting_preds_file", type=str, help="Starting predictions", default=None
    )
    args = parser.parse_args()
    output_file = os.path.join(args.output_dir, "output.jsonl")
    metadata_objs = {}
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.readlines()
        for line in content:
            metadata = json.loads(line)
            metadata_objs[metadata["instance_id"]] = metadata
    starting_preds_file = args.starting_preds_file
    preds_objs = {}
    if starting_preds_file is not None:
        with open(starting_preds_file, "r", encoding="utf-8") as f:
            content = f.readlines()
            for line in content:
                pred = json.loads(line)
                preds_objs[pred["id"]] = pred["preds"]["full"][0]
    parse_json_files(args.root_dir, args.output_dir, metadata_objs, preds_objs)
