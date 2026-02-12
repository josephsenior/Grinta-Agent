"""Tests for the command helper functions in function_calling.py."""

import os
import sys
import pytest
from conftest import _close_test_runtime, _load_runtime
from backend.engines.auditor.function_calling import (
    glob_to_cmdrun,
    grep_to_cmdrun,
)
from backend.core.logger import forge_logger as logger
from backend.events.action import CmdRunAction
from backend.events.observation import CmdOutputObservation, ErrorObservation

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("TEST_RUNTIME") == "cli",
        reason="CLIRuntime: Auditor's GrepTool/GlobTool tests require `rg` (ripgrep), which may not be installed.",
    ),
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows: These tests require `rg` (ripgrep) and bash-style commands which are not available on Windows.",
    ),
]


def _run_cmd_action(runtime, custom_command: str):
    """Helper function to run a command action and return the observation.

    Args:
        runtime: The runtime environment to execute the command in.
        custom_command: The command string to execute.

    Returns:
        The observation result from running the command.
    """
    action = CmdRunAction(command=custom_command)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert isinstance(obs, (CmdOutputObservation, ErrorObservation))
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    return obs


def test_grep_to_cmdrun_basic():
    """Test basic pattern with no special characters."""
    cmd = grep_to_cmdrun("function", "src")
    assert "rg -li function" in cmd
    assert "Below are the execution results" in cmd
    cmd = grep_to_cmdrun("error", "src", "*.js")
    assert "rg -li error" in cmd
    assert "--glob '*.js'" in cmd
    assert "Below are the execution results" in cmd


def test_grep_to_cmdrun_quotes(temp_dir, runtime_cls, run_as_Forge):
    """Test patterns with different types of quotes."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        cmd = grep_to_cmdrun('const message = "Hello"', "/workspace")
        assert "rg -li" in cmd
        setup_cmd = "echo 'const message = \"Hello\";' > /workspace/test_quotes.js"
        obs = _run_cmd_action(runtime, setup_cmd)
        assert obs.exit_code == 0
        obs = _run_cmd_action(runtime, cmd)
        assert obs.exit_code == 0
        assert "/workspace/test_quotes.js" in obs.content
        cmd = grep_to_cmdrun("function\\('test'\\)", "/workspace")
        assert "rg -li" in cmd
        setup_cmd = "echo \"function('test') {}\" > /workspace/test_quotes2.js"
        obs = _run_cmd_action(runtime, setup_cmd)
        assert obs.exit_code == 0
        obs = _run_cmd_action(runtime, cmd)
        assert obs.exit_code == 0
        assert "/workspace/test_quotes2.js" in obs.content
    finally:
        _close_test_runtime(runtime)


def _setup_special_patterns_test_files(runtime):
    """Setup test files with special characters."""
    setup_cmd = '\n        mkdir -p /workspace/test_special_patterns &&         echo "testing x && y || z pattern" > /workspace/test_special_patterns/logical.txt &&         echo "function() { return x; }" > /workspace/test_special_patterns/function.txt &&         echo "using \\$variable here" > /workspace/test_special_patterns/dollar.txt &&         echo "using \\`backticks\\` here" > /workspace/test_special_patterns/backticks.txt &&         echo "line with \\n newline chars" > /workspace/test_special_patterns/newline.txt &&         echo "matching *.js wildcard" > /workspace/test_special_patterns/wildcard.txt &&         echo "testing x > y redirection" > /workspace/test_special_patterns/redirect.txt &&         echo "testing a | b pipe" > /workspace/test_special_patterns/pipe.txt &&         echo "line with #comment" > /workspace/test_special_patterns/comment.txt &&         echo "CSS \\!important rule" > /workspace/test_special_patterns/bang.txt\n        '
    obs = _run_cmd_action(runtime, setup_cmd)
    assert obs.exit_code == 0, "Failed to set up test files"


def _get_special_patterns():
    """Get list of special patterns to test."""
    return [
        "x && y \\|\\| z",
        "function\\(\\) \\{ return x; \\}",
        "\\$variable",
        "\\\\n newline",
        "\\*\\.js",
        "x > y",
        "a \\| b",
        "#comment",
    ]


def _test_pattern_execution(runtime, pattern):
    """Test execution of a single pattern."""
    cmd = grep_to_cmdrun(pattern, "/workspace/test_special_patterns")
    assert "rg -li" in cmd
    assert "Below are the execution results of the search command:" in cmd
    obs = _run_cmd_action(runtime, cmd)
    assert "command not found" not in obs.content
    assert "syntax error" not in obs.content
    assert "unexpected" not in obs.content
    return obs


def _verify_pattern_results(pattern, obs):
    """Verify that pattern results are correct."""
    if "&&" in pattern:
        assert "logical.txt" in obs.content
    elif "function" in pattern:
        assert "function.txt" in obs.content
    elif "$variable" in pattern:
        assert "dollar.txt" in obs.content
    elif "\\n newline" in pattern:
        assert "newline.txt" in obs.content
    elif "*" in pattern:
        assert "wildcard.txt" in obs.content
    elif ">" in pattern:
        assert "redirect.txt" in obs.content
    elif "|" in pattern:
        assert "pipe.txt" in obs.content
    elif "#comment" in pattern:
        assert "comment.txt" in obs.content


def test_grep_to_cmdrun_special_chars(runtime_cls, run_as_Forge, temp_dir):
    """Test patterns with special shell characters."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        # Setup test files
        _setup_special_patterns_test_files(runtime)

        # Test each special pattern
        special_patterns = _get_special_patterns()
        for pattern in special_patterns:
            obs = _test_pattern_execution(runtime, pattern)
            _verify_pattern_results(pattern, obs)
    finally:
        _close_test_runtime(runtime)


