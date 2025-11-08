"""Convert Forge output to a readable markdown format for visualization."""

import argparse
import json
import os
from glob import glob
import pandas as pd
from tqdm import tqdm
from evaluation.benchmarks.swe_bench.eval_infer import process_git_patch
from forge.events.serialization import event_from_dict

tqdm.pandas()
parser = argparse.ArgumentParser()
parser.add_argument("oh_output_file", type=str)
args = parser.parse_args()
output_md_folder = args.oh_output_file.replace(".jsonl", ".viz")
print(f"Converting {args.oh_output_file} to markdown files in {output_md_folder}")
oh_format = pd.read_json(args.oh_output_file, orient="records", lines=True)
output_dir = os.path.dirname(args.oh_output_file)
swebench_eval_file = args.oh_output_file.replace(".jsonl", ".swebench_eval.jsonl")
if os.path.exists(swebench_eval_file):
    eval_output_df = pd.read_json(swebench_eval_file, orient="records", lines=True)
else:
    eval_output_df = None
model_name = os.path.basename(os.path.dirname(args.oh_output_file))


def convert_history_to_str(history):
    ret = ""
    separator = "\n\n" + "-" * 100 + "\n"
    for i, event in enumerate(history):
        if i != 0:
            ret += separator
        if isinstance(event, list):
            event_obj = event_from_dict(event[0])
            ret += f"## {i + 1}| {event_obj.__class__.__name__}\n\n"
            ret += str(event_obj)
            ret += separator
            event_obj = event_from_dict(event[1])
        else:
            event_obj = event_from_dict(event)
        ret += f"## {i + 1}| {event_obj.__class__.__name__}\n\n"
        ret += str(event_obj)
    return ret


def load_completions(instance_id: str):
    global output_dir
    glob_path = os.path.join(output_dir, "llm_completions", instance_id, "*.json")
    files = sorted(glob(glob_path))
    try:
        file_path = files[-1]
    except IndexError:
        return None
    with open(file_path, "r", encoding='utf-8') as f:
        result = json.load(f)
    messages = result["messages"]
    messages.append(result["response"]["choices"][0]["message"])
    tools = result["kwargs"].get("tools", None)
    return {"messages": messages, "tools": tools}


def _convert_content(content) -> str:
    ret = ""
    if isinstance(content, list):
        for item in content:
            assert item["type"] == "text", "Only text is supported for now"
            ret += f"{item['text']}\n"
    else:
        assert isinstance(content, str), "Only str is supported for now"
        ret = content
    return ret


def convert_tool_call_to_string(tool_call: dict) -> str:
    """Convert tool call to content in string format."""
    if "function" not in tool_call:
        raise ValueError("Tool call must contain 'function' key.")
    if "id" not in tool_call:
        raise ValueError("Tool call must contain 'id' key.")
    if "type" not in tool_call:
        raise ValueError("Tool call must contain 'type' key.")
    if tool_call["type"] != "function":
        raise ValueError("Tool call type must be 'function'.")
    ret = f"<function={tool_call['function']['name']}>\n"
    try:
        args = json.loads(tool_call["function"]["arguments"])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse arguments as JSON. Arguments: {tool_call['function']['arguments']}") from e
    for param_name, param_value in args.items():
        is_multiline = isinstance(param_value, str) and "\n" in param_value
        ret += f"<parameter={param_name}>"
        if is_multiline:
            ret += "\n"
        ret += f"{param_value}"
        if is_multiline:
            ret += "\n"
        ret += "</parameter>\n"
    ret += "</function>"
    return ret


def _should_skip_message(i: int, n_turns: int, first_n_turns: int | None, last_n_turns: int | None) -> bool:
    """Determine if a message should be skipped based on turn limits."""
    return (
        _should_skip_first_n_turns(i, first_n_turns, last_n_turns)
        or _should_skip_last_n_turns(i, n_turns, first_n_turns, last_n_turns)
        or _should_skip_middle_turns(i, n_turns, first_n_turns, last_n_turns)
    )


