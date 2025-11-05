"""
Advanced Optimization Strategies

This module provides sophisticated optimization strategies that go beyond
basic prompt optimization to include multi-objective optimization,
context-aware strategies, hierarchical optimization, and intelligent
strategy selection.
"""

from .multi_objective import (
    MultiObjectiveOptimizer,
    OptimizationObjective,
    ObjectiveWeight,
    OptimizationStrategy,
    BALANCED_STRATEGY,
    PERFORMANCE_FOCUSED_STRATEGY,
    EFFICIENCY_FOCUSED_STRATEGY,
    INNOVATION_FOCUSED_STRATEGY
)

from .context_aware import (
    ContextAwareOptimizer,
    OptimizationContext,
    TaskType,
    Domain,
    ExecutionContext,
    ContextualStrategy
)

from .hierarchical import (
    HierarchicalOptimizer,
    HierarchicalStrategy,
    OptimizationLevel,
    LevelConfiguration,
    BALANCED_HIERARCHICAL_STRATEGY
)

from .strategy_manager import (
    AdvancedStrategyManager,
    StrategyType,
    StrategyPerformance,
    StrategySelection,
    EnsembleStrategy
)

__all__ = [
    # Multi-objective optimization
    'MultiObjectiveOptimizer',
    'OptimizationObjective',
    'ObjectiveWeight',
    'OptimizationStrategy',
    'BALANCED_STRATEGY',
    'PERFORMANCE_FOCUSED_STRATEGY',
    'EFFICIENCY_FOCUSED_STRATEGY',
    'INNOVATION_FOCUSED_STRATEGY',
    
    # Context-aware optimization
    'ContextAwareOptimizer',
    'OptimizationContext',
    'TaskType',
    'Domain',
    'ExecutionContext',
    'ContextualStrategy',
    
    # Hierarchical optimization
    'HierarchicalOptimizer',
    'HierarchicalStrategy',
    'OptimizationLevel',
    'LevelConfiguration',
    'BALANCED_HIERARCHICAL_STRATEGY',
    
    # Strategy management
    'AdvancedStrategyManager',
    'StrategyType',
    'StrategyPerformance',
    'StrategySelection',
    'EnsembleStrategy'
]
