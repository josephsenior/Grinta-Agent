"""
Dynamic Prompt Optimization Framework

A self-improving system that automatically optimizes prompts through A/B testing
and performance-based evolution across MetaSOP, CodeAct, and tool prompts.
"""

from .models import PromptVariant, PromptMetrics, PromptPerformance, PromptCategory
from .registry import PromptRegistry
from .tracker import PerformanceTracker
from .optimizer import PromptOptimizer
from .evolver import PromptEvolver
from .storage import PromptStorage
from .tool_optimizer import ToolOptimizer
from .advanced import (
    AdvancedStrategyManager,
    MultiObjectiveOptimizer,
    ContextAwareOptimizer,
    HierarchicalOptimizer,
    StrategyType
)
from .realtime import (
    LiveOptimizer,
    HotSwapper,
    PerformancePredictor,
    StreamingOptimizationEngine,
    RealTimeMonitor,
    WebSocketOptimizationServer,
    RealTimeOptimizationSystem
)

__all__ = [
    'PromptVariant',
    'PromptMetrics', 
    'PromptPerformance',
    'PromptCategory',
    'PromptRegistry',
    'PerformanceTracker',
    'PromptOptimizer',
    'PromptEvolver',
    'PromptStorage',
    'ToolOptimizer',
    'AdvancedStrategyManager',
    'MultiObjectiveOptimizer',
    'ContextAwareOptimizer',
    'HierarchicalOptimizer',
    'StrategyType',
    'LiveOptimizer',
    'HotSwapper',
    'PerformancePredictor',
    'StreamingOptimizationEngine',
    'RealTimeMonitor',
    'WebSocketOptimizationServer',
    'RealTimeOptimizationSystem'
]
