"""Real-Time Monitor - Live Performance Tracking.

Provides real-time monitoring and visualization of prompt optimization
performance with live dashboards and alerting capabilities.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque
import statistics

from forge.core.logger import forge_logger as logger
from forge.prompt_optimization.models import PromptVariant, PromptMetrics


class AlertLevel(Enum):
    """Alert levels for monitoring."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics being monitored."""
    SUCCESS_RATE = "success_rate"
    EXECUTION_TIME = "execution_time"
    ERROR_RATE = "error_rate"
    TOKEN_COST = "token_cost"
    COMPOSITE_SCORE = "composite_score"
    OPTIMIZATION_FREQUENCY = "optimization_frequency"
    VARIANT_SWITCHES = "variant_switches"


@dataclass
class MonitoringAlert:
    """A monitoring alert."""
    alert_id: str
    level: AlertLevel
    metric_type: MetricType
    prompt_id: str
    message: str
    timestamp: datetime
    value: float
    threshold: float
    metadata: Dict[str, Any] = None


@dataclass
class MetricSnapshot:
    """A snapshot of metrics at a point in time."""
    timestamp: datetime
    prompt_id: str
    variant_id: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = None


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""
    prompt_id: str
    metric_type: MetricType
    trend_direction: str  # 'up', 'down', 'stable'
    trend_strength: float  # 0-1
    change_percentage: float
    confidence: float
    time_window: str


