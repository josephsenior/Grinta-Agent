import ast
import logging
import re
from dataclasses import dataclass
from typing import Any, Union
import pandas as pd
from datasets import load_dataset
from openhands.runtime.base import Runtime


@dataclass
class LocalizationInfo:
    """Container for ground-truth localization information."""

    instance_id: str
    files: list[str]
    file_line_ranges: dict[str, list[tuple[int, int]]]
    functions: dict[str, list[str]]
    classes: dict[str, list[str]]
    line_to_function: dict[str, dict[int, str]]
    line_to_class: dict[str, dict[int, str]]
    total_lines_changed: int
    total_files_changed: int
    hunks_per_file: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert LocalizationInfo to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the localization information
        """
        return {
            "instance_id": self.instance_id,
            "files": self.files,
            "file_line_ranges": {
                file: [[start, end] for start, end in ranges] for file, ranges in self.file_line_ranges.items()
            },
            "functions": self.functions,
            "classes": self.classes,
            "line_to_function": {
                file: {str(line): func for line, func in mapping.items()}
                for file, mapping in self.line_to_function.items()
            },
            "line_to_class": {
                file: {str(line): cls for line, cls in mapping.items()} for file, mapping in self.line_to_class.items()
            },
            "total_lines_changed": self.total_lines_changed,
            "total_files_changed": self.total_files_changed,
            "hunks_per_file": self.hunks_per_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalizationInfo":
        """Create LocalizationInfo from a dictionary (for loading from JSON).

        Args:
            data: Dictionary containing localization information

        Returns:
            LocalizationInfo object
        """
        return cls(
            instance_id=data["instance_id"],
            files=data["files"],
            file_line_ranges={file: list(ranges) for file, ranges in data["file_line_ranges"].items()},
            functions=data["functions"],
            classes=data["classes"],
            line_to_function={
                file: {int(line): func for line, func in mapping.items()}
                for file, mapping in data["line_to_function"].items()
            },
            line_to_class={
                file: {int(line): cls for line, cls in mapping.items()}
                for file, mapping in data["line_to_class"].items()
            },
            total_lines_changed=data["total_lines_changed"],
            total_files_changed=data["total_files_changed"],
            hunks_per_file=data["hunks_per_file"],
        )


class LocMeta:
    """SWE-Bench dataset loader and ground-truth localization parser.

    This class handles loading SWE-Bench datasets and extracting ground-truth
    localization information from patches for code localization evaluation.
    Works with both standalone Docker containers and OpenHands runtime.
    """

    def __init__(self, dataset_name: str = "princeton-nlp/SWE-bench_Verified", split: str = "test"):
        """Initialize LocMeta with a SWE-Bench dataset.

        Args:
            dataset_name: HuggingFace dataset name (e.g., "princeton-nlp/SWE-bench_Verified")
            split: Dataset split to load (e.g., "test", "train")
        """
        self.dataset_name = dataset_name
        self.dataset = None
        self.split = split
        self.df = None
        self.instance_lookup = {}
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self._init_swe_dataset()

    def _init_swe_dataset(self) -> None:
        """Load and initialize the SWE-Bench dataset from HuggingFace.

        Converts to pandas DataFrame for easy manipulation.
        """
        try:
            self.logger.info(f"Loading dataset: {self.dataset_name}")
            self.dataset = load_dataset(
                self.dataset_name, split=self.split
            )  # nosec B615 - Safe: evaluation benchmark dataset
            self.df = pd.DataFrame(self.dataset)
            self.instance_lookup = {row["instance_id"]: idx for idx, row in self.df.iterrows()}
            self.logger.info(f"Successfully loaded {len(self.df)} instances")
            self.logger.info(f"Available columns: {list(self.df.columns)}")
        except Exception as e:
            self.logger.error(f"Failed to load dataset {self.dataset_name}: {e}")
            raise

    def get_instance_by_id(self, instance_id: str) -> pd.Series:
        """Retrieve a specific instance by its ID.

        Args:
            instance_id: The instance identifier

        Returns:
            pandas Series containing the instance data

        Raises:
            KeyError: If instance_id is not found
        """
        if instance_id not in self.instance_lookup:
            raise KeyError(f"Instance ID '{instance_id}' not found in dataset")
        idx = self.instance_lookup[instance_id]
        return self.df.iloc[idx]

    def parse_instance_loc(self, instance: Union[pd.Series, str]) -> LocalizationInfo:
        """Parse ground-truth localization information from a SWE-Bench instance.

        Args:
            instance: Either a pandas Series with instance data or an instance_id string

        Returns:
            LocalizationInfo object containing extracted localization data
        """
        if isinstance(instance, str):
            actual_instance_id = instance
            instance = self.get_instance_by_id(actual_instance_id)
        else:
            actual_instance_id = instance.get("instance_id", "unknown")
        self.logger.info(f"Parsing localization for instance: {actual_instance_id}")
        if patch_content := instance.get("patch", ""):
            patch_loc_info = self._parse_patch_localization(patch_content, actual_instance_id)
        else:
            self.logger.warning(f"No patch content found for instance {actual_instance_id}")
            patch_loc_info = self._empty_localization_info(actual_instance_id)
        if patch_content := instance.get("test_patch", ""):
            test_patch_loc_info = self._parse_patch_localization(patch_content, actual_instance_id)
        else:
            self.logger.warning(f"No test patch content found for instance {actual_instance_id}")
            test_patch_loc_info = self._empty_localization_info(actual_instance_id)
        return {"patch": patch_loc_info, "test_patch": test_patch_loc_info}

    def _parse_file_patch_lines(self, file_patch: str) -> tuple[list[tuple[int, int]], int, int]:
        """Parse line ranges and count changes from a single file patch.

        Args:
            file_patch: Patch content for a single file

        Returns:
            Tuple of (line_ranges, total_lines_changed, num_hunks)
        """
        line_ranges = []
        lines_changed = 0
        num_hunks = 0
        lines = file_patch.split("\n")
        for line in lines:
            if hunk_match := re.match("@@\\s+-(\\d+)(?:,(\\d+))?\\s+\\+(\\d+)(?:,(\\d+))?\\s+@@", line):
                num_hunks += 1
                new_start = int(hunk_match[3])
                new_count = int(hunk_match[4]) if hunk_match[4] else 1
                if new_count > 0:
                    line_ranges.append((new_start, new_start + new_count - 1))
                    lines_changed += new_count
        return (line_ranges, lines_changed, num_hunks)

    def _parse_code_structures_from_patch(self, file_patch: str, file_path: str) -> tuple[list[str], list[str]]:
        """Extract function and class names from patch context (fallback method).

        Args:
            file_patch: Patch content for a single file
            file_path: Path to the file being patched

        Returns:
            Tuple of (function_names, class_names)
        """
        functions = set()
        classes = set()
        if not file_path.endswith(".py"):
            return (list(functions), list(classes))
        lines = file_patch.split("\n")
        for line in lines:
            if hunk_match := re.match("@@.*?@@\\s*(.*)", line):
                if context := hunk_match[1].strip():
                    if func_match := re.search("def\\s+([a-zA-Z_][a-zA-Z0-9_]*)", context):
                        functions.add(func_match[1])
                    if class_match := re.search("class\\s+([a-zA-Z_][a-zA-Z0-9_]*)", context):
                        classes.add(class_match[1])
            stripped_line = line.lstrip("+-@ ")
            if func_match := re.match("def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(", stripped_line):
                functions.add(func_match[1])
            if class_match := re.match("class\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[\\(:]", stripped_line):
                classes.add(class_match[1])
        return (list(functions), list(classes))

    def _parse_patch_localization(self, patch_content: str, instance_id: str) -> LocalizationInfo:
        """Parse localization information from a git patch (improved method).

        Args:
            patch_content: The git patch content
            instance_id: Instance ID for logging

        Returns:
            LocalizationInfo object with extracted data
        """
        files = []
        file_line_ranges = {}
        functions = {}
        classes = {}
        line_to_function = {}
        line_to_class = {}
        hunks_per_file = {}
        total_lines_changed = 0
        file_patches = self._split_patch_by_files(patch_content)
        for file_path, file_patch in file_patches.items():
            files.append(file_path)
            line_ranges, lines_changed, num_hunks = self._parse_file_patch_lines(file_patch)
            file_line_ranges[file_path] = line_ranges
            total_lines_changed += lines_changed
            hunks_per_file[file_path] = num_hunks
            file_functions, file_classes = self._extract_code_structures_from_patch(file_patch, file_path)
            functions[file_path] = file_functions
            classes[file_path] = file_classes
            line_func_map = {}
            line_class_map = {}
            affected_lines = []
            for start, end in line_ranges:
                affected_lines.extend(range(start, end + 1))
            if file_functions and affected_lines:
                for line_num in affected_lines:
                    line_func_map[line_num] = file_functions[0]
                    if file_classes:
                        line_class_map[line_num] = file_classes[0]
            line_to_function[file_path] = line_func_map
            line_to_class[file_path] = line_class_map
        return LocalizationInfo(
            instance_id=instance_id,
            files=files,
            file_line_ranges=file_line_ranges,
            functions=functions,
            classes=classes,
            line_to_function=line_to_function,
            line_to_class=line_to_class,
            total_lines_changed=total_lines_changed,
            total_files_changed=len(files),
            hunks_per_file=hunks_per_file,
        )

    def _extract_code_structures_from_patch(self, file_patch: str, file_path: str) -> tuple[list[str], list[str]]:
        """Extract function and class names from patch context and content.

        Args:
            file_patch: Patch content for a single file
            file_path: Path to the file being patched

        Returns:
            Tuple of (function_names, class_names)
        """
        if not self._is_python_file(file_path):
            return ([], [])

        functions = set()
        classes = set()
        lines = file_patch.split("\n")

        self._log_patch_analysis(file_path, len(lines))

        for line in lines:
            self._process_patch_line(line, functions, classes)

        self._log_final_results(file_path, functions, classes)
        return (list(functions), list(classes))

    def _is_python_file(self, file_path: str) -> bool:
        """Check if the file is a Python file."""
        return file_path.endswith(".py") or file_path.endswith(".pyx")

    def _log_patch_analysis(self, file_path: str, line_count: int) -> None:
        """Log patch analysis information."""
        self.logger.info(f"Analyzing patch for {file_path}")
        self.logger.info(f"Patch has {line_count} lines")

    def _process_patch_line(self, line: str, functions: set, classes: set) -> None:
        """Process a single patch line for code structures."""
        if self._is_hunk_header(line):
            self._process_hunk_header(line, functions, classes)
        elif self._is_patch_content_line(line):
            self._process_patch_content_line(line, functions, classes)
        elif self._is_context_line(line):
            self._process_context_line(line, functions, classes)

    def _is_hunk_header(self, line: str) -> bool:
        """Check if line is a hunk header."""
        return bool(re.match("@@.*?@@\\s*(.*)", line))

    def _is_patch_content_line(self, line: str) -> bool:
        """Check if line is patch content (starts with +, -, or space)."""
        return line.startswith(("+", "-", " "))

    def _is_context_line(self, line: str) -> bool:
        """Check if line is a context line."""
        return line.strip() and not line.startswith(("@@", "diff", "---", "+++", "index"))

    def _process_hunk_header(self, line: str, functions: set, classes: set) -> None:
        """Process hunk header line for code structures."""
        if hunk_match := re.match("@@.*?@@\\s*(.*)", line):
            context = hunk_match[1].strip()
            self.logger.info(f"Found hunk context: '{context}'")
            if context:
                self._extract_from_hunk_context(context, functions, classes)

    def _extract_from_hunk_context(self, context: str, functions: set, classes: set) -> None:
        """Extract functions and classes from hunk context."""
        self._extract_functions_from_text(context, functions, "hunk context")
        self._extract_classes_from_text(context, classes, "hunk context")

    def _process_patch_content_line(self, line: str, functions: set, classes: set) -> None:
        """Process patch content line for code structures."""
        stripped_line = line[1:].strip()
        self._extract_functions_from_text(stripped_line, functions, "patch content")
        self._extract_classes_from_text(stripped_line, classes, "patch content")

    def _process_context_line(self, line: str, functions: set, classes: set) -> None:
        """Process context line for code structures."""
        stripped_line = line.strip()
        self._extract_functions_from_text(stripped_line, functions, "context line")
        self._extract_classes_from_text(stripped_line, classes, "context line")

    def _extract_functions_from_text(self, text: str, functions: set, source: str) -> None:
        """Extract function names from text."""
        # Regular function patterns
        patterns = [
            r"(?:def|async\s+def|cdef\s+\w*\s+|cpdef\s+\w*\s+)\s*([a-zA-Z_][a-zA-Z0-9_]*)",
            r"(?:async\s+|cdef\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            r"cdef\s+[^(]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        ]

        for pattern in patterns:
            if match := re.search(pattern, text):
                func_name = match[1]
                functions.add(func_name)
                self.logger.info(f"Found function in {source}: {func_name}")

    def _extract_classes_from_text(self, text: str, classes: set, source: str) -> None:
        """Extract class names from text."""
        patterns = [r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)", r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]"]

        for pattern in patterns:
            if match := re.search(pattern, text):
                class_name = match[1]
                classes.add(class_name)
                self.logger.info(f"Found class in {source}: {class_name}")

    def _log_final_results(self, file_path: str, functions: set, classes: set) -> None:
        """Log final extraction results."""
        self.logger.info(f"Final results for {file_path}: functions={list(functions)}, classes={list(classes)}")

    def _parse_patch_localization_with_runtime(
        self, patch_content: str, instance_id: str, runtime: Runtime
    ) -> LocalizationInfo:
        """Parse localization information from a git patch using OpenHands runtime.

        This is the superior method when runtime is available.

        Args:
            patch_content: The git patch content
            instance_id: Instance ID for logging
            runtime: OpenHands runtime object

        Returns:
            LocalizationInfo object with extracted data
        """
        files = []
        file_line_ranges = {}
        functions = {}
        classes = {}
        line_to_function = {}
        line_to_class = {}
        hunks_per_file = {}
        total_lines_changed = 0
        file_patches = self._split_patch_by_files(patch_content)
        for file_path, file_patch in file_patches.items():
            files.append(file_path)
            line_ranges, lines_changed, num_hunks = self._parse_file_patch_lines(file_patch)
            file_line_ranges[file_path] = line_ranges
            total_lines_changed += lines_changed
            hunks_per_file[file_path] = num_hunks
            affected_lines = []
            for start, end in line_ranges:
                affected_lines.extend(range(start, end + 1))
            if affected_lines and (file_path.endswith(".py") or file_path.endswith(".pyx")):
                file_functions, file_classes, line_func_map, line_class_map = self._analyze_source_code_with_runtime(
                    runtime, file_path, affected_lines
                )
            else:
                file_functions, file_classes = self._extract_code_structures_from_patch(file_patch, file_path)
                line_func_map, line_class_map = ({}, {})
            functions[file_path] = file_functions
            classes[file_path] = file_classes
            line_to_function[file_path] = line_func_map
            line_to_class[file_path] = line_class_map
        return LocalizationInfo(
            instance_id=instance_id,
            files=files,
            file_line_ranges=file_line_ranges,
            functions=functions,
            classes=classes,
            line_to_function=line_to_function,
            line_to_class=line_to_class,
            total_lines_changed=total_lines_changed,
            total_files_changed=len(files),
            hunks_per_file=hunks_per_file,
        )

    def parse_instance_loc_with_runtime(
        self, instance: Union[pd.Series, str], runtime: Runtime = None
    ) -> LocalizationInfo:
        """Parse ground-truth localization information using OpenHands runtime.

        Args:
            instance: Either a pandas Series with instance data or an instance_id string
            runtime: OpenHands runtime object

        Returns:
            LocalizationInfo object containing extracted localization data
        """
        if isinstance(instance, str):
            actual_instance_id = instance
            instance = self.get_instance_by_id(actual_instance_id)
        else:
            actual_instance_id = instance.get("instance_id", "unknown")
        self.logger.info(f"Parsing localization with runtime for instance: {actual_instance_id}")
        patch_content = instance.get("patch", "")
        if not patch_content:
            self.logger.warning(f"No patch content found for instance {actual_instance_id}")
            return self._empty_localization_info(actual_instance_id)
        return self._parse_patch_localization_with_runtime(patch_content, actual_instance_id, runtime)

    def _analyze_source_code_with_runtime(
        self, runtime: Runtime, file_path: str, affected_lines: list[int]
    ) -> tuple[list[str], list[str], dict[int, str], dict[int, str]]:
        """Analyze source code using OpenHands runtime to find functions and classes.

        Args:
            runtime: OpenHands runtime object
            file_path: Path to the file being analyzed
            affected_lines: List of line numbers that were changed

        Returns:
            Tuple of (functions, classes, line_to_function_map, line_to_class_map)
        """
        try:
            if not (file_path.endswith(".py") or file_path.endswith(".pyx")):
                self.logger.info(f"Skipping non-Python/Cython file: {file_path}")
                return ([], [], {}, {})
            from openhands.events.action import CmdRunAction

            check_action = CmdRunAction(command=f'test -f "{file_path}" && echo "EXISTS" || echo "NOT_EXISTS"')
            obs = runtime.run_action(check_action)
            if "NOT_EXISTS" in obs.content:
                self.logger.warning(f"File not found: {file_path}")
                return ([], [], {}, {})
            read_action = CmdRunAction(command=f'cat "{file_path}"')
            obs = runtime.run_action(read_action)
            if obs.exit_code != 0:
                self.logger.warning(f"Failed to read file {file_path}: {obs.content}")
                return ([], [], {}, {})
            file_content = obs.content
            if file_path.endswith(".py"):
                return self._parse_python_content_with_line_mapping(file_content, affected_lines)
            else:
                return self._parse_cython_content_with_line_mapping(file_content, affected_lines)
        except Exception as e:
            self.logger.warning(f"Failed to analyze source code with runtime for {file_path}: {e}")
            return ([], [], {}, {})

    def _extract_cython_classes_and_functions(self, lines: list[str]) -> tuple[set[str], set[str]]:
        """Extract classes and functions from Cython lines using regex patterns."""
        functions = set()
        classes = set()
        current_function = None
        current_class = None

        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()

            # Process class definition
            if self._is_class_definition(stripped_line):
                current_class = self._extract_class_name(stripped_line)
                classes.add(current_class)
                continue

            # Process function definition
            if self._is_function_definition(stripped_line):
                current_function = self._extract_function_name(stripped_line)
                functions.add(current_function)
                continue

            # Update scope tracking
            current_function = self._update_function_scope(current_function, line)
            current_class = self._update_class_scope(current_class, line, stripped_line)

        return functions, classes

    def _is_class_definition(self, line: str) -> bool:
        """Check if line is a class definition."""
        return bool(re.match("class\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[\\(:]", line))

    def _extract_class_name(self, line: str) -> str:
        """Extract class name from class definition line."""
        match = re.match("class\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[\\(:]", line)
        return match[1]

    def _is_function_definition(self, line: str) -> bool:
        """Check if line is a function definition."""
        patterns = [
            r"(?:async\s+|c?p?def\s+(?:[^(]*\s+)?)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            r"cdef\s+[^(]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            r"cpdef\s+[^(]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        ]
        return any(re.match(pattern, line) for pattern in patterns)

    def _extract_function_name(self, line: str) -> str:
        """Extract function name from function definition line."""
        patterns = [
            r"(?:async\s+|c?p?def\s+(?:[^(]*\s+)?)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            r"cdef\s+[^(]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            r"cpdef\s+[^(]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        ]

        for pattern in patterns:
            if match := re.match(pattern, line):
                return match[1]

        return None

    def _update_function_scope(self, current_function: str | None, line: str) -> str | None:
        """Update function scope based on current line."""
        if current_function and line and (not line[0].isspace()) and (not line.startswith("#")):
            return None
        return current_function

    def _update_class_scope(self, current_class: str | None, line: str, stripped_line: str) -> str | None:
        """Update class scope based on current line."""
        if (
            current_class
            and line
            and (not line[0].isspace())
            and (not line.startswith("#"))
            and (not stripped_line.startswith("def "))
            and (not stripped_line.startswith("cdef "))
            and (not stripped_line.startswith("cpdef "))
        ):
            return None
        return current_class

    def _find_nearest_function_and_class(self, lines: list[str], line_num: int) -> tuple[str | None, str | None]:
        """Find the nearest function and class for a given line number."""
        nearest_function = None
        nearest_class = None

        for i in range(line_num - 1, -1, -1):
            if i < len(lines):
                line = lines[i].strip()

                nearest_function = self._check_for_function_definition(line, nearest_function)
                nearest_class = self._check_for_class_definition(line, nearest_class)

                # Stop if we found both or reached the beginning
                if (nearest_function and nearest_class) or i == 0:
                    break

        return nearest_function, nearest_class

    def _check_for_function_definition(self, line: str, current_function: str | None) -> str | None:
        """Check if line contains a function definition."""
        if current_function:
            return current_function

        func_match = (
            re.match("(?:async\\s+|c?p?def\\s+(?:[^(]*\\s+)?)?def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(", line)
            or re.match("cdef\\s+[^(]*\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(", line)
            or re.match("cpdef\\s+[^(]*\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(", line)
        )

        return func_match.group(1) if func_match else None

    def _check_for_class_definition(self, line: str, current_class: str | None) -> str | None:
        """Check if line contains a class definition."""
        if current_class:
            return current_class

        class_match = re.match("class\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[\\(:]", line)
        return class_match[1] if class_match else None

    def _map_affected_lines_to_functions_and_classes(
        self, lines: list[str], affected_lines: list[int]
    ) -> tuple[dict[int, str], dict[int, str]]:
        """Map affected lines to their nearest functions and classes."""
        line_to_function = {}
        line_to_class = {}

        for line_num in affected_lines:
            if line_num <= len(lines):
                nearest_function, nearest_class = self._find_nearest_function_and_class(lines, line_num)

                if nearest_function:
                    line_to_function[line_num] = nearest_function
                if nearest_class:
                    line_to_class[line_num] = nearest_class

        return line_to_function, line_to_class

    def _parse_cython_content_with_line_mapping(
        self, content: str, affected_lines: list[int]
    ) -> tuple[list[str], list[str], dict[int, str], dict[int, str]]:
        """Parse Cython content to extract functions and classes with line mapping.

        Since Cython files can't be parsed with Python's AST, we use regex-based parsing.

        Args:
            content: Cython source code content
            affected_lines: List of line numbers that were changed

        Returns:
            Tuple of (functions, classes, line_to_function_map, line_to_class_map)
        """
        try:
            lines = content.split("\n")

            # Extract classes and functions from all lines
            functions, classes = self._extract_cython_classes_and_functions(lines)

            # Map affected lines to their nearest functions and classes
            line_to_function, line_to_class = self._map_affected_lines_to_functions_and_classes(lines, affected_lines)

            return (list(functions), list(classes), line_to_function, line_to_class)
        except Exception as e:
            self.logger.warning(f"Failed to parse Cython content: {e}")
            return ([], [], {}, {})

    def _parse_python_content_with_line_mapping(
        self, content: str, affected_lines: list[int]
    ) -> tuple[list[str], list[str], dict[int, str], dict[int, str]]:
        """Parse Python content to extract functions and classes with accurate line mapping.

        Args:
            content: Python source code content
            affected_lines: List of line numbers that were changed

        Returns:
            Tuple of (functions, classes, line_to_function_map, line_to_class_map)
        """
        try:
            tree = ast.parse(content)
            functions = set()
            classes = set()
            line_to_function = {}
            line_to_class = {}
            line_to_node = {}

            class NodeVisitor(ast.NodeVisitor):

                def __init__(self):
                    self.current_class = None
                    self.class_stack = []

                def visit_ClassDef(self, node):
                    self.class_stack.append(node.name)
                    old_class = self.current_class
                    self.current_class = node.name
                    classes.add(node.name)
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", node.lineno)
                    if end_line is None:
                        end_line = start_line + 100
                    for line_num in range(start_line, end_line + 1):
                        line_to_node[line_num] = ("class", node.name)
                    self.generic_visit(node)
                    self.current_class = old_class
                    self.class_stack.pop()

                def visit_FunctionDef(self, node):
                    functions.add(node.name)
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", node.lineno)
                    if end_line is None:
                        end_line = start_line + 50
                    for line_num in range(start_line, end_line + 1):
                        line_to_node[line_num] = ("function", node.name)
                    self.generic_visit(node)

                def visit_AsyncFunctionDef(self, node):
                    self.visit_FunctionDef(node)

            visitor = NodeVisitor()
            visitor.visit(tree)
            for line_num in affected_lines:
                if line_num in line_to_node:
                    node_type, node_name = line_to_node[line_num]
                    if node_type == "function":
                        line_to_function[line_num] = node_name
                    elif node_type == "class":
                        line_to_class[line_num] = node_name
            return (list(functions), list(classes), line_to_function, line_to_class)
        except Exception as e:
            self.logger.warning(f"Failed to parse Python content: {e}")
            return ([], [], {}, {})

    def _parse_python_content(
        self, content: str, affected_lines: list[int]
    ) -> tuple[list[str], list[str], dict[int, str], dict[int, str]]:
        """Parse Python content to extract functions and classes.

        Args:
            content: Python source code content
            affected_lines: List of line numbers that were changed

        Returns:
            Tuple of (functions, classes, line_to_function_map, line_to_class_map)
        """
        try:
            tree = ast.parse(content)
            functions = set()
            classes = set()
            line_to_function = {}
            line_to_class = {}

            class Analyzer(ast.NodeVisitor):

                def __init__(self):
                    self.current_class = None
                    self.function_stack = []
                    self.class_stack = []

                def visit_ClassDef(self, node):
                    self.class_stack.append(node.name)
                    old_class = self.current_class
                    self.current_class = node.name
                    classes.add(node.name)
                    end_line = getattr(node, "end_lineno", node.lineno)
                    if end_line is None:
                        end_line = node.lineno
                    for line_num in range(node.lineno, end_line + 1):
                        if line_num in affected_lines:
                            line_to_class[line_num] = node.name
                    self.generic_visit(node)
                    self.current_class = old_class
                    self.class_stack.pop()

                def visit_FunctionDef(self, node):
                    self.function_stack.append(node.name)
                    functions.add(node.name)
                    end_line = getattr(node, "end_lineno", node.lineno)
                    if end_line is None:
                        end_line = node.lineno
                    for line_num in range(node.lineno, end_line + 1):
                        if line_num in affected_lines:
                            line_to_function[line_num] = node.name
                            if self.current_class:
                                line_to_class[line_num] = self.current_class
                    self.generic_visit(node)
                    self.function_stack.pop()

                def visit_AsyncFunctionDef(self, node):
                    self.visit_FunctionDef(node)

            analyzer = Analyzer()
            analyzer.visit(tree)
            return (list(functions), list(classes), line_to_function, line_to_class)
        except Exception as e:
            self.logger.warning(f"Failed to parse Python content: {e}")
            return ([], [], {}, {})

    def _split_patch_by_files(self, patch_content: str) -> dict[str, str]:
        """Split a multi-file patch into individual file patches.

        Args:
            patch_content: Complete patch content

        Returns:
            Dictionary mapping file paths to their patch content
        """
        file_patches = {}
        current_file = None
        current_patch_lines = []
        lines = patch_content.split("\n")

        for line in lines:
            if self._is_diff_git_line(line):
                self._handle_diff_git_line(line, file_patches, current_file, current_patch_lines)
                current_file, current_patch_lines = self._extract_file_from_diff_git(line)
            elif self._is_file_header_line(line):
                current_file, current_patch_lines = self._handle_file_header_line(
                    line, current_file, current_patch_lines
                )
            elif current_file:
                current_patch_lines.append(line)

        # Add final file patch if exists
        if current_file and current_patch_lines:
            file_patches[current_file] = "\n".join(current_patch_lines)

        return file_patches

    def _is_diff_git_line(self, line: str) -> bool:
        """Check if line is a diff --git line."""
        return line.startswith("diff --git")

    def _handle_diff_git_line(
        self, line: str, file_patches: dict, current_file: str | None, current_patch_lines: list
    ) -> None:
        """Handle diff --git line by saving current file patch."""
        if current_file and current_patch_lines:
            file_patches[current_file] = "\n".join(current_patch_lines)

    def _extract_file_from_diff_git(self, line: str) -> tuple[str | None, list]:
        """Extract file path from diff --git line."""
        if match := re.search("diff --git a/(.*?) b/(.*?)(?:\\s|$)", line):
            return match[1], [line]
        else:
            return None, []

    def _is_file_header_line(self, line: str) -> bool:
        """Check if line is a file header line (--- or +++)."""
        return line.startswith("---") or line.startswith("+++")

    def _handle_file_header_line(
        self, line: str, current_file: str | None, current_patch_lines: list
    ) -> tuple[str | None, list]:
        """Handle file header line (--- or +++)."""
        if not current_file:
            return self._extract_file_from_header_line(line, current_patch_lines)
        current_patch_lines.append(line)
        return current_file, current_patch_lines

    def _extract_file_from_header_line(self, line: str, current_patch_lines: list) -> tuple[str | None, list]:
        """Extract file path from header line."""
        match = re.search("[+-]{3}\\s+(?:a/|b/)?(.+?)(?:\\s|$)", line)
        if match and not match[1].startswith("/dev/null"):
            current_file = match[1]
            if current_patch_lines:
                current_patch_lines.append(line)
            else:
                current_patch_lines = [line]
            return current_file, current_patch_lines
        elif current_patch_lines:
            current_patch_lines.append(line)
            return None, current_patch_lines
        else:
            return None, []

    def _empty_localization_info(self, instance_id: str = "unknown") -> LocalizationInfo:
        """Return an empty LocalizationInfo object.

        Args:
            instance_id: Instance identifier

        Returns:
            Empty LocalizationInfo instance
        """
        return LocalizationInfo(
            instance_id=instance_id,
            files=[],
            file_line_ranges={},
            functions={},
            classes={},
            line_to_function={},
            line_to_class={},
            total_lines_changed=0,
            total_files_changed=0,
            hunks_per_file={},
        )

    def get_dataset_statistics(self) -> dict[str, Any]:
        """Get statistics about the loaded dataset.

        Returns:
            Dictionary containing dataset statistics
        """
        if self.df is None:
            return {}
        return {
            "total_instances": len(self.df),
            "repositories": self.df["repo"].nunique() if "repo" in self.df.columns else 0,
            "avg_patch_length": self.df["patch"].str.len().mean() if "patch" in self.df.columns else 0,
            "columns": list(self.df.columns),
        }

    def get_instances_by_repo(self, repo_name: str) -> pd.DataFrame:
        """Get all instances for a specific repository.

        Args:
            repo_name: Repository name (e.g., "django/django")

        Returns:
            DataFrame containing instances for the specified repository
        """
        if "repo" not in self.df.columns:
            raise ValueError("Repository information not available in dataset")
        return self.df[self.df["repo"] == repo_name].copy()
