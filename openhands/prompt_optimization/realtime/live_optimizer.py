"""
Live Optimizer - The Heart of Real-Time Optimization

Provides instant, live optimization of prompts during execution with
zero downtime and seamless adaptation based on real-time performance.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

from openhands.core.logger import openhands_logger as logger
from openhands.prompt_optimization.models import PromptVariant, PromptMetrics, PromptCategory
from openhands.prompt_optimization.advanced import AdvancedStrategyManager
from openhands.prompt_optimization.optimizer import PromptOptimizer


class OptimizationTrigger(Enum):
    """Triggers for real-time optimization."""
    PERFORMANCE_DROP = "performance_drop"
    NEW_VARIANT_AVAILABLE = "new_variant_available"
    CONTEXT_CHANGE = "context_change"
    USER_REQUEST = "user_request"
    SCHEDULED = "scheduled"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class LiveOptimizationEvent:
    """Event for live optimization."""
    event_id: str
    trigger: OptimizationTrigger
    timestamp: datetime
    context: Dict[str, Any]
    priority: int  # 1-10, higher = more urgent
    metadata: Dict[str, Any] = None


@dataclass
class LiveOptimizationResult:
    """Result of live optimization."""
    event_id: str
    success: bool
    old_variant_id: str
    new_variant_id: str
    performance_improvement: float
    confidence: float
    execution_time: float
    metadata: Dict[str, Any] = None


class LiveOptimizer:
    """
    Live Optimizer - The most advanced real-time optimization engine.
    
    Features:
    - Zero-downtime prompt switching
    - Real-time performance monitoring
    - Instant adaptation based on live data
    - Predictive optimization
    - Hot-swapping capabilities
    - Streaming optimization
    """

    def __init__(
        self,
        strategy_manager: AdvancedStrategyManager,
        base_optimizer: PromptOptimizer,
        max_concurrent_optimizations: int = 5,
        optimization_threshold: float = 0.05,
        confidence_threshold: float = 0.8
    ):
        self.strategy_manager = strategy_manager
        self.base_optimizer = base_optimizer
        self.max_concurrent_optimizations = max_concurrent_optimizations
        self.optimization_threshold = optimization_threshold
        self.confidence_threshold = confidence_threshold
        
        # Real-time state
        self.active_optimizations: Dict[str, LiveOptimizationEvent] = {}
        self.optimization_queue: List[LiveOptimizationEvent] = []
        self.performance_cache: Dict[str, float] = {}
        self.variant_switches: Dict[str, List[LiveOptimizationResult]] = {}
        
        # Threading and async
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_optimizations)
        self.optimization_lock = threading.RLock()
        self.is_running = False
        self.optimization_task = None
        
        # Performance tracking
        self.optimization_stats = {
            'total_optimizations': 0,
            'successful_optimizations': 0,
            'failed_optimizations': 0,
            'avg_improvement': 0.0,
            'avg_execution_time': 0.0,
            'last_optimization': None
        }
        
        # Event handlers
        self.event_handlers: Dict[OptimizationTrigger, List[Callable]] = {
            trigger: [] for trigger in OptimizationTrigger
        }
        
        # Performance prediction
        self.performance_predictor = None  # Will be injected
        self.hot_swapper = None  # Will be injected
        
        logger.info("Live Optimizer initialized with real-time capabilities")

    def start(self) -> None:
        """Start the live optimization engine."""
        if self.is_running:
            logger.warning("Live optimizer is already running")
            return
        
        self.is_running = True
        self.optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info("Live optimization engine started")

    def stop(self) -> None:
        """Stop the live optimization engine."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.optimization_task:
            self.optimization_task.cancel()
        self.executor.shutdown(wait=True)
        logger.info("Live optimization engine stopped")

    async def _optimization_loop(self) -> None:
        """Main optimization loop running in background."""
        while self.is_running:
            try:
                # Process optimization queue
                await self._process_optimization_queue()
                
                # Update performance cache
                await self._update_performance_cache()
                
                # Check for optimization triggers
                await self._check_optimization_triggers()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Sleep briefly to prevent excessive CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(1.0)

    async def _process_optimization_queue(self) -> None:
        """Process pending optimization events."""
        with self.optimization_lock:
            if not self.optimization_queue:
                return
            
            # Sort by priority (higher first)
            self.optimization_queue.sort(key=lambda x: x.priority, reverse=True)
            
            # Process up to max concurrent optimizations
            events_to_process = self.optimization_queue[:self.max_concurrent_optimizations]
            self.optimization_queue = self.optimization_queue[self.max_concurrent_optimizations:]
            
            # Process events concurrently
            tasks = []
            for event in events_to_process:
                task = asyncio.create_task(self._process_optimization_event(event))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_optimization_event(self, event: LiveOptimizationEvent) -> None:
        """Process a single optimization event."""
        try:
            logger.info(f"Processing optimization event: {event.event_id}")
            
            # Check if we can optimize
            if not await self._can_optimize(event):
                logger.info(f"Cannot optimize for event {event.event_id}")
                return
            
            # Perform optimization
            result = await self._perform_live_optimization(event)
            
            # Update statistics
            self._update_optimization_stats(result)
            
            # Trigger event handlers
            await self._trigger_event_handlers(event, result)
            
            # Store result
            if event.event_id not in self.variant_switches:
                self.variant_switches[event.event_id] = []
            self.variant_switches[event.event_id].append(result)
            
            logger.info(f"Optimization completed for event {event.event_id}: {result.success}")
            
        except Exception as e:
            logger.error(f"Error processing optimization event {event.event_id}: {e}")
            self.optimization_stats['failed_optimizations'] += 1

    async def _can_optimize(self, event: LiveOptimizationEvent) -> bool:
        """Check if optimization can be performed for the event."""
        # Check if we have enough data
        context = event.context
        prompt_id = context.get('prompt_id')
        
        if not prompt_id:
            return False
        
        # Check performance threshold
        current_performance = self.performance_cache.get(prompt_id, 0.0)
        if current_performance < self.optimization_threshold:
            return False
        
        # Check if optimization is already in progress
        if prompt_id in self.active_optimizations:
            return False
        
        return True

    async def _perform_live_optimization(self, event: LiveOptimizationEvent) -> LiveOptimizationResult:
        """Perform live optimization for an event."""
        start_time = time.time()
        context = event.context
        prompt_id = context.get('prompt_id')
        
        try:
            # Get current variant
            current_variant = self.base_optimizer.registry.get_active_variant(prompt_id)
            if not current_variant:
                raise ValueError(f"No active variant found for prompt {prompt_id}")
            
            # Select optimization strategy
            strategy_selection = self.strategy_manager.select_strategy(context)
            
            # Get available variants
            available_variants = self.base_optimizer.registry.get_all_variants(prompt_id)
            if len(available_variants) < 2:
                raise ValueError(f"Not enough variants for optimization: {len(available_variants)}")
            
            # Get metrics for all variants
            metrics = {}
            for variant in available_variants:
                variant_metrics = self.base_optimizer.tracker.get_metrics(prompt_id, variant.id)
                if variant_metrics:
                    metrics[variant.id] = variant_metrics
            
            if not metrics:
                raise ValueError("No metrics available for optimization")
            
            # Select best variant using strategy
            best_variant = self._select_best_variant(
                available_variants, 
                metrics, 
                strategy_selection,
                context
            )
            
            if not best_variant or best_variant.id == current_variant.id:
                # No improvement possible
                return LiveOptimizationResult(
                    event_id=event.event_id,
                    success=False,
                    old_variant_id=current_variant.id,
                    new_variant_id=current_variant.id,
                    performance_improvement=0.0,
                    confidence=0.0,
                    execution_time=time.time() - start_time,
                    metadata={'reason': 'no_improvement_possible'}
                )
            
            # Calculate performance improvement
            current_score = metrics.get(current_variant.id, PromptMetrics()).composite_score
            new_score = metrics.get(best_variant.id, PromptMetrics()).composite_score
            improvement = new_score - current_score
            
            # Check confidence threshold
            confidence = self._calculate_confidence(metrics, current_variant.id, best_variant.id)
            
            if confidence < self.confidence_threshold:
                return LiveOptimizationResult(
                    event_id=event.event_id,
                    success=False,
                    old_variant_id=current_variant.id,
                    new_variant_id=best_variant.id,
                    performance_improvement=improvement,
                    confidence=confidence,
                    execution_time=time.time() - start_time,
                    metadata={'reason': 'low_confidence'}
                )
            
            # Perform hot swap
            if self.hot_swapper:
                swap_success = await self.hot_swapper.hot_swap(
                    prompt_id, 
                    current_variant.id, 
                    best_variant.id
                )
            else:
                # Fallback to regular swap
                self.base_optimizer.registry.set_active_variant(prompt_id, best_variant.id)
                swap_success = True
            
            if not swap_success:
                raise Exception("Hot swap failed")
            
            # Update performance cache
            self.performance_cache[prompt_id] = new_score
            
            return LiveOptimizationResult(
                event_id=event.event_id,
                success=True,
                old_variant_id=current_variant.id,
                new_variant_id=best_variant.id,
                performance_improvement=improvement,
                confidence=confidence,
                execution_time=time.time() - start_time,
                metadata={
                    'strategy_used': strategy_selection.selected_strategy,
                    'strategy_confidence': strategy_selection.confidence,
                    'variants_evaluated': len(available_variants)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in live optimization: {e}")
            return LiveOptimizationResult(
                event_id=event.event_id,
                success=False,
                old_variant_id=context.get('current_variant_id', 'unknown'),
                new_variant_id=context.get('current_variant_id', 'unknown'),
                performance_improvement=0.0,
                confidence=0.0,
                execution_time=time.time() - start_time,
                metadata={'error': str(e)}
            )

    def _select_best_variant(
        self, 
        variants: List[PromptVariant], 
        metrics: Dict[str, PromptMetrics],
        strategy_selection: Any,
        context: Dict[str, Any]
    ) -> Optional[PromptVariant]:
        """Select the best variant using the selected strategy."""
        if not variants or not metrics:
            return None
        
        # Use the selected strategy to choose variant
        strategy_name = strategy_selection.selected_strategy
        strategy = self.strategy_manager.strategies.get(strategy_name)
        
        if not strategy:
            # Fallback to simple selection
            return max(variants, key=lambda v: metrics.get(v.id, PromptMetrics()).composite_score)
        
        # Use strategy-specific selection
        if hasattr(strategy, 'select_variant_for_exploitation'):
            return strategy.select_variant_for_exploitation(variants, metrics)
        elif hasattr(strategy, 'select_variant'):
            return strategy.select_variant(variants, metrics)
        else:
            # Fallback
            return max(variants, key=lambda v: metrics.get(v.id, PromptMetrics()).composite_score)

    def _calculate_confidence(
        self, 
        metrics: Dict[str, PromptMetrics], 
        current_variant_id: str, 
        new_variant_id: str
    ) -> float:
        """Calculate confidence in the optimization decision."""
        current_metrics = metrics.get(current_variant_id)
        new_metrics = metrics.get(new_variant_id)
        
        if not current_metrics or not new_metrics:
            return 0.0
        
        # Base confidence on sample count and performance difference
        current_samples = current_metrics.sample_count
        new_samples = new_metrics.sample_count
        
        # More samples = higher confidence
        sample_confidence = min(1.0, (current_samples + new_samples) / 100.0)
        
        # Performance difference = higher confidence
        performance_diff = abs(new_metrics.composite_score - current_metrics.composite_score)
        performance_confidence = min(1.0, performance_diff * 2.0)
        
        # Combine confidences
        return (sample_confidence + performance_confidence) / 2.0

    async def _update_performance_cache(self) -> None:
        """Update performance cache with latest metrics."""
        # This would typically fetch from a metrics store
        # For now, we'll simulate with the base optimizer
        try:
            all_prompt_ids = self.base_optimizer.registry.get_all_prompt_ids()
            for prompt_id in all_prompt_ids:
                active_variant = self.base_optimizer.registry.get_active_variant(prompt_id)
                if active_variant:
                    metrics = self.base_optimizer.tracker.get_metrics(prompt_id, active_variant.id)
                    if metrics:
                        self.performance_cache[prompt_id] = metrics.composite_score
        except Exception as e:
            logger.error(f"Error updating performance cache: {e}")

    async def _check_optimization_triggers(self) -> None:
        """Check for conditions that should trigger optimization."""
        # Check for performance drops
        await self._check_performance_drops()
        
        # Check for new variants
        await self._check_new_variants()
        
        # Check for context changes
        await self._check_context_changes()

    async def _check_performance_drops(self) -> None:
        """Check for performance drops that should trigger optimization."""
        for prompt_id, current_performance in self.performance_cache.items():
            # Get historical performance
            historical_performance = self._get_historical_performance(prompt_id)
            
            if historical_performance and len(historical_performance) > 5:
                avg_historical = sum(historical_performance[-10:]) / len(historical_performance[-10:])
                
                # Check for significant drop
                if current_performance < avg_historical - 0.1:  # 10% drop
                    await self._trigger_optimization(
                        prompt_id=prompt_id,
                        trigger=OptimizationTrigger.PERFORMANCE_DROP,
                        priority=8,
                        context={'performance_drop': current_performance - avg_historical}
                    )

    async def _check_new_variants(self) -> None:
        """Check for new variants that might be better."""
        for prompt_id in self.performance_cache.keys():
            variants = self.base_optimizer.registry.get_all_variants(prompt_id)
            if len(variants) > 1:
                # Check if there are untested variants
                for variant in variants:
                    metrics = self.base_optimizer.tracker.get_metrics(prompt_id, variant.id)
                    if not metrics or metrics.sample_count < 5:
                        await self._trigger_optimization(
                            prompt_id=prompt_id,
                            trigger=OptimizationTrigger.NEW_VARIANT_AVAILABLE,
                            priority=6,
                            context={'new_variant_id': variant.id}
                        )

    async def _check_context_changes(self) -> None:
        """Check for context changes that might require different optimization."""
        # This would typically check for changes in task type, domain, etc.
        # For now, we'll implement a simple time-based check
        pass

    def _get_historical_performance(self, prompt_id: str) -> List[float]:
        """Get historical performance data for a prompt."""
        # This would typically fetch from a time-series database
        # For now, return empty list
        return []

    async def _cleanup_old_data(self) -> None:
        """Clean up old optimization data to prevent memory leaks."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Clean up old variant switches
        for event_id in list(self.variant_switches.keys()):
            if event_id in self.active_optimizations:
                event = self.active_optimizations[event_id]
                if event.timestamp < cutoff_time:
                    del self.variant_switches[event_id]

    def _update_optimization_stats(self, result: LiveOptimizationResult) -> None:
        """Update optimization statistics."""
        self.optimization_stats['total_optimizations'] += 1
        
        if result.success:
            self.optimization_stats['successful_optimizations'] += 1
            self.optimization_stats['avg_improvement'] = (
                (self.optimization_stats['avg_improvement'] * 
                 (self.optimization_stats['successful_optimizations'] - 1) + 
                 result.performance_improvement) / 
                self.optimization_stats['successful_optimizations']
            )
        else:
            self.optimization_stats['failed_optimizations'] += 1
        
        # Update average execution time
        total_optimizations = self.optimization_stats['total_optimizations']
        self.optimization_stats['avg_execution_time'] = (
            (self.optimization_stats['avg_execution_time'] * (total_optimizations - 1) + 
             result.execution_time) / total_optimizations
        )
        
        self.optimization_stats['last_optimization'] = datetime.now()

    async def _trigger_event_handlers(self, event: LiveOptimizationEvent, result: LiveOptimizationResult) -> None:
        """Trigger event handlers for the optimization result."""
        handlers = self.event_handlers.get(event.trigger, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, result)
                else:
                    handler(event, result)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    # Public API methods

    async def trigger_optimization(
        self,
        prompt_id: str,
        trigger: OptimizationTrigger = OptimizationTrigger.USER_REQUEST,
        priority: int = 5,
        context: Dict[str, Any] = None
    ) -> str:
        """Trigger optimization for a specific prompt."""
        event_id = f"opt_{int(time.time() * 1000)}_{prompt_id}"
        
        event = LiveOptimizationEvent(
            event_id=event_id,
            trigger=trigger,
            timestamp=datetime.now(),
            context=context or {'prompt_id': prompt_id},
            priority=priority
        )
        
        with self.optimization_lock:
            self.optimization_queue.append(event)
        
        logger.info(f"Triggered optimization for prompt {prompt_id}: {event_id}")
        return event_id

    def add_event_handler(self, trigger: OptimizationTrigger, handler: Callable) -> None:
        """Add an event handler for a specific trigger."""
        self.event_handlers[trigger].append(handler)

    def remove_event_handler(self, trigger: OptimizationTrigger, handler: Callable) -> None:
        """Remove an event handler."""
        if handler in self.event_handlers[trigger]:
            self.event_handlers[trigger].remove(handler)

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            'is_running': self.is_running,
            'active_optimizations': len(self.active_optimizations),
            'queue_size': len(self.optimization_queue),
            'stats': self.optimization_stats.copy(),
            'performance_cache_size': len(self.performance_cache)
        }

    def get_optimization_history(self, prompt_id: str = None) -> List[LiveOptimizationResult]:
        """Get optimization history for a prompt or all prompts."""
        all_results = []
        for event_results in self.variant_switches.values():
            all_results.extend(event_results)
        
        if prompt_id:
            # Filter by prompt_id if specified
            filtered_results = []
            for result in all_results:
                # This would need to be stored in the result metadata
                if result.metadata and result.metadata.get('prompt_id') == prompt_id:
                    filtered_results.append(result)
            return filtered_results
        
        return all_results

    def set_performance_predictor(self, predictor) -> None:
        """Set the performance predictor for predictive optimization."""
        self.performance_predictor = predictor

    def set_hot_swapper(self, hot_swapper) -> None:
        """Set the hot swapper for zero-downtime switching."""
        self.hot_swapper = hot_swapper