def test_grep_to_cmdrun_paths_with_spaces(runtime_cls, run_as_Forge, temp_dir):
    """Test paths with spaces and special characters."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        setup_cmd = '\n        mkdir -p "src/my project" "test files/unit tests" "src/special$chars" "path with spaces and $pecial ch@rs" &&         echo "function searchablePattern() { return true; }" > "src/my project/test.js" &&         echo "function testFunction() { return 42; }" > "test files/unit tests/test.js" &&         echo "function specialFunction() { return null; }" > "src/special$chars/test.js" &&         echo "function weirdFunction() { return []; }" > "path with spaces and $pecial ch@rs/test.js"\n        '
        obs = _run_cmd_action(runtime, setup_cmd)
        assert obs.exit_code == 0, "Failed to set up test files"
        special_paths = ["src/my project", "test files/unit tests"]
        for path in special_paths:
            cmd = grep_to_cmdrun("function", path)
            assert "rg -li" in cmd
            obs = _run_cmd_action(runtime, cmd)
            assert obs.exit_code == 0, f"Grep command failed for path: {path}"
            assert "function" in obs.content, (
                f"Expected pattern not found in output for path: {path}"
            )
            if path == "src/my project":
                assert "src/my project/test.js" in obs.content
            elif path == "test files/unit tests":
                assert "test files/unit tests/test.js" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_glob_to_cmdrun_basic():
    """Test basic glob patterns."""
    cmd = glob_to_cmdrun("*.js", "src")
    assert "rg --files src -g '*.js'" in cmd
    assert "head -n 100" in cmd
    assert 'echo "Below are the execution results of the glob command:' in cmd
    cmd = glob_to_cmdrun("*.py")
    assert "rg --files . -g '*.py'" in cmd
    assert "head -n 100" in cmd
    assert 'echo "Below are the execution results of the glob command:' in cmd


def _setup_glob_special_patterns_test_files(runtime):
    """Setup test files for glob special patterns testing."""
    setup_cmd = '\n        mkdir -p src/components src/utils && \\\n        touch src/file1.js src/file2.js src/file9.js && \\\n        touch src/components/comp.jsx src/components/comp.tsx && \\\n        touch src/$special-file.js && \\\n        touch src/temp1.js src/temp2.js && \\\n        touch src/file.js src/file.ts src/file.jsx && \\\n        touch "src/weird\\`file\\`.js" && \\\n        touch "src/file with spaces.js"\n        '
    obs = _run_cmd_action(runtime, setup_cmd)
    assert obs.exit_code == 0, "Failed to set up test files"


def _get_glob_special_patterns():
    """Get list of special glob patterns to test."""
    return [
        "**/*.js",
        "**/{*.jsx,*.tsx}",
        "file[0-9].js",
        "temp?.js",
        "file.{js,ts,jsx}",
        "file with spaces.js",
    ]


def _test_glob_pattern_execution(runtime, pattern):
    """Test execution of a single glob pattern."""
    cmd = glob_to_cmdrun(pattern, "src")
    logger.info("Command: %s", cmd)
    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0, f"Glob command failed for pattern: {pattern}"
    return obs


def _verify_glob_pattern_results(pattern, obs):
    """Verify that glob pattern results are correct."""
    pattern_verifiers = {
        "**/*.js": _verify_js_files_pattern,
        "**/{*.jsx,*.tsx}": _verify_jsx_tsx_files_pattern,
        "file with spaces.js": _verify_spaces_filename_pattern,
        "file.{js,ts,jsx}": _verify_multiple_extensions_pattern,
        "file[0-9].js": _verify_numbered_files_pattern,
        "temp?.js": _verify_wildcard_files_pattern,
    }

    if verifier := pattern_verifiers.get(pattern):
        verifier(obs)
    else:
        raise ValueError(f"Unknown pattern: {pattern}")


def _verify_js_files_pattern(obs):
    """Verify **/*.js pattern results."""
    assert "file1.js" in obs.content
    assert "file2.js" in obs.content


def _verify_jsx_tsx_files_pattern(obs):
    """Verify **/{*.jsx,*.tsx} pattern results."""
    assert "comp.jsx" in obs.content
    assert "comp.tsx" in obs.content


def _verify_spaces_filename_pattern(obs):
    """Verify file with spaces pattern results."""
    assert "file with spaces.js" in obs.content


def _verify_multiple_extensions_pattern(obs):
    """Verify file.{js,ts,jsx} pattern results."""
    assert "file.js" in obs.content
    assert "file.ts" in obs.content
    assert "file.jsx" in obs.content


def _verify_numbered_files_pattern(obs):
    """Verify file[0-9].js pattern results."""
    assert "file1.js" in obs.content
    assert "file2.js" in obs.content
    assert "file9.js" in obs.content


def _verify_wildcard_files_pattern(obs):
    """Verify temp?.js pattern results."""
    assert "temp1.js" in obs.content
    assert "temp2.js" in obs.content


def test_glob_to_cmdrun_special_patterns(runtime_cls, run_as_Forge, temp_dir):
    """Test glob patterns with special characters."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        # Setup test files
        _setup_glob_special_patterns_test_files(runtime)

        # Test each special pattern
        special_patterns = _get_glob_special_patterns()
        for pattern in special_patterns:
            obs = _test_glob_pattern_execution(runtime, pattern)
            _verify_glob_pattern_results(pattern, obs)
    finally:
        _close_test_runtime(runtime)


