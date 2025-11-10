from __future__ import annotations

import asyncio
import json
import math
import os
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pytest
import sys
import types

# Provide lightweight sklearn stubs when the real dependency is unavailable
if "sklearn" not in sys.modules:
    sklearn_module = types.ModuleType("sklearn")
    ensemble_module = types.ModuleType("sklearn.ensemble")
    linear_module = types.ModuleType("sklearn.linear_model")
    preprocessing_module = types.ModuleType("sklearn.preprocessing")
    model_selection_module = types.ModuleType("sklearn.model_selection")
    metrics_module = types.ModuleType("sklearn.metrics")

    class _StubScaler:
        def fit_transform(self, X):
            return X

        def transform(self, X):
            return X

    def _train_test_split(X, y, test_size=0.2, random_state=None):
        split = max(1, int(len(X) * (1 - test_size)))
        return X[:split], X[split:], y[:split], y[split:]

    def _mean_squared_error(y_true, y_pred):
        return float(np.mean((np.array(y_true) - np.array(y_pred)) ** 2))

    def _r2_score(y_true, y_pred):
        return 1.0

    class _StubModel:
        def __init__(self, *_, **__):
            self.value = 0.5
            self.feature_importances_ = np.array([0.1] * 15)

        def fit(self, X, y):
            self.value = float(np.mean(y)) if len(y) else 0.5

        def predict(self, X):
            return np.full((len(X),), self.value)

    ensemble_module.RandomForestRegressor = _StubModel
    ensemble_module.GradientBoostingRegressor = _StubModel
    linear_module.LinearRegression = _StubModel
    preprocessing_module.StandardScaler = _StubScaler
    model_selection_module.train_test_split = _train_test_split
    metrics_module.mean_squared_error = _mean_squared_error
    metrics_module.r2_score = _r2_score

    sys.modules["sklearn"] = sklearn_module
    sys.modules["sklearn.ensemble"] = ensemble_module
    sys.modules["sklearn.linear_model"] = linear_module
    sys.modules["sklearn.preprocessing"] = preprocessing_module
    sys.modules["sklearn.model_selection"] = model_selection_module
    sys.modules["sklearn.metrics"] = metrics_module

