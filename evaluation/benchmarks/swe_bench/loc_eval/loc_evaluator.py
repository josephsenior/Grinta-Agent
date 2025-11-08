import argparse
import ast
import json
import os
import re
import pandas as pd
from datasets import load_dataset
from tqdm import tqdm
from evaluation.benchmarks.swe_bench.loc_eval.loc_utils import LocMeta
from evaluation.benchmarks.swe_bench.run_infer import filter_dataset
from evaluation.utils.shared import prepare_dataset
from forge.core.logger import forge_logger as logger


class LocEvaluator:

    def __init__(self, args):
        """Localization evaluation.

        Args:
            args: all main arguments
        """
        self.args = args
        self.eval_dir = args.eval_dir
        self.eval_task_success = self._check_if_to_eval_success()
        self.sandbox_root = "/workspace"
        self.agent_turn_num = -1
        self.max_agent_turn = args.max_infer_turn
        self.align_failed_with_max_iter = args.align_with_max
        self.instance = None
        self.trajectory = None
        self.localizer = LocMeta(args.dataset, args.split)
        self.gold_loc = {"file": [], "function": []}
        self.agent_loc = {
            "gold loc": {"file": [], "function": []},
            "agent loc": {"file": [], "function": []},
            "turn index": {"file": [], "function": []},
            "loc progress": {"file": [], "function": []},
        }
        self.task_resolved = False
        self.cost_summary = {"total_cost": 0.0, "avg_cost": 0.0, "details": {}}
        self.save_dir = os.path.join(args.save_dir, "loc_eval_results")
        self._init_dir(self.save_dir)
        self.all_eval_results = {}
        self.overall_eval = {}

    def _init_config(self):
        self.instance = None
        self.gold_loc = {"file": [], "function": []}
        self.trajectory = None
        self.agent_turn_num = -1
        self.agent_loc = {
            "gold loc": {"file": [], "function": []},
            "agent loc": {"file": [], "function": []},
            "turn index": {"file": [], "function": []},
            "loc progress": {"file": [], "function": []},
        }
        self.task_resolved = False

    def _init_dir(self, directory_path):
        """Check if a directory exists and create it if it doesn't.

        Args:
            directory_path (str): Path to the directory to check/create

        Returns:
            bool: True if directory already existed, False if it was created
        """
        if os.path.exists(directory_path):
            if not os.path.isdir(directory_path):
                raise NotADirectoryError(f"Path exists but is not a directory: {directory_path}")
            return True
        else:
            os.makedirs(directory_path)
            return False

    def _check_if_to_eval_success(self):
        """Check if post-evaluation outputs exist."""
        return bool(os.path.isdir(self.eval_dir))

    def _compute_avg_over_all(self):
        """Compute average loc evaluations over all instances."""
        macro_la_file, micro_la_file = (0, 0)
        macro_la_func, micro_la_func = (0, 0)
        resolve_rate = 0
        macro_avg_file_idx, macro_avg_func_idx = (0, 0)
        micro_avg_file_idx, micro_avg_func_idx = (0, 0)
        avg_resolve_idx = 0
        total_instance_num = len(self.all_eval_results)
        for instance_id in self.all_eval_results:
            curr_eval_result = self.all_eval_results[instance_id]["final_eval"]
            macro_la_file += curr_eval_result["localization"]["loc_acc (%)"]["la_file (%)"]["la_file_macro"]
            micro_la_file += curr_eval_result["localization"]["loc_acc (%)"]["la_file (%)"]["la_file_micro"]
            macro_avg_file_idx += curr_eval_result["localization"]["turn_idx"]["file"]["macro"]
            micro_avg_file_idx += curr_eval_result["localization"]["turn_idx"]["file"]["micro"]
            macro_la_func += curr_eval_result["localization"]["loc_acc (%)"]["la_func (%)"]["la_func_macro"]
            micro_la_func += curr_eval_result["localization"]["loc_acc (%)"]["la_func (%)"]["la_func_micro"]
            macro_avg_func_idx += curr_eval_result["localization"]["turn_idx"]["function"]["macro"]
            micro_avg_func_idx += curr_eval_result["localization"]["turn_idx"]["function"]["micro"]
            if self.eval_task_success:
                if curr_eval_result["task_success"]["resolved"]:
                    resolve_rate += 1
                    avg_resolve_idx += curr_eval_result["task_success"]["resolve_index"]
                else:
                    avg_resolve_idx += self.max_agent_turn
        macro_la_file = macro_la_file / total_instance_num
        micro_la_file = micro_la_file / total_instance_num
        macro_la_func = macro_la_func / total_instance_num
        micro_la_func = micro_la_func / total_instance_num
        macro_avg_file_idx = macro_avg_file_idx / total_instance_num
        micro_avg_file_idx = micro_avg_file_idx / total_instance_num
        macro_avg_func_idx = macro_avg_func_idx / total_instance_num
        micro_avg_func_idx = micro_avg_func_idx / total_instance_num
        if self.eval_task_success:
            resolve_rate = resolve_rate / total_instance_num * 100
            avg_resolve_idx = avg_resolve_idx / total_instance_num
        total_cost, avg_cost = (0.0, 0.0)
        for instance_key in self.cost_summary["details"]:
            total_cost += self.cost_summary["details"][instance_key]
        avg_cost = total_cost / len(self.cost_summary["details"])
        self.cost_summary["total_cost"] = total_cost
        self.cost_summary["avg_cost"] = avg_cost
        self.overall_eval = {
            "la_file (%)": {"macro": macro_la_file, "micro": micro_la_file},
            "la_func (%)": {"macro": macro_la_func, "micro": micro_la_func},
            "resolve_rate (%)": resolve_rate if self.eval_task_success else None,
            "loc_file_idx (turn idx)": {"macro": macro_avg_file_idx, "micro": micro_avg_file_idx},
            "loc_func_idx (turn idx)": {"macro": macro_avg_func_idx, "micro": micro_avg_func_idx},
            "resolve_idx (turn idx)": avg_resolve_idx if self.eval_task_success else None,
            "max_turn_limit": self.max_agent_turn,
            "total_instance_num": total_instance_num,
            "cost_summary": self.cost_summary,
        }
        self._write_to_json(self.overall_eval, "overall_eval.json")

    def _save_to_eval_dicts(self, agent_trajectory: dict):
        self._write_to_json(agent_trajectory, f"loc__instance_{self.instance.instance_id}.json")
        self.all_eval_results[self.instance.instance_id] = agent_trajectory
        self._write_to_json(self.all_eval_results, "all_loc_evals.json")
        self._compute_avg_over_all()

    def _write_to_json(self, data, file_name):
        """Writes the current object data to a JSON file.

        Returns:
            bool: True if writing was successful, False otherwise.
        """
        try:
            output_dir = os.path.join(self.save_dir, "loc_acc")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, file_name)
            with open(filepath, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error("Error writing to JSON: %s", str(e))
            return False

    def read_from_json(self, file_path):
        """Reads data from a JSON file and loads it into the current object.

        Returns:
            dict: The loaded JSON data, or an empty dict if the file doesn't exist
                or an error occurs.
        """
        try:
            with open(file_path, "r", encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning("Warning: File '%s' not found. Returning an empty dictionary...", file_path)
            return {}
        except json.JSONDecodeError:
            logger.error("Error: File '%s' contains invalid JSON. Returning an empty dictionary...", file_path)
            return {}
        except Exception as e:
            logger.error("Error reading from JSON: %s\nReturning an empty dictionary...", str(e))
            return {}

    def read_from_jsonl(self, file_path):
        """Reads data from a JSON file and loads it into the current object.

        Returns:
            dict: The loaded JSON data, or an empty dict if the file doesn't exist
                or an error occurs.
        """
        try:
            with open(file_path, "r", encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning("Warning: File '%s' not found. Returning an empty dictionary...", file_path)
            return {}
        except json.JSONDecodeError:
            logger.error("Error: File '%s' contains invalid JSON. Returning an empty dictionary...", file_path)
            return {}
        except Exception as e:
            logger.error("Error reading from JSON: %s\nReturning an empty dictionary...", str(e))
            return {}

    def _parse_agent_turn_num(self):
        """Get the max agent turn for current instance."""
        history_idx = 1
        self.agent_turn_num = 0
        while history_idx < len(self.trajectory) - 1:
            if (
                self.trajectory[history_idx]["source"] == "agent"
                and "action" in self.trajectory[history_idx].keys()
                and (self.trajectory[history_idx]["action"] != "system")
            ):
                self.agent_turn_num += 1
            history_idx += 1

    def _parse_string_to_dict(self, dict_string) -> dict:
        """Convert a string representation of a dictionary to an actual dictionary.

        Args:
            dict_string (str): String representation of a dictionary

        Returns:
            dict or None: The parsed dictionary if successful, None if failed
        """
        if not isinstance(dict_string, str):
            return None
        dict_string = dict_string.strip()
        try:
            return json.loads(dict_string)
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            result = ast.literal_eval(dict_string)
            return result if isinstance(result, dict) else None
        except (ValueError, SyntaxError):
            pass
        return None

    def _parse_value_from_args(self, argument_str: str, key: str) -> str:
        """Parse a specific key's value from argument string.

        Args:
            argument_str (str): The argument string containing key-value pairs
            key (str): The key to extract (e.g., "path", "new_str", "old_str")

        Returns:
            str: The extracted value, or empty string if not found
        """
        if not self._is_valid_input(argument_str, key):
            return ""

        try:
            if value := self._try_json_style_parsing(argument_str, key):
                return value

            if value := self._try_python_style_parsing(argument_str, key):
                return value

            return value if (value := self._try_generic_parsing(argument_str, key)) else ""
        except Exception:
            return ""

    def _is_valid_input(self, argument_str: str, key: str) -> bool:
        """Check if input parameters are valid."""
        return isinstance(argument_str, str) and isinstance(key, str)

    def _try_json_style_parsing(self, argument_str: str, key: str) -> str:
        """Try to parse value using JSON-style double quotes."""
        json_pattern = f'"{re.escape(key)}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`'
        if match := re.search(json_pattern, argument_str, re.DOTALL):
            value = match[1]
            return self._unescape_json_string(value)
        return ""

    def _try_python_style_parsing(self, argument_str: str, key: str) -> str:
        """Try to parse value using Python-style single quotes."""
        python_pattern = f"'{re.escape(key)}'\\s*:\\s*'((?:[^'\\\\]|\\\\.)*)'"
        if match := re.search(python_pattern, argument_str, re.DOTALL):
            value = match[1]
            return self._unescape_python_string(value)
        return ""

    def _try_generic_parsing(self, argument_str: str, key: str) -> str:
        """Try generic parsing methods."""
        if key not in argument_str:
            return ""

        # Split by key and process remainder
        parts = self._split_by_key(argument_str, key)
        if len(parts) <= 1:
            return ""

        remainder = parts[1].strip()
        return self._extract_value_from_remainder(remainder, key)

    def _split_by_key(self, argument_str: str, key: str) -> list[str]:
        """Split argument string by key."""
        parts = argument_str.split(f'"{key}"', 1)
        if len(parts) == 1:
            parts = argument_str.split(f"'{key}'", 1)
        return parts

    def _extract_value_from_remainder(self, remainder: str, key: str) -> str:
        """Extract value from remainder string."""
        # Try quoted values
        for quote_char in ['"', "'"]:
            if value := self._try_quoted_value(remainder, quote_char):
                return value

        # Special handling for path key
        return self._extract_path_value(remainder) if key == "path" else ""

    def _try_quoted_value(self, remainder: str, quote_char: str) -> str:
        """Try to extract quoted value."""
        pattern = f"\\s*:\\s*{quote_char}((?:[^{quote_char}\\\\]|\\\\.)*)(?:{quote_char}|$)"
        if match := re.search(pattern, remainder, re.DOTALL):
            value = match[1]
            if quote_char == '"':
                return self._unescape_json_string(value)
            else:
                return self._unescape_python_string(value)
        return ""

    def _extract_path_value(self, remainder: str) -> str:
        """Extract path value from remainder."""
        path_pattern = "/[^\\s,}\"\\']*"
        return match[0] if (match := re.search(path_pattern, remainder)) else ""

    def _unescape_json_string(self, value: str) -> str:
        """Unescape JSON-style string."""
        return value.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

    def _unescape_python_string(self, value: str) -> str:
        """Unescape Python-style string."""
        return value.replace("\\'", "'").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

    def _parse_path_from_args(self, argument_str: str) -> str:
        """Parse path from argument string.

        Args:
            argument_str (str): The argument string containing path information

        Returns:
            str: The extracted file path, or empty string if not found
        """
        return self._parse_value_from_args(argument_str, "path")

    def _parse_func_names_from_str(self, code_patch) -> list:
        """Parse function names from the new_str code patch.

        Args:
            code_patch: Either a string (argument string) or already extracted new_str code

        Returns:
            list: List of function names found in the code patch
        """
        if not code_patch:
            return []
        try:
            func_pattern = "\\bdef\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\("
            matches = re.findall(func_pattern, code_patch)
            seen = set()
            unique_funcs = []
            for func_name in matches:
                if func_name not in seen:
                    seen.add(func_name)
                    unique_funcs.append(func_name)
            return unique_funcs
        except Exception:
            return []

    def _parse_loc_from_history(self, action_history: dict) -> list:
        """Parse function name and file path."""
        if not action_history:
            logger.error("No action history provided.")
            raise
        curr_turn_agent_loc = {}
        if action_history["action"] != "edit":
            return curr_turn_agent_loc
        agent_msg_list = action_history["tool_call_metadata"]["model_response"]["choices"]
        agent_edit = {"create": ["file_text"], "str_replace": ["old_str", "new_str"]}
        for cho in agent_msg_list:
            for func_dict in cho["message"]["tool_calls"]:
                self._process_tool_call(func_dict, agent_edit, curr_turn_agent_loc)
        return curr_turn_agent_loc

    def _process_tool_call(self, func_dict: dict, agent_edit: dict, curr_turn_agent_loc: dict) -> None:
        """Process a single tool call and update location tracking."""
        edit_args = func_dict["function"]["arguments"]
        edit_dict = self._parse_string_to_dict(edit_args)
        func_names = []

        if edit_dict:
            self._process_parsed_edit_dict(edit_dict, agent_edit, func_names)
        else:
            self._process_raw_edit_args(edit_args, agent_edit, func_names)

        self._update_location_tracking(func_names, edit_dict, edit_args, curr_turn_agent_loc)

    def _process_parsed_edit_dict(self, edit_dict: dict, agent_edit: dict, func_names: list) -> None:
        """Process parsed edit dictionary."""
        curr_command = edit_dict["command"]
        agent_acts = agent_edit[curr_command]
        for act in agent_acts:
            code_patch = edit_dict.get(act)
            func_names.extend(self._parse_func_names_from_str(code_patch))

    def _process_raw_edit_args(self, edit_args: str, agent_edit: dict, func_names: list) -> None:
        """Process raw edit arguments."""
        for new_act in list(agent_edit.values()):
            if new_act in edit_args:
                agent_acts = new_act
                break
        for act in agent_acts:
            code_patch = edit_args.split(agent_acts)[-1].strip()
            func_names.extend(self._parse_func_names_from_str(code_patch))

    def _update_location_tracking(
        self, func_names: list, edit_dict: dict, edit_args: str, curr_turn_agent_loc: dict
    ) -> None:
        """Update location tracking with function names."""
        file_path = edit_dict.get("path") if edit_dict else self._parse_path_from_args(edit_args)

        if file_path and len(file_path) > 0:
            if func_names := list(set(func_names)):
                if file_path in curr_turn_agent_loc:
                    curr_turn_agent_loc[file_path].extend(func_names)
                else:
                    curr_turn_agent_loc[file_path] = func_names
            else:
                curr_turn_agent_loc[file_path] = []

    def _add_task_success_metric(self) -> bool:
        """Task success evaluation result."""
        self.task_resolved = False
        report_pth = os.path.join(self.eval_dir, self.instance.instance_id, "report.json")
        eval_report = self.read_from_json(report_pth)
        if self.instance.instance_id in eval_report.keys():
            self.task_resolved = eval_report[self.instance.instance_id]["resolved"]
        if self.task_resolved:
            return {"resolved": self.task_resolved, "resolve_index": self.agent_turn_num}
        if self.align_failed_with_max_iter:
            return {"resolved": self.task_resolved, "resolve_index": self.max_agent_turn}
        else:
            return {"resolved": self.task_resolved, "resolve_index": self.agent_turn_num}

    def _process_turn_trajectory(
        self, turn_idx: int, action_history: dict, observ_history: dict, curr_turn_agent_loc: dict
    ) -> dict:
        """Process a single turn and return trajectory entry."""
        turn_entry = {
            "loc_eval": None,
            "loc": curr_turn_agent_loc,
            "action": {"action": action_history["action"], "message": action_history["message"]},
            "observation": None,
        }

        if "observation" in observ_history:
            turn_entry["observation"] = {
                "observation": observ_history["observation"],
                "message": observ_history["message"],
            }

        return turn_entry

    def _update_agent_location(self, curr_turn_agent_loc: dict, turn_idx: int) -> None:
        """Update agent location tracking based on current turn location."""
        if not curr_turn_agent_loc:
            return

        for file_key in curr_turn_agent_loc:
            for func_name in curr_turn_agent_loc[file_key]:
                # Update file location
                if file_key in self.gold_loc["file"] and file_key not in self.agent_loc["agent loc"]["file"]:
                    self.agent_loc["agent loc"]["file"].append(file_key)
                    self.agent_loc["turn index"]["file"][self.gold_loc["file"].index(file_key)] = turn_idx
                    self.agent_loc["loc progress"]["file"][self.gold_loc["file"].index(file_key)] = True

                # Update function location
                new_agent_loc = {"file": file_key, "function": func_name}
                if (
                    new_agent_loc in self.gold_loc["function"]
                    and new_agent_loc not in self.agent_loc["agent loc"]["function"]
                ):
                    self.agent_loc["agent loc"]["function"].append(new_agent_loc)
                    self.agent_loc["turn index"]["function"][self.gold_loc["function"].index(new_agent_loc)] = turn_idx
                    self.agent_loc["loc progress"]["function"][self.gold_loc["function"].index(new_agent_loc)] = True

    def _build_final_eval_metrics(self) -> dict:
        """Build final evaluation metrics."""
        file_progress = self.agent_loc["loc progress"]["file"]
        func_progress = self.agent_loc["loc progress"]["function"]

        return {
            "total turn": self.agent_turn_num,
            "max turn": self.max_agent_turn,
            "localization": {
                "loc_acc (%)": {
                    "la_file (%)": {
                        "la_file_micro": sum(file_progress) / len(file_progress) * 100,
                        "la_file_macro": 100.0 if sum(file_progress) > 0 else 0.0,
                    },
                    "la_func (%)": {
                        "la_func_micro": sum(func_progress) / len(func_progress) * 100,
                        "la_func_macro": 100.0 if sum(func_progress) > 0 else 0.0,
                    },
                },
                "turn_idx": {
                    "file": {
                        "micro": max(self.agent_loc["turn index"]["file"]),
                        "macro": min(self.agent_loc["turn index"]["file"]),
                    },
                    "function": {
                        "micro": max(self.agent_loc["turn index"]["function"]),
                        "macro": min(self.agent_loc["turn index"]["function"]),
                    },
                },
                "details": {"loc_file": file_progress, "loc_func": func_progress},
            },
            "task_success": None,
        }

    def _handle_task_resolved_corrections(self, agent_trajectory: dict) -> None:
        """Handle corrections when task is resolved."""
        if not self.task_resolved:
            return

        # Check if perfect localization was achieved
        perfect_loc = {
            "la_file (%)": {"la_file_micro": 100.0, "la_file_macro": 100.0},
            "la_func (%)": {"la_func_micro": 100.0, "la_func_macro": 100.0},
        }

        if agent_trajectory["final_eval"]["localization"]["loc_acc (%)"] != perfect_loc:
            agent_trajectory["final_eval"]["localization"]["loc_acc (%)"] = perfect_loc
            agent_trajectory["final_eval"]["localization"]["details"] = {
                "loc_file": [True for _ in range(len(self.agent_loc["loc progress"]["file"]))],
                "loc_func": [True for _ in range(len(self.agent_loc["loc progress"]["function"]))],
            }

        # Adjust turn indices if alignment failed
        if self.align_failed_with_max_iter:
            for level1 in agent_trajectory["final_eval"]["localization"]["turn_idx"]:
                for level2 in agent_trajectory["final_eval"]["localization"]["turn_idx"][level1]:
                    agent_trajectory["final_eval"]["localization"]["turn_idx"][level1][level2] = min(
                        agent_trajectory["final_eval"]["localization"]["turn_idx"][level1][level2], self.agent_turn_num
                    )

    def eval_agent_trajectory(self):
        """Evaluate agent's localization at current state."""
        if not self.trajectory:
            logger.warning(
                "Inference trajectory for current instance (instance ID: %s) is None, skipping localization evaluation for current instance...",
                self.instance.instance_id,
            )
            return

        agent_trajectory = {"final_eval": {}, "trajectory": {}}
        turn_idx = 0
        history_idx = 1

        # Process trajectory turns
        while history_idx < len(self.trajectory) - 2:
            history_idx += 1
            action_history = self.trajectory[history_idx]
            observ_history = self.trajectory[history_idx + 1]

            if action_history["source"] != "agent" or "action" not in action_history.keys():
                continue

            turn_idx += 1
            curr_turn_agent_loc = self._parse_loc_from_history(action_history)

            # Process turn and update trajectory
            turn_entry = self._process_turn_trajectory(turn_idx, action_history, observ_history, curr_turn_agent_loc)
            agent_trajectory["trajectory"][f"turn {turn_idx}"] = turn_entry

            # Update agent location tracking
            self._update_agent_location(curr_turn_agent_loc, turn_idx)

            # Update turn evaluation
            agent_trajectory["trajectory"][f"turn {turn_idx}"]["loc_eval"] = self.agent_loc

        # Build final evaluation metrics
        agent_trajectory["final_eval"] = self._build_final_eval_metrics()

        # Add task success metric if needed
        if self.eval_task_success:
            agent_trajectory["final_eval"]["task_success"] = self._add_task_success_metric()

        # Handle task resolved corrections
        self._handle_task_resolved_corrections(agent_trajectory)

        self._save_to_eval_dicts(agent_trajectory)

    def _get_instance_gt_loc(self):
        """Get ground-truth localization for current instance."""
        gt_localization = self.localizer.parse_instance_loc(self.instance)
        gt_loc_dict = gt_localization["patch"].to_dict()
        assert gt_loc_dict["instance_id"] == self.instance.instance_id

        self.gold_loc = {"gt_loc_dict": gt_loc_dict["functions"], "file": [], "function": []}
        self._process_gt_functions(gt_loc_dict)
        self._initialize_agent_loc_tracking()

    def _process_gt_functions(self, gt_loc_dict: dict) -> None:
        """Process ground-truth functions and build file/function lists."""
        for file_key in gt_loc_dict["functions"]:
            if len(gt_loc_dict["functions"][file_key]) == 0:
                continue

            self._add_file_to_gold_loc(file_key)
            self._add_functions_to_gold_loc(file_key, gt_loc_dict["functions"][file_key])

    def _add_file_to_gold_loc(self, file_key: str) -> None:
        """Add file to gold location if not already present."""
        if file_key not in self.gold_loc["file"]:
            self.gold_loc["file"].append(f"{self.sandbox_root}/{file_key}")

    def _add_functions_to_gold_loc(self, file_key: str, functions: list) -> None:
        """Add functions to gold location."""
        for func_name in functions:
            new_gt = {"file": f"{self.sandbox_root}/{file_key}", "function": func_name}
            self.gold_loc["function"].append(new_gt)

    def _initialize_agent_loc_tracking(self) -> None:
        """Initialize agent location tracking with turn indices and progress."""
        init_turn = self.max_agent_turn if self.align_failed_with_max_iter else self.agent_turn_num

        self.agent_loc["gold loc"] = {"file": self.gold_loc["file"], "function": self.gold_loc["function"]}
        self.agent_loc["turn index"]["file"] = [init_turn for _ in range(len(self.gold_loc["file"]))]
        self.agent_loc["turn index"]["function"] = [init_turn for _ in range(len(self.gold_loc["function"]))]
        self.agent_loc["loc progress"]["file"] = [False for _ in range(len(self.gold_loc["file"]))]
        self.agent_loc["loc progress"]["function"] = [False for _ in range(len(self.gold_loc["function"]))]

    def instance_loc_eval(
        self, instance: pd.Series = None, repo_root: str = None, trajectory: list = None, infer_cost: dict = None
    ):
        if instance is None:
            logger.error("No instance provided. Skipping current localization evaluation...")
        if trajectory is None:
            logger.error("No inference trajectory provided for current instance with ID: %s", instance.instance_id)
        if infer_cost is None:
            logger.error("No inference accumulated cost for current instance with ID: %s", instance.instance_id)
        self._init_config()
        self.cost_summary["details"][instance.instance_id] = infer_cost
        self.instance = instance
        self.trajectory = trajectory
        self.sandbox_root = repo_root
        self._parse_agent_turn_num()
        self._get_instance_gt_loc()
        self.eval_agent_trajectory()


def swe_data_loader(args):
    """Loading SWE-Bench data.

    Args:
        args: Main arguments.
    """
    dataset = load_dataset(args.dataset, split=args.split)  # nosec B615 - Safe: evaluation benchmark dataset
    swe_bench_tests = filter_dataset(dataset.to_pandas(), "instance_id")
    logger.info("Loaded dataset %s with split %s: %s tasks", args.dataset, args.split, len(swe_bench_tests))
    if "SWE-Gym" in args.dataset:
        with open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "split", "swegym_verified_instances.json"), "r"
        ) as f:
            swegym_verified_instances = json.load(f)
            swe_bench_tests = swe_bench_tests[swe_bench_tests["instance_id"].isin(swegym_verified_instances)]
        logger.info("%s tasks left after filtering for SWE-Gym verified instances", len(swe_bench_tests))
    return prepare_dataset(swe_bench_tests, args.swe_output_file, -1)


def infer_data_loader(args):
    """Load instance IDs.

    Args:
        args: Main arguments.

    Returns:
        list: A list of instance IDs (strings) extracted from JSON filenames
              in the histories directory.

    Raises:
        FileNotFoundError: If the histories directory doesn't exist.
        AttributeError: If args doesn't have a 'infer_dir' attribute.
    """
    infer_output_filepath = os.path.join(args.infer_dir, "output.jsonl")
    infer_outputs = []
    with open(infer_output_filepath, "r", encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            if line := line.strip():
                try:
                    json_obj = json.loads(line)
                    infer_outputs.append(json_obj)
                except json.JSONDecodeError as e:
                    logger.error("Error parsing JSON on line %s in '%s': %s", line_num, infer_output_filepath, str(e))
                    continue
    return infer_outputs


def infer_cost_calculator(args):
    """Calculate total and average costs from metric JSON files with detailed output.

    Args:
        args: Main arguments.

    Returns:
        dict: A dictionary containing:
              - 'total_cost': Sum of all accumulated costs
              - 'average_cost': Average cost per JSON file
              - 'file_count': Number of JSON files processed
              - 'individual_costs': List of individual costs (optional)
    """
    metrics_dir = os.path.join(args.infer_dir, "metrics")
    if not os.path.exists(metrics_dir):
        raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")
    individual_costs = []
    for filename in os.listdir(metrics_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(metrics_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    metric_data = json.load(file)
                if "accumulated_cost" not in metric_data:
                    raise KeyError(f"'accumulated_cost' not found in {filename}")
                cost = float(metric_data["accumulated_cost"])
                individual_costs.append(cost)
            except (json.JSONDecodeError, ValueError, TypeError, IOError) as e:
                logger.warning("Warning: Error processing %s: %s", filename, e)
                continue
    if not individual_costs:
        raise ValueError("No valid JSON files found in the metrics directory")
    total_cost = sum(individual_costs)
    average_cost = total_cost / len(individual_costs)
    return {
        "total_cost": total_cost,
        "average_cost": average_cost,
        "file_count": len(individual_costs),
        "individual_costs": individual_costs,
    }


if __name__ == "__main__":
    "Main function for localization evaluation"
    parser = argparse.ArgumentParser(description="Localization evaluation on SWE-Bench.")
    parser.add_argument("--infer-dir", type=str, default=None, help="Directory containing model inference outputs")
    parser.add_argument("--dataset", type=str, default=None, help="SWE-Bench dataset version")
    parser.add_argument("--split", type=str, default=None, help="SWE-Bench dataset split selection")
    parser.add_argument(
        "--max-infer-turn", type=int, default=None, help="Max number of turns allowed for coding agent."
    )
    parser.add_argument(
        "--align-with-max",
        type=str,
        choices=["true", "false"],
        default="true",
        help="Whether to align failed instances with max iteration count (true/false)",
    )
    args = parser.parse_args()
    args.align_with_max = args.align_with_max.lower() == "true"
    args.save_dir = f"{args.infer_dir}/loc_eval"
    os.makedirs(args.save_dir, exist_ok=True)
    args.eval_dir = f"{args.infer_dir}/eval_outputs"
    if not os.path.isdir(args.eval_dir):
        args.eval_dir = None
    args.swe_output_file = os.path.join(args.save_dir, "swe_dataset.json")
    swe_instances = swe_data_loader(args)
    infer_outputs = infer_data_loader(args)
    processed_instances = []
    loc_eval_results = {}
    loc_evaluator = LocEvaluator(args)
    for infer_idx, infer_instance in tqdm(
        enumerate(infer_outputs), total=len(infer_outputs), desc="Processing instances"
    ):
        instance_id = infer_instance["instance_id"]
        swe_instance = swe_instances.query(f"instance_id == '{instance_id}'").iloc[0]
        assert instance_id == swe_instance.instance_id
        processed_instances.append(instance_id)
        upload_instruction = infer_instance["instruction"]
        repo_root = upload_instruction.split("<uploaded_files>")[1].split("</uploaded_files>")[0].strip()
        curr_trajectory = infer_instance["history"]
        curr_cost = infer_instance["metrics"]["accumulated_cost"]
        loc_evaluator.instance_loc_eval(swe_instance, repo_root, curr_trajectory, curr_cost)
    logger.info(
        "\n[Inference Data Summary]\n%s - Total cost:   $ %s\n%s - Average cost: $ %s\n%s - Number of Instances: %s",
        " " * 4,
        loc_evaluator.cost_summary["total_cost"],
        " " * 4,
        loc_evaluator.cost_summary["avg_cost"],
        " " * 4,
        len(processed_instances),
    )
