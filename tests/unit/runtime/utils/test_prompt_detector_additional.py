from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class StubLogger:
        def __init__(self):
            self.info_calls: list[tuple[str, tuple, dict]] = []
            self.warning_calls: list[tuple[str, tuple, dict]] = []

        def info(self, msg, *args, **kwargs):
            self.info_calls.append((msg, args, kwargs))

        def warning(self, msg, *args, **kwargs):
            self.warning_calls.append((msg, args, kwargs))

    setattr(logger_mod, "forge_logger", StubLogger())


spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.prompt_detector",
    ROOT / "forge" / "runtime" / "utils" / "prompt_detector.py",
)
assert spec and spec.loader
prompt_detector_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.prompt_detector"] = prompt_detector_mod
spec.loader.exec_module(prompt_detector_mod)

PromptPattern = prompt_detector_mod.PromptPattern
PromptType = prompt_detector_mod.PromptType
InteractivePromptDetector = prompt_detector_mod.InteractivePromptDetector
detect_interactive_prompt = prompt_detector_mod.detect_interactive_prompt
suggest_noninteractive_command = prompt_detector_mod.suggest_noninteractive_command


@pytest.fixture(autouse=True)
def reset_logger():
    stub_logger = sys.modules["forge.core.logger"].forge_logger  # type: ignore[attr-defined]
    stub_logger.info_calls.clear()
    stub_logger.warning_calls.clear()
    yield stub_logger


def test_prompt_pattern_matches_case_insensitive():
    pattern = PromptPattern(
        pattern=r"Proceed\s+\(y/n\)\?",
        prompt_type=PromptType.OK_PROCEED,
        response="y\n",
        description="Proceed prompt",
    )
    assert pattern.matches("PROCEED (y/n)?")
    assert not pattern.matches("something else")


def test_detect_prompt_returns_pattern_and_logs(reset_logger):
    detector = InteractivePromptDetector()
    output = "Installing packages...\nOk to proceed? (y)"
    pattern = detector.detect_prompt(output)
    assert pattern is not None
    assert pattern.prompt_type == PromptType.OK_PROCEED
    assert any(
        "Auto-detected interactive prompt" in call[0]
        for call in reset_logger.info_calls
    )


def test_detect_prompt_respects_confidence_threshold():
    detector = InteractivePromptDetector(min_confidence=0.95)

    low_conf_pattern = PromptPattern(
        pattern=r"Continue\?",
        prompt_type=PromptType.OK_PROCEED,
        response="y\n",
        description="Low confidence prompt",
        confidence=0.8,
    )
    detector.patterns = [low_conf_pattern]
    assert detector.detect_prompt("Continue?") is None


def test_detect_prompt_handles_empty_output():
    detector = InteractivePromptDetector()
    assert detector.detect_prompt("") is None
    assert detector.detect_prompt("   ") is None


def test_detect_prompt_warns_on_generic_prompt(reset_logger):
    detector = InteractivePromptDetector()
    pattern = detector.detect_prompt(
        "Please select option:\n1) Foo\n2) Bar\nSelect option:"
    )
    assert pattern is None
    assert any(
        "potential interactive prompt" in call[0] for call in reset_logger.warning_calls
    )


def test_should_auto_respond_handles_password(reset_logger):
    detector = InteractivePromptDetector()
    password_pattern = PromptPattern(
        pattern=r"Password:",
        prompt_type=PromptType.PASSWORD,
        response="secret\n",
        description="Password prompt",
        confidence=1.0,
    )
    assert detector.should_auto_respond(password_pattern) is False
    assert any(
        "Password prompt detected" in call[0] for call in reset_logger.warning_calls
    )


def test_should_auto_respond_disabled():
    detector = InteractivePromptDetector(enable_auto_response=False)
    pattern = PromptPattern(
        pattern=r"\(y/n\)",
        prompt_type=PromptType.YES_NO_CONFIRMATION,
        response="y\n",
        description="Yes/No prompt",
        confidence=1.0,
    )
    assert detector.should_auto_respond(pattern) is False


def test_get_response_returns_pattern_response():
    detector = InteractivePromptDetector()
    pattern = PromptPattern(
        pattern=r"\(y/n\)",
        prompt_type=PromptType.YES_NO_CONFIRMATION,
        response="y\n",
        description="Yes/No prompt",
    )
    assert detector.get_response(pattern) == "y\n"


def test_detect_interactive_prompt_convenience():
    detected, response = detect_interactive_prompt("Do you accept the license terms?")
    assert detected is True
    assert response == "yes\n"


def test_detect_interactive_prompt_returns_false_when_no_prompt():
    detected, response = detect_interactive_prompt("Compilation successful.")
    assert detected is False
    assert response is None


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("npx create-react-app", "npx --yes create-react-app"),
        ("apt install curl", "apt install -y curl"),
        ("docker rm my-container", "docker rm -f my-container"),
    ],
)
def test_suggest_noninteractive_command(command, expected, reset_logger):
    result = suggest_noninteractive_command(command)
    assert result == expected
    assert any(
        "Suggested non-interactive command" in call[0]
        for call in reset_logger.info_calls
    )


@pytest.mark.parametrize(
    "command",
    [
        "apt install -y curl",
        "pip install --yes numpy",
        "rm -f foo.txt",
        "echo hello",
    ],
)
def test_suggest_noninteractive_command_skips_when_already_noninteractive(command):
    assert suggest_noninteractive_command(command) is None


def test_looks_like_prompt_private_method():
    detector = InteractivePromptDetector()
    assert detector._looks_like_prompt("Enter your choice:") is True
    assert detector._looks_like_prompt("All done!") is False


def test_detect_prompt_respects_last_lines_window():
    detector = InteractivePromptDetector()
    lines = [f"line {i}" for i in range(5)]
    lines.append("Ok to proceed? (y)")
    lines.extend([f"after {i}" for i in range(5)])
    output = "\n".join(lines)
    pattern = detector.detect_prompt(output, last_n_lines=8)
    assert pattern is not None
    pattern_none = detector.detect_prompt(output, last_n_lines=3)
    assert pattern_none is None


def test_custom_patterns_can_be_used():
    detector = InteractivePromptDetector()
    custom_pattern = PromptPattern(
        pattern=r"Type YES to continue",
        prompt_type=PromptType.YES_NO_CONFIRMATION,
        response="YES\n",
        description="Custom yes",
        confidence=0.99,
    )
    detector.patterns = [custom_pattern]
    pattern = detector.detect_prompt("Please Type YES to continue")
    assert pattern == custom_pattern


def test_detect_prompt_returns_none_when_confidence_below_threshold():
    detector = InteractivePromptDetector(min_confidence=0.95)
    pattern = PromptPattern(
        pattern=r"Type YES to continue",
        prompt_type=PromptType.YES_NO_CONFIRMATION,
        response="YES\n",
        description="Custom",
        confidence=0.8,
    )
    detector.patterns = [pattern]
    assert detector.detect_prompt("Type YES to continue") is None
