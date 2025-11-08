"""Advanced Optimization Configuration.

Configuration management for advanced optimization strategies including
multi-objective optimization, context-aware strategies, and hierarchical optimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from forge.prompt_optimization.advanced.multi_objective import (
    OptimizationObjective, 
    ObjectiveWeight, 
    OptimizationStrategy
)
from forge.prompt_optimization.advanced.context_aware import (
    TaskType, 
    Domain, 
    ExecutionContext
)
from forge.prompt_optimization.advanced.hierarchical import (
    OptimizationLevel, 
    LevelConfiguration
)


class AdvancedOptimizationMode(Enum):
    """Modes for advanced optimization."""
    DISABLED = "disabled"
    BASIC = "basic"           # Multi-objective only
    CONTEXT_AWARE = "context_aware"  # + Context-aware
    HIERARCHICAL = "hierarchical"    # + Hierarchical
    FULL = "full"             # All strategies + ensemble


@dataclass
class AdvancedOptimizationConfig:
    """Configuration for advanced optimization strategies."""
    
    # General settings
    mode: AdvancedOptimizationMode = AdvancedOptimizationMode.BASIC
    enable_ensemble: bool = False
    enable_adaptive_learning: bool = True
    exploration_rate: float = 0.2
    adaptation_rate: float = 0.1
    
    # Multi-objective optimization
    multi_objective_enabled: bool = True
    default_objectives: List[OptimizationObjective] = None
    objective_weights: Dict[str, float] = None
    
    # Context-aware optimization
    context_aware_enabled: bool = False
    context_analysis_depth: str = "medium"  # "shallow", "medium", "deep"
    enable_domain_detection: bool = True
    enable_task_type_detection: bool = True
    
    # Hierarchical optimization
    hierarchical_enabled: bool = False
    level_coordination: bool = True
    global_optimization: bool = True
    
    # Performance thresholds
    min_performance_threshold: float = 0.6
    high_performance_threshold: float = 0.8
    adaptation_threshold: float = 0.1
    
    # Resource constraints
    max_memory_usage: int = 1000  # MB
    max_optimization_time: int = 30  # seconds
    max_concurrent_optimizations: int = 5
    
    # Learning and adaptation
    learning_rate: float = 0.1
    performance_history_size: int = 100
    adaptation_frequency: int = 10  # Optimizations between adaptations
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.default_objectives is None:
            self.default_objectives = [
                OptimizationObjective.PERFORMANCE,
                OptimizationObjective.EFFICIENCY,
                OptimizationObjective.COST,
                OptimizationObjective.RELIABILITY
            ]
        
        if self.objective_weights is None:
            self.objective_weights = {
                "performance": 0.4,
                "efficiency": 0.3,
                "cost": 0.2,
                "reliability": 0.1
            }
    
    def get_multi_objective_strategy(self) -> OptimizationStrategy:
        """Get multi-objective optimization strategy based on configuration."""
        objectives = []
        
        for obj in self.default_objectives:
            weight = self.objective_weights.get(obj.value, 0.25)
            objectives.append(ObjectiveWeight(
                objective=obj,
                weight=weight,
                min_value=0.0,
                max_value=1.0,
                is_higher_better=True
            ))
        
        return OptimizationStrategy(
            name="configured_multi_objective",
            description="Multi-objective strategy based on configuration",
            objectives=objectives,
            pareto_threshold=0.1,
            exploration_rate=self.exploration_rate,
            exploitation_rate=1.0 - self.exploration_rate,
            adaptation_rate=self.adaptation_rate
        )
    
    def get_hierarchical_strategy(self) -> Dict[OptimizationLevel, LevelConfiguration]:
        """Get hierarchical optimization configuration."""
        if not self.hierarchical_enabled:
            return {}
        
        return {
            OptimizationLevel.SYSTEM: LevelConfiguration(
                level=OptimizationLevel.SYSTEM,
                priority=5,
                optimization_frequency=0.3,
                max_variants=5,
                performance_threshold=self.high_performance_threshold,
                coordination_weight=0.7,
                adaptation_rate=self.adaptation_rate
            ),
            OptimizationLevel.ROLE: LevelConfiguration(
                level=OptimizationLevel.ROLE,
                priority=4,
                optimization_frequency=0.5,
                max_variants=8,
                performance_threshold=self.min_performance_threshold,
                coordination_weight=0.8,
                adaptation_rate=self.adaptation_rate
            ),
            OptimizationLevel.TOOL: LevelConfiguration(
                level=OptimizationLevel.TOOL,
                priority=3,
                optimization_frequency=0.7,
                max_variants=10,
                performance_threshold=self.min_performance_threshold,
                coordination_weight=0.6,
                adaptation_rate=self.adaptation_rate
            )
        }
    
    def _validate_mode_consistency(self, errors: List[str]) -> None:
        """Validate mode consistency with enabled strategies."""
        if self.mode == AdvancedOptimizationMode.DISABLED:
            if any([self.multi_objective_enabled, self.context_aware_enabled, self.hierarchical_enabled]):
                errors.append("Mode is disabled but some strategies are enabled")

    def _validate_rates(self, errors: List[str]) -> None:
        """Validate rate parameters are in valid range."""
        if not 0.0 <= self.exploration_rate <= 1.0:
            errors.append("Exploration rate must be between 0.0 and 1.0")
        
        if not 0.0 <= self.adaptation_rate <= 1.0:
            errors.append("Adaptation rate must be between 0.0 and 1.0")
        
        if not 0.0 <= self.learning_rate <= 1.0:
            errors.append("Learning rate must be between 0.0 and 1.0")

    def _validate_thresholds(self, errors: List[str]) -> None:
        """Validate performance thresholds."""
        if not 0.0 <= self.min_performance_threshold <= 1.0:
            errors.append("Min performance threshold must be between 0.0 and 1.0")
        
        if not 0.0 <= self.high_performance_threshold <= 1.0:
            errors.append("High performance threshold must be between 0.0 and 1.0")
        
        if self.min_performance_threshold >= self.high_performance_threshold:
            errors.append("Min performance threshold must be less than high performance threshold")

    def _validate_resource_constraints(self, errors: List[str]) -> None:
        """Validate resource constraint parameters."""
        if self.max_memory_usage <= 0:
            errors.append("Max memory usage must be positive")
        
        if self.max_optimization_time <= 0:
            errors.append("Max optimization time must be positive")
        
        if self.max_concurrent_optimizations <= 0:
            errors.append("Max concurrent optimizations must be positive")

    def _validate_learning_parameters(self, errors: List[str]) -> None:
        """Validate learning-related parameters."""
        if self.performance_history_size <= 0:
            errors.append("Performance history size must be positive")
        
        if self.adaptation_frequency <= 0:
            errors.append("Adaptation frequency must be positive")

    def validate(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        self._validate_mode_consistency(errors)
        self._validate_rates(errors)
        self._validate_thresholds(errors)
        self._validate_resource_constraints(errors)
        self._validate_learning_parameters(errors)
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'mode': self.mode.value,
            'enable_ensemble': self.enable_ensemble,
            'enable_adaptive_learning': self.enable_adaptive_learning,
            'exploration_rate': self.exploration_rate,
            'adaptation_rate': self.adaptation_rate,
            'multi_objective_enabled': self.multi_objective_enabled,
            'default_objectives': [obj.value for obj in self.default_objectives],
            'objective_weights': self.objective_weights,
            'context_aware_enabled': self.context_aware_enabled,
            'context_analysis_depth': self.context_analysis_depth,
            'enable_domain_detection': self.enable_domain_detection,
            'enable_task_type_detection': self.enable_task_type_detection,
            'hierarchical_enabled': self.hierarchical_enabled,
            'level_coordination': self.level_coordination,
            'global_optimization': self.global_optimization,
            'min_performance_threshold': self.min_performance_threshold,
            'high_performance_threshold': self.high_performance_threshold,
            'adaptation_threshold': self.adaptation_threshold,
            'max_memory_usage': self.max_memory_usage,
            'max_optimization_time': self.max_optimization_time,
            'max_concurrent_optimizations': self.max_concurrent_optimizations,
            'learning_rate': self.learning_rate,
            'performance_history_size': self.performance_history_size,
            'adaptation_frequency': self.adaptation_frequency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdvancedOptimizationConfig':
        """Create configuration from dictionary."""
        # Convert mode
        mode = AdvancedOptimizationMode(data.get('mode', 'basic'))
        
        # Convert objectives
        default_objectives = [
            OptimizationObjective(obj) for obj in data.get('default_objectives', [])
        ]
        
        config = cls(
            mode=mode,
            enable_ensemble=data.get('enable_ensemble', False),
            enable_adaptive_learning=data.get('enable_adaptive_learning', True),
            exploration_rate=data.get('exploration_rate', 0.2),
            adaptation_rate=data.get('adaptation_rate', 0.1),
            multi_objective_enabled=data.get('multi_objective_enabled', True),
            default_objectives=default_objectives,
            objective_weights=data.get('objective_weights', {}),
            context_aware_enabled=data.get('context_aware_enabled', False),
            context_analysis_depth=data.get('context_analysis_depth', 'medium'),
            enable_domain_detection=data.get('enable_domain_detection', True),
            enable_task_type_detection=data.get('enable_task_type_detection', True),
            hierarchical_enabled=data.get('hierarchical_enabled', False),
            level_coordination=data.get('level_coordination', True),
            global_optimization=data.get('global_optimization', True),
            min_performance_threshold=data.get('min_performance_threshold', 0.6),
            high_performance_threshold=data.get('high_performance_threshold', 0.8),
            adaptation_threshold=data.get('adaptation_threshold', 0.1),
            max_memory_usage=data.get('max_memory_usage', 1000),
            max_optimization_time=data.get('max_optimization_time', 30),
            max_concurrent_optimizations=data.get('max_concurrent_optimizations', 5),
            learning_rate=data.get('learning_rate', 0.1),
            performance_history_size=data.get('performance_history_size', 100),
            adaptation_frequency=data.get('adaptation_frequency', 10)
        )
        
        return config


# Predefined configurations for common use cases
BASIC_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.BASIC,
    multi_objective_enabled=True,
    context_aware_enabled=False,
    hierarchical_enabled=False
)

CONTEXT_AWARE_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.CONTEXT_AWARE,
    multi_objective_enabled=True,
    context_aware_enabled=True,
    hierarchical_enabled=False,
    context_analysis_depth="deep"
)

HIERARCHICAL_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.HIERARCHICAL,
    multi_objective_enabled=True,
    context_aware_enabled=True,
    hierarchical_enabled=True,
    level_coordination=True,
    global_optimization=True
)

FULL_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.FULL,
    multi_objective_enabled=True,
    context_aware_enabled=True,
    hierarchical_enabled=True,
    enable_ensemble=True,
    enable_adaptive_learning=True,
    exploration_rate=0.3,
    adaptation_rate=0.15
)

PERFORMANCE_FOCUSED_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.CONTEXT_AWARE,
    multi_objective_enabled=True,
    context_aware_enabled=True,
    objective_weights={
        "performance": 0.6,
        "reliability": 0.3,
        "efficiency": 0.1,
        "cost": 0.0
    },
    min_performance_threshold=0.8,
    high_performance_threshold=0.9
)

EFFICIENCY_FOCUSED_CONFIG = AdvancedOptimizationConfig(
    mode=AdvancedOptimizationMode.CONTEXT_AWARE,
    multi_objective_enabled=True,
    context_aware_enabled=True,
    objective_weights={
        "efficiency": 0.5,
        "cost": 0.3,
        "performance": 0.2,
        "reliability": 0.0
    },
    max_optimization_time=10,
    max_memory_usage=500
)