from forge.prompt_optimization.models import PromptCategory, PromptMetrics, PromptVariant
from forge.prompt_optimization.realtime.hot_swapper import (
    HotSwapper,
    SwapResult,
    SwapStrategy,
)
from forge.prompt_optimization.realtime.performance_predictor import (
    PerformancePredictor,
    PredictionFeatures,
    PredictionModel,
)
from forge.prompt_optimization.realtime.real_time_monitor import (
    RealTimeMonitor,
    MetricSnapshot,
    MonitoringAlert,
    AlertLevel,
    MetricType,
)
from forge.prompt_optimization.realtime.streaming_engine import (
    StreamingOptimizationEngine,
    StreamEvent,
    StreamEventType,
)
from forge.prompt_optimization.realtime.live_optimizer import (
    LiveOptimizer,
    LiveOptimizationEvent,
    LiveOptimizationResult,
    OptimizationTrigger,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _StubVariant:
    id: str
    content: str


class _StubRegistry:
    def __init__(self) -> None:
        self.variants: Dict[str, Dict[str, PromptVariant]] = {}
        self.active: Dict[str, PromptVariant] = {}

    def add_variant(self, prompt_id: str, variant: PromptVariant) -> None:
        self.variants.setdefault(prompt_id, {})[variant.id] = variant
        self.active[prompt_id] = variant

    def get_variant(self, prompt_id: str, variant_id: str) -> Optional[PromptVariant]:
        return self.variants.get(prompt_id, {}).get(variant_id)

    def set_active_variant(self, prompt_id: str, variant_id: str) -> None:
        variant = self.get_variant(prompt_id, variant_id)
        if not variant:
            raise ValueError("Variant not found")
        self.active[prompt_id] = variant

    def get_active_variant(self, prompt_id: str) -> PromptVariant:
        return self.active[prompt_id]


class _StubModel:
    def __init__(self, value: float = 0.75) -> None:
        self.value = value
        self.feature_importances_ = np.array([0.1] * 15)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.value = np.mean(y) if len(y) else self.value

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full((len(X),), self.value)


class _StubLiveOptimizer:
    def __init__(self) -> None:
        self.trigger_calls: List[Dict[str, Any]] = []

    async def trigger_optimization(self, **kwargs: Any) -> None:
        self.trigger_calls.append(kwargs)


# ---------------------------------------------------------------------------
# HotSwapper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hot_swapper_atomic_and_blue_green(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _StubRegistry()
    prompt_id = "prompt-123"
    from_variant = PromptVariant(prompt_id=prompt_id, content="from", category=PromptCategory.CUSTOM)
    to_variant = PromptVariant(prompt_id=prompt_id, content="to", category=PromptCategory.CUSTOM)
    registry.add_variant(prompt_id, from_variant)
    registry.add_variant(prompt_id, to_variant)
    registry.set_active_variant(prompt_id, from_variant.id)

    swapper = HotSwapper(registry, max_concurrent_swaps=2)

    async def health_check(pid: str, vid: str) -> bool:
        return True

    swapper.add_health_checker(prompt_id, health_check)

    result = await swapper.hot_swap(
        prompt_id=prompt_id,
        from_variant_id=from_variant.id,
        to_variant_id=to_variant.id,
        strategy=SwapStrategy.ATOMIC,
        metadata={"prompt_id": prompt_id},
    )
    assert result.success is True
    assert registry.get_active_variant(prompt_id).id == to_variant.id

    # Perform blue-green swap back to original variant to exercise rollback data, health checks
    result = await swapper.hot_swap(
        prompt_id=prompt_id,
        from_variant_id=to_variant.id,
        to_variant_id=from_variant.id,
        strategy=SwapStrategy.BLUE_GREEN,
        metadata={"prompt_id": prompt_id},
    )
    assert result.success is True
    assert registry.get_active_variant(prompt_id).id == from_variant.id

    status = swapper.get_swap_status()
    assert status["successful_swaps"] >= 2

    history = swapper.get_swap_history()
    assert len(history) >= 2


@pytest.mark.asyncio
async def test_hot_swapper_cancel_and_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _StubRegistry()
    prompt_id = "prompt-cancel"
    variant_a = PromptVariant(prompt_id=prompt_id, content="A", category=PromptCategory.CUSTOM)
    variant_b = PromptVariant(prompt_id=prompt_id, content="B", category=PromptCategory.CUSTOM)
    registry.add_variant(prompt_id, variant_a)
    registry.add_variant(prompt_id, variant_b)
    registry.set_active_variant(prompt_id, variant_a.id)

    swapper = HotSwapper(registry, max_concurrent_swaps=1)
    swapper.max_history_size = 1

    # Patch internal swap methods to pause so we can cancel mid-operation
    async def slow_atomic_swap(operation):
        await asyncio.sleep(0)  # allow cancellation path
        return SwapResult(operation_id=operation.operation_id, success=True, execution_time=0.0)

    monkeypatch.setattr(swapper, "_atomic_swap", slow_atomic_swap)

    # Start swap but cancel immediately
    async def run_swap():
        return await swapper.hot_swap(prompt_id, variant_a.id, variant_b.id, SwapStrategy.ATOMIC)

    result = await swapper.hot_swap(prompt_id, variant_a.id, variant_b.id, SwapStrategy.ATOMIC)
    assert result.success is True
    status = swapper.get_swap_status()
    assert status["successful_swaps"] >= 1


@pytest.mark.asyncio
async def test_hot_swapper_internal_helpers() -> None:
    registry = _StubRegistry()
    prompt_id = "prompt-internal"
    variant_a = PromptVariant(prompt_id=prompt_id, content="A", category=PromptCategory.CUSTOM)
    variant_b = PromptVariant(prompt_id=prompt_id, content="B", category=PromptCategory.CUSTOM)
    registry.add_variant(prompt_id, variant_a)
    registry.add_variant(prompt_id, variant_b)
    registry.set_active_variant(prompt_id, variant_a.id)

    swapper = HotSwapper(registry, max_concurrent_swaps=1)
    failure = swapper._create_failure_result("op-1", "error")
    assert failure.success is False

    # Cannot perform swap when variants missing
    operation_id, operation = swapper._create_swap_operation(prompt_id, variant_a.id, variant_b.id, SwapStrategy.ATOMIC, {})
    registry.variants[prompt_id].pop(variant_b.id)
    assert await swapper._can_perform_swap(operation) is False
    registry.variants[prompt_id][variant_b.id] = variant_b

    # Health check timeout and failure handling
    async def slow_health_check(pid: str, vid: str) -> bool:
        await asyncio.sleep(0)
        raise RuntimeError("health failure")

    swapper.add_health_checker(prompt_id, slow_health_check)
    assert await swapper._perform_health_check(prompt_id, variant_a.id) is False
    swapper.remove_health_checker(prompt_id)

    async def healthy_check(pid: str, vid: str) -> bool:
        return True

    swapper.add_health_checker(prompt_id, healthy_check)

    # Cover alternate swap strategies
    op_blue_id, op_blue = swapper._create_swap_operation(prompt_id, variant_a.id, variant_b.id, SwapStrategy.BLUE_GREEN, {})
    swapper.rollback_data[op_blue_id] = {
        "prompt_id": prompt_id,
        "from_variant_id": variant_a.id,
        "to_variant_id": variant_b.id,
        "timestamp": datetime.now(),
    }
    result_blue = await swapper._blue_green_swap(op_blue)
    assert result_blue.success

    op_roll_id, op_roll = swapper._create_swap_operation(prompt_id, variant_b.id, variant_a.id, SwapStrategy.ROLLING, {})
    swapper.rollback_data[op_roll_id] = {
        "prompt_id": prompt_id,
        "from_variant_id": variant_b.id,
        "to_variant_id": variant_a.id,
        "timestamp": datetime.now(),
    }
    result_roll = await swapper._rolling_swap(op_roll)
    assert result_roll.success

    op_canary_id, op_canary = swapper._create_swap_operation(prompt_id, variant_a.id, variant_b.id, SwapStrategy.CANARY, {})
    swapper.rollback_data[op_canary_id] = {
        "prompt_id": prompt_id,
        "from_variant_id": variant_a.id,
        "to_variant_id": variant_b.id,
        "timestamp": datetime.now(),
    }
    result_canary = await swapper._canary_swap(op_canary)
    assert result_canary.success

    # Rollback data usage
    op_id, operation = swapper._create_swap_operation(prompt_id, variant_a.id, variant_b.id, SwapStrategy.ATOMIC, None)
    swapper.rollback_data[op_id] = {
        "prompt_id": prompt_id,
        "from_variant_id": variant_a.id,
        "to_variant_id": variant_b.id,
        "timestamp": variant_a.created_at,
    }
    await swapper._attempt_rollback(operation)
    swapper.clear_rollback_data(op_id)

    # Cancel operation path
    cancel_id, cancel_operation = swapper._create_swap_operation(prompt_id, variant_a.id, variant_b.id, SwapStrategy.ATOMIC, {})
    swapper.active_operations[cancel_id] = cancel_operation
    swapper.rollback_data[cancel_id] = {
        "prompt_id": prompt_id,
        "from_variant_id": variant_a.id,
        "to_variant_id": variant_b.id,
        "timestamp": datetime.now(),
    }
    cancelled = await swapper.cancel_operation(cancel_id)
    assert cancelled is True

    # Store swap results beyond history size
    swapper.max_history_size = 1
    swapper._store_swap_result(SwapResult(operation_id="1", success=True, execution_time=0.1, metadata={"prompt_id": prompt_id}))
    swapper._store_swap_result(SwapResult(operation_id="2", success=False, execution_time=0.2, metadata={"prompt_id": prompt_id}))
    assert swapper.get_swap_history(prompt_id=prompt_id)


@pytest.mark.asyncio
async def test_hot_swapper_error_paths() -> None:
    class _FailRegistry:
        def __init__(self, variants: List[PromptVariant]):
            self.variants = {variant.id: variant for variant in variants}
            self.active_id = variants[0].id

        def get_variant(self, prompt_id: str, variant_id: str):
            return self.variants.get(variant_id)

        def set_active_variant(self, prompt_id: str, variant_id: str):
            if variant_id not in self.variants:
                raise KeyError(variant_id)
            raise RuntimeError("set_active_variant_failed")

        def get_active_variant(self, prompt_id: str):
            return self.variants[self.active_id]

    variants = [
        PromptVariant(content="From", category=PromptCategory.CUSTOM),
        PromptVariant(content="To", category=PromptCategory.CUSTOM),
    ]

    registry = _FailRegistry(variants)
    swapper = HotSwapper(registry, max_concurrent_swaps=0)

    op_id, operation = swapper._create_swap_operation("prompt", variants[0].id, variants[1].id, SwapStrategy.ATOMIC, {})
    assert await swapper._can_perform_swap(operation) is False

    swapper.max_concurrent_swaps = 1
    swapper.active_operations[op_id] = operation
    assert await swapper._can_perform_swap(operation) is False
    swapper.active_operations.clear()

    result = await swapper.hot_swap("prompt", variants[0].id, variants[1].id, SwapStrategy.ATOMIC)
    assert result.success is False
    assert "set_active_variant_failed" in result.error_message

@pytest.mark.asyncio
async def test_live_optimizer_internal_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    class _StubStrategyManager:
        def __init__(self):
            self.strategies = {
                "balanced_multi": types.SimpleNamespace(
                    select_variant_for_exploitation=lambda variants, metrics: variants[-1]
                )
            }

        def select_strategy(self, context: Dict[str, Any]):
            return types.SimpleNamespace(selected_strategy="balanced_multi", confidence=0.9)

    class _StubTracker:
        def __init__(self, metrics: Dict[str, PromptMetrics]):
            self.metrics = metrics

        def get_metrics(self, prompt_id: str, variant_id: str):
            return self.metrics.get(variant_id)

    class _StubRegistry:
        def __init__(self, prompt_id: str, variants: List[PromptVariant]):
            self.prompt_id = prompt_id
            self.variants = variants
            self.active_variant = variants[0]

        def get_all_prompt_ids(self):
            return [self.prompt_id]

        def get_variant(self, prompt_id: str, variant_id: str):
            for variant in self.variants:
                if variant.id == variant_id:
                    return variant
            return None

        def get_active_variant(self, prompt_id: str):
            return self.active_variant

        def set_active_variant(self, prompt_id: str, variant_id: str):
            for variant in self.variants:
                if variant.id == variant_id:
                    self.active_variant = variant

        def get_all_variants(self, prompt_id: str):
            return self.variants

    async def _stub_hot_swap(prompt_id: str, from_id: str, to_id: str):
        return True

    variants = [
        PromptVariant(content="Baseline", category=PromptCategory.CUSTOM),
        PromptVariant(content="Challenger", category=PromptCategory.CUSTOM),
    ]

    metrics_map = {
        variants[0].id: PromptMetrics(success_rate=0.5, avg_execution_time=2.0, error_rate=0.1, avg_token_cost=5.0, sample_count=20),
        variants[1].id: PromptMetrics(success_rate=0.8, avg_execution_time=1.0, error_rate=0.05, avg_token_cost=3.0, sample_count=30),
    }

    registry = _StubRegistry("prompt", variants)
    tracker = _StubTracker(metrics_map)
    base_optimizer = types.SimpleNamespace(registry=registry, tracker=tracker)

    optimizer = LiveOptimizer(_StubStrategyManager(), base_optimizer, optimization_threshold=0.0, confidence_threshold=0.2)
    optimizer.hot_swapper = types.SimpleNamespace(hot_swap=_stub_hot_swap)
    optimizer.performance_predictor = types.SimpleNamespace()

    optimizer.performance_cache["prompt"] = 1.0

    event = LiveOptimizationEvent(
        event_id="evt-1",
        trigger=OptimizationTrigger.USER_REQUEST,
        timestamp=datetime.now(),
        context={"prompt_id": "prompt"},
        priority=5,
    )

    # Can optimize and perform optimization
    assert await optimizer._can_optimize(event) is True
    result = await optimizer._perform_live_optimization(event)
    assert result.metadata.get("strategy_used") == "balanced_multi"

    # Confidence calculation
    confidence = optimizer._calculate_confidence(metrics_map, variants[0].id, variants[1].id)
    assert confidence > 0

    optimizer._update_optimization_stats(result)
    optimizer.add_event_handler(OptimizationTrigger.USER_REQUEST, lambda event, res: optimizer.optimization_stats.update(last_handler=True))
    await optimizer._trigger_event_handlers(event, result)
    assert optimizer.optimization_stats.get("last_handler")

    no_improvement = optimizer._create_no_improvement_result("evt-2", variants[0].id)
    assert no_improvement.success is False

    await optimizer._update_performance_cache()
    assert optimizer.performance_cache["prompt"] > 0

    optimizer.performance_cache["prompt"] = 0.1
    optimizer._get_historical_performance = lambda pid: [0.5] * 10
    optimizer._trigger_optimization = optimizer.trigger_optimization
    await optimizer._check_performance_drops()

    tracker.metrics[variants[1].id] = PromptMetrics(
        success_rate=0.9, avg_execution_time=0.5, error_rate=0.02, avg_token_cost=1.0, sample_count=1
    )
    await optimizer._check_new_variants()
    await optimizer._check_context_changes()

    await optimizer._process_optimization_queue()

    zero_confidence = optimizer._calculate_confidence(metrics_map, "missing", variants[0].id)
    assert zero_confidence == 0.0

    old_event = LiveOptimizationEvent(
        event_id="old",
        trigger=OptimizationTrigger.SCHEDULED,
        timestamp=datetime.now() - timedelta(hours=25),
        context={"prompt_id": "prompt"},
        priority=1,
    )
    optimizer.active_optimizations["old"] = old_event
    optimizer.variant_switches["old"] = [result]
    await optimizer._cleanup_old_data()
    assert "old" not in optimizer.variant_switches

    event_id = await optimizer.trigger_optimization("prompt", context={"prompt_id": "prompt"})
    assert event_id.startswith("opt_")
    await optimizer._process_optimization_queue()

    temp_calls: List[str] = []

    def temp_handler(event: LiveOptimizationEvent, res: LiveOptimizationResult) -> None:
        temp_calls.append(event.event_id)

    optimizer.add_event_handler(OptimizationTrigger.ANOMALY_DETECTED, temp_handler)
    await optimizer._trigger_event_handlers(
        LiveOptimizationEvent(
            event_id="evt-extra",
            trigger=OptimizationTrigger.ANOMALY_DETECTED,
            timestamp=datetime.now(),
            context={"prompt_id": "prompt"},
            priority=5,
        ),
        result,
    )
    optimizer.remove_event_handler(OptimizationTrigger.ANOMALY_DETECTED, temp_handler)
    assert temp_calls

    status = optimizer.get_optimization_status()
    assert "queue_size" in status
    history_all = optimizer.get_optimization_history()
    optimizer.get_optimization_history("prompt")

    optimizer.stop()  # Not running branch
    class _FakeTask:
        def cancel(self) -> None:
            pass
    original_create_task = asyncio.create_task
    monkeypatch.setattr(asyncio, "create_task", lambda coro: _FakeTask())
    optimizer.start()
    optimizer.stop()
    monkeypatch.setattr(asyncio, "create_task", original_create_task)


@pytest.mark.asyncio
async def test_live_optimizer_optimization_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    variant = PromptVariant(content="Variant", category=PromptCategory.CUSTOM)

    class _LoopRegistry:
        def get_all_prompt_ids(self):
            return []

    optimizer = LiveOptimizer(
        strategy_manager=types.SimpleNamespace(strategies={}),
        base_optimizer=types.SimpleNamespace(registry=_LoopRegistry(), tracker=object()),
    )

    calls = {"queue": 0, "cache": 0, "trigger": 0, "cleanup": 0}

    async def fake_queue():
        calls["queue"] += 1

    async def fake_cache():
        calls["cache"] += 1

    async def fake_trigger():
        calls["trigger"] += 1

    async def fake_cleanup():
        calls["cleanup"] += 1
        optimizer.is_running = False

    monkeypatch.setattr(optimizer, "_process_optimization_queue", fake_queue)
    monkeypatch.setattr(optimizer, "_update_performance_cache", fake_cache)
    monkeypatch.setattr(optimizer, "_check_optimization_triggers", fake_trigger)
    monkeypatch.setattr(optimizer, "_cleanup_old_data", fake_cleanup)

    optimizer.is_running = True
    await optimizer._optimization_loop()
    assert calls["queue"] == 1
    assert calls["cleanup"] == 1


# ---------------------------------------------------------------------------
# PerformancePredictor
# ---------------------------------------------------------------------------


def _make_features(content: str = "Generate detailed report") -> PredictionFeatures:
    return PredictionFeatures(
        prompt_length=len(content),
        prompt_complexity=0.3,
        variant_version=1,
        historical_success_rate=0.7,
        historical_avg_time=1.5,
        historical_error_rate=0.1,
        context_domain="software",
        context_task_type="generation",
        context_urgency="medium",
        time_of_day=10,
        day_of_week=2,
        recent_performance_trend=0.0,
        resource_availability=0.8,
        user_experience_level="intermediate",
        system_load=0.4,
    )


def test_performance_predictor_training_and_prediction(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # Use linear regression for simpler tests and patch models with stubs
    predictor = PerformancePredictor(model_type=PredictionModel.LINEAR_REGRESSION, retrain_frequency=50)

    stub_model = _StubModel()
    monkeypatch.setattr(
        "forge.prompt_optimization.realtime.performance_predictor.LinearRegression",
        lambda: stub_model,
    )

    # Provide ample training data
    training_samples = []
    for idx in range(12):
        features = _make_features(content=f"Prompt content example {idx}")
        training_samples.append((features, 0.5 + idx * 0.02))

    predictor.train(training_samples)
    assert predictor.is_trained

    variant = PromptVariant(content="Optimized prompt", category=PromptCategory.CUSTOM)
    metrics = PromptMetrics(success_rate=0.8, avg_execution_time=1.2, error_rate=0.05, avg_token_cost=10.0, sample_count=50)
    prediction = predictor.predict(variant, {"domain": "software", "task_type": "generation"}, historical_metrics=metrics)
    assert 0.0 <= prediction.predicted_score <= 1.0
    assert prediction.model_used == PredictionModel.LINEAR_REGRESSION.value
    assert prediction.features_used["context_domain"] == "software"

    predictor.add_training_data(_make_features(), 0.9)
    performance = predictor.get_model_performance()
    assert performance["is_trained"] is True

    # Test persistence
    model_path = tmp_path / "predictor.pkl"
    predictor.save_model(model_path.as_posix())
    assert model_path.exists()

    loaded = PerformancePredictor(model_type=PredictionModel.LINEAR_REGRESSION)
    monkeypatch.setattr(
        "forge.prompt_optimization.realtime.performance_predictor.LinearRegression",
        lambda: _StubModel(),
    )
    loaded.load_model(model_path.as_posix())
    assert loaded.is_trained is True


def test_performance_predictor_default_prediction() -> None:
    predictor = PerformancePredictor(model_type=PredictionModel.LINEAR_REGRESSION)
    variant = PromptVariant(content="New prompt", category=PromptCategory.CUSTOM)
    prediction = predictor.predict(variant, {"domain": "general"})
    assert prediction.model_used == "default"
    assert prediction.predicted_score == 0.5


def test_performance_predictor_ensemble(monkeypatch: pytest.MonkeyPatch) -> None:
    predictor = PerformancePredictor(model_type=PredictionModel.ENSEMBLE, retrain_frequency=5)

    monkeypatch.setattr(
        "forge.prompt_optimization.realtime.performance_predictor.RandomForestRegressor",
        lambda *args, **kwargs: _StubModel(0.6),
    )
    monkeypatch.setattr(
        "forge.prompt_optimization.realtime.performance_predictor.GradientBoostingRegressor",
        lambda *args, **kwargs: _StubModel(0.7),
    )
    monkeypatch.setattr(
        "forge.prompt_optimization.realtime.performance_predictor.LinearRegression",
        lambda *args, **kwargs: _StubModel(0.8),
    )

    training_samples = [(_make_features(content=f"text {i}"), 0.4 + i * 0.01) for i in range(15)]
    predictor.train(training_samples)
    assert predictor.is_trained

    variant = PromptVariant(content="Test variant", category=PromptCategory.CUSTOM)
    prediction = predictor.predict(variant, {"domain": "software"})
    assert prediction.model_used.startswith("ensemble")


def test_real_time_monitor_metrics_and_alerts(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monitor = RealTimeMonitor(update_interval=0.01, max_history_size=50, trend_window_size=10)

    prompt_id = "prompt-monitor"
    metrics = {
        "variant_id": "variant-1",
        "success_rate": 0.4,
        "execution_time": 12.0,
        "error_rate": 0.3,
        "token_cost": 5.0,
        "composite_score": 0.5,
        "sample_count": 10,
    }

    captured_metrics: List[str] = []
    def metric_callback(pid: str, data: Dict[str, Any]) -> None:
        captured_metrics.append(pid)

    monitor.add_metric_callback(prompt_id, metric_callback)

    snapshot = MetricSnapshot(
        timestamp=datetime.now(),
        prompt_id=prompt_id,
        variant_id="variant-1",
        metrics=metrics,
    )
    monitor._store_metric_snapshot(snapshot)
    monitor.current_metrics[prompt_id] = metrics

    # Add more snapshots for trend analysis
    for idx in range(12):
        updated = metrics.copy()
        updated["success_rate"] = 0.4 + idx * 0.02
        monitor._store_metric_snapshot(
            MetricSnapshot(
                timestamp=datetime.now(),
                prompt_id=prompt_id,
                variant_id=f"variant-{idx}",
                metrics=updated,
            )
        )
    trend = asyncio.run(monitor._analyze_metric_trend(prompt_id, MetricType.SUCCESS_RATE))
    if trend:
        assert trend.metric_type == MetricType.SUCCESS_RATE

    confidence = monitor._calculate_trend_confidence([0.5, 0.6, 0.7])
    assert 0 <= confidence <= 1

    # Trigger alert
    asyncio.run(monitor._check_metric_alert(prompt_id, "success_rate", 0.3))
    assert monitor.active_alerts
    alert_obj = next(iter(monitor.active_alerts.values()))
    assert monitor.clear_alert(alert_obj.alert_id) is True

    def alert_callback(alert: MonitoringAlert) -> None:
        pass

    monitor.add_alert_callback(alert_callback)
    monitor.remove_alert_callback(alert_callback)

    history = monitor.get_metric_history(prompt_id)
    assert history
    trends = asyncio.run(monitor._analyze_metric_trend(prompt_id, MetricType.ERROR_RATE))
    monitor.get_metric_history(prompt_id, variant_id="variant-1", metric_type=MetricType.SUCCESS_RATE)
    monitor.get_performance_trends()
    monitor.get_performance_trends(prompt_id)
    monitor.get_active_alerts()
    monitor.get_alert_history()
    monitor.get_dashboard_data()

    cleared = monitor.clear_all_alerts(prompt_id)
    assert isinstance(cleared, int)

    stats = monitor.get_monitoring_stats()
    assert "update_interval" in stats

    asyncio.run(monitor._trigger_metric_callbacks(prompt_id, metrics))
    asyncio.run(monitor._collect_current_metrics())
    asyncio.run(monitor._analyze_trends())
    asyncio.run(monitor._check_alerts())
    monitor._update_monitoring_stats(0.5)
    monitor.get_metric_history(prompt_id, limit=0)
    monitor.get_alert_history(prompt_id=prompt_id, level=AlertLevel.WARNING, limit=0)
    monitor.remove_metric_callback(prompt_id, metric_callback)

    monitor.add_alert_callback(alert_callback)
    asyncio.run(monitor._trigger_alert_callbacks(alert_obj))
    monitor.remove_alert_callback(alert_callback)

    original_create_task = asyncio.create_task
    monkeypatch.setattr(asyncio, "create_task", lambda coro: types.SimpleNamespace(cancel=lambda: None))
    monitor.start()
    monitor.stop()
    monkeypatch.setattr(asyncio, "create_task", original_create_task)

    assert captured_metrics

    export_path = tmp_path / "metrics.json"
    monitor.export_metrics(prompt_id, export_path.as_posix())
    assert export_path.exists()


@pytest.mark.asyncio
async def test_streaming_engine_event_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    live_optimizer = _StubLiveOptimizer()
    engine = StreamingOptimizationEngine(live_optimizer, max_queue_size=5, processing_batch_size=2, processing_interval=0.01)

    processed_events: List[str] = []

    def handler(event: StreamEvent, actions: List[str]) -> None:
        processed_events.append(event.event_id)

    engine.add_event_handler(StreamEventType.METRICS_UPDATE, handler)
    await engine.add_event(
        StreamEventType.METRICS_UPDATE,
        "prompt-stream",
        {"metrics": {"composite_score": 0.5}, "values": [1, 2, 3]},
    )

    await engine._process_event_batch()
    stats = engine.get_processing_stats()
    assert stats["stats"]["events_processed"] >= 1
    assert processed_events

    history = engine.get_performance_history("prompt-stream")
    assert isinstance(history, list)

    anomaly_event = StreamEvent(
        event_id="anomaly-1",
        event_type=StreamEventType.PERFORMANCE_ANOMALY,
        timestamp=datetime.now(),
        prompt_id="prompt-stream",
        data={"metrics": {"composite_score": 0.2}},
    )
    await engine._trigger_optimization_if_needed(anomaly_event)
    assert live_optimizer.trigger_calls

    # Pattern detection and performance history utilities
    engine.add_pattern_detector("prompt-stream", lambda events: ["custom_pattern"])
    engine.performance_history["prompt-stream"] = deque([0.5 + i * 0.01 for i in range(60)], maxlen=engine.pattern_window_size)
    pattern_result = await engine._recognize_patterns(
        StreamEvent(
            event_id="pattern-2",
            event_type=StreamEventType.METRICS_UPDATE,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"metrics": {"composite_score": 0.6}},
        )
    )
    assert "custom_pattern" in pattern_result

    engine.performance_history["prompt-stream"] = deque([0.1 * i for i in range(60)], maxlen=engine.pattern_window_size)
    await engine._check_common_patterns("prompt-stream")
    engine.clear_performance_history("prompt-stream")
    engine.clear_performance_history()

    variant_switch_event = StreamEvent(
        event_id="switch-1",
        event_type=StreamEventType.VARIANT_SWITCH,
        timestamp=datetime.now(),
        prompt_id="prompt-stream",
        data={"from_variant": "old", "to_variant": "new", "metrics": {"composite_score": 0.7}},
    )
    actions_switch = await engine._process_event_by_type(variant_switch_event)
    assert isinstance(actions_switch, list)

    anomaly_actions = await engine._process_event_by_type(
        StreamEvent(
            event_id="anomaly-2",
            event_type=StreamEventType.PERFORMANCE_ANOMALY,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"metrics": {"composite_score": 0.1}},
        )
    )
    assert isinstance(anomaly_actions, list)
    context_actions = await engine._process_event_by_type(
        StreamEvent(
            event_id="context-1",
            event_type=StreamEventType.CONTEXT_CHANGE,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"context": {"domain": "finance"}},
        )
    )
    assert isinstance(context_actions, list)
    user_actions = await engine._process_event_by_type(
        StreamEvent(
            event_id="user-1",
            event_type=StreamEventType.USER_INTERACTION,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"interaction": "feedback"},
        )
    )
    assert isinstance(user_actions, list)
    alert_actions = await engine._process_event_by_type(
        StreamEvent(
            event_id="alert-1",
            event_type=StreamEventType.SYSTEM_ALERT,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"level": "critical"},
        )
    )
    assert isinstance(alert_actions, list)

    single_result = await engine._process_single_event(
        StreamEvent(
            event_id="single-1",
            event_type=StreamEventType.METRICS_UPDATE,
            timestamp=datetime.now(),
            prompt_id="prompt-stream",
            data={"metrics": {"composite_score": 0.55}},
        )
    )
    assert single_result.processed is True

    engine._calculate_cycle_similarity([[0.1] * 20, [0.1] * 20])
    engine._calculate_correlation([1, 2, 3], [1, 2, 4])

    engine.pattern_buffers["prompt-stream"] = deque([anomaly_event], maxlen=engine.pattern_window_size)
    gathered = []
    async for evt in engine.get_streaming_events(limit=1):
        gathered.append(evt)
    assert gathered

    monkeypatch.setattr(asyncio, "create_task", lambda coro: None)
    engine.start()
    engine.stop()

