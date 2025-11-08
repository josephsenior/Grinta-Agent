"""Predictive Execution Planner for MetaSOP Multi-Agent Orchestration.

This module provides intelligent pre-execution planning that analyzes upcoming steps,
predicts optimal execution paths, and prevents resource conflicts before they occur.
This transforms the system from reactive to predictive execution planning.
"""

from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any, Union, TYPE_CHECKING
from collections import defaultdict

from forge.core.logger import forge_logger as logger
from forge.metasop.models import SopStep, Artifact, OrchestrationContext

if TYPE_CHECKING:
    from forge.metasop.parallel_execution import ParallelExecutionEngine
    from forge.metasop.causal_reasoning import CausalReasoningEngine


class ExecutionComplexity(Enum):
    """Complexity levels for execution prediction."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class ResourceType(Enum):
    """Types of resources that can be predicted and optimized."""
    LLM_CAPACITY = "llm_capacity"
    I_O_LOCK = "io_lock"
    NETWORK_BANDWIDTH = "network_bandwidth"
    MEMORY_USAGE = "memory_usage"
    COMPUTE_RESOURCES = "compute_resources"


@dataclass
class ExecutionPrediction:
    """Prediction for step execution characteristics."""
    step_id: str
    estimated_duration_ms: float
    complexity: ExecutionComplexity
    resource_requirements: Dict[ResourceType, float]
    confidence_score: float
    potential_conflicts: List[str]
    optimal_model: Optional[str] = None
    parallel_capability: bool = True


@dataclass
class ResourceAllocation:
    """Resource allocation plan for execution."""
    resource_type: ResourceType
    total_capacity: float
    allocated: Dict[str, float]  # step_id -> amount
    remaining: float
    bottleneck_level: float  # 0.0 to 1.0


@dataclass
class ExecutionPlan:
    """Optimized execution plan with predictive insights."""
    original_steps: List[SopStep]
    optimized_steps: List[SopStep]
    execution_groups: List[List[SopStep]]
    resource_allocations: Dict[ResourceType, ResourceAllocation]
    predicted_total_time_ms: float
    confidence_score: float
    conflict_warnings: List[str]
    optimization_opportunities: List[str]
    parallelization_factor: float


class PredictiveExecutionPlanner:
    """Predict and optimize step execution before runtime.

    Provides predictive intelligence for maximum efficiency and resource utilization.
    """
    
    def __init__(
        self,
        parallel_engine: Optional["ParallelExecutionEngine"] = None,
        causal_engine: Optional["CausalReasoningEngine"] = None,
        max_prediction_time_ms: int = 100,
        confidence_threshold: float = 0.7
    ):
        """Initialize the predictive execution planner."""
        self.parallel_engine = parallel_engine
        self.causal_engine = causal_engine
        self.max_prediction_time_ms = max_prediction_time_ms
        self.confidence_threshold = confidence_threshold
        
        # Historical data for predictions
        self.execution_history: Dict[str, List[ExecutionPrediction]] = defaultdict(list)
        self.resource_usage_patterns: Dict[ResourceType, List[float]] = defaultdict(list)
        self.step_complexity_patterns: Dict[str, ExecutionComplexity] = {}
        
        # Performance tracking
        self.prediction_stats = {
            "total_predictions": 0,
            "accurate_predictions": 0,
            "avg_accuracy": 0.0,
            "total_planning_time_ms": 0.0
        }
        
        logger.info("Predictive Execution Planner initialized")

    async def analyze_execution_path(
        self, 
        steps: List[SopStep], 
        context: OrchestrationContext
    ) -> ExecutionPlan:
        """Analyze and optimize the entire execution path before starting execution.
        
        This is the core method that transforms reactive execution into predictive execution.
        """
        start_time = time.perf_counter()
        
        try:
            logger.info(f"🔮 Starting predictive analysis of {len(steps)} steps")
            
            # Step 1: Generate execution predictions for each step
            predictions = await self._predict_execution_characteristics(steps, context)
            
            # Step 2: Analyze resource requirements and potential conflicts
            resource_analysis = await self._analyze_resource_requirements(predictions)
            
            # Step 3: Optimize step ordering for maximum parallelization
            optimized_steps = await self._optimize_step_ordering(steps, predictions, resource_analysis)
            
            # Step 4: Create execution groups based on dependencies and resources
            execution_groups = await self._create_optimal_execution_groups(optimized_steps, predictions, resource_analysis)
            
            # Step 5: Generate resource allocation plan
            resource_allocations = await self._create_resource_allocation_plan(predictions, execution_groups)
            
            # Step 6: Calculate overall execution metrics
            total_time_ms = await self._calculate_predicted_execution_time(predictions, execution_groups)
            confidence_score = await self._calculate_plan_confidence(predictions, resource_analysis)
            
            # Step 7: Identify conflicts and optimization opportunities
            conflict_warnings, optimization_opportunities = await self._identify_conflicts_and_opportunities(
                predictions, resource_analysis, execution_groups
            )
            
            planning_time_ms = (time.perf_counter() - start_time) * 1000
            
            plan = ExecutionPlan(
                original_steps=steps,
                optimized_steps=optimized_steps,
                execution_groups=execution_groups,
                resource_allocations=resource_allocations,
                predicted_total_time_ms=total_time_ms,
                confidence_score=confidence_score,
                conflict_warnings=conflict_warnings,
                optimization_opportunities=optimization_opportunities,
                parallelization_factor=len(steps) / max(len(execution_groups), 1)
            )
            
            # Update prediction statistics
            self._update_prediction_stats(planning_time_ms)
            
            logger.info(f"🎯 Predictive analysis completed in {planning_time_ms:.2f}ms")
            logger.info(f"📊 Predicted execution time: {total_time_ms:.2f}ms, confidence: {confidence_score:.2f}")
            logger.info(f"🚀 Parallelization factor: {plan.parallelization_factor:.2f}x")
            
            return plan
            
        except Exception as e:
            logger.error(f"Predictive execution planning failed: {e}")
            # Fallback to simple execution plan
            return ExecutionPlan(
                original_steps=steps,
                optimized_steps=steps,
                execution_groups=[steps],
                resource_allocations={},
                predicted_total_time_ms=len(steps) * 1000,  # Estimate
                confidence_score=0.5,
                conflict_warnings=[],
                optimization_opportunities=[],
                parallelization_factor=1.0
            )

    async def _predict_execution_characteristics(
        self, 
        steps: List[SopStep], 
        context: OrchestrationContext
    ) -> List[ExecutionPrediction]:
        """Predict execution characteristics for each step using historical data and patterns."""
        predictions: List[ExecutionPrediction] = []
        
        for step in steps:
            # Use historical data if available
            historical_predictions = self.execution_history.get(step.id, [])
            
            # Base prediction from step characteristics
            estimated_duration = await self._estimate_step_duration(step, context)
            complexity = await self._classify_step_complexity(step, context)
            resource_req = await self._predict_resource_requirements(step, context)
            conflicts = await self._predict_potential_conflicts(step, context)
            
            # Adjust based on historical accuracy
            confidence = 0.8 if historical_predictions else 0.6
            if historical_predictions:
                historical_accuracy = self._calculate_historical_accuracy(historical_predictions)
                confidence = max(confidence, historical_accuracy)
            
            prediction = ExecutionPrediction(
                step_id=step.id,
                estimated_duration_ms=estimated_duration,
                complexity=complexity,
                resource_requirements=resource_req,
                confidence_score=confidence,
                potential_conflicts=conflicts,
                optimal_model=await self._suggest_optimal_model(step, context)
            )
            
            predictions.append(prediction)
        
        return predictions

    async def _estimate_step_duration(self, step: SopStep, context: OrchestrationContext) -> float:
        """Estimate execution duration for a step based on characteristics and history."""
        # Base estimation rules
        role_weights = {
            "engineer": 2000,      # 2 seconds
            "qa": 1500,           # 1.5 seconds  
            "product_manager": 1000,  # 1 second
            "architect": 2500,    # 2.5 seconds
            "ui_designer": 1800   # 1.8 seconds
        }
        
        base_duration = role_weights.get(step.role.lower(), 1500)
        
        # Adjust based on task complexity indicators
        task_indicators = {
            "complex": 1.5, "test": 0.8, "review": 0.6, "create": 1.3, 
            "design": 1.4, "implement": 1.2, "fix": 1.1, "refactor": 1.6
        }
        
        task_multiplier = 1.0
        for indicator, multiplier in task_indicators.items():
            if indicator in step.task.lower():
                task_multiplier *= multiplier
                break
        
        # Check for lock resources which might cause delays
        if step.lock:
            task_multiplier *= 1.2  # 20% longer with locks
        
        estimated = base_duration * task_multiplier
        
        # Use historical data if available
        historical_data = self.execution_history.get(step.id, [])
        if historical_data:
            avg_historical = sum(p.estimated_duration_ms for p in historical_data[-5:]) / len(historical_data[-5:])
            estimated = (estimated + avg_historical) / 2  # Blend with history
        
        return estimated

    async def _classify_step_complexity(self, step: SopStep, context: OrchestrationContext) -> ExecutionComplexity:
        """Classify step execution complexity."""
        # Use cached classification if available
        if step.id in self.step_complexity_patterns:
            return self.step_complexity_patterns[step.id]
        
        # Analyze task characteristics
        complexity_score: float = 0.0
        
        # Role-based complexity
        role_complexity = {
            "engineer": 3, "architect": 4, "qa": 2, 
            "product_manager": 2, "ui_designer": 3
        }
        complexity_score += role_complexity.get(step.role.lower(), 2)
        
        # Task keywords that indicate complexity
        complex_keywords = ["implement", "design", "refactor", "optimize", "debug"]
        simple_keywords = ["review", "check", "validate", "test"]
        
        task_lower = step.task.lower()
        if any(kw in task_lower for kw in complex_keywords):
            complexity_score += 2
        elif any(kw in task_lower for kw in simple_keywords):
            complexity_score -= 1
        
        # Lock usage increases complexity
        if step.lock:
            complexity_score += 1
            
        # Dependencies increase complexity
        complexity_score += len(step.depends_on) * 0.5
        
        # Classify based on score
        if complexity_score >= 5:
            complexity = ExecutionComplexity.CRITICAL
        elif complexity_score >= 4:
            complexity = ExecutionComplexity.COMPLEX
        elif complexity_score >= 2:
            complexity = ExecutionComplexity.MODERATE
        else:
            complexity = ExecutionComplexity.SIMPLE
        
        # Cache the classification
        self.step_complexity_patterns[step.id] = complexity
        return complexity

    async def _predict_resource_requirements(self, step: SopStep, context: OrchestrationContext) -> Dict[ResourceType, float]:
        """Predict resource requirements for a step."""
        requirements: Dict[ResourceType, float] = {}
        
        # LLM capacity requirements based on role and complexity
        llm_requirements = {
            "engineer": 0.8, "architect": 1.0, "qa": 0.6,
            "product_manager": 0.7, "ui_designer": 0.9
        }
        requirements[ResourceType.LLM_CAPACITY] = llm_requirements.get(step.role.lower(), 0.8)
        
        # I/O lock requirements
        if step.lock:
            if step.lock in ["write", "test"]:
                requirements[ResourceType.I_O_LOCK] = 1.0  # Exclusive access
            else:
                requirements[ResourceType.I_O_LOCK] = 0.3  # Shared access
        
        # Network bandwidth (for LLM API calls)
        requirements[ResourceType.NETWORK_BANDWIDTH] = 0.5
        
        # Memory usage estimation
        requirements[ResourceType.MEMORY_USAGE] = 0.3
        
        # Compute resources
        requirements[ResourceType.COMPUTE_RESOURCES] = 0.4
        
        return requirements

    async def _predict_potential_conflicts(self, step: SopStep, context: OrchestrationContext) -> List[str]:
        """Predict potential conflicts for this step."""
        conflicts: List[str] = []
        
        # Use causal engine if available for conflict prediction
        if self.causal_engine:
            try:
                # This would integrate with the causal reasoning engine
                # For now, we'll use basic pattern matching
                if step.lock:
                    conflicts.append(f"resource_lock_{step.lock}")
            except Exception:
                pass
        
        # Check for dependency conflicts
        if step.depends_on:
            conflicts.append("dependency_chain_delay")
        
        # Role-based conflicts
        role_conflicts = {
            "engineer": ["write_lock_conflict", "test_resource_conflict"],
            "qa": ["write_lock_conflict"],
            "ui_designer": ["design_resource_conflict"]
        }
        conflicts.extend(role_conflicts.get(step.role.lower(), []))
        
        return conflicts

    async def _suggest_optimal_model(self, step: SopStep, context: OrchestrationContext) -> Optional[str]:
        """Suggest the optimal LLM model for this step."""
        # Model selection based on role and complexity
        model_mapping = {
            "engineer": "gpt-4",  # Best coding capabilities
            "architect": "claude-3-opus",  # Best reasoning
            "qa": "gpt-3.5-turbo",  # Efficient for testing
            "product_manager": "gpt-4",
            "ui_designer": "gpt-4-vision"  # Visual capabilities
        }
        
        return model_mapping.get(step.role.lower())

    async def _analyze_resource_requirements(self, predictions: List[ExecutionPrediction]) -> Dict[ResourceType, float]:
        """Analyze total resource requirements across all predictions."""
        total_requirements: defaultdict[ResourceType, float] = defaultdict(float)
        
        for prediction in predictions:
            for resource_type, amount in prediction.resource_requirements.items():
                total_requirements[resource_type] += amount
        
        return dict(total_requirements)

    async def _optimize_step_ordering(self, steps: List[SopStep], predictions: List[ExecutionPrediction], resource_analysis: Dict[ResourceType, float]) -> List[SopStep]:
        """Optimize step ordering for maximum parallelization and resource efficiency."""
        # Group predictions by step_id for quick lookup
        prediction_map = {p.step_id: p for p in predictions}
        
        # Sort by priority, complexity, and resource requirements
        def sort_key(step: SopStep) -> Tuple[int, float, float]:
            """Return tuple for sorting steps by priority, complexity, and predicted duration."""
            prediction = prediction_map.get(step.id)
            priority = step.priority
            
            # Prefer simpler, faster steps first for better parallelization
            complexity_score = {
                ExecutionComplexity.SIMPLE: 0,
                ExecutionComplexity.MODERATE: 1,
                ExecutionComplexity.COMPLEX: 2,
                ExecutionComplexity.CRITICAL: 3
            }.get(prediction.complexity if prediction else ExecutionComplexity.MODERATE, 1)
            
            # Shorter estimated duration is better for early parallelization
            duration = prediction.estimated_duration_ms if prediction else 1500
            
            return (priority, complexity_score, duration)
        
        # Create optimized ordering while respecting dependencies
        remaining_steps = steps.copy()
        optimized_steps = []
        added_steps: Set[str] = set()
        
        while remaining_steps:
            # Find steps with satisfied dependencies
            ready_steps = [
                step for step in remaining_steps
                if all(dep in added_steps for dep in step.depends_on)
            ]
            
            if not ready_steps:
                # No ready steps, just take the next one (shouldn't happen in valid DAG)
                step = remaining_steps[0]
                optimized_steps.append(step)
                remaining_steps.remove(step)
                added_steps.add(step.id)
                continue
            
            # Sort ready steps by optimization criteria
            ready_steps.sort(key=sort_key)
            
            # Add the best step
            best_step = ready_steps[0]
            optimized_steps.append(best_step)
            remaining_steps.remove(best_step)
            added_steps.add(best_step.id)
        
        return optimized_steps

    def _find_ready_steps(
        self,
        remaining_steps: List[SopStep],
        added_steps: Set[str]
    ) -> List[SopStep]:
        """Find steps that are ready to execute.
        
        Args:
            remaining_steps: Steps not yet executed
            added_steps: Set of completed step IDs
            
        Returns:
            List of ready steps

        """
        return [
            step for step in remaining_steps
            if all(dep in added_steps for dep in step.depends_on)
        ]

    def _find_non_conflicting_steps(
        self,
        ready_steps: List[SopStep],
        predictions: List[ExecutionPrediction]
    ) -> List[SopStep]:
        """Find steps that don't conflict on resources.
        
        Args:
            ready_steps: Steps ready for execution
            predictions: Execution predictions
            
        Returns:
            List of non-conflicting steps for parallel execution

        """
        current_group: List[SopStep] = []
        used_resources: Set[ResourceType] = set()
        
        for step in ready_steps:
            prediction = next((p for p in predictions if p.step_id == step.id), None)
            if not prediction:
                current_group.append(step)
                continue
            
            # Check resource conflicts
            step_resources: Set[ResourceType] = set(prediction.resource_requirements.keys())
            if not (step_resources & used_resources):
                current_group.append(step)
                used_resources.update(step_resources)
        
        return current_group

    def _create_fallback_execution_groups(
        self,
        optimized_steps: List[SopStep],
        predictions: List[ExecutionPrediction]
    ) -> List[List[SopStep]]:
        """Create execution groups using dependency-based grouping.
        
        Args:
            optimized_steps: Steps to group
            predictions: Execution predictions
            
        Returns:
            List of execution groups

        """
        groups: List[List[SopStep]] = []
        remaining_steps = optimized_steps.copy()
        added_steps: Set[str] = set()
        
        while remaining_steps:
            ready_steps = self._find_ready_steps(remaining_steps, added_steps)
            
            if not ready_steps:
                break
            
            # Group non-conflicting steps
            current_group = self._find_non_conflicting_steps(ready_steps, predictions)
            
            if current_group:
                groups.append(current_group)
                for step in current_group:
                    remaining_steps.remove(step)
                    added_steps.add(step.id)
            else:
                # Take first ready step
                step = ready_steps[0]
                groups.append([step])
                remaining_steps.remove(step)
                added_steps.add(step.id)
        
        return groups

    async def _create_optimal_execution_groups(
        self, 
        optimized_steps: List[SopStep], 
        predictions: List[ExecutionPrediction],
        resource_analysis: Dict[ResourceType, float]
    ) -> List[List[SopStep]]:
        """Create optimal execution groups for parallel execution."""
        # Try using parallel engine if available
        if self.parallel_engine:
            try:
                completed_artifacts: Dict[str, Artifact] = {}
                return self.parallel_engine.identify_parallel_groups(optimized_steps, completed_artifacts)
            except Exception:
                pass
        
        # Fallback to dependency-based grouping
        return self._create_fallback_execution_groups(optimized_steps, predictions)

    async def _create_resource_allocation_plan(
        self, 
        predictions: List[ExecutionPrediction], 
        execution_groups: List[List[SopStep]]
    ) -> Dict[ResourceType, ResourceAllocation]:
        """Create resource allocation plan to prevent bottlenecks."""
        allocations: Dict[ResourceType, ResourceAllocation] = {}
        
        # Estimate total capacity (this could be made configurable)
        total_capacity: Dict[ResourceType, float] = {
            ResourceType.LLM_CAPACITY: 10.0,  # Max concurrent LLM operations
            ResourceType.I_O_LOCK: 5.0,       # Max concurrent I/O operations
            ResourceType.NETWORK_BANDWIDTH: 8.0,
            ResourceType.MEMORY_USAGE: 100.0,  # Percentage
            ResourceType.COMPUTE_RESOURCES: 80.0  # Percentage
        }
        
        for resource_type in ResourceType:
            allocated: Dict[str, float] = {}
            total_required = 0.0
            
            # Calculate requirements per group
            for group_idx, group in enumerate(execution_groups):
                group_requirement = 0.0
                for step in group:
                    prediction = next((p for p in predictions if p.step_id == step.id), None)
                    if prediction and resource_type in prediction.resource_requirements:
                        group_requirement += prediction.resource_requirements[resource_type]
                
                if group_requirement > 0:
                    allocated[f"group_{group_idx}"] = group_requirement
                    total_required += group_requirement
            
            capacity = total_capacity.get(resource_type, 10.0)
            remaining = max(0.0, capacity - total_required)
            bottleneck_level = (total_required / capacity) if capacity else 0.0
            
            allocations[resource_type] = ResourceAllocation(
                resource_type=resource_type,
                total_capacity=total_capacity.get(resource_type, 10.0),
                allocated=allocated,
                remaining=remaining,
                bottleneck_level=min(bottleneck_level, 1.0)
            )
        
        return allocations

    async def _calculate_predicted_execution_time(
        self, 
        predictions: List[ExecutionPrediction], 
        execution_groups: List[List[SopStep]]
    ) -> float:
        """Calculate total predicted execution time considering parallelization."""
        if not execution_groups:
            return sum(p.estimated_duration_ms for p in predictions)
        
        # Calculate time for each group (assumes true parallelization within groups)
        group_times: List[float] = []
        for group in execution_groups:
            group_predictions = [p for p in predictions if p.step_id in [s.id for s in group]]
            if group_predictions:
                # Parallel execution within group = max time in group
                group_time = max(p.estimated_duration_ms for p in group_predictions)
                group_times.append(group_time)
        
        # Sequential execution between groups = sum of group times
        return sum(group_times)

    async def _calculate_plan_confidence(
        self, 
        predictions: List[ExecutionPrediction], 
        resource_analysis: Dict[ResourceType, float]
    ) -> float:
        """Calculate overall confidence in the execution plan."""
        if not predictions:
            return 0.5
        
        # Average confidence across predictions
        avg_confidence = sum(p.confidence_score for p in predictions) / len(predictions)
        
        # Reduce confidence if resource bottlenecks detected
        bottleneck_factor = 1.0
        for resource_type, total_req in resource_analysis.items():
            if total_req > 8.0:  # High resource usage
                bottleneck_factor *= 0.9
        
        return min(1.0, avg_confidence * bottleneck_factor)

    async def _identify_conflicts_and_opportunities(
        self, 
        predictions: List[ExecutionPrediction],
        resource_analysis: Dict[ResourceType, float],
        execution_groups: List[List[SopStep]]
    ) -> Tuple[List[str], List[str]]:
        """Identify potential conflicts and optimization opportunities."""
        conflicts = []
        opportunities = []
        
        # Resource bottleneck conflicts
        for resource_type, total_req in resource_analysis.items():
            if total_req > 8.0:
                conflicts.append(f"Potential {resource_type.value} bottleneck detected")
        
        # Execution time opportunities
        total_sequential_time = sum(p.estimated_duration_ms for p in predictions)
        parallel_time = await self._calculate_predicted_execution_time(predictions, execution_groups)
        speedup = total_sequential_time / parallel_time if parallel_time > 0 else 1.0
        
        if speedup > 2.0:
            opportunities.append(f"High parallelization potential: {speedup:.1f}x speedup")
        elif speedup < 1.5:
            opportunities.append("Limited parallelization opportunity - consider dependency optimization")
        
        # Low confidence warnings
        low_confidence_steps = [p for p in predictions if p.confidence_score < 0.6]
        if low_confidence_steps:
            conflicts.append(f"{len(low_confidence_steps)} steps have low prediction confidence")
        
        return conflicts, opportunities

    def _calculate_historical_accuracy(self, historical_predictions: List[ExecutionPrediction]) -> float:
        """Calculate historical prediction accuracy."""
        # This would compare historical predictions with actual execution results
        # For now, return a base confidence score
        return min(0.9, 0.6 + (len(historical_predictions) * 0.05))

    def _update_prediction_stats(self, planning_time_ms: float) -> None:
        """Update prediction statistics."""
        self.prediction_stats["total_predictions"] += 1
        self.prediction_stats["total_planning_time_ms"] += planning_time_ms
        
        if self.prediction_stats["total_predictions"] > 0:
            self.prediction_stats["avg_planning_time_ms"] = (
                self.prediction_stats["total_planning_time_ms"] / 
                self.prediction_stats["total_predictions"]
            )

    def get_prediction_stats(self) -> Dict[str, Any]:
        """Get prediction performance statistics."""
        return self.prediction_stats.copy()

    def learn_from_execution(self, step_id: str, actual_duration_ms: float, success: bool) -> None:
        """Learn from actual execution results to improve future predictions."""
        # This would update the historical data for better future predictions
        # For now, we'll simulate learning by updating patterns
        
        # Find the prediction that was made for this step
        if step_id in self.execution_history:
            historical = self.execution_history[step_id]
            if historical:
                last_prediction = historical[-1]
                # Update complexity classification based on actual results
                if actual_duration_ms > last_prediction.estimated_duration_ms * 1.5:
                    # Actual was much longer, increase complexity
                    if last_prediction.complexity == ExecutionComplexity.SIMPLE:
                        self.step_complexity_patterns[step_id] = ExecutionComplexity.MODERATE
                    elif last_prediction.complexity == ExecutionComplexity.MODERATE:
                        self.step_complexity_patterns[step_id] = ExecutionComplexity.COMPLEX
        
        logger.debug(f"Updated predictions for step {step_id}: actual={actual_duration_ms}ms, success={success}")
