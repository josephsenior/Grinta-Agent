"""
Hierarchical Optimization Engine

Implements multi-level optimization that works at system, role, and tool levels
simultaneously, with coordination between levels for optimal overall performance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from openhands.core.logger import openhands_logger as logger
from openhands.prompt_optimization.models import PromptVariant, PromptMetrics, PromptCategory


class OptimizationLevel(Enum):
    """Levels of hierarchical optimization."""
    SYSTEM = "system"      # Overall system prompts
    ROLE = "role"          # Role-specific prompts (MetaSOP)
    TOOL = "tool"          # Tool-specific prompts
    TASK = "task"          # Task-specific prompts
    CONTEXT = "context"    # Context-specific prompts


@dataclass
class LevelConfiguration:
    """Configuration for optimization at a specific level."""
    level: OptimizationLevel
    priority: int  # Higher number = higher priority
    optimization_frequency: float  # How often to optimize (0.0-1.0)
    max_variants: int
    performance_threshold: float
    coordination_weight: float  # How much to consider other levels
    adaptation_rate: float


@dataclass
class HierarchicalStrategy:
    """Strategy for hierarchical optimization."""
    name: str
    description: str
    level_configurations: Dict[OptimizationLevel, LevelConfiguration]
    coordination_rules: List[Dict[str, Any]]
    global_objectives: Dict[str, float]
    level_dependencies: Dict[OptimizationLevel, List[OptimizationLevel]]


class HierarchicalOptimizer:
    """
    Hierarchical optimization engine that coordinates optimization
    across multiple levels simultaneously.
    """

    def __init__(self, strategy: HierarchicalStrategy):
        self.strategy = strategy
        self.level_optimizers: Dict[OptimizationLevel, Any] = {}
        self.coordination_history: List[Dict[str, Any]] = []
        self.level_performance: Dict[OptimizationLevel, Dict[str, float]] = {}
        self.global_metrics: Dict[str, float] = {}

    def initialize_level_optimizer(
        self, 
        level: OptimizationLevel, 
        optimizer: Any
    ) -> None:
        """Initialize optimizer for a specific level."""
        self.level_optimizers[level] = optimizer
        self.level_performance[level] = {
            'avg_score': 0.0,
            'success_rate': 0.0,
            'efficiency': 0.0,
            'coordination_score': 0.0
        }

    def optimize_hierarchically(
        self, 
        optimization_request: Dict[str, Any]
    ) -> Dict[OptimizationLevel, Dict[str, Any]]:
        """
        Perform hierarchical optimization across all levels.
        
        Returns:
            Dict mapping each level to its optimization results
        """
        results = {}
        
        # Phase 1: Independent optimization at each level
        for level, config in self.strategy.level_configurations.items():
            if level in self.level_optimizers:
                level_result = self._optimize_level(
                    level, 
                    config, 
                    optimization_request
                )
                results[level] = level_result
        
        # Phase 2: Coordination between levels
        coordination_results = self._coordinate_levels(results, optimization_request)
        
        # Phase 3: Global optimization based on coordination
        global_results = self._apply_global_optimization(
            results, 
            coordination_results, 
            optimization_request
        )
        
        # Update performance tracking
        self._update_performance_tracking(results, coordination_results)
        
        return global_results

    def _optimize_level(
        self, 
        level: OptimizationLevel, 
        config: LevelConfiguration,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize at a specific level."""
        optimizer = self.level_optimizers.get(level)
        if not optimizer:
            return {"error": f"No optimizer available for level {level.value}"}
        
        # Check if optimization is needed based on frequency
        if not self._should_optimize_level(level, config):
            return {"status": "skipped", "reason": "frequency_threshold"}
        
        # Get level-specific context
        level_context = self._get_level_context(level, request)
        
        # Perform optimization
        try:
            if hasattr(optimizer, 'optimize'):
                result = optimizer.optimize(level_context)
            elif hasattr(optimizer, 'select_variant'):
                # Fallback for simple optimizers
                variants = level_context.get('variants', [])
                metrics = level_context.get('metrics', {})
                result = optimizer.select_variant(variants, metrics)
            else:
                result = {"error": "Optimizer does not support optimization"}
            
            # Add level metadata
            result['level'] = level.value
            result['timestamp'] = datetime.now().isoformat()
            result['config'] = {
                'priority': config.priority,
                'max_variants': config.max_variants,
                'performance_threshold': config.performance_threshold
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing level {level.value}: {e}")
            return {"error": str(e), "level": level.value}

    def _should_optimize_level(
        self, 
        level: OptimizationLevel, 
        config: LevelConfiguration
    ) -> bool:
        """Determine if a level should be optimized based on frequency and performance."""
        # Check frequency threshold
        import random
        if random.random() > config.optimization_frequency:
            return False
        
        # Check performance threshold
        level_perf = self.level_performance.get(level, {})
        current_score = level_perf.get('avg_score', 0.0)
        
        if current_score >= config.performance_threshold:
            return False
        
        return True

    def _get_level_context(
        self, 
        level: OptimizationLevel, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get context specific to optimization level."""
        base_context = request.copy()
        
        if level == OptimizationLevel.SYSTEM:
            return {
                **base_context,
                'focus': 'system_wide_performance',
                'scope': 'global',
                'variants': request.get('system_variants', []),
                'metrics': request.get('system_metrics', {})
            }
        elif level == OptimizationLevel.ROLE:
            return {
                **base_context,
                'focus': 'role_specific_performance',
                'scope': 'role_based',
                'variants': request.get('role_variants', []),
                'metrics': request.get('role_metrics', {}),
                'role_context': request.get('role_context', {})
            }
        elif level == OptimizationLevel.TOOL:
            return {
                **base_context,
                'focus': 'tool_specific_performance',
                'scope': 'tool_based',
                'variants': request.get('tool_variants', []),
                'metrics': request.get('tool_metrics', {}),
                'tool_context': request.get('tool_context', {})
            }
        elif level == OptimizationLevel.TASK:
            return {
                **base_context,
                'focus': 'task_specific_performance',
                'scope': 'task_based',
                'variants': request.get('task_variants', []),
                'metrics': request.get('task_metrics', {}),
                'task_context': request.get('task_context', {})
            }
        elif level == OptimizationLevel.CONTEXT:
            return {
                **base_context,
                'focus': 'context_specific_performance',
                'scope': 'context_based',
                'variants': request.get('context_variants', []),
                'metrics': request.get('context_metrics', {}),
                'context_data': request.get('context_data', {})
            }
        
        return base_context

    def _coordinate_levels(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate optimization results between levels."""
        coordination_results = {
            'conflicts': [],
            'synergies': [],
            'recommendations': [],
            'global_score': 0.0
        }
        
        # Check for conflicts between levels
        conflicts = self._detect_conflicts(level_results)
        coordination_results['conflicts'] = conflicts
        
        # Identify synergies
        synergies = self._identify_synergies(level_results)
        coordination_results['synergies'] = synergies
        
        # Generate coordination recommendations
        recommendations = self._generate_coordination_recommendations(
            level_results, 
            conflicts, 
            synergies
        )
        coordination_results['recommendations'] = recommendations
        
        # Calculate global coordination score
        global_score = self._calculate_global_score(level_results, conflicts, synergies)
        coordination_results['global_score'] = global_score
        
        # Record coordination history
        self.coordination_history.append({
            'timestamp': datetime.now().isoformat(),
            'level_results': {k.value: v for k, v in level_results.items()},
            'coordination_results': coordination_results,
            'request_context': request.get('context', {})
        })
        
        return coordination_results

    def _detect_conflicts(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between optimization results at different levels."""
        conflicts = []
        
        # Check for conflicting optimization directions
        for level1, result1 in level_results.items():
            for level2, result2 in level_results.items():
                if level1 == level2:
                    continue
                
                # Check if levels have conflicting recommendations
                if self._has_conflicting_recommendations(result1, result2):
                    conflicts.append({
                        'level1': level1.value,
                        'level2': level2.value,
                        'conflict_type': 'conflicting_recommendations',
                        'description': f"Levels {level1.value} and {level2.value} have conflicting optimization directions"
                    })
        
        return conflicts

    def _has_conflicting_recommendations(
        self, 
        result1: Dict[str, Any], 
        result2: Dict[str, Any]
    ) -> bool:
        """Check if two results have conflicting recommendations."""
        # Simple heuristic - can be made more sophisticated
        if 'recommendation' in result1 and 'recommendation' in result2:
            rec1 = result1['recommendation']
            rec2 = result2['recommendation']
            
            # Check for opposite directions
            opposite_pairs = [
                ('increase', 'decrease'),
                ('simplify', 'complexify'),
                ('speed_up', 'slow_down'),
                ('reduce_cost', 'increase_cost')
            ]
            
            for pair in opposite_pairs:
                if (pair[0] in str(rec1).lower() and pair[1] in str(rec2).lower()) or \
                   (pair[1] in str(rec1).lower() and pair[0] in str(rec2).lower()):
                    return True
        
        return False

    def _identify_synergies(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify synergies between optimization results at different levels."""
        synergies = []
        
        # Check for complementary optimizations
        for level1, result1 in level_results.items():
            for level2, result2 in level_results.items():
                if level1 == level2:
                    continue
                
                if self._has_synergistic_recommendations(result1, result2):
                    synergies.append({
                        'level1': level1.value,
                        'level2': level2.value,
                        'synergy_type': 'complementary_optimizations',
                        'description': f"Levels {level1.value} and {level2.value} have complementary optimization directions",
                        'potential_benefit': 'enhanced_overall_performance'
                    })
        
        return synergies

    def _has_synergistic_recommendations(
        self, 
        result1: Dict[str, Any], 
        result2: Dict[str, Any]
    ) -> bool:
        """Check if two results have synergistic recommendations."""
        if 'recommendation' in result1 and 'recommendation' in result2:
            rec1 = result1['recommendation']
            rec2 = result2['recommendation']
            
            # Check for complementary directions
            complementary_pairs = [
                ('increase', 'increase'),
                ('optimize', 'optimize'),
                ('improve', 'enhance'),
                ('streamline', 'simplify')
            ]
            
            for pair in complementary_pairs:
                if (pair[0] in str(rec1).lower() and pair[1] in str(rec2).lower()) or \
                   (pair[1] in str(rec1).lower() and pair[0] in str(rec2).lower()):
                    return True
        
        return False

    def _generate_coordination_recommendations(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        synergies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for coordinating between levels."""
        recommendations = []
        
        # Address conflicts
        for conflict in conflicts:
            recommendations.append({
                'type': 'conflict_resolution',
                'priority': 'high',
                'description': f"Resolve conflict between {conflict['level1']} and {conflict['level2']}",
                'action': 'coordinate_optimization_directions',
                'affected_levels': [conflict['level1'], conflict['level2']]
            })
        
        # Leverage synergies
        for synergy in synergies:
            recommendations.append({
                'type': 'synergy_leverage',
                'priority': 'medium',
                'description': f"Leverage synergy between {synergy['level1']} and {synergy['level2']}",
                'action': 'coordinate_optimization_timing',
                'affected_levels': [synergy['level1'], synergy['level2']]
            })
        
        # Global optimization recommendations
        if len(level_results) > 1:
            recommendations.append({
                'type': 'global_optimization',
                'priority': 'medium',
                'description': 'Optimize global objectives across all levels',
                'action': 'balance_level_priorities',
                'affected_levels': list(level_results.keys())
            })
        
        return recommendations

    def _calculate_global_score(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        synergies: List[Dict[str, Any]]
    ) -> float:
        """Calculate global coordination score."""
        base_score = 0.5  # Start with neutral score
        
        # Penalize conflicts
        conflict_penalty = len(conflicts) * 0.1
        base_score -= conflict_penalty
        
        # Reward synergies
        synergy_bonus = len(synergies) * 0.05
        base_score += synergy_bonus
        
        # Consider individual level performance
        level_scores = []
        for level, result in level_results.items():
            if 'score' in result:
                level_scores.append(result['score'])
            elif 'success_rate' in result:
                level_scores.append(result['success_rate'])
        
        if level_scores:
            avg_level_score = sum(level_scores) / len(level_scores)
            base_score = (base_score + avg_level_score) / 2
        
        return max(0.0, min(1.0, base_score))

    def _apply_global_optimization(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]],
        coordination_results: Dict[str, Any],
        request: Dict[str, Any]
    ) -> Dict[OptimizationLevel, Dict[str, Any]]:
        """Apply global optimization based on coordination results."""
        global_results = level_results.copy()
        
        # Apply coordination recommendations
        for recommendation in coordination_results.get('recommendations', []):
            if recommendation['type'] == 'conflict_resolution':
                self._resolve_conflict(global_results, recommendation)
            elif recommendation['type'] == 'synergy_leverage':
                self._leverage_synergy(global_results, recommendation)
            elif recommendation['type'] == 'global_optimization':
                self._apply_global_balance(global_results, recommendation)
        
        # Add global metadata to all results
        for level, result in global_results.items():
            result['global_coordination_score'] = coordination_results.get('global_score', 0.0)
            result['coordination_conflicts'] = len(coordination_results.get('conflicts', []))
            result['coordination_synergies'] = len(coordination_results.get('synergies', []))
        
        return global_results

    def _resolve_conflict(
        self, 
        results: Dict[OptimizationLevel, Dict[str, Any]], 
        recommendation: Dict[str, Any]
    ) -> None:
        """Resolve conflict between levels."""
        # Simple conflict resolution - can be made more sophisticated
        affected_levels = recommendation.get('affected_levels', [])
        
        if len(affected_levels) >= 2:
            level1_name, level2_name = affected_levels[0], affected_levels[1]
            
            # Find the levels
            level1 = None
            level2 = None
            for level in results.keys():
                if level.value == level1_name:
                    level1 = level
                elif level.value == level2_name:
                    level2 = level
            
            if level1 and level2:
                # Apply compromise solution
                if 'compromise' not in results[level1]:
                    results[level1]['compromise'] = True
                    results[level1]['conflict_resolution'] = 'applied'
                
                if 'compromise' not in results[level2]:
                    results[level2]['compromise'] = True
                    results[level2]['conflict_resolution'] = 'applied'

    def _leverage_synergy(
        self, 
        results: Dict[OptimizationLevel, Dict[str, Any]], 
        recommendation: Dict[str, Any]
    ) -> None:
        """Leverage synergy between levels."""
        affected_levels = recommendation.get('affected_levels', [])
        
        for level_name in affected_levels:
            for level in results.keys():
                if level.value == level_name:
                    if 'synergy_leveraged' not in results[level]:
                        results[level]['synergy_leveraged'] = True
                        results[level]['synergy_benefit'] = 'enhanced_performance'

    def _apply_global_balance(
        self, 
        results: Dict[OptimizationLevel, Dict[str, Any]], 
        recommendation: Dict[str, Any]
    ) -> None:
        """Apply global balance across all levels."""
        # Apply global objectives to all levels
        for level, result in results.items():
            result['global_balance_applied'] = True
            result['global_objectives'] = self.strategy.global_objectives

    def _update_performance_tracking(
        self, 
        level_results: Dict[OptimizationLevel, Dict[str, Any]],
        coordination_results: Dict[str, Any]
    ) -> None:
        """Update performance tracking for all levels."""
        for level, result in level_results.items():
            if level not in self.level_performance:
                self.level_performance[level] = {}
            
            # Update level performance metrics
            if 'score' in result:
                self.level_performance[level]['avg_score'] = result['score']
            if 'success_rate' in result:
                self.level_performance[level]['success_rate'] = result['success_rate']
            if 'efficiency' in result:
                self.level_performance[level]['efficiency'] = result['efficiency']
            
            # Update coordination score
            self.level_performance[level]['coordination_score'] = coordination_results.get('global_score', 0.0)
        
        # Update global metrics
        self.global_metrics['total_optimizations'] = self.global_metrics.get('total_optimizations', 0) + 1
        self.global_metrics['avg_coordination_score'] = coordination_results.get('global_score', 0.0)
        self.global_metrics['total_conflicts'] = self.global_metrics.get('total_conflicts', 0) + len(coordination_results.get('conflicts', []))
        self.global_metrics['total_synergies'] = self.global_metrics.get('total_synergies', 0) + len(coordination_results.get('synergies', []))

    def get_hierarchical_insights(self) -> Dict[str, Any]:
        """Get insights about hierarchical optimization performance."""
        return {
            'strategy_name': self.strategy.name,
            'active_levels': list(self.level_optimizers.keys()),
            'level_performance': {
                level.value: perf for level, perf in self.level_performance.items()
            },
            'global_metrics': self.global_metrics,
            'coordination_history_size': len(self.coordination_history),
            'total_coordination_events': len(self.coordination_history),
            'avg_coordination_score': self.global_metrics.get('avg_coordination_score', 0.0),
            'conflict_resolution_rate': self._calculate_conflict_resolution_rate(),
            'synergy_leverage_rate': self._calculate_synergy_leverage_rate()
        }

    def _calculate_conflict_resolution_rate(self) -> float:
        """Calculate rate of successful conflict resolution."""
        if not self.coordination_history:
            return 0.0
        
        total_conflicts = sum(
            len(event.get('coordination_results', {}).get('conflicts', []))
            for event in self.coordination_history
        )
        
        resolved_conflicts = sum(
            sum(1 for rec in event.get('coordination_results', {}).get('recommendations', [])
                if rec.get('type') == 'conflict_resolution')
            for event in self.coordination_history
        )
        
        return resolved_conflicts / max(total_conflicts, 1)

    def _calculate_synergy_leverage_rate(self) -> float:
        """Calculate rate of synergy leverage."""
        if not self.coordination_history:
            return 0.0
        
        total_synergies = sum(
            len(event.get('coordination_results', {}).get('synergies', []))
            for event in self.coordination_history
        )
        
        leveraged_synergies = sum(
            sum(1 for rec in event.get('coordination_results', {}).get('recommendations', [])
                if rec.get('type') == 'synergy_leverage')
            for event in self.coordination_history
        )
        
        return leveraged_synergies / max(total_synergies, 1)


# Predefined hierarchical strategies
BALANCED_HIERARCHICAL_STRATEGY = HierarchicalStrategy(
    name="balanced_hierarchical",
    description="Balanced optimization across all levels",
    level_configurations={
        OptimizationLevel.SYSTEM: LevelConfiguration(
            level=OptimizationLevel.SYSTEM,
            priority=5,
            optimization_frequency=0.3,
            max_variants=5,
            performance_threshold=0.8,
            coordination_weight=0.7,
            adaptation_rate=0.1
        ),
        OptimizationLevel.ROLE: LevelConfiguration(
            level=OptimizationLevel.ROLE,
            priority=4,
            optimization_frequency=0.5,
            max_variants=8,
            performance_threshold=0.75,
            coordination_weight=0.8,
            adaptation_rate=0.15
        ),
        OptimizationLevel.TOOL: LevelConfiguration(
            level=OptimizationLevel.TOOL,
            priority=3,
            optimization_frequency=0.7,
            max_variants=10,
            performance_threshold=0.7,
            coordination_weight=0.6,
            adaptation_rate=0.2
        )
    },
    coordination_rules=[
        {"rule": "system_guides_role", "weight": 0.8},
        {"rule": "role_guides_tool", "weight": 0.6},
        {"rule": "global_consistency", "weight": 0.9}
    ],
    global_objectives={
        "performance": 0.4,
        "efficiency": 0.3,
        "reliability": 0.3
    },
    level_dependencies={
        OptimizationLevel.SYSTEM: [],
        OptimizationLevel.ROLE: [OptimizationLevel.SYSTEM],
        OptimizationLevel.TOOL: [OptimizationLevel.ROLE, OptimizationLevel.SYSTEM]
    }
)