def _should_skip_first_n_turns(i: int, first_n_turns: int | None, last_n_turns: int | None) -> bool:
    """Check if message should be skipped due to first N turns limit."""
    return first_n_turns is not None and i >= first_n_turns and last_n_turns is None


def _should_skip_last_n_turns(i: int, n_turns: int, first_n_turns: int | None, last_n_turns: int | None) -> bool:
    """Check if message should be skipped due to last N turns limit."""
    return last_n_turns is not None and i < n_turns - last_n_turns and first_n_turns is None


def _should_skip_middle_turns(i: int, n_turns: int, first_n_turns: int | None, last_n_turns: int | None) -> bool:
    """Check if message should be skipped due to middle turns (both limits set)."""
    return first_n_turns is not None and last_n_turns is not None and i >= first_n_turns and i < n_turns - last_n_turns


def _process_system_message(traj: list) -> tuple[str, list]:
    """Process system message if present and return output and remaining trajectory."""
    output = ""
    if traj[0]["role"] == "system":
        system_message = traj[0]
        traj = traj[1:]
        content = _convert_content(system_message["content"])
        output += "*** System Message that describes the assistant's behavior ***\n"
        output += f"{content}\n"
    return output, traj


def _merge_consecutive_user_messages(traj: list, first_n_turns: int | None, last_n_turns: int | None) -> list:
    """Merge consecutive user messages into single messages."""
    merged_traj = []
    current_messages = []
    n_turns = len(traj)

    for i, message in enumerate(traj):
        if _should_skip_message(i, n_turns, first_n_turns, last_n_turns):
            continue

        if message["role"] == "user":
            current_messages.append(message)
        else:
            if current_messages:
                merged_content = "\n".join((_convert_content(msg["content"]) for msg in current_messages))
                merged_traj.append({"role": "user", "content": merged_content})
                current_messages = []
            merged_traj.append(message)

    # Handle any remaining user messages
    if current_messages:
        merged_content = "\n".join((_convert_content(msg["content"]) for msg in current_messages))
        merged_traj.append({"role": "user", "content": merged_content})

    return merged_traj


def _format_turn_header(turn_id: int, role: str) -> str:
    """Format the turn header with role information."""
    role_display = role.upper() if role != "tool" else "TOOL EXECUTION RESULT"
    return f"*** Turn {turn_id} - {role_display} ***\n"


def _format_tool_calls(message: dict) -> str:
    """Format tool calls for assistant messages."""
    output = ""
    if "tool_calls" in message and message["tool_calls"] is not None and len(message["tool_calls"]) > 0:
        for toolcall_id, tool_call in enumerate(message["tool_calls"]):
            output += f"### Tool Call {toolcall_id}\n"
            output += f"{convert_tool_call_to_string(tool_call)}\n"
    return output


def _format_message_content(role: str, content: str, message: dict) -> str:
    """Format message content based on role."""
    output = f"{content}\n"

    if role == "assistant":
        output += _format_tool_calls(message)

    return output


def format_traj(traj, first_n_turns=None, last_n_turns=None) -> str:
    """Format trajectory into a readable string representation."""
    # Process system message if present
    output, traj = _process_system_message(traj)

    # Merge consecutive user messages
    merged_traj = _merge_consecutive_user_messages(traj, first_n_turns, last_n_turns)

    # Format each message
    for i, message in enumerate(merged_traj):
        role, content = message["role"], message["content"]
        content = _convert_content(content) if isinstance(content, list) else content
        turn_id = i // 2 + 1

        output += "-" * 100 + "\n"
        output += _format_turn_header(turn_id, role)

        if role in ["user", "tool"]:
            output += f"{content}\n"
        elif role == "assistant":
            output += _format_message_content(role, content, message)
        else:
            raise ValueError(f"Unexpected role: {role}")

    output += "-" * 100 + "\n"
    return output