def test_glob_to_cmdrun_paths_with_spaces(runtime_cls, run_as_Forge, temp_dir):
    """Test paths with spaces and special characters for glob command."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        setup_cmd = '\n        mkdir -p "project files/src" "test results/unit tests" "weird$path/code" "path with spaces and $pecial ch@rs" &&         touch "project files/src/file1.js" "project files/src/file2.js" &&         touch "test results/unit tests/test1.js" "test results/unit tests/test2.js" &&         touch "weird$path/code/weird1.js" "weird$path/code/weird2.js" &&         touch "path with spaces and $pecial ch@rs/special1.js" "path with spaces and $pecial ch@rs/special2.js"\n        '
        obs = _run_cmd_action(runtime, setup_cmd)
        assert obs.exit_code == 0, "Failed to set up test files"
        special_paths = ["project files/src", "test results/unit tests"]
        for path in special_paths:
            cmd = glob_to_cmdrun("*.js", path)
            obs = _run_cmd_action(runtime, cmd)
            assert obs.exit_code == 0, f"Glob command failed for path: {path}"
            if path == "project files/src":
                assert "file1.js" in obs.content
                assert "file2.js" in obs.content
            elif path == "test results/unit tests":
                assert "test1.js" in obs.content
                assert "test2.js" in obs.content
    finally:
        _close_test_runtime(runtime)
