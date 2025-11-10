from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
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

from forge.prompt_optimization.realtime.integration import RealTimeOptimizationSystem
from forge.prompt_optimization.realtime.live_optimizer import (
    LiveOptimizationEvent,
    LiveOptimizationResult,
    OptimizationTrigger,
)
from forge.prompt_optimization.realtime.real_time_monitor import MonitoringAlert, AlertLevel, MetricType
from forge.prompt_optimization.realtime.websocket_server import WebSocketMessageType, WebSocketOptimizationServer


class _StubLiveOptimizer:
    def __init__(self, *args, **kwargs):
        self.hot_swapper = None
        self.performance_predictor = None
        self.handlers: Dict[str, List[Any]] = {}
        self.started = False
        self.triggered: List[Dict[str, Any]] = []

    def set_hot_swapper(self, swapper: Any) -> None:
        self.hot_swapper = swapper

    def set_performance_predictor(self, predictor: Any) -> None:
        self.performance_predictor = predictor

    def add_event_handler(self, event_type: str, handler: Any) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    async def trigger_optimization(self, prompt_id: str, priority: int, context: Dict[str, Any]) -> str:
        self.triggered.append({"prompt_id": prompt_id, "priority": priority, "context": context})
        return f"opt-{prompt_id}"

    def get_optimization_status(self) -> Dict[str, Any]:
        return {"status": "ready"}

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        return []


class _StubHotSwapper:
    def __init__(self, *args, **kwargs):
        pass

    def get_swap_status(self) -> Dict[str, Any]:
        return {"swaps": 0}


class _StubPerformancePredictor:
    def __init__(self, *args, **kwargs):
        pass

    def get_model_performance(self) -> Dict[str, Any]:
        return {"models": 0}


class _StubStreamingEngine:
    def __init__(self, *args, **kwargs):
        self.handlers: Dict[str, Any] = {}
        self.started = False
        self.events: List[Dict[str, Any]] = []

    def add_event_handler(self, event_type: str, handler: Any) -> None:
        self.handlers[event_type] = handler

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    async def add_event(self, event_type: str, prompt_id: str, data: Dict[str, Any], priority: int = 5) -> str:
        self.events.append({"event_type": event_type, "prompt_id": prompt_id, "data": data, "priority": priority})
        return f"event-{prompt_id}"

    def get_processing_stats(self) -> Dict[str, Any]:
        return {"events_tracked": len(self.events)}


