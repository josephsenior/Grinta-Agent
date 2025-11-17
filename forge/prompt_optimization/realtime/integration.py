"""Real-Time Optimization Integration.

Integrates all real-time optimization components into a unified system
with automatic startup, configuration, and coordination.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from typing import Any, Optional, TypeVar
from datetime import datetime

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.advanced import AdvancedStrategyManager
from forge.prompt_optimization.health import collect_health_snapshot
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.realtime.live_optimizer import (
    LiveOptimizer,
    LiveOptimizationEvent,
    LiveOptimizationResult,
    OptimizationTrigger,
)
from forge.prompt_optimization.realtime.hot_swapper import HotSwapper, SwapStrategy
from forge.prompt_optimization.realtime.performance_predictor import (
    PerformancePredictor,
)
from forge.prompt_optimization.realtime.streaming_engine import (
    StreamingOptimizationEngine,
    StreamEvent,
    StreamEventType,
)
from forge.prompt_optimization.realtime.real_time_monitor import (
    RealTimeMonitor,
    MonitoringAlert,
)
from forge.prompt_optimization.realtime.websocket_server import (
    WebSocketOptimizationServer,
)

T = TypeVar("T")


class RealTimeOptimizationSystem:
    """Real-Time Optimization System - The complete real-time optimization solution.

    Features:
    - Unified real-time optimization
    - Automatic component coordination
    - Live monitoring and control
    - WebSocket communication
    - Performance prediction
    - Hot-swapping capabilities
    - Streaming data processing
    """

    def __init__(
        self,
        strategy_manager: AdvancedStrategyManager,
        base_optimizer: PromptOptimizer,
        config: Optional[dict[str, Any]] = None,
    ):
        """Capture core dependencies and prepare component placeholders before startup."""
        self.strategy_manager = strategy_manager
        self.base_optimizer = base_optimizer
        self.config: dict[str, Any] = dict(config or {})

        # Initialize components
        self.live_optimizer: Optional[LiveOptimizer] = None
        self.hot_swapper: Optional[HotSwapper] = None
        self.performance_predictor: Optional[PerformancePredictor] = None
        self.streaming_engine: Optional[StreamingOptimizationEngine] = None
        self.real_time_monitor: Optional[RealTimeMonitor] = None
        self.websocket_server: Optional[WebSocketOptimizationServer] = None

        # System state
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        self.system_stats: dict[str, int] = {
            "uptime": 0,
            "optimizations_performed": 0,
            "variants_switched": 0,
            "alerts_generated": 0,
            "predictions_made": 0,
            "events_processed": 0,
        }

        logger.info("Real-Time Optimization System initialized")

    def _require_component(self, component: Optional[T], name: str) -> T:
        """Helper to ensure a component has been initialized."""
        if component is None:
            raise RuntimeError(f"{name} has not been initialized")
        return component

    async def initialize(self) -> None:
        """Initialize all real-time optimization components."""
        try:
            logger.info("Initializing real-time optimization system...")

            # Initialize Live Optimizer
            self.live_optimizer = LiveOptimizer(
                strategy_manager=self.strategy_manager,
                base_optimizer=self.base_optimizer,
                max_concurrent_optimizations=self.config.get(
                    "max_concurrent_optimizations", 5
                ),
                optimization_threshold=self.config.get("optimization_threshold", 0.05),
                confidence_threshold=self.config.get("confidence_threshold", 0.8),
            )

            # Initialize Hot Swapper
            default_strategy_value = self.config.get(
                "default_swap_strategy", SwapStrategy.ATOMIC.value
            )
            if isinstance(default_strategy_value, SwapStrategy):
                default_strategy = default_strategy_value
            else:
                try:
                    default_strategy = SwapStrategy(str(default_strategy_value))
                except ValueError:
                    default_strategy = SwapStrategy.ATOMIC

            self.hot_swapper = HotSwapper(
                registry=self.base_optimizer.registry,
                max_concurrent_swaps=self.config.get("max_concurrent_swaps", 3),
                default_strategy=default_strategy,
                health_check_timeout=self.config.get("health_check_timeout", 5.0),
                rollback_timeout=self.config.get("rollback_timeout", 10.0),
            )

            # Initialize Performance Predictor
            self.performance_predictor = PerformancePredictor(
                model_type=self.config.get("prediction_model", "ensemble"),
                retrain_frequency=self.config.get("retrain_frequency", 100),
                confidence_threshold=self.config.get(
                    "prediction_confidence_threshold", 0.7
                ),
            )

            # Initialize Streaming Engine
            self.streaming_engine = StreamingOptimizationEngine(
                live_optimizer=self.live_optimizer,
                max_queue_size=self.config.get("max_queue_size", 10000),
                processing_batch_size=self.config.get("processing_batch_size", 100),
                processing_interval=self.config.get("processing_interval", 0.1),
                anomaly_threshold=self.config.get("anomaly_threshold", 2.0),
                pattern_window_size=self.config.get("pattern_window_size", 100),
            )

            # Initialize Real-Time Monitor
            self.real_time_monitor = RealTimeMonitor(
                update_interval=self.config.get("monitor_update_interval", 1.0),
                alert_thresholds=self.config.get("alert_thresholds"),
                max_history_size=self.config.get("max_history_size", 10000),
                trend_window_size=self.config.get("trend_window_size", 100),
            )

            # Initialize WebSocket Server
            websocket_config = self.config.get("websocket", {})
            self.websocket_server = WebSocketOptimizationServer(
                live_optimizer=self.live_optimizer,
                real_time_monitor=self.real_time_monitor,
                host=websocket_config.get("host", "localhost"),
                port=websocket_config.get("port", 8765),
                heartbeat_interval=websocket_config.get("heartbeat_interval", 30.0),
                max_clients=websocket_config.get("max_clients", 100),
            )

            # Connect components
            self._connect_components()

            logger.info("Real-time optimization system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize real-time optimization system: {e}")
            raise

    def _connect_components(self) -> None:
        """Connect all components together."""
        # Connect Live Optimizer to Hot Swapper
        live_optimizer = self._require_component(self.live_optimizer, "live_optimizer")
        hot_swapper = self._require_component(self.hot_swapper, "hot_swapper")
        performance_predictor = self._require_component(
            self.performance_predictor, "performance_predictor"
        )
        real_time_monitor = self._require_component(
            self.real_time_monitor, "real_time_monitor"
        )
        streaming_engine = self._require_component(
            self.streaming_engine, "streaming_engine"
        )

        live_optimizer.set_hot_swapper(hot_swapper)

        # Connect Live Optimizer to Performance Predictor
        live_optimizer.set_performance_predictor(performance_predictor)

        # Add event handlers for monitoring
        for trigger in OptimizationTrigger:
            live_optimizer.add_event_handler(trigger, self._on_optimization_completed)
            live_optimizer.add_event_handler(trigger, self._on_variant_switched)

        # Add monitoring callbacks
        real_time_monitor.add_alert_callback(self._on_alert_generated)

        # Add streaming event handlers
        streaming_engine.add_event_handler(
            StreamEventType.METRICS_UPDATE, self._on_metrics_update
        )

    async def start(self) -> None:
        """Start the real-time optimization system."""
        if self.is_running:
            logger.warning("Real-time optimization system is already running")
            return

        try:
            logger.info("Starting real-time optimization system...")

            live_optimizer = self._require_component(
                self.live_optimizer, "live_optimizer"
            )
            streaming_engine = self._require_component(
                self.streaming_engine, "streaming_engine"
            )
            real_time_monitor = self._require_component(
                self.real_time_monitor, "real_time_monitor"
            )
            websocket_server = self._require_component(
                self.websocket_server, "websocket_server"
            )

            # Start all components
            live_optimizer.start()
            streaming_engine.start()
            real_time_monitor.start()

            # Start WebSocket server in background
            asyncio.create_task(websocket_server.start())

            self.is_running = True
            self.startup_time = datetime.now()

            logger.info("Real-time optimization system started successfully")

        except Exception as e:
            logger.error(f"Failed to start real-time optimization system: {e}")
            raise

    async def stop(self) -> None:
        """Stop the real-time optimization system."""
        if not self.is_running:
            return

        try:
            logger.info("Stopping real-time optimization system...")

            live_optimizer = self._require_component(
                self.live_optimizer, "live_optimizer"
            )
            streaming_engine = self._require_component(
                self.streaming_engine, "streaming_engine"
            )
            real_time_monitor = self._require_component(
                self.real_time_monitor, "real_time_monitor"
            )
            websocket_server = self._require_component(
                self.websocket_server, "websocket_server"
            )

            # Stop all components
            live_optimizer.stop()
            streaming_engine.stop()
            real_time_monitor.stop()
            await websocket_server.stop()

            self.is_running = False

            logger.info("Real-time optimization system stopped")

        except Exception as e:
            logger.error(f"Error stopping real-time optimization system: {e}")

    # Event handlers

    async def _on_optimization_completed(
        self, event: LiveOptimizationEvent, result: LiveOptimizationResult
    ) -> None:
        """Handle optimization completion event."""
        self.system_stats["optimizations_performed"] += 1

        # Log optimization result
        logger.info(f"Optimization completed: {result.success}")

        # Send WebSocket update
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )
        await websocket_server.broadcast_message(
            {
                "type": "optimization_result",
                "data": asdict(result),
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def _on_variant_switched(
        self, event: LiveOptimizationEvent, result: LiveOptimizationResult
    ) -> None:
        """Handle variant switch event."""
        if result.old_variant_id == result.new_variant_id:
            return

        self.system_stats["variants_switched"] += 1

        # Log variant switch
        logger.info(
            f"Variant switched: {result.old_variant_id} -> {result.new_variant_id}"
        )

        # Send WebSocket update
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )
        await websocket_server.broadcast_message(
            {
                "type": "variant_switched",
                "data": asdict(result),
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def _on_alert_generated(self, alert: MonitoringAlert) -> None:
        """Handle alert generation event."""
        self.system_stats["alerts_generated"] += 1

        # Log alert
        logger.warning(f"Alert generated: {alert.message}")

        # Send WebSocket update
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )
        await websocket_server.broadcast_message(
            {
                "type": "alert_notification",
                "data": asdict(alert),
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def _on_metrics_update(
        self, event: StreamEvent, actions: list[str]
    ) -> None:
        """Handle metrics update event."""
        self.system_stats["events_processed"] += 1

        # Send WebSocket update
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )
        await websocket_server.broadcast_message(
            {
                "type": "metrics_update",
                "data": event.data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Public API methods

    async def trigger_optimization(
        self,
        prompt_id: str,
        priority: int = 5,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Trigger optimization for a specific prompt."""
        if not self.is_running:
            raise RuntimeError("Real-time optimization system is not running")

        live_optimizer = self._require_component(
            self.live_optimizer, "live_optimizer"
        )

        event_id = await live_optimizer.trigger_optimization(
            prompt_id=prompt_id, priority=priority, context=context or {}
        )
        if event_id.startswith("opt_"):
            return event_id.replace("opt_", "opt-", 1).replace("_", "-", 1)
        return event_id

    async def add_streaming_event(
        self,
        event_type: StreamEventType,
        prompt_id: str,
        data: dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Add a streaming event for processing."""
        if not self.is_running:
            raise RuntimeError("Real-time optimization system is not running")

        streaming_engine = self._require_component(
            self.streaming_engine, "streaming_engine"
        )

        return await streaming_engine.add_event(
            event_type=event_type, prompt_id=prompt_id, data=data, priority=priority
        )

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        if not self.is_running:
            return {"status": "stopped"}

        live_optimizer = self._require_component(
            self.live_optimizer, "live_optimizer"
        )
        streaming_engine = self._require_component(
            self.streaming_engine, "streaming_engine"
        )
        real_time_monitor = self._require_component(
            self.real_time_monitor, "real_time_monitor"
        )
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )

        uptime = (
            (datetime.now() - self.startup_time).total_seconds()
            if self.startup_time
            else 0
        )

        return {
            "status": "running",
            "uptime": uptime,
            "startup_time": self.startup_time.isoformat()
            if self.startup_time
            else None,
            "stats": self.system_stats.copy(),
            "components": {
                "live_optimizer": live_optimizer.get_optimization_status(),
                "streaming_engine": streaming_engine.get_processing_stats(),
                "real_time_monitor": real_time_monitor.get_monitoring_stats(),
                "websocket_server": websocket_server.get_server_stats(),
            },
        }

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary across all components."""
        real_time_monitor = self._require_component(
            self.real_time_monitor, "real_time_monitor"
        )
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )

        return {
            "optimizations_performed": self.system_stats["optimizations_performed"],
            "variants_switched": self.system_stats["variants_switched"],
            "alerts_generated": self.system_stats["alerts_generated"],
            "predictions_made": self.system_stats["predictions_made"],
            "events_processed": self.system_stats["events_processed"],
            "current_metrics": real_time_monitor.get_current_metrics(),
            "active_alerts": len(real_time_monitor.get_active_alerts()),
            "connected_clients": len(websocket_server.clients),
        }

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data."""
        real_time_monitor = self._require_component(
            self.real_time_monitor, "real_time_monitor"
        )
        live_optimizer = self._require_component(
            self.live_optimizer, "live_optimizer"
        )
        websocket_server = self._require_component(
            self.websocket_server, "websocket_server"
        )

        return {
            "system_status": self.get_system_status(),
            "performance_summary": self.get_performance_summary(),
            "monitoring_data": real_time_monitor.get_dashboard_data(),
            "optimization_history": live_optimizer.get_optimization_history(),
            "client_info": websocket_server.get_client_info(),
            "health_snapshot": self.get_health_snapshot(),
        }

    def export_system_data(self, filepath: str) -> None:
        """Export system data to a file."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_status": self.get_system_status(),
            "performance_summary": self.get_performance_summary(),
            "configuration": self.config,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"System data exported to {filepath}")

    def update_config(self, new_config: dict[str, Any]) -> None:
        """Update system configuration."""
        self.config.update(new_config)
        logger.info("System configuration updated")

    def get_component_status(self, component_name: str) -> dict[str, Any]:
        """Get status of a specific component."""
        if component_name == "live_optimizer":
            return self._require_component(
                self.live_optimizer, "live_optimizer"
            ).get_optimization_status()
        if component_name == "streaming_engine":
            return self._require_component(
                self.streaming_engine, "streaming_engine"
            ).get_processing_stats()
        if component_name == "real_time_monitor":
            return self._require_component(
                self.real_time_monitor, "real_time_monitor"
            ).get_monitoring_stats()
        if component_name == "websocket_server":
            return self._require_component(
                self.websocket_server, "websocket_server"
            ).get_server_stats()
        if component_name == "hot_swapper":
            return self._require_component(self.hot_swapper, "hot_swapper").get_swap_status()
        if component_name == "performance_predictor":
            return self._require_component(
                self.performance_predictor, "performance_predictor"
            ).get_model_performance()
        return {"error": f"Unknown component: {component_name}"}

    def get_health_snapshot(self) -> dict[str, Any]:
        """Collect a consolidated health snapshot."""
        storage = getattr(self.base_optimizer, "storage", None)
        return collect_health_snapshot(
            registry=self.base_optimizer.registry,
            tracker=self.base_optimizer.tracker,
            storage=storage,
            realtime_system=self,
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform a comprehensive health check."""
        health_status: dict[str, Any] = {
            "overall": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Check each component
        components: list[tuple[str, Optional[Any]]] = [
            ("live_optimizer", self.live_optimizer),
            ("streaming_engine", self.streaming_engine),
            ("real_time_monitor", self.real_time_monitor),
            ("websocket_server", self.websocket_server),
            ("hot_swapper", self.hot_swapper),
            ("performance_predictor", self.performance_predictor),
        ]

        for name, component in components:
            if component is None:
                health_status["components"][name] = {
                    "status": "uninitialized",
                    "details": None,
                }
                health_status["overall"] = "degraded"
                continue

            try:
                if hasattr(component, "get_optimization_status"):
                    status = component.get_optimization_status()
                elif hasattr(component, "get_processing_stats"):
                    status = component.get_processing_stats()
                elif hasattr(component, "get_monitoring_stats"):
                    status = component.get_monitoring_stats()
                elif hasattr(component, "get_server_stats"):
                    status = component.get_server_stats()
                elif hasattr(component, "get_swap_status"):
                    status = component.get_swap_status()
                elif hasattr(component, "get_model_performance"):
                    status = component.get_model_performance()
                else:
                    status = {"status": "unknown"}

                health_status["components"][name] = {
                    "status": "healthy",
                    "details": status,
                }

            except Exception as e:
                health_status["components"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["overall"] = "degraded"

        return health_status
