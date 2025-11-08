"""Tests for `forge.llm.cost_tracker`."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from forge.llm import cost_tracker
from forge.llm.metrics import Metrics


def test_record_llm_cost_from_metrics_handles_missing_dependency(monkeypatch) -> None:
    metrics = Metrics()
    metrics.add_cost(0.75)
    # No forge.server.middleware.cost_quota module available -> should not raise
    cost_tracker.record_llm_cost_from_metrics("user:1", metrics)


def test_record_llm_cost_from_metrics_invokes_quota(monkeypatch) -> None:
    recorded = {}

    def fake_record(user, cost):
        recorded["call"] = (user, cost)

    fake_module = SimpleNamespace(record_llm_cost=fake_record)
    monkeypatch.setitem(sys.modules, "forge.server.middleware.cost_quota", fake_module)

    metrics = Metrics()
    metrics.add_cost(1.5)
    cost_tracker.record_llm_cost_from_metrics("user:2", metrics)
    assert recorded["call"] == ("user:2", 1.5)


def test_record_llm_cost_from_response(monkeypatch) -> None:
    calls = {}

    def fake_record(user, cost):
        calls["record"] = (user, cost)

    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.record_llm_cost",
        fake_record,
        raising=False,
    )

    monkeypatch.setattr(
        "litellm.completion_cost",
        lambda completion_response: completion_response["usage"]["cost"],
        raising=False,
    )
    monkeypatch.setattr(
        cost_tracker,
        "logger",
        SimpleNamespace(debug=lambda *args, **kwargs: None, error=lambda *args, **kwargs: None),
    )

    response = {"usage": {"cost": 2.0}}
    cost_tracker.record_llm_cost_from_response("user:3", response)
    assert calls["record"] == ("user:3", 2.0)

