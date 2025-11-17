"""Tests for `forge.llm.metrics`."""

from __future__ import annotations

import copy
import pickle

import pytest

from forge.llm.metrics import Cost, Metrics, TokenUsage


def test_add_cost_and_latency() -> None:
    metrics = Metrics(model_name="demo")
    metrics.add_cost(0.75)
    metrics.add_response_latency(-1.0, response_id="r1")

    assert metrics.accumulated_cost == pytest.approx(0.75)
    assert len(metrics.costs) == 1
    assert metrics.response_latencies[-1].latency == 0.0  # negative latency clamped

    with pytest.raises(ValueError):
        metrics.add_cost(-0.1)


def test_token_usage_accumulation_and_merge() -> None:
    metrics = Metrics(model_name="m1")
    metrics.add_token_usage(
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=3,
        cache_write_tokens=1,
        context_window=100,
        response_id="resp-1",
    )

    usage = metrics.accumulated_token_usage
    assert usage.prompt_tokens == 10
    assert usage.cache_read_tokens == 3

    other = Metrics(model_name="m1")
    other.add_cost(0.5)
    other.add_token_usage(2, 1, 0, 0, 100, "resp-2")
    other.add_response_latency(0.2, "resp-2")

    metrics.merge(other)
    assert metrics.accumulated_cost == pytest.approx(0.5)
    assert metrics.accumulated_token_usage.prompt_tokens == 12
    assert len(metrics.response_latencies) == 1


def test_token_usage_addition_operator() -> None:
    usage_a = TokenUsage(
        prompt_tokens=1,
        completion_tokens=2,
        cache_read_tokens=3,
        cache_write_tokens=4,
        context_window=10,
    )
    usage_b = TokenUsage(
        prompt_tokens=5,
        completion_tokens=7,
        cache_read_tokens=11,
        cache_write_tokens=13,
        context_window=15,
    )
    total = usage_a + usage_b
    assert total.prompt_tokens == 6
    assert total.completion_tokens == 9
    assert total.cache_read_tokens == 14
    assert total.context_window == 15


def test_diff_returns_incremental_metrics() -> None:
    baseline = Metrics(model_name="demo")
    baseline.add_cost(1.0)
    baseline.add_token_usage(10, 5, 0, 0, 100, "r0")

    current = copy.deepcopy(baseline)
    current.add_cost(0.5)
    current.add_token_usage(4, 2, 1, 0, 100, "r1")
    current.add_response_latency(0.3, "r1")

    delta = current.diff(baseline)
    assert delta.accumulated_cost == pytest.approx(0.5)
    assert delta.accumulated_token_usage.prompt_tokens == 4
    assert len(delta.response_latencies) == 1


def test_serialization_cycle() -> None:
    metrics = Metrics(model_name="demo")
    metrics.add_cost(1.25)
    metrics.add_token_usage(3, 4, 0, 0, 50, "resp")

    state = metrics.__getstate__()
    restored = Metrics()
    restored.__setstate__(state)
    assert restored.accumulated_cost == pytest.approx(1.25)

    serialized = pickle.dumps(metrics)
    loaded = pickle.loads(serialized)
    assert isinstance(loaded, Metrics)
    assert loaded.accumulated_cost == pytest.approx(1.25)
