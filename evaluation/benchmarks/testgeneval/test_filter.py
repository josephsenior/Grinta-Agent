import ast
import re
from evaluation.benchmarks.testgeneval.constants import Status as TestStatus
from evaluation.benchmarks.testgeneval.log_parsers import (
    MAP_REPO_TO_PARSER,
    parse_log_pytest,
)


def indent_text(text, indent_level):
    return "\n".join(
        (
            " " * indent_level + line if line.strip() else line
            for line in text.split("\n")
        )
    )


def extract_preamble_classes_and_functions(code):
    """Extract preamble, classes, and test functions from code."""
    patterns = _compile_regex_patterns()
    preamble = ""
    classes = []
    test_functions = []
    current_position = 0

    while current_position < len(code):
        class_match = patterns["class"].search(code, current_position)
        method_match = patterns["method"].search(code, current_position)

        if class_match and (
            not method_match or class_match.start() < method_match.start()
        ):
            current_position = _process_class_match(
                code, class_match, classes, patterns
            )
        elif method_match:
            current_position = _process_method_match(
                code, method_match, test_functions, patterns, class_match
            )
        else:
            break

    preamble = _determine_preamble(code, classes, test_functions)
    return (preamble.strip(), classes, test_functions)


def _compile_regex_patterns():
    """Compile regex patterns for class, method, and function matching."""
    return {
        "class": re.compile(
            "(?P<decorators>(?:^@[^\\r\\n]*(?:\\r?\\n(?:[ \\t]+[^\\r\\n]*|^\\)[^\\r\\n]*)*)*\\r?\\n)*?)^class\\s+([\\w]+)(?:\\([^)]*\\))?:",
            re.MULTILINE,
        ),
        "method": re.compile(
            "(^(\\s*@.*\\s*)*^\\s*def\\s+[\\w_]+\\(.*\\):)", re.MULTILINE
        ),
        "function": re.compile(
            "(?P<decorators>(?:^@[^\\r\\n]*(?:\\r?\\n(?:[ \\t]+[^\\r\\n]*|^\\)[^\\r\\n]*)*)*\\r?\\n)*?)^def\\s+([\\w_]+)\\(.*\\):",
            re.MULTILINE,
        ),
    }


def _extract_class_body(code: str, start_index: int) -> tuple[str, int]:
    """Extract the body of a class from the given code starting from the specified index."""
    if not code or start_index < 0 or start_index >= len(code):
        raise ValueError("Invalid code or start index")

    lines = code[start_index:].split("\n")
    class_start_line = lines[0]
    start_indent = len(class_start_line) - len(class_start_line.lstrip())
    inside_multiline_comment = False
    end_index = start_index

    for i, line in enumerate(lines[1:], start=1):
        if _should_break_class_extraction(line, start_indent, inside_multiline_comment):
            break
        inside_multiline_comment = _update_multiline_comment_state(
            line, inside_multiline_comment
        )
        end_index = start_index + len("\n".join(lines[: i + 1])) + 1

    return (code[start_index:end_index], end_index)


def _should_break_class_extraction(
    line: str, start_indent: int, inside_multiline_comment: bool
) -> bool:
    """Check if class extraction should break at this line."""
    stripped_line = line.strip()
    current_indent = len(line) - len(line.lstrip())
    return not inside_multiline_comment and (
        current_indent <= start_indent and stripped_line
    )


def _update_multiline_comment_state(line: str, inside_multiline_comment: bool) -> bool:
    """Update the multiline comment state based on the current line."""
    stripped_line = line.strip()
    if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
        return not inside_multiline_comment
    return inside_multiline_comment


def _process_class_match(code: str, class_match, classes: list, patterns: dict) -> int:
    """Process a class match and extract its methods."""
    class_name = class_match[0]
    class_body, end_idx = _extract_class_body(code, class_match.end())
    methods = _extract_class_methods(class_body, class_name, patterns["method"])
    classes.append((class_name, methods, class_match.start()))
    return end_idx


def _extract_class_methods(class_body: str, class_name: str, method_pattern) -> list:
    """Extract methods from a class body."""
    methods = []
    class_prefix = class_name
    set_prefix = False

    for method_match in method_pattern.finditer(class_body):
        method_name = method_match.group()
        method_start = method_match.start()

        if not set_prefix:
            # Store the prefix (not currently used but may be needed for future enhancements)
            _ = class_name + class_body[:method_start]
            set_prefix = True

        method_body = _extract_method_body(
            class_body, method_start, method_name, method_pattern
        )
        methods.append((method_name, method_body))

    return methods


