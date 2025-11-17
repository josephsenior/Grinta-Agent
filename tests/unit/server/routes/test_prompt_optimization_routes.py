"""Unit tests for prompt optimization routes."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
import json

import pytest

from fastapi import HTTPException

from forge.server.routes import prompt_optimization as prompt_routes
from forge.server.session.session import Session


class DummyMetric:
    def __init__(self, score: float = 0.5):
        self.success_rate = 0.8
        self.avg_execution_time = 120.0
        self.error_rate = 0.1
        self.avg_token_cost = 0.2
        self.sample_count = 10
        self.composite_score = score
        self.last_updated = datetime.now()


class DummyVariant:
    def __init__(self, variant_id: str, version: int = 1):
        self.id = variant_id
        self.content = f"content-{variant_id}"
        self.version = version
        self.parent_id = None
        self.created_at = datetime.now()
        self.metadata = {"source": "test"}


class DummyRegistry:
    def __init__(self):
        self._prompts = {
            "prompt1": [DummyVariant("v1"), DummyVariant("v2")],
            "prompt2": [DummyVariant("v3")],
        }
        self.active = {
            "prompt1": self._prompts["prompt1"][0],
            "prompt2": self._prompts["prompt2"][0],
        }
        self.categories = {
            "prompt1": SimpleNamespace(value="agent"),
            "prompt2": SimpleNamespace(value="tool"),
        }
        self.switched_to = None

    def get_all_prompt_ids(self):
        return list(self._prompts.keys())

    def get_all_variants(self, prompt_id):
        return self._prompts.get(prompt_id, [])

    def get_active_variant(self, prompt_id):
        return self.active.get(prompt_id)

    def get_prompt_category(self, prompt_id):
        return self.categories.get(prompt_id)

    def get_variant(self, prompt_id, variant_id):
        for variant in self._prompts.get(prompt_id, []):
            if variant.id == variant_id:
                return variant
        return None

    def set_active_variant(self, prompt_id, variant_id):
        variant = self.get_variant(prompt_id, variant_id)
        if variant:
            self.active[prompt_id] = variant
            self.switched_to = (prompt_id, variant_id)


class DummyTracker:
    def __init__(self):
        self._metrics = {
            "prompt1": {"v1": DummyMetric(0.9), "v2": DummyMetric(0.7)},
            "prompt2": {"v3": DummyMetric(0.5)},
        }

    def get_all_metrics(self, prompt_id):
        return self._metrics.get(prompt_id, {})


class DummyStorage:
    def __init__(self):
        self.saved = False

    def auto_save(self):
        self.saved = True


class DummyConfig:
    def __init__(self):
        self.ab_split_ratio = 0.5
        self.min_samples_for_switch = 5
        self.enable_evolution = True

    def dict(self):
        return {
            "ab_split_ratio": self.ab_split_ratio,
            "min_samples_for_switch": self.min_samples_for_switch,
            "enable_evolution": self.enable_evolution,
        }


class DummyOptimizer:
    def __init__(self):
        self.config = DummyConfig()


def make_prompt_optimizer(enable_evolution: bool = True):
    optimizer = DummyOptimizer()
    optimizer.config.enable_evolution = enable_evolution
    return {
        "optimizer": optimizer,
        "registry": DummyRegistry(),
        "tracker": DummyTracker(),
        "storage": DummyStorage(),
        "config": DummyConfig(),
    }


def make_session(prompt_optimizer: Any = None) -> Session:
    session = SimpleNamespace()
    session.agent = SimpleNamespace(prompt_optimizer=prompt_optimizer)
    return cast(Session, session)


def test_get_prompt_optimizer_agent():
    session = make_session(prompt_optimizer={"test": True})
    result = prompt_routes.get_prompt_optimizer(session)
    assert result == {"test": True}


def test_get_prompt_optimizer_orchestrator():
    session = cast(
        Session,
        SimpleNamespace(
            agent=SimpleNamespace(),
            orchestrator=SimpleNamespace(prompt_optimizer={"ok": True}),
        ),
    )
    result = prompt_routes.get_prompt_optimizer(session)
    assert result == {"ok": True}


def test_get_prompt_optimizer_not_available():
    with pytest.raises(HTTPException) as exc:
        prompt_routes.get_prompt_optimizer(cast(Session, SimpleNamespace()))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_optimization_status_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    summary = await prompt_routes.get_optimization_status(
        make_session(prompt_optimizer)
    )
    assert summary.total_prompts == 2
    assert summary.optimized_prompts == 1
    assert summary.total_variants == 3


@pytest.mark.asyncio
async def test_get_optimization_status_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: {})
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_optimization_status(make_session({}))
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_optimization_status_error(monkeypatch):
    def failing_optimizer(session):
        raise RuntimeError("fail")

    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", failing_optimizer)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_optimization_status(make_session())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_all_prompts_status_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    status_list = await prompt_routes.get_all_prompts_status(
        make_session(prompt_optimizer)
    )
    assert len(status_list) == 2
    assert status_list[0].total_variants >= 1


@pytest.mark.asyncio
async def test_get_all_prompts_status_error(monkeypatch):
    monkeypatch.setattr(
        prompt_routes,
        "get_prompt_optimizer",
        lambda session: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_all_prompts_status(make_session())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_all_prompts_status_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_all_prompts_status(make_session())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_prompt_variants_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    variants = await prompt_routes.get_prompt_variants(
        "prompt1", make_session(prompt_optimizer)
    )
    assert len(variants) == 2
    assert variants[0].id == "v1"


@pytest.mark.asyncio
async def test_get_prompt_variants_not_found(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_variants(
            "missing", make_session(prompt_optimizer)
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_variants_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_variants("prompt1", make_session())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_metrics_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    metrics = await prompt_routes.get_prompt_metrics(
        "prompt1", make_session(prompt_optimizer)
    )
    assert "v1" in metrics and metrics["v1"].sample_count == 10


@pytest.mark.asyncio
async def test_get_prompt_metrics_not_found(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    prompt_optimizer["tracker"]._metrics = {}
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_metrics(
            "prompt1", make_session(prompt_optimizer)
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_metrics_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_metrics("prompt1", make_session())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_switch_active_variant_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    registry = prompt_optimizer["registry"]
    storage = prompt_optimizer["storage"]
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    response = await prompt_routes.switch_active_variant(
        "prompt1",
        prompt_routes.VariantSwitchRequest(prompt_id="prompt1", variant_id="v2"),
        make_session(prompt_optimizer),
    )
    assert registry.switched_to == ("prompt1", "v2")
    assert storage.saved is True
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_switch_active_variant_missing(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.switch_active_variant(
            "prompt1",
            prompt_routes.VariantSwitchRequest(
                prompt_id="prompt1", variant_id="missing"
            ),
            make_session(prompt_optimizer),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_switch_active_variant_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.switch_active_variant(
            "prompt1",
            prompt_routes.VariantSwitchRequest(prompt_id="prompt1", variant_id="v1"),
            make_session(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_switch_active_variant_internal_error(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()

    def failing_set_active(prompt_id, variant_id):
        raise RuntimeError("set failed")

    prompt_optimizer["registry"].set_active_variant = failing_set_active
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )

    with pytest.raises(HTTPException) as exc:
        await prompt_routes.switch_active_variant(
            "prompt1",
            prompt_routes.VariantSwitchRequest(prompt_id="prompt1", variant_id="v1"),
            make_session(prompt_optimizer),
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_evolve_prompt_success(monkeypatch):
    prompt_optimizer = make_prompt_optimizer(enable_evolution=True)
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    response = await prompt_routes.evolve_prompt(
        "prompt1",
        prompt_routes.EvolutionRequest(prompt_id="prompt1", max_variants=2),
        make_session(prompt_optimizer),
    )
    data = json.loads(response.body)
    assert data["message"].startswith("Evolution triggered")
    assert len(data["new_variants"]) == 2


@pytest.mark.asyncio
async def test_evolve_prompt_disabled(monkeypatch):
    prompt_optimizer = make_prompt_optimizer(enable_evolution=False)
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.evolve_prompt(
            "prompt1",
            prompt_routes.EvolutionRequest(prompt_id="prompt1"),
            make_session(prompt_optimizer),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_evolve_prompt_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.evolve_prompt(
            "prompt1",
            prompt_routes.EvolutionRequest(prompt_id="prompt1"),
            make_session(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_evolve_prompt_internal_error(monkeypatch):
    prompt_optimizer = make_prompt_optimizer(enable_evolution=True)

    def failing_optimizer(session):
        return {
            "optimizer": SimpleNamespace(config=SimpleNamespace(enable_evolution=True))
        }

    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", failing_optimizer)
    monkeypatch.setattr(
        prompt_routes,
        "datetime",
        SimpleNamespace(now=lambda: (_ for _ in ()).throw(RuntimeError("time fail"))),
    )

    with pytest.raises(HTTPException) as exc:
        await prompt_routes.evolve_prompt(
            "prompt1",
            prompt_routes.EvolutionRequest(prompt_id="prompt1"),
            make_session(prompt_optimizer),
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_optimization_analytics(monkeypatch):
    summary = prompt_routes.OptimizationSummary(
        total_prompts=1,
        optimized_prompts=1,
        total_variants=2,
        active_ab_tests=1,
        avg_improvement=0.2,
        total_savings=10.0,
        last_updated=datetime.now(),
    )

    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )

    async def fake_status(session):
        return summary

    monkeypatch.setattr(prompt_routes, "get_optimization_status", fake_status)

    analytics = await prompt_routes.get_optimization_analytics(
        "month", make_session(prompt_optimizer)
    )
    assert analytics["summary"]["total_prompts"] == 1
    assert analytics["period"] == "month"


@pytest.mark.asyncio
async def test_get_optimization_analytics_error(monkeypatch):
    monkeypatch.setattr(
        prompt_routes,
        "get_prompt_optimizer",
        lambda session: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_optimization_analytics("week", make_session())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_optimization_analytics_period_variants(monkeypatch):
    summary = prompt_routes.OptimizationSummary(
        total_prompts=2,
        optimized_prompts=1,
        total_variants=3,
        active_ab_tests=1,
        avg_improvement=0.3,
        total_savings=5.0,
        last_updated=datetime.now(),
    )

    async def fake_status(session):
        return summary

    prompt_optimizer = make_prompt_optimizer()
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    monkeypatch.setattr(prompt_routes, "get_optimization_status", fake_status)

    result_day = await prompt_routes.get_optimization_analytics(
        "day", make_session(prompt_optimizer)
    )
    result_unknown = await prompt_routes.get_optimization_analytics(
        "unknown", make_session(prompt_optimizer)
    )
    result_week = await prompt_routes.get_optimization_analytics(
        "week", make_session(prompt_optimizer)
    )
    assert result_day["period"] == "day"
    assert result_unknown["period"] == "unknown"
    assert result_week["period"] == "week"


@pytest.mark.asyncio
async def test_get_optimization_analytics_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_optimization_analytics("week", make_session())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_optimization_analytics_http_exception(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()

    async def raise_http(session):
        raise HTTPException(status_code=418, detail="teapot")

    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )
    monkeypatch.setattr(prompt_routes, "get_optimization_status", raise_http)

    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_optimization_analytics(
            "week", make_session(prompt_optimizer)
        )
    assert exc.value.status_code == 418


@pytest.mark.asyncio
async def test_update_optimization_config(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    config = prompt_optimizer["config"]
    storage = prompt_optimizer["storage"]
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )

    payload = prompt_routes.OptimizationConfigUpdate.model_validate(
        {
            "ab_split_ratio": 0.7,
            "min_samples_for_switch": 5,
            "confidence_threshold": 0.8,
            "success_weight": 0.3,
            "time_weight": 0.2,
            "error_weight": 0.1,
            "cost_weight": 0.1,
            "enable_evolution": False,
            "evolution_threshold": 0.5,
            "max_variants_per_prompt": 4,
        },
    )
    response = await prompt_routes.update_optimization_config(
        payload, make_session(prompt_optimizer)
    )
    data = json.loads(response.body)
    assert config.ab_split_ratio == 0.7
    assert config.enable_evolution is False
    assert storage.saved is True
    assert "ab_split_ratio" in data["updated_fields"]


@pytest.mark.asyncio
async def test_update_optimization_config_error(monkeypatch):
    monkeypatch.setattr(
        prompt_routes,
        "get_prompt_optimizer",
        lambda session: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.update_optimization_config(
            prompt_routes.OptimizationConfigUpdate.model_validate({}),
            make_session(),
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_optimization_config_not_enabled(monkeypatch):
    monkeypatch.setattr(prompt_routes, "get_prompt_optimizer", lambda session: None)
    with pytest.raises(HTTPException) as exc:
        await prompt_routes.update_optimization_config(
            prompt_routes.OptimizationConfigUpdate.model_validate(
                {
                    "ab_split_ratio": 0.6,
                    "min_samples_for_switch": 5,
                    "confidence_threshold": 0.8,
                    "success_weight": 0.3,
                    "time_weight": 0.2,
                    "error_weight": 0.1,
                    "cost_weight": 0.1,
                    "enable_evolution": True,
                    "evolution_threshold": 0.4,
                    "max_variants_per_prompt": 4,
                },
            ),
            make_session(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_metrics_handles_exception(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()
    tracker = prompt_optimizer["tracker"]

    def failing_metrics(prompt_id):
        raise RuntimeError("tracker fail")

    tracker.get_all_metrics = failing_metrics
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )

    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_metrics(
            "prompt1", make_session(prompt_optimizer)
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_prompt_variants_handles_exception(monkeypatch):
    prompt_optimizer = make_prompt_optimizer()

    def failing_variants(prompt_id):
        raise RuntimeError("registry fail")

    prompt_optimizer["registry"].get_all_variants = failing_variants
    monkeypatch.setattr(
        prompt_routes, "get_prompt_optimizer", lambda session: prompt_optimizer
    )

    with pytest.raises(HTTPException) as exc:
        await prompt_routes.get_prompt_variants(
            "prompt1", make_session(prompt_optimizer)
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_health_check():
    response = await prompt_routes.health_check()
    assert response.status_code == 200