class _StubRealTimeMonitor:
    def __init__(self, *args, **kwargs):
        self.alert_callbacks: List[Any] = []
        self.started = False

    def add_alert_callback(self, callback: Any) -> None:
        self.alert_callbacks.append(callback)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def get_monitoring_stats(self) -> Dict[str, Any]:
        return {"monitoring": "active"}

    def get_current_metrics(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        return {"metric": 1}

    def get_active_alerts(self, prompt_id: Optional[str] = None) -> List[MonitoringAlert]:
        return []

    def get_alert_history(self, prompt_id: Optional[str] = None, limit: int = 100) -> List[MonitoringAlert]:
        return []

    def get_dashboard_data(self) -> Dict[str, Any]:
        return {"dashboard": True}


class _StubWebSocketServer:
    def __init__(self, *args, **kwargs):
        self.messages: List[Dict[str, Any]] = []
        self.clients: set = set()
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    async def broadcast_message(self, message: Dict[str, Any], subscription_type: Optional[str] = None) -> None:
        self.messages.append({"message": message, "subscription": subscription_type})

    def get_server_stats(self) -> Dict[str, Any]:
        return {"running": self.started}

    def get_client_info(self) -> List[Dict[str, Any]]:
        return []


@pytest.mark.asyncio
async def test_real_time_optimization_system_lifecycle(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import forge.prompt_optimization.realtime.integration as integration_module

    monkeypatch.setattr(integration_module, "LiveOptimizer", _StubLiveOptimizer)
    monkeypatch.setattr(integration_module, "HotSwapper", _StubHotSwapper)
    monkeypatch.setattr(integration_module, "PerformancePredictor", _StubPerformancePredictor)
    monkeypatch.setattr(integration_module, "StreamingOptimizationEngine", _StubStreamingEngine)
    monkeypatch.setattr(integration_module, "RealTimeMonitor", _StubRealTimeMonitor)
    monkeypatch.setattr(integration_module, "WebSocketOptimizationServer", _StubWebSocketServer)
    monkeypatch.setattr(integration_module.asyncio, "create_task", lambda coro: None)

    base_optimizer = type("BaseOptimizer", (), {"registry": object(), "tracker": object()})()
    system = RealTimeOptimizationSystem(strategy_manager=object(), base_optimizer=base_optimizer, config={"websocket": {"host": "0.0.0.0", "port": 1234}})

    assert system.get_system_status()["status"] == "stopped"
    await system.initialize()
    await system.start()

    result = LiveOptimizationResult(
        event_id="evt",
        success=True,
        old_variant_id="old",
        new_variant_id="new",
        performance_improvement=0.1,
        confidence=0.9,
        execution_time=0.2,
        metadata={"info": True},
    )
    await system._on_optimization_completed(None, result)
    await system._on_variant_switched(None, result)

    alert = MonitoringAlert(
        alert_id="alert-1",
        level=AlertLevel.ERROR,
        metric_type=MetricType.ERROR_RATE,
        prompt_id="prompt",
        message="High error rate",
        timestamp=datetime.now(),
        value=0.5,
        threshold=0.2,
        metadata={},
    )
    await system._on_alert_generated(alert)
    await system._on_metrics_update(type("Event", (), {"data": {"metric": 1}}), [])

    trigger_id = await system.trigger_optimization("prompt", priority=3, context={"extra": True})
    assert trigger_id.startswith("opt-")

    event_id = await system.add_streaming_event("metrics_update", "prompt", {"metrics": {"value": 1}})
    assert event_id.startswith("event-")

    status = system.get_system_status()
    assert status["status"] == "running"

    summary = system.get_performance_summary()
    assert "optimizations_performed" in summary

    dashboard = system.get_dashboard_data()
    assert "system_status" in dashboard

    export_path = tmp_path / "system.json"
    system.export_system_data(export_path.as_posix())
    assert export_path.exists()

    system.update_config({"new_option": True})
    assert system.config["new_option"] is True

    system.get_component_status("live_optimizer")
    system.get_component_status("streaming_engine")
    system.get_component_status("real_time_monitor")
    system.get_component_status("websocket_server")
    system.get_component_status("hot_swapper")
    system.get_component_status("performance_predictor")
    assert system.get_component_status("unknown")["error"]
    await system.health_check()

    await system.stop()

    with pytest.raises(RuntimeError):
        await system.trigger_optimization("prompt")

    with pytest.raises(RuntimeError):
        await system.add_streaming_event("metrics_update", "prompt", {})


class _WSStubLiveOptimizer:
    def __init__(self):
        self.triggered: List[Dict[str, Any]] = []

    async def trigger_optimization(self, prompt_id: str, priority: int, context: Dict[str, Any]) -> str:
        self.triggered.append({"prompt_id": prompt_id, "priority": priority, "context": context})
        return "event-123"

    def get_optimization_status(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        return []


class _WSStubMonitor:
    def get_current_metrics(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        return {"metric": 1}

    def get_active_alerts(self, prompt_id: Optional[str] = None) -> List[MonitoringAlert]:
        return [
            MonitoringAlert(
                alert_id="alert",
                level=AlertLevel.WARNING,
                metric_type=MetricType.SUCCESS_RATE,
                prompt_id="prompt",
                message="Warning",
                timestamp=datetime.now(),
                value=0.4,
                threshold=0.6,
                metadata={},
            )
        ]

    def clear_alert(self, alert_id: str) -> bool:
        return True

    def get_alert_history(self, prompt_id: Optional[str] = None, limit: int = 100) -> List[MonitoringAlert]:
        return []


class _FakeWebSocket:
    def __init__(self):
        self.sent: List[Dict[str, Any]] = []
        self.closed = False
        self.remote_address = ("127.0.0.1", 0)
        self.connected_at = datetime.now().isoformat()

    async def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    async def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_websocket_server_message_handlers(monkeypatch: pytest.MonkeyPatch):
    async def fake_serve(*args, **kwargs):
        class _Server:
            def close(self):
                pass

            async def wait_closed(self):
                await asyncio.sleep(0)

        return _Server()

    monkeypatch.setattr("websockets.serve", fake_serve)
    server = WebSocketOptimizationServer(_WSStubLiveOptimizer(), _WSStubMonitor(), heartbeat_interval=0.01)

    fake_ws = _FakeWebSocket()
    server.clients.add(fake_ws)
    server.client_subscriptions[fake_ws] = set()

    await server._handle_subscribe(fake_ws, {"subscription_type": "metrics"})
    await server._handle_unsubscribe(fake_ws, {"subscription_type": "metrics"})
    await server._handle_get_status(fake_ws, {})
    await server._handle_get_metrics(fake_ws, {"prompt_id": "prompt"})
    await server._handle_get_alerts(fake_ws, {"prompt_id": "prompt"})
    await server._handle_clear_alert(fake_ws, {"alert_id": "alert"})
    await server._handle_trigger_optimization(fake_ws, {"prompt_id": "prompt", "priority": 6, "context": {}})

    await server._handle_message(fake_ws, json.dumps({"type": WebSocketMessageType.SUBSCRIBE, "subscription_type": "metrics"}))
    await server._handle_message(fake_ws, json.dumps({"type": WebSocketMessageType.GET_STATUS}))
    await server._handle_message(fake_ws, json.dumps({"type": "unknown"}))

    server.client_subscriptions[fake_ws].update({"metrics", "alerts"})
    async def fake_sleep(_: float):
        server.is_running = False
    original_sleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    server.is_running = True
    await server._heartbeat_loop()

    server.is_running = True
    await server._monitoring_loop()

    await server.broadcast_message({"type": "test"})
    await server.broadcast_message({"type": "metrics_specific"}, subscription_type="metrics")
    clients_before_stop = server.get_client_info()
    assert clients_before_stop
    await server.start()
    await server.stop()
    await server._close_client(fake_ws)

    stats = server.get_server_stats()
    clients = server.get_client_info()

    assert stats["max_clients"] == server.max_clients
    assert isinstance(clients, list)

    monkeypatch.setattr(asyncio, "sleep", original_sleep)