def _extract_method_body(
    class_body: str, method_start: int, method_name: str, method_pattern
) -> str:
    """Extract the body of a method."""
    if next_method := method_pattern.search(
        class_body, method_start + len(method_name)
    ):
        return class_body[method_start : next_method.start()]
    else:
        return class_body[method_start:]


def _process_method_match(
    code: str, method_match, test_functions: list, patterns: dict, class_match
) -> int:
    """Process a method/function match and extract its body."""
    function_name = method_match.group(0)
    start_idx = method_match.start()
    function_body = _extract_function_body(
        code, start_idx, function_name, patterns["function"], class_match
    )
    test_functions.append((function_body, start_idx))
    return start_idx + len(function_body)


def _extract_function_body(
    code: str, start_idx: int, function_name: str, function_pattern, class_match
) -> str:
    """Extract the body of a function."""
    lines = code[start_idx:].split("\n")
    len(lines[0]) - len(lines[0].lstrip())
    if next_function := _find_next_function(
        code, start_idx, function_name, function_pattern, class_match
    ):
        next_function_start = next_function.start()
        if class_match and next_function_start > class_match.start():
            next_function_start = class_match.start()
        return code[start_idx:next_function_start]
    else:
        return code[start_idx:]


def _find_next_function(
    code: str, start_idx: int, function_name: str, function_pattern, class_match
):
    """Find the next function in the code."""
    next_function = function_pattern.search(code, start_idx + len(function_name))

    while (
        next_function
        and (class_match is None or next_function.start() < class_match.start())
        and not _is_function_at_same_level(code, next_function, start_idx)
    ):
        next_function = function_pattern.search(
            code, next_function.start() + len(next_function[0])
        )

    return next_function


def _is_function_at_same_level(code: str, next_function, start_idx: int) -> bool:
    """Check if the next function is at the same indentation level."""
    next_function_start = next_function.start()
    next_line = code[next_function_start:].split("\n", 1)[0]
    next_indent = len(next_line) - len(next_line.lstrip())

    lines = code[start_idx:].split("\n")
    current_indent = len(lines[0]) - len(lines[0].lstrip())

    return next_indent <= current_indent


def _determine_preamble(code: str, classes: list, test_functions: list) -> str:
    """Determine the preamble based on classes and test functions."""
    if classes and test_functions:
        return code[: min(classes[0][2], test_functions[0][1])]
    elif classes:
        return code[: classes[0][2]]
    elif test_functions:
        return code[: test_functions[0][1]]
    else:
        return code


def filter_passing_tests(
    test_content: str, test_output: str, repo: str
) -> tuple[str, list[str], list[str]]:
    """Filter tests based on their execution results.

    Returns:
        Tuple containing:
        - Modified test content with only passing tests
        - List of passing test names
        - List of failing test names
    """
    # Parse test results
    test_results = _parse_test_results(test_output, repo)
    passing_tests, failing_tests = _categorize_test_results(test_results)

    # Early return if no passing tests
    if not passing_tests:
        return ("", passing_tests, failing_tests)

    # Extract and filter test content
    preamble, classes, functions = extract_preamble_classes_and_functions(test_content)
    filtered_classes = _filter_test_classes(classes, failing_tests)
    filtered_functions = _filter_test_functions(functions, failing_tests)

    # Reconstruct filtered content
    filtered_content = _reconstruct_filtered_content(
        preamble, filtered_classes, filtered_functions
    )

    return (filtered_content, passing_tests, failing_tests)


def _filter_test_classes(classes: list, failing_tests: list[str]) -> list:
    """Filter test classes to remove failing test methods."""
    filtered_classes = []

    for class_name, methods, start_idx in classes:
        if non_fail_methods := _filter_class_methods(methods, failing_tests):
            filtered_classes.append((class_name, non_fail_methods, start_idx))

    return filtered_classes


def _filter_class_methods(methods: list, failing_tests: list[str]) -> list:
    """Filter methods within a class to remove failing tests."""
    non_fail_methods = []

    for method_name, method_body in methods:
        method_full_name = _extract_method_name(method_name)
        if _is_method_passing(method_full_name, failing_tests):
            non_fail_methods.append((method_name, method_body))

    return non_fail_methods


def _extract_method_name(method_name: str) -> str:
    """Extract clean method name from full method name."""
    return method_name.split(".")[-1].split("(")[0].strip().split(" ")[-1]


def _is_method_passing(method_name: str, failing_tests: list[str]) -> bool:
    """Check if a method is passing (not in failing tests)."""
    return all(
        method_name not in failing_test for failing_test in failing_tests
    ) and all(failing_test not in method_name for failing_test in failing_tests)


