"""
Context-Aware Optimization Engine

Implements intelligent optimization strategies that adapt based on context,
task type, domain, and execution environment.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from openhands.core.logger import openhands_logger as logger
from openhands.prompt_optimization.models import PromptVariant, PromptMetrics, PromptCategory


class TaskType(Enum):
    """Types of tasks that require different optimization strategies."""
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    GENERAL = "general"


class Domain(Enum):
    """Domain-specific optimization contexts."""
    SOFTWARE_DEVELOPMENT = "software_development"
    DATA_SCIENCE = "data_science"
    WEB_DEVELOPMENT = "web_development"
    MOBILE_DEVELOPMENT = "mobile_development"
    AI_ML = "ai_ml"
    DEVOPS = "devops"
    SECURITY = "security"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    GENERAL = "general"


class ExecutionContext(Enum):
    """Execution environment contexts."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEBUG = "debug"
    PERFORMANCE = "performance"


@dataclass
class OptimizationContext:
    """Context information for optimization decisions."""
    task_type: TaskType
    domain: Domain
    execution_context: ExecutionContext
    complexity_level: str  # "low", "medium", "high"
    urgency: str  # "low", "medium", "high", "critical"
    user_preferences: Dict[str, Any]
    historical_performance: Dict[str, float]
    available_resources: Dict[str, Any]
    constraints: Dict[str, Any]


@dataclass
class ContextualStrategy:
    """Strategy configuration for specific contexts."""
    name: str
    description: str
    applicable_contexts: List[Tuple[TaskType, Domain, ExecutionContext]]
    optimization_weights: Dict[str, float]
    prompt_modifications: Dict[str, Any]
    performance_expectations: Dict[str, float]
    adaptation_rules: List[Dict[str, Any]]


