"""Coverage-focused tests for cost tracking, debug logging, and metrics utilities."""

from __future__ import annotations

import pickle
import sys
import types
from typing import Any
import builtins

import pytest

from forge.llm import cost_tracker, debug_mixin, metrics


class StubLogger:
    """Simple logger stub that records debug messages."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.records: list[str] = []

    def debug(self, message: str, *args: Any) -> None:
        if args:
            message = message % args
        self.records.append(message)

    def error(self, message: str, *args: Any) -> None:
        if args:
            message = message % args
        self.records.append(message)

    def warning(self, message: str, *args: Any) -> None:
        if args:
            message = message % args
        self.records.append(message)

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802 - mirror logging API
        return self.enabled


class DummyMetrics:
    """Minimal metrics stub exposing accumulated_cost attribute."""

    def __init__(self, cost: float) -> None:
        self.accumulated_cost = cost


@pytest.fixture
def quota_module(monkeypatch: pytest.MonkeyPatch):
    """Provide a stub cost quota module that records invocations."""
    original_module = sys.modules.get("forge.server.middleware.cost_quota")
    recorded: list[tuple[str, float]] = []

    def record_llm_cost(user_key: str, cost: float) -> None:
        recorded.append((user_key, cost))

    module = types.ModuleType("forge.server.middleware.cost_quota")
    module.record_llm_cost = record_llm_cost  # type: ignore[attr-defined]
    sys.modules[module.__name__] = module
    yield recorded
    if original_module is not None:
        sys.modules[module.__name__] = original_module
    else:
        module.record_llm_cost = lambda *args, **kwargs: None  # type: ignore[attr-defined]
        sys.modules[module.__name__] = module


def test_record_llm_cost_from_metrics_records_positive_cost(quota_module) -> None:
    metrics_stub = DummyMetrics(cost=1.25)
    cost_tracker.record_llm_cost_from_metrics("user:123", metrics_stub)  # type: ignore[arg-type]
    assert quota_module == [("user:123", 1.25)]


def test_record_llm_cost_from_metrics_ignores_zero_cost(quota_module) -> None:
    metrics_stub = DummyMetrics(cost=0.0)
    cost_tracker.record_llm_cost_from_metrics("user:123", metrics_stub)  # type: ignore[arg-type]
    assert quota_module == []


def test_record_llm_cost_from_metrics_handles_missing_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.modules.pop("forge.server.middleware.cost_quota", None)
    metrics_stub = DummyMetrics(cost=3.3)
    cost_tracker.record_llm_cost_from_metrics("user:123", metrics_stub)  # type: ignore[arg-type]
    # Should not raise or record anything when module import fails


def test_record_llm_cost_from_metrics_logs_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failing_module = types.ModuleType("forge.server.middleware.cost_quota")

    def failing_record(*args, **kwargs):
        raise RuntimeError("quota failed")

    failing_module.record_llm_cost = failing_record  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules, "forge.server.middleware.cost_quota", failing_module
    )
    logger = StubLogger()
    monkeypatch.setattr(cost_tracker, "logger", logger)
    metrics_stub = DummyMetrics(cost=1.0)
    cost_tracker.record_llm_cost_from_metrics("user:err", metrics_stub)  # type: ignore[arg-type]
    assert any("Failed to record LLM cost" in msg for msg in logger.records)


def test_record_llm_cost_from_response_records_cost(
    quota_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Use a known model from MODEL_PRICES in cost_tracker
    model = "gpt-4o"
    # prompt: 1M tokens = $5.00. 1 token = $0.000005
    # Let's use 200,000 tokens to get $1.00
    response = {"usage": {"prompt_tokens": 200000, "completion_tokens": 0}}
    
    cost_tracker.record_llm_cost_from_response(
        "ip:1.2.3.4", response, model=model
    )
    assert quota_module == [("ip:1.2.3.4", 1.0)]


def test_record_llm_cost_from_response_handles_errors(
    quota_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_get_cost(*args, **kwargs):
        raise RuntimeError("boom")

    logger = StubLogger()
    monkeypatch.setattr(cost_tracker, "get_completion_cost", failing_get_cost)
    monkeypatch.setitem(
        sys.modules,
        "forge.server.middleware.cost_quota",
        types.SimpleNamespace(record_llm_cost=lambda *a, **k: None),
    )
    monkeypatch.setattr(cost_tracker, "logger", logger)

    cost_tracker.record_llm_cost_from_response(
        "user:err", {"usage": {"prompt_tokens": 1}}, model="gpt-4o"
    )
    assert any(
        "Failed to record LLM cost from response" in entry for entry in logger.records
    )
    assert quota_module == []


class DummyDebug(debug_mixin.DebugMixin):
    """Concrete subclass for exercising DebugMixin behaviour."""

    def __init__(self, *, debug: bool = False) -> None:
        super().__init__(debug=debug)
        self._vision_enabled = True

    def vision_is_active(self) -> bool:
        return self._vision_enabled

    def set_vision(self, enabled: bool) -> None:
        self._vision_enabled = enabled


@pytest.fixture
def debug_loggers(monkeypatch: pytest.MonkeyPatch):
    """Patch debug mixin loggers and return their stubs."""
    main_logger = StubLogger()
    prompt_logger = StubLogger()
    response_logger = StubLogger()

    monkeypatch.setattr(debug_mixin, "logger", main_logger)
    monkeypatch.setattr(debug_mixin, "llm_prompt_logger", prompt_logger)
    monkeypatch.setattr(debug_mixin, "llm_response_logger", response_logger)
    return main_logger, prompt_logger, response_logger


def test_log_prompt_with_text_and_image(debug_loggers) -> None:
    main_logger, prompt_logger, _ = debug_loggers
    mixin = DummyDebug()
    messages = [
        {"role": "user", "content": "hello"},
        {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": "http://example"}}],
        },
    ]
    mixin.log_prompt(messages)
    assert main_logger.records == []
    assert len(prompt_logger.records) == 1
    assert "hello" in prompt_logger.records[0]
    assert "http://example" in prompt_logger.records[0]


def test_log_prompt_handles_empty_messages(debug_loggers) -> None:
    main_logger, prompt_logger, _ = debug_loggers
    mixin = DummyDebug()
    mixin.log_prompt([])
    assert "No completion messages!" in main_logger.records[-1]
    assert prompt_logger.records == []


def test_log_prompt_respects_logger_level(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled_logger = StubLogger(enabled=False)
    monkeypatch.setattr(debug_mixin, "logger", disabled_logger)
    monkeypatch.setattr(debug_mixin, "llm_prompt_logger", StubLogger())
    mixin = DummyDebug()
    mixin.log_prompt([{"role": "user", "content": "ignored"}])
    assert disabled_logger.records == []


def test_log_prompt_skips_none_content(debug_loggers) -> None:
    main_logger, prompt_logger, _ = debug_loggers
    mixin = DummyDebug()
    mixin.log_prompt([{"role": "user", "content": None}])
    assert "No completion messages!" in main_logger.records[-1]
    assert prompt_logger.records == []


def test_log_response_with_tool_calls(debug_loggers) -> None:
    _, _, response_logger = debug_loggers
    mixin = DummyDebug()
    tool_call = types.SimpleNamespace(
        function=types.SimpleNamespace(name="lookup", arguments='{"arg": 1}')
    )
    response = {
        "choices": [
            {
                "message": {
                    "content": "answer",
                    "tool_calls": [tool_call],
                }
            }
        ]
    }
    mixin.log_response(response)
    assert any("Function call: lookup" in entry for entry in response_logger.records)


def test_log_response_when_debug_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled_logger = StubLogger(enabled=False)
    monkeypatch.setattr(debug_mixin, "logger", disabled_logger)
    mixin = DummyDebug()
    mixin.log_response(
        {"choices": [{"message": {"content": "no-log", "tool_calls": []}}]}
    )
    assert disabled_logger.records == []


def test_format_content_element_handles_non_dict(debug_loggers) -> None:
    mixin = DummyDebug()
    mixin.set_vision(False)
    assert mixin._format_content_element("plain") == "plain"


def test_debug_mixin_requires_vision_override() -> None:
    class Bare(debug_mixin.DebugMixin):
        pass

    bare = Bare()
    with pytest.raises(NotImplementedError):
        bare.vision_is_active()


def test_metrics_add_cost_and_latency() -> None:
    m = metrics.Metrics(model_name="demo")
    m.add_cost(1.0)
    m.add_response_latency(-5.0, "resp-1")
    assert pytest.approx(m.accumulated_cost) == 1.0
    assert m.costs[-1].cost == 1.0
    assert m.response_latencies[-1].latency == 0.0  # negative values clamped

    with pytest.raises(ValueError):
        m.add_cost(-0.1)

    with pytest.raises(ValueError):
        m.accumulated_cost = -1.0

    m.accumulated_cost = 2.5
    assert m.accumulated_cost == 2.5


def test_metrics_token_usage_and_merge_diff() -> None:
    m1 = metrics.Metrics(model_name="demo")
    m1.add_token_usage(10, 5, 1, 2, 1000, "resp-a")
    m1.add_cost(0.5)

    m2 = metrics.Metrics(model_name="demo")
    m2.add_token_usage(3, 7, 0, 0, 800, "resp-b")
    m2.add_cost(0.3)
    m2.max_budget_per_task = 5.0

    m_combined = m1.copy()
    m_combined.merge(m2)
    assert m_combined.accumulated_cost == pytest.approx(0.8)
    assert len(m_combined.token_usages) == 2
    assert m_combined.max_budget_per_task == 5.0

    baseline = m1.copy()
    baseline.add_cost(0.2)
    diff = m_combined.diff(baseline)
    assert diff.accumulated_cost == pytest.approx(
        m_combined.accumulated_cost - baseline.accumulated_cost
    )
    assert diff.accumulated_token_usage.prompt_tokens >= 0


def test_metrics_lazy_property_defaults() -> None:
    m = metrics.Metrics()
    del m.__dict__["_response_latencies"]
    del m.__dict__["_token_usages"]
    del m.__dict__["_accumulated_token_usage"]
    assert m.response_latencies == []
    assert m.token_usages == []
    assert m.accumulated_token_usage.prompt_tokens == 0


def test_metrics_diff_without_costs() -> None:
    m = metrics.Metrics()
    empty = metrics.Metrics()
    m.add_cost(0.1)
    result = m.diff(empty)
    assert result._costs == m._costs


def test_metrics_serialization_roundtrip() -> None:
    m = metrics.Metrics(model_name="demo")
    m.add_token_usage(1, 2, 0, 0, 500, "resp-1")
    m.add_response_latency(0.5, "resp-1")
    m.add_cost(0.05)
    m.max_budget_per_task = 2.0

    state = m.__getstate__()
    restored = metrics.Metrics(model_name="other")
    restored.__setstate__(state)
    assert restored.accumulated_cost == m.accumulated_cost
    assert restored.max_budget_per_task == 2.0
    assert restored.token_usages[-1].prompt_tokens == 1

    pickled = pickle.loads(pickle.dumps(m))
    assert pickled.get() == m.get()

    text = m.log()
    assert "accumulated_cost" in text
    assert repr(m).startswith("Metrics(")
