"""Tests for hallucination detection heuristics."""

from __future__ import annotations

from forge.agenthub.codeact_agent.hallucination_detector import HallucinationDetector
from forge.events.action import FileEditAction


def test_detection_disabled_returns_false() -> None:
    detector = HallucinationDetector()
    detector.detection_enabled = False
    result = detector.detect_text_hallucination("I created file.py", [], [])
    assert result == {"hallucinated": False}


def test_file_creation_hallucination_detected() -> None:
    detector = HallucinationDetector()
    text = "I created src/app.py"
    result = detector.detect_text_hallucination(text, [], [])
    assert result["hallucinated"] is True
    assert "src/app.py" in result["claimed_operations"][0]
    assert "edit_file" in result["missing_tools"]
    assert result["severity"] == "critical"


def test_no_hallucination_when_tool_called() -> None:
    detector = HallucinationDetector()
    text = "I created the file src/app.py"
    result = detector.detect_text_hallucination(
        text, ["edit_file"], [FileEditAction(path="src/app.py")]
    )
    assert result["hallucinated"] is False


def test_file_edit_hallucination_detected() -> None:
    detector = HallucinationDetector()
    text = "I edited src/utils/helpers.py to add logging."
    result = detector.detect_text_hallucination(text, [], [])
    assert result["hallucinated"]
    assert any("file_edit" == detail["type"] for detail in result["details"])
    assert result["severity"] in {"high", "critical"}


def test_code_execution_hallucination_detected() -> None:
    detector = HallucinationDetector()
    text = "I ran the unit tests to ensure everything passes."
    result = detector.detect_text_hallucination(text, [], [])
    assert result["hallucinated"]
    assert result["severity"] in {
        "medium",
        "high",
        "critical",
        "low",
    }  # severity depends on confidence
    assert "code_execution" in [detail["type"] for detail in result["details"]]


def test_severity_scaling_with_multiple_events() -> None:
    detector = HallucinationDetector()
    text = "I created src/app.py. Then I edited src/utils.py and finally I ran pytest."
    result = detector.detect_text_hallucination(text, [], [])
    assert result["hallucinated"]
    assert result["severity"] in {"high", "critical"}
    # should include different claim types
    types = {detail["type"] for detail in result["details"]}
    assert {"file_creation", "file_edit", "code_execution"}.intersection(types)


def test_generate_correction_prompt_contains_details() -> None:
    detector = HallucinationDetector()
    detection = {
        "hallucinated": True,
        "claimed_operations": ["I created src/app.py"],
        "missing_tools": ["edit_file"],
    }
    prompt = detector.generate_correction_prompt(detection, "Create the app.")
    assert "HALLUCINATION DETECTED" in prompt
    assert "src/app.py" in prompt
    assert "edit_file" in prompt


def test_generate_correction_prompt_no_hallucination_returns_empty() -> None:
    detector = HallucinationDetector()
    prompt = detector.generate_correction_prompt({"hallucinated": False}, "Do nothing.")
    assert prompt == ""
