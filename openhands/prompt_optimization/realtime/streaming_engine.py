"""
Streaming Optimization Engine - Real-Time Data Processing

Processes streaming data in real-time to enable instant optimization decisions
and continuous improvement of prompt performance.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from datetime import datetime, timedelta
import threading
from collections import deque
import statistics

from openhands.core.logger import openhands_logger as logger
from openhands.prompt_optimization.models import PromptVariant, PromptMetrics


class StreamEventType(Enum):
    """Types of streaming events."""
    METRICS_UPDATE = "metrics_update"
    VARIANT_SWITCH = "variant_switch"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    CONTEXT_CHANGE = "context_change"
    USER_INTERACTION = "user_interaction"
    SYSTEM_ALERT = "system_alert"


@dataclass
class StreamEvent:
    """A streaming event."""
    event_id: str
    event_type: StreamEventType
    timestamp: datetime
    prompt_id: str
    data: Dict[str, Any]
    priority: int = 5  # 1-10, higher = more urgent


@dataclass
class StreamProcessingResult:
    """Result of stream processing."""
    event_id: str
    processed: bool
    actions_taken: List[str]
    optimization_triggered: bool
    processing_time: float
    metadata: Dict[str, Any] = None


class StreamingOptimizationEngine:
    """
    Streaming Optimization Engine - Real-time data processing for optimization.
    
    Features:
    - Real-time event processing
    - Streaming data analysis
    - Anomaly detection
    - Pattern recognition
    - Continuous optimization
    - Event-driven architecture
    """

    def __init__(
        self,
        live_optimizer,
        max_queue_size: int = 10000,
        processing_batch_size: int = 100,
        processing_interval: float = 0.1,
        anomaly_threshold: float = 2.0,  # Standard deviations
        pattern_window_size: int = 100
    ):
        self.live_optimizer = live_optimizer
        self.max_queue_size = max_queue_size
        self.processing_batch_size = processing_batch_size
        self.processing_interval = processing_interval
        self.anomaly_threshold = anomaly_threshold
        self.pattern_window_size = pattern_window_size
        
        # Event processing
        self.event_queue: deque = deque(maxlen=max_queue_size)
        self.processing_lock = threading.RLock()
        self.is_running = False
        self.processing_task = None
        
        # Event handlers
        self.event_handlers: Dict[StreamEventType, List[Callable]] = {
            event_type: [] for event_type in StreamEventType
        }
        
        # Performance tracking
        self.performance_history: Dict[str, deque] = {}
        self.anomaly_detectors: Dict[str, Any] = {}
        
        # Pattern recognition
        self.pattern_buffers: Dict[str, deque] = {}
        self.pattern_detectors: Dict[str, Callable] = {}
        
        # Statistics
        self.processing_stats = {
            'events_processed': 0,
            'events_dropped': 0,
            'optimizations_triggered': 0,
            'anomalies_detected': 0,
            'patterns_recognized': 0,
            'avg_processing_time': 0.0,
            'queue_size': 0
        }
        
        logger.info("Streaming Optimization Engine initialized")

    def start(self) -> None:
        """Start the streaming engine."""
        if self.is_running:
            logger.warning("Streaming engine is already running")
            return
        
        self.is_running = True
        self.processing_task = asyncio.create_task(self._processing_loop())
        logger.info("Streaming optimization engine started")

    def stop(self) -> None:
        """Stop the streaming engine."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
        logger.info("Streaming optimization engine stopped")

    async def _processing_loop(self) -> None:
        """Main processing loop for streaming events."""
        while self.is_running:
            try:
                # Process events in batches
                await self._process_event_batch()
                
                # Update statistics
                self._update_processing_stats()
                
                # Sleep briefly to prevent excessive CPU usage
                await asyncio.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1.0)

    async def _process_event_batch(self) -> None:
        """Process a batch of events from the queue."""
        with self.processing_lock:
            if not self.event_queue:
                return
            
            # Get batch of events
            batch_size = min(self.processing_batch_size, len(self.event_queue))
            events_to_process = []
            
            for _ in range(batch_size):
                if self.event_queue:
                    events_to_process.append(self.event_queue.popleft())
            
            if not events_to_process:
                return
        
        # Process events concurrently
        tasks = []
        for event in events_to_process:
            task = asyncio.create_task(self._process_single_event(event))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Event processing error: {result}")
                else:
                    self.processing_stats['events_processed'] += 1

    async def _process_single_event(self, event: StreamEvent) -> StreamProcessingResult:
        """Process a single streaming event."""
        start_time = time.time()
        
        try:
            # Update performance history
            self._update_performance_history(event)
            
            # Detect anomalies
            anomaly_detected = await self._detect_anomalies(event)
            
            # Recognize patterns
            patterns = await self._recognize_patterns(event)
            
            # Process event based on type
            actions_taken = []
            optimization_triggered = False
            
            if event.event_type == StreamEventType.METRICS_UPDATE:
                actions_taken.extend(await self._handle_metrics_update(event))
            elif event.event_type == StreamEventType.VARIANT_SWITCH:
                actions_taken.extend(await self._handle_variant_switch(event))
            elif event.event_type == StreamEventType.PERFORMANCE_ANOMALY:
                actions_taken.extend(await self._handle_performance_anomaly(event))
            elif event.event_type == StreamEventType.CONTEXT_CHANGE:
                actions_taken.extend(await self._handle_context_change(event))
            elif event.event_type == StreamEventType.USER_INTERACTION:
                actions_taken.extend(await self._handle_user_interaction(event))
            elif event.event_type == StreamEventType.SYSTEM_ALERT:
                actions_taken.extend(await self._handle_system_alert(event))
            
            # Check if optimization should be triggered
            if anomaly_detected or patterns:
                optimization_triggered = await self._trigger_optimization_if_needed(event)
                if optimization_triggered:
                    self.processing_stats['optimizations_triggered'] += 1
            
            # Trigger event handlers
            await self._trigger_event_handlers(event, actions_taken)
            
            processing_time = time.time() - start_time
            
            return StreamProcessingResult(
                event_id=event.event_id,
                processed=True,
                actions_taken=actions_taken,
                optimization_triggered=optimization_triggered,
                processing_time=processing_time,
                metadata={
                    'anomaly_detected': anomaly_detected,
                    'patterns_recognized': len(patterns) if patterns else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
            return StreamProcessingResult(
                event_id=event.event_id,
                processed=False,
                actions_taken=[],
                optimization_triggered=False,
                processing_time=time.time() - start_time,
                metadata={'error': str(e)}
            )

    def _update_performance_history(self, event: StreamEvent) -> None:
        """Update performance history for pattern recognition."""
        prompt_id = event.prompt_id
        
        if prompt_id not in self.performance_history:
            self.performance_history[prompt_id] = deque(maxlen=self.pattern_window_size)
        
        # Extract performance metrics from event data
        if 'metrics' in event.data:
            metrics = event.data['metrics']
            if 'composite_score' in metrics:
                self.performance_history[prompt_id].append(metrics['composite_score'])
            elif 'success_rate' in metrics:
                self.performance_history[prompt_id].append(metrics['success_rate'])

    async def _detect_anomalies(self, event: StreamEvent) -> bool:
        """Detect performance anomalies in the event."""
        prompt_id = event.prompt_id
        
        if prompt_id not in self.performance_history:
            return False
        
        history = list(self.performance_history[prompt_id])
        if len(history) < 10:  # Need enough data for anomaly detection
            return False
        
        # Simple statistical anomaly detection
        if 'metrics' in event.data:
            metrics = event.data['metrics']
            current_value = metrics.get('composite_score', metrics.get('success_rate', 0))
            
            if current_value:
                mean_value = statistics.mean(history)
                std_value = statistics.stdev(history) if len(history) > 1 else 0
                
                if std_value > 0:
                    z_score = abs(current_value - mean_value) / std_value
                    
                    if z_score > self.anomaly_threshold:
                        logger.warning(f"Performance anomaly detected for {prompt_id}: z-score={z_score:.2f}")
                        self.processing_stats['anomalies_detected'] += 1
                        return True
        
        return False

    async def _recognize_patterns(self, event: StreamEvent) -> List[str]:
        """Recognize patterns in the event stream."""
        prompt_id = event.prompt_id
        patterns = []
        
        if prompt_id not in self.pattern_buffers:
            self.pattern_buffers[prompt_id] = deque(maxlen=self.pattern_window_size)
        
        # Add event to pattern buffer
        self.pattern_buffers[prompt_id].append(event)
        
        # Check for known patterns
        pattern_detector = self.pattern_detectors.get(prompt_id)
        if pattern_detector:
            detected_patterns = pattern_detector(list(self.pattern_buffers[prompt_id]))
            patterns.extend(detected_patterns)
        
        # Check for common patterns
        patterns.extend(await self._check_common_patterns(prompt_id))
        
        if patterns:
            self.processing_stats['patterns_recognized'] += len(patterns)
        
        return patterns

    async def _check_common_patterns(self, prompt_id: str) -> List[str]:
        """Check for common performance patterns."""
        patterns = []
        
        if prompt_id not in self.performance_history:
            return patterns
        
        history = list(self.performance_history[prompt_id])
        if len(history) < 20:
            return patterns
        
        # Check for declining performance trend
        recent_10 = history[-10:]
        older_10 = history[-20:-10]
        
        if len(recent_10) >= 10 and len(older_10) >= 10:
            recent_avg = statistics.mean(recent_10)
            older_avg = statistics.mean(older_10)
            
            if recent_avg < older_avg - 0.1:  # 10% decline
                patterns.append('declining_performance')
        
        # Check for cyclical patterns
        if len(history) >= 50:
            # Simple cycle detection
            cycle_length = 10
            cycles = []
            for i in range(cycle_length, len(history) - cycle_length):
                cycle_data = history[i-cycle_length:i+cycle_length]
                if len(cycle_data) == cycle_length * 2:
                    cycles.append(cycle_data)
            
            if len(cycles) >= 3:
                # Check if cycles are similar
                cycle_similarity = self._calculate_cycle_similarity(cycles)
                if cycle_similarity > 0.8:
                    patterns.append('cyclical_performance')
        
        return patterns

    def _calculate_cycle_similarity(self, cycles: List[List[float]]) -> float:
        """Calculate similarity between performance cycles."""
        if len(cycles) < 2:
            return 0.0
        
        similarities = []
        for i in range(len(cycles) - 1):
            cycle1 = cycles[i]
            cycle2 = cycles[i + 1]
            
            if len(cycle1) == len(cycle2):
                # Calculate correlation
                correlation = self._calculate_correlation(cycle1, cycle2)
                similarities.append(abs(correlation))
        
        return statistics.mean(similarities) if similarities else 0.0

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate correlation coefficient between two lists."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        sum_y2 = sum(y[i] ** 2 for i in range(n))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator

    async def _handle_metrics_update(self, event: StreamEvent) -> List[str]:
        """Handle metrics update events."""
        actions = []
        
        # Check if optimization is needed based on metrics
        metrics = event.data.get('metrics', {})
        if 'composite_score' in metrics:
            score = metrics['composite_score']
            if score < 0.6:  # Low performance threshold
                actions.append('low_performance_detected')
        
        return actions

    async def _handle_variant_switch(self, event: StreamEvent) -> List[str]:
        """Handle variant switch events."""
        actions = []
        
        # Log the switch
        from_variant = event.data.get('from_variant_id')
        to_variant = event.data.get('to_variant_id')
        
        if from_variant and to_variant:
            actions.append(f'switched_from_{from_variant}_to_{to_variant}')
        
        return actions

    async def _handle_performance_anomaly(self, event: StreamEvent) -> List[str]:
        """Handle performance anomaly events."""
        actions = []
        
        # Anomaly-specific handling
        anomaly_type = event.data.get('anomaly_type', 'unknown')
        actions.append(f'anomaly_handled_{anomaly_type}')
        
        return actions

    async def _handle_context_change(self, event: StreamEvent) -> List[str]:
        """Handle context change events."""
        actions = []
        
        # Context change might require different optimization strategy
        old_context = event.data.get('old_context', {})
        new_context = event.data.get('new_context', {})
        
        if old_context != new_context:
            actions.append('context_change_processed')
        
        return actions

    async def _handle_user_interaction(self, event: StreamEvent) -> List[str]:
        """Handle user interaction events."""
        actions = []
        
        # User interactions might provide feedback for optimization
        interaction_type = event.data.get('interaction_type', 'unknown')
        actions.append(f'user_interaction_{interaction_type}_processed')
        
        return actions

    async def _handle_system_alert(self, event: StreamEvent) -> List[str]:
        """Handle system alert events."""
        actions = []
        
        # System alerts might require immediate attention
        alert_level = event.data.get('alert_level', 'info')
        actions.append(f'system_alert_{alert_level}_processed')
        
        return actions

    async def _trigger_optimization_if_needed(self, event: StreamEvent) -> bool:
        """Trigger optimization if conditions are met."""
        try:
            # Check if optimization should be triggered
            should_optimize = False
            
            # Check for performance issues
            if 'metrics' in event.data:
                metrics = event.data['metrics']
                if metrics.get('composite_score', 1.0) < 0.7:
                    should_optimize = True
            
            # Check for anomalies
            if event.event_type == StreamEventType.PERFORMANCE_ANOMALY:
                should_optimize = True
            
            if should_optimize:
                # Trigger optimization
                await self.live_optimizer.trigger_optimization(
                    prompt_id=event.prompt_id,
                    trigger='performance_anomaly',
                    priority=8,
                    context=event.data
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error triggering optimization: {e}")
            return False

    async def _trigger_event_handlers(self, event: StreamEvent, actions: List[str]) -> None:
        """Trigger event handlers for the processed event."""
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, actions)
                else:
                    handler(event, actions)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def _update_processing_stats(self) -> None:
        """Update processing statistics."""
        with self.processing_lock:
            self.processing_stats['queue_size'] = len(self.event_queue)
            
            # Update average processing time
            if self.processing_stats['events_processed'] > 0:
                # This would be calculated from actual processing times
                pass

    # Public API methods

    async def add_event(
        self,
        event_type: StreamEventType,
        prompt_id: str,
        data: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """Add an event to the processing queue."""
        event_id = f"stream_{int(time.time() * 1000)}_{prompt_id}"
        
        event = StreamEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            prompt_id=prompt_id,
            data=data,
            priority=priority
        )
        
        with self.processing_lock:
            if len(self.event_queue) >= self.max_queue_size:
                # Drop oldest event
                self.event_queue.popleft()
                self.processing_stats['events_dropped'] += 1
            
            self.event_queue.append(event)
        
        logger.debug(f"Added event to queue: {event_id}")
        return event_id

    def add_event_handler(self, event_type: StreamEventType, handler: Callable) -> None:
        """Add an event handler for a specific event type."""
        self.event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: StreamEventType, handler: Callable) -> None:
        """Remove an event handler."""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)

    def add_pattern_detector(self, prompt_id: str, detector: Callable) -> None:
        """Add a custom pattern detector for a specific prompt."""
        self.pattern_detectors[prompt_id] = detector

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        with self.processing_lock:
            return {
                'is_running': self.is_running,
                'queue_size': len(self.event_queue),
                'max_queue_size': self.max_queue_size,
                'processing_batch_size': self.processing_batch_size,
                'processing_interval': self.processing_interval,
                'stats': self.processing_stats.copy(),
                'performance_history_size': sum(len(h) for h in self.performance_history.values()),
                'pattern_detectors': len(self.pattern_detectors)
            }

    def get_performance_history(self, prompt_id: str) -> List[float]:
        """Get performance history for a specific prompt."""
        return list(self.performance_history.get(prompt_id, []))

    def clear_performance_history(self, prompt_id: str = None) -> None:
        """Clear performance history for a prompt or all prompts."""
        if prompt_id:
            if prompt_id in self.performance_history:
                del self.performance_history[prompt_id]
        else:
            self.performance_history.clear()

    async def get_streaming_events(
        self, 
        prompt_id: str = None,
        event_type: StreamEventType = None,
        limit: int = 100
    ) -> AsyncGenerator[StreamEvent, None]:
        """Get streaming events as an async generator."""
        # This would typically connect to a real-time data source
        # For now, we'll return events from the pattern buffers
        count = 0
        for pid, buffer in self.pattern_buffers.items():
            if prompt_id and pid != prompt_id:
                continue
            
            for event in buffer:
                if event_type and event.event_type != event_type:
                    continue
                
                if count >= limit:
                    return
                
                yield event
                count += 1
