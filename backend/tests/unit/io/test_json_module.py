"""Unit tests for `forge.io.json` helpers."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from forge.core.exceptions import LLMResponseError
from forge.events.observation.commands import CmdOutputMetadata, CmdOutputObservation
from forge.io import json as forge_json
from forge.llm.metrics import Metrics


@dataclass
class DummyModelResponse:
    """Minimal stand-in for a ModelResponse."""

    payload: dict[str, str]

    def model_dump(self, **kwargs) -> dict[str, str]:
        return self.payload


def test_dumps_handles_custom_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """ForgeJSONEncoder should serialize Forge-specific types without error."""
    event = CmdOutputObservation(content="output", command="ls")
    event.timestamp = dt.datetime(2024, 1, 1, 12, 0, 0)
    metrics = Metrics(model_name="demo")
    metrics.add_cost(0.5)
    metadata = CmdOutputMetadata(exit_code=0, pid=42, working_dir="/tmp")
    response = DummyModelResponse({"message": "ok"})

    payload = {
        "time": dt.datetime(2024, 1, 1, 0, 0, 0),
        "event": event,
        "metrics": metrics,
        "metadata": metadata,
        "response": response,
    }

    dumped = forge_json.dumps(payload)

    serialized = json.loads(dumped)
    assert serialized["time"] == "2024-01-01T00:00:00"
    assert serialized["metadata"]["exit_code"] == 0
    assert serialized["metrics"]["accumulated_cost"] == pytest.approx(0.5)
    assert serialized["response"] == {"message": "ok"}


def test_dumps_respects_custom_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dumps should honour caller-supplied kwargs, including custom encoder."""

    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):  # noqa: D401 - standard JSON hook
            return "custom"

    result = forge_json.dumps({"value": object()}, cls=CustomEncoder)
    assert json.loads(result)["value"] == "custom"


def test_dumps_injects_default_encoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dumps should inject ForgeJSONEncoder when kwargs omit cls."""
    captured: dict[str, object] = {}

    original = json.dumps

    def recording_dumps(obj, **kwargs):
        captured.update(kwargs)
        return original(obj, **kwargs)

    monkeypatch.setattr(forge_json, "json", SimpleNamespace(dumps=recording_dumps))
    result = forge_json.dumps({"key": "value"}, indent=2)
    assert json.loads(result)["key"] == "value"
    assert captured.get("cls") is forge_json.ForgeJSONEncoder


def test_print_json_noop(capsys) -> None:
    """print_json is a no-op placeholder that should not raise."""
    forge_json.print_json({"demo": 1}, pretty=True)
    forge_json.print_json({"demo": 2}, pretty=False)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_loads_valid_json() -> None:
    """Loads should return parsed JSON when input is valid."""
    assert forge_json.loads('{"ok": true}') == {"ok": True}


def test_loads_repairs_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loads should use json_repair when the initial parse fails."""
    monkeypatch.setattr(forge_json, "repair_json", lambda value: '{"fixed": 1}')
    assert forge_json.loads("invalid {json}") == {"fixed": 1}


def test_loads_raises_when_repair_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loads should raise LLMResponseError when repair does not yield an object."""
    monkeypatch.setattr(forge_json, "repair_json", lambda value: value)
    with pytest.raises(LLMResponseError):
        forge_json.loads("no braces here")


def test_encoder_falls_back_to_super(monkeypatch: pytest.MonkeyPatch) -> None:
    """ForgeJSONEncoder should delegate to the base encoder for unknown objects."""
    encoder = forge_json.ForgeJSONEncoder()
    with pytest.raises(TypeError):
        encoder.default(object())


def test_loads_raises_when_repair_json_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loads should raise an LLMResponseError when repaired JSON remains invalid."""
    monkeypatch.setattr(forge_json, "repair_json", lambda value: value)
    invalid = '{"value": "missing closing brace",}'
    with pytest.raises(LLMResponseError):
        forge_json.loads(invalid)