class ContextAwareOptimizer:
    """
    Intelligent optimization engine that adapts strategies based on context.
    """

    def __init__(self):
        self.context_strategies = self._initialize_strategies()
        self.context_history: List[Dict[str, Any]] = []
        self.performance_patterns: Dict[str, Dict[str, float]] = {}
        self.adaptation_models: Dict[str, Any] = {}

    def _initialize_strategies(self) -> Dict[str, ContextualStrategy]:
        """Initialize context-specific optimization strategies."""
        strategies = {}
        
        # Reasoning tasks
        strategies["reasoning_software"] = ContextualStrategy(
            name="reasoning_software",
            description="Optimized for software development reasoning tasks",
            applicable_contexts=[
                (TaskType.REASONING, Domain.SOFTWARE_DEVELOPMENT, ExecutionContext.DEVELOPMENT),
                (TaskType.REASONING, Domain.SOFTWARE_DEVELOPMENT, ExecutionContext.PRODUCTION)
            ],
            optimization_weights={
                "performance": 0.4,
                "efficiency": 0.3,
                "reliability": 0.3
            },
            prompt_modifications={
                "add_technical_depth": True,
                "include_examples": True,
                "emphasize_best_practices": True,
                "add_error_handling": True
            },
            performance_expectations={
                "min_success_rate": 0.85,
                "max_execution_time": 5.0,
                "max_error_rate": 0.05
            },
            adaptation_rules=[
                {"condition": "success_rate < 0.8", "action": "increase_technical_depth"},
                {"condition": "execution_time > 10", "action": "simplify_approach"},
                {"condition": "error_rate > 0.1", "action": "add_validation"}
            ]
        )

        # Code generation tasks
        strategies["code_generation_web"] = ContextualStrategy(
            name="code_generation_web",
            description="Optimized for web development code generation",
            applicable_contexts=[
                (TaskType.CODE_GENERATION, Domain.WEB_DEVELOPMENT, ExecutionContext.DEVELOPMENT)
            ],
            optimization_weights={
                "performance": 0.35,
                "efficiency": 0.25,
                "cost": 0.2,
                "reliability": 0.2
            },
            prompt_modifications={
                "include_frameworks": ["React", "TypeScript", "CSS"],
                "add_responsive_design": True,
                "include_accessibility": True,
                "add_testing": True
            },
            performance_expectations={
                "min_success_rate": 0.9,
                "max_execution_time": 3.0,
                "max_error_rate": 0.03
            },
            adaptation_rules=[
                {"condition": "success_rate < 0.85", "action": "add_framework_examples"},
                {"condition": "execution_time > 5", "action": "simplify_code_structure"}
            ]
        )

        # Creative tasks
        strategies["creative_general"] = ContextualStrategy(
            name="creative_general",
            description="Optimized for creative and innovative tasks",
            applicable_contexts=[
                (TaskType.CREATIVE, Domain.GENERAL, ExecutionContext.DEVELOPMENT),
                (TaskType.CREATIVE, Domain.GENERAL, ExecutionContext.PRODUCTION)
            ],
            optimization_weights={
                "innovation": 0.5,
                "performance": 0.3,
                "efficiency": 0.2
            },
            prompt_modifications={
                "encourage_creativity": True,
                "allow_experimentation": True,
                "include_brainstorming": True,
                "add_inspiration": True
            },
            performance_expectations={
                "min_success_rate": 0.7,
                "max_execution_time": 8.0,
                "max_error_rate": 0.1
            },
            adaptation_rules=[
                {"condition": "innovation_score < 0.5", "action": "increase_creativity_prompts"},
                {"condition": "success_rate < 0.6", "action": "add_guidance"}
            ]
        )

        # High-urgency production tasks
        strategies["urgent_production"] = ContextualStrategy(
            name="urgent_production",
            description="Optimized for urgent production tasks",
            applicable_contexts=[
                (TaskType.GENERAL, Domain.GENERAL, ExecutionContext.PRODUCTION)
            ],
            optimization_weights={
                "reliability": 0.4,
                "efficiency": 0.35,
                "performance": 0.25
            },
            prompt_modifications={
                "prioritize_safety": True,
                "add_validation": True,
                "include_rollback_plan": True,
                "emphasize_testing": True
            },
            performance_expectations={
                "min_success_rate": 0.95,
                "max_execution_time": 2.0,
                "max_error_rate": 0.01
            },
            adaptation_rules=[
                {"condition": "success_rate < 0.9", "action": "increase_validation"},
                {"condition": "execution_time > 3", "action": "optimize_for_speed"}
            ]
        )

        return strategies

    def analyze_context(self, context_data: Dict[str, Any]) -> OptimizationContext:
        """Analyze context data and create optimization context."""
        # Extract task type from content analysis
        task_type = self._detect_task_type(context_data.get('content', ''))
        
        # Extract domain from metadata or content
        domain = self._detect_domain(context_data.get('metadata', {}), context_data.get('content', ''))
        
        # Extract execution context
        execution_context = self._detect_execution_context(context_data.get('environment', {}))
        
        # Analyze complexity
        complexity_level = self._analyze_complexity(context_data.get('content', ''))
        
        # Extract urgency
        urgency = context_data.get('urgency', 'medium')
        
        # Get user preferences
        user_preferences = context_data.get('user_preferences', {})
        
        # Get historical performance
        historical_performance = context_data.get('historical_performance', {})
        
        # Get available resources
        available_resources = context_data.get('available_resources', {})
        
        # Get constraints
        constraints = context_data.get('constraints', {})
        
        return OptimizationContext(
            task_type=task_type,
            domain=domain,
            execution_context=execution_context,
            complexity_level=complexity_level,
            urgency=urgency,
            user_preferences=user_preferences,
            historical_performance=historical_performance,
            available_resources=available_resources,
            constraints=constraints
        )

    def _detect_task_type(self, content: str) -> TaskType:
        """Detect task type from content analysis."""
        content_lower = content.lower()
        
        # Code generation indicators
        if any(keyword in content_lower for keyword in [
            'write code', 'generate code', 'create function', 'implement',
            'build', 'develop', 'program'
        ]):
            return TaskType.CODE_GENERATION
        
        # Analysis indicators
        if any(keyword in content_lower for keyword in [
            'analyze', 'evaluate', 'assess', 'review', 'examine',
            'investigate', 'study', 'compare'
        ]):
            return TaskType.ANALYSIS
        
        # Creative indicators
        if any(keyword in content_lower for keyword in [
            'creative', 'innovative', 'design', 'brainstorm', 'imagine',
            'invent', 'create new', 'original'
        ]):
            return TaskType.CREATIVE
        
        # Debugging indicators
        if any(keyword in content_lower for keyword in [
            'debug', 'fix', 'error', 'bug', 'issue', 'problem',
            'troubleshoot', 'resolve'
        ]):
            return TaskType.DEBUGGING
        
        # Testing indicators
        if any(keyword in content_lower for keyword in [
            'test', 'testing', 'unit test', 'integration test',
            'validate', 'verify'
        ]):
            return TaskType.TESTING
        
        # Documentation indicators
        if any(keyword in content_lower for keyword in [
            'document', 'documentation', 'explain', 'describe',
            'tutorial', 'guide', 'manual'
        ]):
            return TaskType.DOCUMENTATION
        
        # Reasoning indicators
        if any(keyword in content_lower for keyword in [
            'think', 'reason', 'logic', 'why', 'how', 'what if',
            'consider', 'evaluate', 'decide'
        ]):
            return TaskType.REASONING
        
        return TaskType.GENERAL

    def _detect_domain(self, metadata: Dict[str, Any], content: str) -> Domain:
        """Detect domain from metadata and content."""
        # Check metadata first
        if 'domain' in metadata:
            try:
                return Domain(metadata['domain'])
            except ValueError:
                pass
        
        # Analyze content for domain indicators
        content_lower = content.lower()
        
        # Software development
        if any(keyword in content_lower for keyword in [
            'software', 'application', 'program', 'algorithm',
            'data structure', 'api', 'framework'
        ]):
            return Domain.SOFTWARE_DEVELOPMENT
        
        # Web development
        if any(keyword in content_lower for keyword in [
            'web', 'html', 'css', 'javascript', 'react', 'vue',
            'frontend', 'backend', 'fullstack'
        ]):
            return Domain.WEB_DEVELOPMENT
        
        # Data science
        if any(keyword in content_lower for keyword in [
            'data', 'analysis', 'machine learning', 'ai', 'statistics',
            'pandas', 'numpy', 'tensorflow', 'pytorch'
        ]):
            return Domain.DATA_SCIENCE
        
        # Mobile development
        if any(keyword in content_lower for keyword in [
            'mobile', 'ios', 'android', 'react native', 'flutter',
            'app', 'smartphone'
        ]):
            return Domain.MOBILE_DEVELOPMENT
        
        # DevOps
        if any(keyword in content_lower for keyword in [
            'devops', 'deployment', 'ci/cd', 'docker', 'kubernetes',
            'infrastructure', 'monitoring'
        ]):
            return Domain.DEVOPS
        
        return Domain.GENERAL

    def _detect_execution_context(self, environment: Dict[str, Any]) -> ExecutionContext:
        """Detect execution context from environment data."""
        env_name = environment.get('name', '').lower()
        
        if 'production' in env_name or 'prod' in env_name:
            return ExecutionContext.PRODUCTION
        elif 'staging' in env_name or 'stage' in env_name:
            return ExecutionContext.STAGING
        elif 'test' in env_name or 'testing' in env_name:
            return ExecutionContext.TESTING
        elif 'debug' in env_name:
            return ExecutionContext.DEBUG
        elif 'performance' in env_name or 'perf' in env_name:
            return ExecutionContext.PERFORMANCE
        else:
            return ExecutionContext.DEVELOPMENT

    def _analyze_complexity(self, content: str) -> str:
        """Analyze content complexity level."""
        # Simple heuristics for complexity analysis
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        
        # Check for complex indicators
        complex_indicators = [
            'complex', 'sophisticated', 'advanced', 'intricate',
            'multi-step', 'recursive', 'algorithm', 'optimization'
        ]
        
        has_complex_indicators = any(
            indicator in content.lower() for indicator in complex_indicators
        )
        
        # Determine complexity level
        if word_count > 200 or has_complex_indicators:
            return "high"
        elif word_count > 100:
            return "medium"
        else:
            return "low"

    def select_strategy(self, context: OptimizationContext) -> ContextualStrategy:
        """Select the best optimization strategy for the given context."""
        # Find applicable strategies
        applicable_strategies = []
        
        for strategy in self.context_strategies.values():
            for task_type, domain, exec_context in strategy.applicable_contexts:
                if (context.task_type == task_type and 
                    context.domain == domain and 
                    context.execution_context == exec_context):
                    applicable_strategies.append(strategy)
                    break
        
        if not applicable_strategies:
            # Fallback to general strategy
            return self._create_fallback_strategy(context)
        
        # Select best strategy based on context characteristics
        best_strategy = applicable_strategies[0]
        best_score = self._score_strategy_fit(best_strategy, context)
        
        for strategy in applicable_strategies[1:]:
            score = self._score_strategy_fit(strategy, context)
            if score > best_score:
                best_strategy = strategy
                best_score = score
        
        return best_strategy

    def _score_strategy_fit(self, strategy: ContextualStrategy, context: OptimizationContext) -> float:
        """Score how well a strategy fits the given context."""
        score = 0.0
        
        # Base score for exact match
        score += 1.0
        
        # Adjust for complexity level
        if context.complexity_level == "high" and strategy.name in [
            "reasoning_software", "code_generation_web"
        ]:
            score += 0.3
        
        # Adjust for urgency
        if context.urgency == "critical" and strategy.name == "urgent_production":
            score += 0.5
        
        # Adjust for historical performance
        if context.historical_performance:
            strategy_key = f"{strategy.name}_performance"
            if strategy_key in context.historical_performance:
                score += context.historical_performance[strategy_key] * 0.2
        
        return score

    def _create_fallback_strategy(self, context: OptimizationContext) -> ContextualStrategy:
        """Create a fallback strategy for unknown contexts."""
        return ContextualStrategy(
            name="fallback",
            description="Fallback strategy for unknown contexts",
            applicable_contexts=[(context.task_type, context.domain, context.execution_context)],
            optimization_weights={
                "performance": 0.4,
                "efficiency": 0.3,
                "reliability": 0.3
            },
            prompt_modifications={},
            performance_expectations={
                "min_success_rate": 0.8,
                "max_execution_time": 5.0,
                "max_error_rate": 0.05
            },
            adaptation_rules=[]
        )

    def adapt_strategy(
        self, 
        strategy: ContextualStrategy, 
        context: OptimizationContext,
        performance_data: Dict[str, Any]
    ) -> ContextualStrategy:
        """Adapt strategy based on performance data and context."""
        adapted_strategy = ContextualStrategy(
            name=f"{strategy.name}_adapted",
            description=f"Adapted version of {strategy.description}",
            applicable_contexts=strategy.applicable_contexts.copy(),
            optimization_weights=strategy.optimization_weights.copy(),
            prompt_modifications=strategy.prompt_modifications.copy(),
            performance_expectations=strategy.performance_expectations.copy(),
            adaptation_rules=strategy.adaptation_rules.copy()
        )
        
        # Apply adaptation rules
        for rule in strategy.adaptation_rules:
            condition = rule.get('condition', '')
            action = rule.get('action', '')
            
            if self._evaluate_condition(condition, performance_data):
                self._apply_action(action, adapted_strategy, context)
        
        return adapted_strategy

    def _evaluate_condition(self, condition: str, performance_data: Dict[str, Any]) -> bool:
        """Evaluate adaptation rule condition."""
        try:
            # Simple condition evaluation (can be extended)
            if 'success_rate' in condition:
                threshold = float(condition.split()[-1])
                return performance_data.get('success_rate', 0) < threshold
            elif 'execution_time' in condition:
                threshold = float(condition.split()[-1])
                return performance_data.get('execution_time', 0) > threshold
            elif 'error_rate' in condition:
                threshold = float(condition.split()[-1])
                return performance_data.get('error_rate', 0) > threshold
            return False
        except (ValueError, KeyError):
            return False

    def _apply_action(
        self, 
        action: str, 
        strategy: ContextualStrategy, 
        context: OptimizationContext
    ) -> None:
        """Apply adaptation action to strategy."""
        if action == "increase_technical_depth":
            strategy.prompt_modifications["add_technical_depth"] = True
            strategy.optimization_weights["performance"] += 0.1
        elif action == "simplify_approach":
            strategy.optimization_weights["efficiency"] += 0.1
            strategy.performance_expectations["max_execution_time"] *= 0.8
        elif action == "add_validation":
            strategy.prompt_modifications["add_validation"] = True
            strategy.optimization_weights["reliability"] += 0.1
        elif action == "increase_creativity_prompts":
            strategy.prompt_modifications["encourage_creativity"] = True
            strategy.optimization_weights["innovation"] = strategy.optimization_weights.get("innovation", 0) + 0.2
        elif action == "optimize_for_speed":
            strategy.optimization_weights["efficiency"] += 0.2
            strategy.performance_expectations["max_execution_time"] *= 0.6

    def get_context_insights(self) -> Dict[str, Any]:
        """Get insights about context-aware optimization performance."""
        if not self.context_history:
            return {"message": "No context data available"}
        
        # Analyze context patterns
        task_types = [h.get('task_type') for h in self.context_history]
        domains = [h.get('domain') for h in self.context_history]
        strategies_used = [h.get('strategy_name') for h in self.context_history]
        
        return {
            "total_contexts_analyzed": len(self.context_history),
            "most_common_task_type": max(set(task_types), key=task_types.count) if task_types else None,
            "most_common_domain": max(set(domains), key=domains.count) if domains else None,
            "most_used_strategy": max(set(strategies_used), key=strategies_used.count) if strategies_used else None,
            "available_strategies": list(self.context_strategies.keys()),
            "adaptation_models": list(self.adaptation_models.keys())
        }