def write_row_to_md_file(row, instance_id_to_test_result):
    model_patch = _extract_model_patch(row)
    if model_patch is None:
        return

    resolved, test_output = _determine_resolution_status(row, instance_id_to_test_result)
    instance_id = row["instance_id"]
    filepath = _prepare_output_file(instance_id, resolved)

    completions = load_completions(instance_id)
    report = _load_report_file(instance_id)
    test_output = _load_test_output_if_needed(test_output, instance_id)

    _write_markdown_content(filepath, instance_id, resolved, row, completions, model_patch, report, test_output)


def _extract_model_patch(row):
    """Extract model patch from row data."""
    if "git_patch" in row:
        return row["git_patch"]
    elif "test_result" in row and "git_patch" in row["test_result"]:
        return row["test_result"]["git_patch"]
    else:
        print(f"Row {row} does not have a git_patch")
        return None


def _determine_resolution_status(row, instance_id_to_test_result):
    """Determine resolution status and test output."""
    test_output = None

    if "report" in row and row["report"] is not None:
        if not isinstance(row["report"], dict):
            print(f"ERROR: Report is not a dict, but a {type(row['report'])}. Row: {row}")
            return None, None
        else:
            resolved = row["report"].get("resolved", False)
    elif row["instance_id"] in instance_id_to_test_result:
        report = instance_id_to_test_result[row["instance_id"]].get("report", {})
        resolved = report.get("resolved", False)
        test_output = instance_id_to_test_result[row["instance_id"]].get("test_output", None)
    else:
        resolved = None

    return resolved, test_output


def _prepare_output_file(instance_id, resolved):
    """Prepare output file path."""
    filename = f"{str(resolved).lower()}.{instance_id}.md"
    os.makedirs(output_md_folder, exist_ok=True)
    return os.path.join(output_md_folder, filename)


def _load_report_file(instance_id):
    """Load report file if it exists."""
    global output_dir
    report_file = os.path.join(output_dir, "eval_outputs", instance_id, "report.json")
    if os.path.exists(report_file):
        with open(report_file, "r", encoding='utf-8') as f:
            return json.load(f)
    return None


def _load_test_output_if_needed(test_output, instance_id):
    """Load test output if not already available."""
    if test_output is None:
        global output_dir
        test_output_file = os.path.join(output_dir, "eval_outputs", instance_id, "test_output.txt")
        if os.path.exists(test_output_file):
            with open(test_output_file, "r", encoding='utf-8') as f:
                return f.read()
    return test_output


def _write_markdown_content(filepath, instance_id, resolved, row, completions, model_patch, report, test_output):
    """Write markdown content to file."""
    with open(filepath, "w", encoding='utf-8') as f:
        f.write(f"# {instance_id} (resolved: {resolved})\n")
        f.write("## MetaData\n")
        f.write("```json\n")
        f.write(json.dumps(row["metadata"], indent=2))
        f.write("\n```\n")

        if completions is not None:
            f.write("## Completion\n")
            traj = completions["messages"]
            f.write(format_traj(traj))

        f.write("## History\n")
        f.write(convert_history_to_str(row["history"]))
        f.write("## Model Patch\n")
        f.write(f"{process_git_patch(model_patch)}\n")

        if report is not None:
            f.write("## Report\n")
            f.write(json.dumps(report, indent=2))
            f.write("\n")

        f.write("## Test Output\n")
        f.write(str(test_output))
        f.write("\n")


instance_id_to_test_result = {}
if eval_output_df is not None:
    instance_id_to_test_result = (
        eval_output_df[["instance_id", "test_result"]].set_index("instance_id")["test_result"].to_dict()
    )
oh_format.progress_apply(write_row_to_md_file, axis=1, instance_id_to_test_result=instance_id_to_test_result)
