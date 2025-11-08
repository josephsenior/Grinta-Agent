"""Performance Tracker for Dynamic Prompt Optimization.

Collects and analyzes performance metrics for prompt variants,
calculates composite scores, and provides statistical analysis.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import PromptCategory, PromptMetrics, PromptPerformance, PromptVariant


class PerformanceTracker:
    """Tracks and analyzes performance metrics for prompt variants."""
    
    def __init__(self, config: Optional[Dict[str, float]] = None):
        """Initialize the performance tracker.
        
        Args:
            config: Configuration for composite score weights

        """
        self._performance_data: List[PromptPerformance] = []
        self._variant_metrics: Dict[str, PromptMetrics] = {}
        
        # Default weights for composite score
        self.weights = {
            'success': config.get('success_weight', 0.4) if config else 0.4,
            'time': config.get('time_weight', 0.2) if config else 0.2,
            'error': config.get('error_weight', 0.2) if config else 0.2,
            'cost': config.get('cost_weight', 0.2) if config else 0.2
        }
        
        # Ensure weights sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for key in self.weights:
                self.weights[key] /= total_weight
    
    def record_performance(self, performance: PromptPerformance):
        """Record a performance data point."""
        self._performance_data.append(performance)
        
        # Update variant metrics
        self._update_variant_metrics(performance)
    
    def record_execution(self, variant_id: str, prompt_id: str, category: PromptCategory,
                        success: bool, execution_time: float, token_cost: float = 0.0,
                        error_message: Optional[str] = None, metadata: Optional[Dict] = None):
        """Record a single execution performance."""
        performance = PromptPerformance(
            variant_id=variant_id,
            prompt_id=prompt_id,
            category=category,
            success=success,
            execution_time=execution_time,
            token_cost=token_cost,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        self.record_performance(performance)
    
    def _ensure_variant_metrics_exists(self, variant_id: str) -> None:
        """Ensure metrics object exists for variant.
        
        Args:
            variant_id: Variant identifier

        """
        if variant_id not in self._variant_metrics:
            self._variant_metrics[variant_id] = PromptMetrics(
                success_weight=self.weights['success'],
                time_weight=self.weights['time'],
                error_weight=self.weights['error'],
                cost_weight=self.weights['cost']
            )

    def _calculate_variant_statistics(self, variant_performances: List) -> dict:
        """Calculate statistics from variant performances.
        
        Args:
            variant_performances: List of performances
            
        Returns:
            Dictionary of calculated metrics

        """
        total_executions = len(variant_performances)
        successful_executions = sum(1 for p in variant_performances if p.success)
        
        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        error_rate = 1.0 - success_rate
        
        execution_times = [p.execution_time for p in variant_performances]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
        
        token_costs = [p.token_cost for p in variant_performances]
        avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0
        
        return {
            'success_rate': success_rate,
            'error_rate': error_rate,
            'avg_execution_time': avg_execution_time,
            'avg_token_cost': avg_token_cost,
            'sample_count': total_executions
        }

    def _update_variant_metrics(self, performance: PromptPerformance):
        """Update metrics for a specific variant."""
        variant_id = performance.variant_id
        
        self._ensure_variant_metrics_exists(variant_id)
        
        variant_performances = [
            p for p in self._performance_data 
            if p.variant_id == variant_id
        ]
        
        if not variant_performances:
            return
        
        # Calculate and update metrics
        stats = self._calculate_variant_statistics(variant_performances)
        metrics = self._variant_metrics[variant_id]
        
        metrics.success_rate = stats['success_rate']
        metrics.avg_execution_time = stats['avg_execution_time']
        metrics.error_rate = stats['error_rate']
        metrics.avg_token_cost = stats['avg_token_cost']
        metrics.sample_count = stats['sample_count']
        metrics.composite_score = metrics._calculate_composite_score()
    
    def get_variant_metrics(self, variant_id: str) -> Optional[PromptMetrics]:
        """Get metrics for a specific variant."""
        return self._variant_metrics.get(variant_id)
    
    def get_prompt_metrics(self, prompt_id: str) -> List[Tuple[str, PromptMetrics]]:
        """Get metrics for all variants of a prompt."""
        prompt_variants = [
            (p.variant_id, p.prompt_id) for p in self._performance_data
            if p.prompt_id == prompt_id
        ]
        
        variant_ids = list(set(vid for vid, _ in prompt_variants))
        return [
            (vid, self._variant_metrics[vid]) 
            for vid in variant_ids 
            if vid in self._variant_metrics
        ]
    
    def get_category_metrics(self, category: PromptCategory) -> List[Tuple[str, PromptMetrics]]:
        """Get metrics for all variants in a category."""
        category_variants = [
            (p.variant_id, p.category) for p in self._performance_data
            if p.category == category
        ]
        
        variant_ids = list(set(vid for vid, _ in category_variants))
        return [
            (vid, self._variant_metrics[vid]) 
            for vid in variant_ids 
            if vid in self._variant_metrics
        ]
    
    def get_best_variant(self, prompt_id: str) -> Optional[Tuple[str, PromptMetrics]]:
        """Get the best performing variant for a prompt."""
        prompt_metrics = self.get_prompt_metrics(prompt_id)
        if not prompt_metrics:
            return None
        
        # Sort by composite score (highest first)
        prompt_metrics.sort(key=lambda x: x[1].composite_score, reverse=True)
        return prompt_metrics[0]
    
    def get_worst_variant(self, prompt_id: str) -> Optional[Tuple[str, PromptMetrics]]:
        """Get the worst performing variant for a prompt."""
        prompt_metrics = self.get_prompt_metrics(prompt_id)
        if not prompt_metrics:
            return None
        
        # Sort by composite score (lowest first)
        prompt_metrics.sort(key=lambda x: x[1].composite_score)
        return prompt_metrics[0]
    
    def compare_variants(self, variant_id1: str, variant_id2: str) -> Optional[Dict[str, any]]:
        """Compare two variants and return detailed comparison."""
        metrics1 = self._variant_metrics.get(variant_id1)
        metrics2 = self._variant_metrics.get(variant_id2)
        
        if not metrics1 or not metrics2:
            return None
        
        return {
            'variant1': {
                'id': variant_id1,
                'metrics': metrics1.to_dict()
            },
            'variant2': {
                'id': variant_id2,
                'metrics': metrics2.to_dict()
            },
            'comparison': {
                'success_rate_diff': metrics1.success_rate - metrics2.success_rate,
                'execution_time_diff': metrics1.avg_execution_time - metrics2.avg_execution_time,
                'error_rate_diff': metrics1.error_rate - metrics2.error_rate,
                'token_cost_diff': metrics1.avg_token_cost - metrics2.avg_token_cost,
                'composite_score_diff': metrics1.composite_score - metrics2.composite_score,
                'sample_count_diff': metrics1.sample_count - metrics2.sample_count
            }
        }
    
    def is_significantly_better(self, variant_id1: str, variant_id2: str, 
                              confidence_level: float = 0.95) -> Optional[bool]:
        """Check if variant1 is significantly better than variant2.
        
        Uses statistical significance testing based on sample sizes and variance.
        """
        metrics1 = self._variant_metrics.get(variant_id1)
        metrics2 = self._variant_metrics.get(variant_id2)
        
        if not metrics1 or not metrics2:
            return None
        
        # Need minimum samples for significance testing
        if metrics1.sample_count < 5 or metrics2.sample_count < 5:
            return None
        
        # Simple significance test based on composite score difference
        score_diff = metrics1.composite_score - metrics2.composite_score
        
        # Calculate confidence based on sample sizes
        # Larger sample sizes = higher confidence
        min_samples = min(metrics1.sample_count, metrics2.sample_count)
        confidence_factor = min(1.0, min_samples / 20.0)  # Full confidence at 20+ samples
        
        # Threshold for significance (adjust based on confidence level)
        significance_threshold = 0.1 * confidence_factor
        
        return score_diff > significance_threshold
    
    def _group_performances_by_day(self, variant_performances: List) -> dict:
        """Group performances by day.
        
        Args:
            variant_performances: List of performances
            
        Returns:
            Dictionary mapping day to performances

        """
        daily_data = defaultdict(list)
        for perf in variant_performances:
            day_key = perf.timestamp.date().isoformat()
            daily_data[day_key].append(perf)
        return daily_data

    def _calculate_daily_metrics(self, performances: List) -> dict:
        """Calculate metrics for a day's worth of performances.
        
        Args:
            performances: Day's performances
            
        Returns:
            Dictionary of metrics

        """
        total_executions = len(performances)
        successful_executions = sum(1 for p in performances if p.success)
        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        
        execution_times = [p.execution_time for p in performances]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
        
        token_costs = [p.token_cost for p in performances]
        avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0
        
        return {
            'total_executions': total_executions,
            'success_rate': success_rate,
            'avg_execution_time': avg_execution_time,
            'avg_token_cost': avg_token_cost
        }

    def get_performance_trend(self, variant_id: str, days: int = 7) -> List[Dict[str, any]]:
        """Get performance trend for a variant over time."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        variant_performances = [
            p for p in self._performance_data
            if p.variant_id == variant_id and p.timestamp >= cutoff_date
        ]
        
        if not variant_performances:
            return []
        
        daily_data = self._group_performances_by_day(variant_performances)
        
        # Calculate daily metrics
        trend_data = []
        for day, performances in sorted(daily_data.items()):
            metrics = self._calculate_daily_metrics(performances)
            trend_data.append({'date': day, **metrics})
        
        return trend_data
    
    def _calculate_overall_metrics(self) -> dict:
        """Calculate overall performance metrics.
        
        Returns:
            Dictionary of overall metrics

        """
        total_executions = len(self._performance_data)
        successful_executions = sum(1 for p in self._performance_data if p.success)
        overall_success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        
        execution_times = [p.execution_time for p in self._performance_data]
        overall_avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
        
        token_costs = [p.token_cost for p in self._performance_data]
        overall_avg_token_cost = statistics.mean(token_costs) if token_costs else 0.0
        
        unique_variants = len(set(p.variant_id for p in self._performance_data))
        unique_prompts = len(set(p.prompt_id for p in self._performance_data))
        
        return {
            'total_executions': total_executions,
            'overall_success_rate': overall_success_rate,
            'overall_avg_execution_time': overall_avg_execution_time,
            'overall_avg_token_cost': overall_avg_token_cost,
            'total_variants': unique_variants,
            'total_prompts': unique_prompts
        }

    def get_overall_statistics(self) -> Dict[str, any]:
        """Get overall performance statistics."""
        if not self._performance_data:
            return {
                'total_executions': 0,
                'overall_success_rate': 0.0,
                'overall_avg_execution_time': 0.0,
                'overall_avg_token_cost': 0.0,
                'total_variants': 0,
                'total_prompts': 0
            }
        
        return self._calculate_overall_metrics()
    
    def _accumulate_category_counts(self) -> dict:
        """Accumulate execution and success counts by category.
        
        Returns:
            Dictionary of category statistics

        """
        category_stats = defaultdict(lambda: {
            'total_executions': 0,
            'success_rate': 0.0,
            'avg_execution_time': 0.0,
            'avg_token_cost': 0.0,
            'unique_variants': 0,
            'unique_prompts': 0
        })
        
        for performance in self._performance_data:
            category = performance.category.value
            stats = category_stats[category]
            stats['total_executions'] += 1
            if performance.success:
                stats['success_rate'] += 1
        
        return category_stats

    def _calculate_category_success_rate(self, stats: dict) -> None:
        """Calculate success rate for category stats.
        
        Args:
            stats: Category statistics dict

        """
        if stats['total_executions'] > 0:
            stats['success_rate'] /= stats['total_executions']

    def _calculate_category_unique_counts(self, category: str, category_performances: list, stats: dict) -> None:
        """Calculate unique variant and prompt counts for category.
        
        Args:
            category: Category name
            category_performances: List of performances for category
            stats: Category statistics dict

        """
        stats['unique_variants'] = len(set(p.variant_id for p in category_performances))
        stats['unique_prompts'] = len(set(p.prompt_id for p in category_performances))

    def _calculate_category_averages(self, category_performances: list, stats: dict) -> None:
        """Calculate average execution time and token cost for category.
        
        Args:
            category_performances: List of performances for category
            stats: Category statistics dict

        """
        execution_times = [p.execution_time for p in category_performances]
        stats['avg_execution_time'] = statistics.mean(execution_times) if execution_times else 0.0
        
        token_costs = [p.token_cost for p in category_performances]
        stats['avg_token_cost'] = statistics.mean(token_costs) if token_costs else 0.0

    def _finalize_category_stats(self, category_stats: dict) -> None:
        """Finalize category statistics with averages and unique counts.
        
        Args:
            category_stats: Accumulated category stats to finalize

        """
        for category, stats in category_stats.items():
            self._calculate_category_success_rate(stats)
            
            category_performances = [
                p for p in self._performance_data 
                if p.category.value == category
            ]
            
            self._calculate_category_unique_counts(category, category_performances, stats)
            self._calculate_category_averages(category_performances, stats)

    def get_category_statistics(self) -> Dict[str, Dict[str, any]]:
        """Get performance statistics by category."""
        category_stats = self._accumulate_category_counts()
        self._finalize_category_stats(category_stats)
        return dict(category_stats)
    
    def clear_data(self):
        """Clear all performance data."""
        self._performance_data.clear()
        self._variant_metrics.clear()
    
    def export_data(self) -> Dict[str, any]:
        """Export all performance data for persistence."""
        return {
            'performance_data': [p.to_dict() for p in self._performance_data],
            'variant_metrics': {vid: metrics.to_dict() for vid, metrics in self._variant_metrics.items()},
            'weights': self.weights
        }
    
    def import_data(self, data: Dict[str, any]):
        """Import performance data from persistence."""
        # Clear existing data
        self.clear_data()
        
        # Import performance data
        for perf_data in data.get('performance_data', []):
            performance = PromptPerformance.from_dict(perf_data)
            self._performance_data.append(performance)
        
        # Import variant metrics
        for vid, metrics_data in data.get('variant_metrics', {}).items():
            metrics = PromptMetrics(**metrics_data)
            self._variant_metrics[vid] = metrics
        
        # Import weights
        if 'weights' in data:
            self.weights.update(data['weights'])