class RealTimeMonitor:
    """Real-Time Monitor - Live performance tracking and alerting.
    
    Features:
    - Real-time metric collection
    - Live dashboards
    - Alerting system
    - Trend analysis
    - Performance visualization
    - Historical data storage
    """

    def __init__(
        self,
        update_interval: float = 1.0,  # seconds
        alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        max_history_size: int = 10000,
        trend_window_size: int = 100
    ):
        """Configure monitoring cadence, thresholds, and initialize storage structures."""
        self.update_interval = update_interval
        self.alert_thresholds = alert_thresholds or self._get_default_thresholds()
        self.max_history_size = max_history_size
        self.trend_window_size = trend_window_size
        
        # Monitoring state
        self.is_running = False
        self.monitoring_task = None
        self.monitoring_lock = threading.RLock()
        
        # Metric storage
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.current_metrics: Dict[str, Dict[str, float]] = {}
        self.performance_trends: Dict[str, Dict[MetricType, PerformanceTrend]] = defaultdict(dict)
        
        # Alerting
        self.active_alerts: Dict[str, MonitoringAlert] = {}
        self.alert_history: List[MonitoringAlert] = []
        self.alert_handlers: List[Callable] = []
        
        # Monitoring callbacks
        self.metric_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.alert_callbacks: List[Callable] = []
        
        # Statistics
        self.monitoring_stats = {
            'snapshots_collected': 0,
            'alerts_generated': 0,
            'trends_analyzed': 0,
            'avg_processing_time': 0.0,
            'last_update': None
        }
        
        logger.info("Real-Time Monitor initialized")

    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default alert thresholds."""
        return {
            'success_rate': {
                'warning': 0.7,
                'error': 0.5,
                'critical': 0.3
            },
            'execution_time': {
                'warning': 10.0,  # seconds
                'error': 30.0,
                'critical': 60.0
            },
            'error_rate': {
                'warning': 0.1,
                'error': 0.2,
                'critical': 0.4
            },
            'composite_score': {
                'warning': 0.6,
                'error': 0.4,
                'critical': 0.2
            }
        }

    def start(self) -> None:
        """Start the real-time monitor."""
        if self.is_running:
            logger.warning("Real-time monitor is already running")
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Real-time monitor started")

    def stop(self) -> None:
        """Stop the real-time monitor."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("Real-time monitor stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Collect current metrics
                await self._collect_current_metrics()
                
                # Analyze trends
                await self._analyze_trends()
                
                # Check for alerts
                await self._check_alerts()
                
                # Update statistics
                self._update_monitoring_stats(time.time() - start_time)
                
                # Sleep until next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1.0)

    async def _collect_current_metrics(self) -> None:
        """Collect current metrics from all active prompts."""
        # This would typically collect from a metrics store
        # For now, we'll simulate metric collection
        
        # Get all active prompts (this would come from the registry)
        active_prompts = self._get_active_prompts()
        
        for prompt_id in active_prompts:
            # Simulate metric collection
            metrics = await self._simulate_metric_collection(prompt_id)
            
            if metrics:
                # Store metrics
                snapshot = MetricSnapshot(
                    timestamp=datetime.now(),
                    prompt_id=prompt_id,
                    variant_id=metrics.get('variant_id', 'unknown'),
                    metrics=metrics
                )
                
                self._store_metric_snapshot(snapshot)
                
                # Update current metrics
                self.current_metrics[prompt_id] = metrics
                
                # Trigger metric callbacks
                await self._trigger_metric_callbacks(prompt_id, metrics)

    async def _simulate_metric_collection(self, prompt_id: str) -> Dict[str, float]:
        """Simulate metric collection for a prompt."""
        # In a real implementation, this would collect actual metrics
        # For now, we'll return simulated data
        
        import random
        
        return {
            'variant_id': f'variant_{random.randint(1, 10)}',
            'success_rate': random.uniform(0.5, 1.0),
            'execution_time': random.uniform(0.5, 5.0),
            'error_rate': random.uniform(0.0, 0.2),
            'token_cost': random.uniform(0.001, 0.01),
            'composite_score': random.uniform(0.3, 1.0),
            'sample_count': random.randint(1, 100)
        }

    def _get_active_prompts(self) -> List[str]:
        """Get list of active prompts being monitored."""
        # This would typically come from the prompt registry
        # For now, return a static list
        return ['prompt_1', 'prompt_2', 'prompt_3']

    def _store_metric_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Store a metric snapshot in history."""
        key = f"{snapshot.prompt_id}_{snapshot.variant_id}"
        
        with self.monitoring_lock:
            self.metric_history[key].append(snapshot)
            self.monitoring_stats['snapshots_collected'] += 1

    async def _analyze_trends(self) -> None:
        """Analyze performance trends for all prompts."""
        for prompt_id in self.current_metrics.keys():
            for metric_type in MetricType:
                trend = await self._analyze_metric_trend(prompt_id, metric_type)
                if trend:
                    self.performance_trends[prompt_id][metric_type] = trend
                    self.monitoring_stats['trends_analyzed'] += 1

    async def _analyze_metric_trend(
        self, 
        prompt_id: str, 
        metric_type: MetricType
    ) -> Optional[PerformanceTrend]:
        """Analyze trend for a specific metric."""
        # Get metric history
        metric_key = f"{prompt_id}_*"  # Match all variants
        metric_data = []
        
        for key, history in self.metric_history.items():
            if key.startswith(f"{prompt_id}_"):
                for snapshot in history:
                    if metric_type.value in snapshot.metrics:
                        metric_data.append({
                            'timestamp': snapshot.timestamp,
                            'value': snapshot.metrics[metric_type.value]
                        })
        
        if len(metric_data) < 10:  # Need enough data for trend analysis
            return None
        
        # Sort by timestamp
        metric_data.sort(key=lambda x: x['timestamp'])
        
        # Get recent data for trend analysis
        recent_data = metric_data[-self.trend_window_size:]
        values = [d['value'] for d in recent_data]
        
        if len(values) < 5:
            return None
        
        # Calculate trend
        trend_direction, trend_strength, change_percentage = self._calculate_trend(values)
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_trend_confidence(values)
        
        return PerformanceTrend(
            prompt_id=prompt_id,
            metric_type=metric_type,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            change_percentage=change_percentage,
            confidence=confidence,
            time_window=f"{len(recent_data)}_samples"
        )

    def _calculate_trend(self, values: List[float]) -> tuple[str, float, float]:
        """Calculate trend direction, strength, and change percentage."""
        if len(values) < 2:
            return 'stable', 0.0, 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Determine direction
        if slope > 0.01:
            direction = 'up'
        elif slope < -0.01:
            direction = 'down'
        else:
            direction = 'stable'
        
        # Calculate strength (0-1)
        strength = min(1.0, abs(slope) * 10)
        
        # Calculate change percentage
        first_value = values[0]
        last_value = values[-1]
        if first_value != 0:
            change_percentage = ((last_value - first_value) / first_value) * 100
        else:
            change_percentage = 0.0
        
        return direction, strength, change_percentage

    def _calculate_trend_confidence(self, values: List[float]) -> float:
        """Calculate confidence in trend analysis."""
        if len(values) < 3:
            return 0.0
        
        # Calculate coefficient of variation
        mean_value = statistics.mean(values)
        if mean_value == 0:
            return 0.0
        
        std_value = statistics.stdev(values)
        cv = std_value / mean_value
        
        # Lower CV = higher confidence
        confidence = max(0.0, 1.0 - cv)
        
        return confidence

    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        for prompt_id, metrics in self.current_metrics.items():
            for metric_name, value in metrics.items():
                if metric_name in self.alert_thresholds:
                    await self._check_metric_alert(prompt_id, metric_name, value)

    async def _check_metric_alert(self, prompt_id: str, metric_name: str, value: float) -> None:
        """Check for alerts on a specific metric."""
        thresholds = self.alert_thresholds[metric_name]
        
        # Determine alert level
        alert_level = None
        if value <= thresholds.get('critical', float('inf')):
            alert_level = AlertLevel.CRITICAL
        elif value <= thresholds.get('error', float('inf')):
            alert_level = AlertLevel.ERROR
        elif value <= thresholds.get('warning', float('inf')):
            alert_level = AlertLevel.WARNING
        
        if alert_level:
            # Check if alert already exists
            alert_key = f"{prompt_id}_{metric_name}_{alert_level.value}"
            
            if alert_key not in self.active_alerts:
                # Create new alert
                alert = MonitoringAlert(
                    alert_id=f"alert_{int(time.time() * 1000)}_{prompt_id}",
                    level=alert_level,
                    metric_type=MetricType(metric_name),
                    prompt_id=prompt_id,
                    message=f"{metric_name} is {value:.3f}, below {alert_level.value} threshold",
                    timestamp=datetime.now(),
                    value=value,
                    threshold=thresholds[alert_level.value],
                    metadata={'metric_name': metric_name}
                )
                
                self.active_alerts[alert_key] = alert
                self.alert_history.append(alert)
                self.monitoring_stats['alerts_generated'] += 1
                
                # Trigger alert callbacks
                await self._trigger_alert_callbacks(alert)
                
                logger.warning(f"Alert generated: {alert.message}")

    async def _trigger_metric_callbacks(self, prompt_id: str, metrics: Dict[str, float]) -> None:
        """Trigger metric callbacks."""
        callbacks = self.metric_callbacks.get(prompt_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(prompt_id, metrics)
                else:
                    callback(prompt_id, metrics)
            except Exception as e:
                logger.error(f"Error in metric callback: {e}")

    async def _trigger_alert_callbacks(self, alert: MonitoringAlert) -> None:
        """Trigger alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _update_monitoring_stats(self, processing_time: float) -> None:
        """Update monitoring statistics."""
        with self.monitoring_lock:
            # Update average processing time
            total_snapshots = self.monitoring_stats['snapshots_collected']
            if total_snapshots > 0:
                current_avg = self.monitoring_stats['avg_processing_time']
                self.monitoring_stats['avg_processing_time'] = (
                    (current_avg * (total_snapshots - 1) + processing_time) / total_snapshots
                )
            
            self.monitoring_stats['last_update'] = datetime.now()

    # Public API methods

    def add_metric_callback(self, prompt_id: str, callback: Callable) -> None:
        """Add a callback for metric updates."""
        self.metric_callbacks[prompt_id].append(callback)

    def remove_metric_callback(self, prompt_id: str, callback: Callable) -> None:
        """Remove a metric callback."""
        if callback in self.metric_callbacks[prompt_id]:
            self.metric_callbacks[prompt_id].remove(callback)

    def add_alert_callback(self, callback: Callable) -> None:
        """Add a callback for alerts."""
        self.alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable) -> None:
        """Remove an alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)

    def get_current_metrics(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current metrics for a prompt or all prompts."""
        if prompt_id:
            return self.current_metrics.get(prompt_id, {})
        return self.current_metrics.copy()

    def get_metric_history(
        self, 
        prompt_id: str, 
        variant_id: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        limit: int = 100
    ) -> List[MetricSnapshot]:
        """Get metric history for a prompt."""
        key = f"{prompt_id}_{variant_id}" if variant_id else f"{prompt_id}_*"
        
        all_snapshots = []
        for history_key, history in self.metric_history.items():
            if history_key.startswith(f"{prompt_id}_"):
                if not variant_id or history_key.endswith(f"_{variant_id}"):
                    all_snapshots.extend(history)
        
        # Sort by timestamp
        all_snapshots.sort(key=lambda x: x.timestamp)
        
        # Filter by metric type if specified
        if metric_type:
            filtered_snapshots = []
            for snapshot in all_snapshots:
                if metric_type.value in snapshot.metrics:
                    filtered_snapshots.append(snapshot)
            all_snapshots = filtered_snapshots
        
        # Limit results
        return all_snapshots[-limit:] if limit else all_snapshots

    def get_performance_trends(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance trends for a prompt or all prompts."""
        if prompt_id:
            trends = self.performance_trends.get(prompt_id, {})
            return {metric_type.value: asdict(trend) for metric_type, trend in trends.items()}
        
        all_trends = {}
        for pid, trends in self.performance_trends.items():
            all_trends[pid] = {metric_type.value: asdict(trend) for metric_type, trend in trends.items()}
        
        return all_trends

    def get_active_alerts(self, prompt_id: Optional[str] = None) -> List[MonitoringAlert]:
        """Get active alerts for a prompt or all prompts."""
        if prompt_id:
            return [alert for alert in self.active_alerts.values() if alert.prompt_id == prompt_id]
        return list(self.active_alerts.values())

    def get_alert_history(
        self, 
        prompt_id: Optional[str] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[MonitoringAlert]:
        """Get alert history."""
        alerts = self.alert_history
        
        if prompt_id:
            alerts = [alert for alert in alerts if alert.prompt_id == prompt_id]
        
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit] if limit else alerts

    def clear_alert(self, alert_id: str) -> bool:
        """Clear an active alert."""
        for key, alert in list(self.active_alerts.items()):
            if alert.alert_id == alert_id:
                del self.active_alerts[key]
                return True
        return False

    def clear_all_alerts(self, prompt_id: Optional[str] = None) -> int:
        """Clear all alerts for a prompt or all prompts."""
        cleared_count = 0
        
        if prompt_id:
            keys_to_remove = [
                key for key, alert in self.active_alerts.items() 
                if alert.prompt_id == prompt_id
            ]
        else:
            keys_to_remove = list(self.active_alerts.keys())
        
        for key in keys_to_remove:
            del self.active_alerts[key]
            cleared_count += 1
        
        return cleared_count

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        with self.monitoring_lock:
            return {
                'is_running': self.is_running,
                'update_interval': self.update_interval,
                'max_history_size': self.max_history_size,
                'trend_window_size': self.trend_window_size,
                'stats': self.monitoring_stats.copy(),
                'active_prompts': len(self.current_metrics),
                'active_alerts': len(self.active_alerts),
                'total_alerts': len(self.alert_history),
                'metric_history_size': sum(len(h) for h in self.metric_history.values())
            }

    def set_alert_thresholds(self, thresholds: Dict[str, Dict[str, float]]) -> None:
        """Update alert thresholds."""
        self.alert_thresholds.update(thresholds)
        logger.info("Alert thresholds updated")

    def export_metrics(self, prompt_id: str, filepath: str) -> None:
        """Export metrics to a file."""
        history = self.get_metric_history(prompt_id)
        
        export_data = {
            'prompt_id': prompt_id,
            'export_timestamp': datetime.now().isoformat(),
            'metrics': [asdict(snapshot) for snapshot in history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {filepath}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard visualization."""
        return {
            'current_metrics': self.current_metrics,
            'performance_trends': self.get_performance_trends(),
            'active_alerts': [asdict(alert) for alert in self.get_active_alerts()],
            'monitoring_stats': self.get_monitoring_stats(),
            'recent_alerts': [asdict(alert) for alert in self.get_alert_history(limit=10)]
        }
