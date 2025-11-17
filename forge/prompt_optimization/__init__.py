"""Dynamic Prompt Optimization Framework.

A self-improving system that automatically optimizes prompts through A/B testing
and performance-based evolution across MetaSOP, CodeAct, and tool prompts.
"""

from typing import Any

from .models import PromptVariant, PromptMetrics, PromptPerformance, PromptCategory
from .registry import PromptRegistry
from .tracker import PerformanceTracker
from .history_store import PromptHistoryStore, JsonPromptHistoryStore
from .health import collect_health_snapshot
from .optimizer import PromptOptimizer
from .evolver import PromptEvolver
from .storage import PromptStorage
from .tool_optimizer import ToolOptimizer

__all__ = [
    "PromptVariant",
    "PromptMetrics",
    "PromptPerformance",
    "PromptCategory",
    "PromptRegistry",
    "PerformanceTracker",
    "PromptHistoryStore",
    "JsonPromptHistoryStore",
    "collect_health_snapshot",
    "PromptOptimizer",
    "PromptEvolver",
    "PromptStorage",
    "ToolOptimizer",
]

AdvancedStrategyManager: Any
MultiObjectiveOptimizer: Any
ContextAwareOptimizer: Any
HierarchicalOptimizer: Any
StrategyType: Any

try:  # pragma: no cover - optional dependency
    from .advanced import (
        AdvancedStrategyManager,
        MultiObjectiveOptimizer,
        ContextAwareOptimizer,
        HierarchicalOptimizer,
        StrategyType,
    )
except Exception:  # pragma: no cover - provide graceful fallback
    AdvancedStrategyManager = None
    MultiObjectiveOptimizer = None
    ContextAwareOptimizer = None
    HierarchicalOptimizer = None
    StrategyType = None
else:  # pragma: no cover - exercised when optional deps installed
    __all__.extend(
        [
            "AdvancedStrategyManager",
            "MultiObjectiveOptimizer",
            "ContextAwareOptimizer",
            "HierarchicalOptimizer",
            "StrategyType",
        ]
    )

LiveOptimizer: Any
HotSwapper: Any
PerformancePredictor: Any
StreamingOptimizationEngine: Any
RealTimeMonitor: Any
WebSocketOptimizationServer: Any
RealTimeOptimizationSystem: Any

try:  # pragma: no cover - optional dependency
    from .realtime import (
        LiveOptimizer,
        HotSwapper,
        PerformancePredictor,
        StreamingOptimizationEngine,
        RealTimeMonitor,
        WebSocketOptimizationServer,
        RealTimeOptimizationSystem,
    )
except Exception:  # pragma: no cover - provide graceful fallback
    LiveOptimizer = None
    HotSwapper = None
    PerformancePredictor = None
    StreamingOptimizationEngine = None
    RealTimeMonitor = None
    WebSocketOptimizationServer = None
    RealTimeOptimizationSystem = None
else:  # pragma: no cover - exercised when optional deps installed
    __all__.extend(
        [
            "LiveOptimizer",
            "HotSwapper",
            "PerformancePredictor",
            "StreamingOptimizationEngine",
            "RealTimeMonitor",
            "WebSocketOptimizationServer",
            "RealTimeOptimizationSystem",
        ]
    )