def _filter_test_functions(functions: list, failing_tests: list[str]) -> list:
    """Filter standalone test functions to remove failing tests."""
    filtered_functions = []

    for func_body, start_idx in functions:
        func_name = _extract_function_name(func_body)
        if _is_method_passing(func_name, failing_tests):
            filtered_functions.append((func_body, start_idx))

    return filtered_functions


def _extract_function_name(func_body: str) -> str:
    """Extract function name from function body."""
    return func_body.split("def ")[1].split("(")[0].strip()


def _reconstruct_filtered_content(
    preamble: str, filtered_classes: list, filtered_functions: list
) -> str:
    """Reconstruct the filtered test content."""
    content_parts = [preamble]

    # Add filtered classes
    for class_name, methods, _ in filtered_classes:
        class_content = _build_class_content(class_name, methods)
        content_parts.append(class_content)

    # Add filtered functions
    content_parts.extend(func_body for func_body, _ in filtered_functions)
    return "\n\n".join(content_parts)


def _build_class_content(class_name: str, methods: list) -> str:
    """Build content for a filtered class."""
    class_content = class_name + "\n"
    for _, method_body in methods:
        class_content += method_body + "\n"
    return class_content


def filter_tests(
    test_content: str, test_output: str, repo: str
) -> tuple[str, list[str], list[str]]:
    """Filter tests using AST parsing to remove failing test functions from the test file.

    Non-test functions (e.g. setup or helper methods) and classes (even if all test methods are failing)
    are preserved.

    If AST processing fails (for example, because the test file cannot be parsed),
    this function falls back on the existing regex-based filtering (filter_passing_tests).

    Returns:
        Tuple containing:
         - Modified test content (as a string) containing only passing tests.
         - List of passing test names.
         - List of failing test names.
    """
    try:
        return _filter_tests_with_ast(test_content, test_output, repo)
    except Exception:
        print("AST processing failed; falling back on regex-based filtering.")
        return filter_passing_tests(test_content, test_output, repo)


def _filter_tests_with_ast(
    test_content: str, test_output: str, repo: str
) -> tuple[str, list[str], list[str]]:
    """Filter tests using AST parsing."""
    tree = ast.parse(test_content)
    test_results = _parse_test_results(test_output, repo)
    passing_tests, failing_tests = _categorize_test_results(test_results)

    is_failing = _create_failing_test_checker(failing_tests)
    new_body = _filter_ast_nodes(tree.body, is_failing)

    tree.body = new_body
    new_test_content = ast.unparse(tree)
    return (new_test_content, passing_tests, failing_tests)


def _parse_test_results(test_output: str, repo: str) -> dict[str, str]:
    """Parse test results from output."""
    parser = MAP_REPO_TO_PARSER.get(repo, parse_log_pytest)
    return parser(test_output)


def _categorize_test_results(
    test_results: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Categorize test results into passing and failing."""
    passing_tests = [
        name
        for name, status in test_results.items()
        if status == TestStatus.PASSED.value
    ]
    failing_tests = [
        name
        for name, status in test_results.items()
        if status != TestStatus.PASSED.value
    ]
    return passing_tests, failing_tests


def _create_failing_test_checker(failing_tests: list[str]) -> callable:
    """Create a function to check if a test is failing."""

    def is_failing(name: str) -> bool:
        for ft in failing_tests:
            if name in ft or ft in name:
                return True
        return False

    return is_failing


def _filter_ast_nodes(body: list, is_failing: callable) -> list:
    """Filter AST nodes based on test results."""
    new_body = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _should_skip_function(node, is_failing):
                new_body.append(node)
        elif isinstance(node, ast.ClassDef):
            if filtered_class := _filter_class_node(node, is_failing):
                new_body.append(filtered_class)
        else:
            new_body.append(node)
    return new_body


def _should_skip_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, is_failing: callable
) -> bool:
    """Check if a function should be skipped."""
    return node.name.startswith("test") and is_failing(node.name)


def _filter_class_node(node: ast.ClassDef, is_failing: callable) -> ast.ClassDef | None:
    """Filter class node to remove failing test methods."""
    new_class_body = []
    for subnode in node.body:
        if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _should_skip_class_method(subnode, node.name, is_failing):
                new_class_body.append(subnode)
        else:
            new_class_body.append(subnode)

    if new_class_body:
        node.body = new_class_body
        return node
    return None


def _should_skip_class_method(
    subnode: ast.FunctionDef | ast.AsyncFunctionDef,
    class_name: str,
    is_failing: callable,
) -> bool:
    """Check if a class method should be skipped."""
    qualified_name = f"{class_name}.{subnode.name}"
    return is_failing(subnode.name) or is_failing(qualified_name)
