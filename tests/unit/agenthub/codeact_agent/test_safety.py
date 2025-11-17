from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

from forge.agenthub.codeact_agent.safety import CodeActSafetyManager
from forge.events.action import MessageAction


class StubAntiHallucination:
    def __init__(self) -> None:
        self.turn_counter = 0
        self.should_calls: list[tuple[str, bool]] = []
        self.validate_next: tuple[bool, str | None] = (True, None)
        self.injected: list[Any] = []

    def should_enforce_tools(self, message: str, state, strict_mode: bool) -> str:
        self.should_calls.append((message, strict_mode))
        return "tools"

    def validate_response(self, response_text: str, actions: List[Any]) -> tuple[bool, str | None]:
        return self.validate_next

    def inject_verification_commands(self, actions: List[Any], turn: int) -> List[Any]:
        self.injected.append((list(actions), turn))
        return actions + [MessageAction("verify")]


class StubHallucinationDetector:
    def __init__(self) -> None:
        self.next_detection: dict | None = None
        self.calls: list[tuple[str, list[str], list[Any]]] = []

    def detect_text_hallucination(self, response_text: str, tools_called: list[str], actions: List[Any]) -> dict | None:
        self.calls.append((response_text, tools_called, list(actions)))
        return self.next_detection


class DummyAction:
    def __init__(self, name: str | None = None, func_name: str | None = None) -> None:
        self.action = name
        if func_name is not None:
            self.tool_call_metadata = SimpleNamespace(function_name=func_name)


def test_should_enforce_tools_returns_default_without_user_message() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    sentinel_state = object()

    result = manager.should_enforce_tools(last_user_message=None, state=sentinel_state, default="default")
    assert result == "default"


def test_should_enforce_tools_uses_anti_hallucination() -> None:
    anti = StubAntiHallucination()
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)
    state = object()

    assert manager.should_enforce_tools("hi", state, "default") == "tools"
    assert anti.should_calls == [("hi", True)]


def test_should_enforce_tools_returns_default_when_no_anti() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    assert manager.should_enforce_tools("hello", object(), "default") == "default"


def test_should_enforce_tools_handles_exceptions() -> None:
    class ExplodingAnti(StubAntiHallucination):
        def should_enforce_tools(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("boom")

    anti = ExplodingAnti()
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)

    assert manager.should_enforce_tools("msg", object(), "safe") == "safe"


def test_pre_validate_passthrough_without_anti() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    proceed, actions = manager._pre_validate("resp", [MessageAction("hi")])
    assert proceed is True
    assert len(actions) == 1


def test_pre_validate_blocks_invalid_response(monkeypatch: pytest.MonkeyPatch) -> None:
    anti = StubAntiHallucination()
    anti.validate_next = (False, "bad")
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)

    proceed, actions = manager._pre_validate("resp", [])
    assert proceed is False
    assert isinstance(actions[0], MessageAction)
    assert "bad" in actions[0].content


def test_pre_validate_returns_actions_when_valid() -> None:
    anti = StubAntiHallucination()
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)
    proceed, actions = manager._pre_validate("resp", [MessageAction("ok")])
    assert proceed is True
    assert actions[0].content == "ok"


def test_inject_verification_increments_turn_counter() -> None:
    anti = StubAntiHallucination()
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)
    actions = [MessageAction("orig")]

    updated = manager._inject_verification(actions)
    assert anti.turn_counter == 1
    assert updated[-1].content == "verify"


def test_inject_verification_passthrough_without_anti() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    actions = [MessageAction("noop")]
    assert manager._inject_verification(actions) == actions


def test_detect_and_warn_no_detector_returns_actions() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    actions = [MessageAction("ok")]
    assert manager._detect_and_warn("resp", actions) == actions


def test_detect_and_warn_inserts_warning_for_critical_detection() -> None:
    detector = StubHallucinationDetector()
    detector.next_detection = {
        "hallucinated": True,
        "severity": "critical",
        "claimed_operations": ["read db"],
        "missing_tools": ["database.query"],
    }
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=detector)
    actions = [MessageAction("continue")]

    updated = manager._detect_and_warn("resp", actions)
    assert isinstance(updated[0], MessageAction)
    assert "read db" in updated[0].content
    assert "database.query" in updated[0].content


def test_detect_and_warn_skips_non_critical_detection() -> None:
    detector = StubHallucinationDetector()
    detector.next_detection = {"hallucinated": True, "severity": "low"}
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=detector)
    actions = [MessageAction("ok")]

    assert manager._detect_and_warn("resp", actions) == actions


def test_derive_tools_called_uses_metadata_and_action_names() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    actions = [DummyAction(func_name="meta_tool"), DummyAction(name="simple"), DummyAction()]
    tools = manager._derive_tools_called(actions)  # type: ignore[arg-type]
    assert tools == ["meta_tool", "simple"]


def test_tool_function_name_rejects_blank_values() -> None:
    manager = CodeActSafetyManager(anti_hallucination=None, hallucination_detector=None)
    assert manager._tool_function_name(DummyAction(func_name="")) is None
    assert manager._tool_function_name(DummyAction(name="  ")) is None


def test_build_warning_content_lists_claimed_ops_and_missing_tools() -> None:
    content = CodeActSafetyManager._build_warning_content(
        claimed_operations=["op1"],
        missing_tools=["toolA"],
    )
    assert "op1" in content
    assert "toolA" in content


def test_apply_returns_blocked_message_when_prevalidation_fails() -> None:
    anti = StubAntiHallucination()
    anti.validate_next = (False, "blocked")
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=None)
    continue_processing, actions = manager.apply("resp", [])
    assert continue_processing is False
    assert "blocked" in actions[0].content


def test_apply_runs_full_pipeline_when_valid() -> None:
    anti = StubAntiHallucination()
    detector = StubHallucinationDetector()
    detector.next_detection = None
    manager = CodeActSafetyManager(anti_hallucination=anti, hallucination_detector=detector)
    continue_processing, actions = manager.apply("resp", [MessageAction("a")])
    assert continue_processing is True
    assert actions[-1].content == "verify"


def test_should_warn_on_detection_handles_missing_info() -> None:
    assert CodeActSafetyManager._should_warn_on_detection({}) is False

