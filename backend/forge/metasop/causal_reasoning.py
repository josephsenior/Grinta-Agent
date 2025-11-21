"""LLM-Powered Causal Reasoning Engine for MetaSOP Multi-Agent Orchestration.

This module provides advanced conflict prediction and prevention using the same
LLM model as the main agent for consistent reasoning across the system.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING, Set

from forge.core.logger import forge_logger as logger
from forge.metasop.models import SopStep, Artifact, OrchestrationContext

if TYPE_CHECKING:
    from forge.llm.llm import LLM


class ConflictType(Enum):
    """Types of conflicts that can be detected."""

    RESOURCE_LOCK = "resource_lock"
    ARTIFACT_DEPENDENCY = "artifact_dependency"
    SEQUENCE_VIOLATION = "sequence_violation"
    CAUSAL_SIDE_EFFECT = "causal_side_effect"
    COLLABORATIVE_OPPORTUNITY = "collaborative_opportunity"


@dataclass
class ConflictPrediction:
    """Result of conflict prediction analysis."""

    conflict_type: ConflictType
    affected_steps: List[str]
    confidence: float
    recommendation: str
    reasoning: Optional[str] = None


@dataclass
class CausalChain:
    """A causal chain predicted by LLM reasoning."""

    source_step: str
    effects: List[Dict[str, Any]]
    risk_level: str
    confidence: float
    recommendations: List[str] = field(default_factory=list)


class CausalReasoningEngine:
    """LLM-powered reasoning engine that predicts conflicts and opportunities.

    Uses the same model as the main agent for consistent reasoning and falls back to heuristics when LLM support is unavailable.
    """

    def __init__(self, llm: Optional["LLM"] = None):
        """Initialize the causal reasoning engine.

        Args:
            llm: The LLM instance to use for reasoning (same as main agent)

        """
        self.llm: Optional["LLM"] = llm

        # Fallback heuristics - used when LLM is unavailable
        self.conflict_patterns: Dict[str, List[str]] = {}
        self.resource_usage_history: Dict[str, List[Dict[str, Any]]] = {}

        # Performance tracking
        self.performance_stats = {
            "total_checks": 0,
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0,
            "conflicts_detected": 0,
            "llm_reasoning_used": 0,
            "fallback_heuristics_used": 0,
        }

        mode = "LLM-powered" if llm else "heuristic fallback"
        logger.info(f"CausalReasoningEngine initialized in {mode} mode")

    def _should_skip_analysis(
        self, proposed_step: SopStep, active_steps: List[SopStep]
    ) -> bool:
        """Check if analysis can be skipped for performance.

        Args:
            proposed_step: Step being considered
            active_steps: Currently executing steps

        Returns:
            True if analysis can be skipped

        """
        # Skip if no active steps
        if not active_steps:
            return True

        # Skip if step has no lock, few active steps, and not modifying
        return (
            proposed_step.lock is None
            and len(active_steps) < 2
            and not self._is_modifying_step(proposed_step)
        )

    def _run_llm_analysis(
        self,
        proposed_step: SopStep,
        active_steps: List[SopStep],
        completed_artifacts: Dict[str, Artifact],
        current_context: Optional[OrchestrationContext],
    ) -> List[ConflictPrediction]:
        """Run LLM-powered conflict analysis.

        Args:
            proposed_step: Step to analyze
            active_steps: Active steps
            completed_artifacts: Completed artifacts
            current_context: Current context

        Returns:
            List of predicted conflicts

        """
        predictions: List[ConflictPrediction] = []

        if not self.llm or len(active_steps) <= 1:
            self.performance_stats["fallback_heuristics_used"] += 1
            return predictions

        try:
            llm_predictions = self._llm_powered_analysis_sync(
                proposed_step, active_steps, completed_artifacts, current_context
            )
            if llm_predictions:
                predictions.extend(llm_predictions)
                self.performance_stats["llm_reasoning_used"] += 1
                logger.info(
                    f"🧠 LLM causal reasoning predicted {len(llm_predictions)} potential conflicts"
                )
        except Exception as e:
            logger.warning(
                f"LLM causal analysis failed: {e}, falling back to heuristics"
            )
            self.performance_stats["fallback_heuristics_used"] += 1

        return predictions

    def _run_heuristic_checks(
        self,
        proposed_step: SopStep,
        active_steps: List[SopStep],
        completed_artifacts: Dict[str, Artifact],
    ) -> List[ConflictPrediction]:
        """Run fast heuristic conflict checks.

        Args:
            proposed_step: Step to check
            active_steps: Active steps
            completed_artifacts: Completed artifacts

        Returns:
            List of predicted conflicts

        """
        predictions: List[ConflictPrediction] = []

        # Resource lock conflicts
        if conflict := self._check_resource_conflicts(proposed_step, active_steps):
            predictions.append(conflict)

        # Artifact dependency conflicts
        if conflict := self._check_artifact_conflicts(
            proposed_step, active_steps, completed_artifacts
        ):
            predictions.append(conflict)

        # Learned pattern conflicts
        if conflict := self._check_learned_patterns(proposed_step, active_steps):
            predictions.append(conflict)

        return predictions

    def analyze_step_safety(
        self,
        proposed_step: SopStep,
        active_steps: List[SopStep],
        completed_artifacts: Dict[str, Artifact],
        current_context: Optional[OrchestrationContext] = None,
        max_analysis_time_ms: float = 50.0,
    ) -> Tuple[bool, List[ConflictPrediction]]:
        """Analyze if a step can safely proceed without conflicts using LLM reasoning.

        Uses the same LLM as the main agent for consistent reasoning.
        Falls back to heuristics if LLM is unavailable or for fast checks.

        Args:
            proposed_step: The step being considered for execution
            active_steps: List of currently executing steps
            completed_artifacts: Previously completed artifacts
            current_context: Current orchestration context
            max_analysis_time_ms: Maximum time allowed for analysis

        Returns:
            Tuple of (can_proceed, predictions)

        """
        start_time = time.perf_counter()

        # Performance optimization: Early exit if safe to skip
        if self._should_skip_analysis(proposed_step, active_steps):
            return True, []

        try:
            # Run LLM analysis
            predictions = self._run_llm_analysis(
                proposed_step, active_steps, completed_artifacts, current_context
            )

            # Run heuristic checks
            predictions.extend(
                self._run_heuristic_checks(
                    proposed_step, active_steps, completed_artifacts
                )
            )

        except Exception as e:
            logger.warning(f"Causal analysis failed: {e}")
            return True, []  # Fail-safe: allow step

        # Determine if step can proceed
        blocking_conflicts = [p for p in predictions if p.confidence > 0.8]
        can_proceed = len(blocking_conflicts) == 0

        # Update performance stats
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._update_performance_stats(elapsed_ms, len(predictions))

        # Log warning if too slow
        if elapsed_ms > max_analysis_time_ms:
            logger.warning(
                f"Causal analysis took {elapsed_ms:.2f}ms, "
                f"exceeds threshold of {max_analysis_time_ms}ms"
            )

        return can_proceed, predictions

    def _llm_powered_analysis_sync(
        self,
        proposed_step: SopStep,
        active_steps: List[SopStep],
        completed_artifacts: Dict[str, Artifact],
        current_context: Optional[OrchestrationContext] = None,
    ) -> List[ConflictPrediction]:
        """Use LLM reasoning to predict causal effects and conflicts (synchronous version).

        This uses the SAME model as the main agent for consistent reasoning.
        """
        # Build analysis prompt
        prompt = self._build_causal_analysis_prompt(
            proposed_step, active_steps, completed_artifacts
        )

        # Call LLM with structured output request
        messages = [
            {
                "role": "system",
                "content": """You are a causal reasoning expert analyzing multi-agent software development workflows.
Your task is to predict conflicts, side effects, and collaborative opportunities when an agent takes an action.

Focus on:
1. Resource conflicts (file locks, API rate limits, concurrent edits)
2. Artifact dependencies (one agent needs output from another)
3. Causal side effects (unintended consequences)
4. Collaborative opportunities (agents that should work together)

Be concise but thorough. Assign confidence scores honestly.""",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            # Use the same LLM as the main agent (synchronous call)
            if self.llm is None:
                return []
            response = self.llm.completion(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent reasoning
                response_format={"type": "json_object"},
            )

            # Parse response
            first_choice = response.choices[0]
            message = getattr(first_choice, "message", None)
            content = getattr(message, "content", "") if message else ""
            if not isinstance(content, str):
                content = str(content)
            analysis = json.loads(content)

            # Convert to ConflictPrediction objects
            predictions: List[ConflictPrediction] = []
            for conflict in analysis.get("conflicts", []):
                try:
                    conflict_type = ConflictType[
                        conflict.get("type", "CAUSAL_SIDE_EFFECT")
                    ]
                    predictions.append(
                        ConflictPrediction(
                            conflict_type=conflict_type,
                            affected_steps=conflict.get("affected_steps", []),
                            confidence=float(conflict.get("confidence", 0.7)),
                            recommendation=conflict.get("recommendation", ""),
                            reasoning=conflict.get("reasoning"),
                        )
                    )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse conflict prediction: {e}")
                    continue

            return predictions

        except Exception as e:
            logger.warning(f"LLM causal analysis exception: {e}")
            return []

    def _build_causal_analysis_prompt(
        self,
        proposed_step: SopStep,
        active_steps: List[SopStep],
        completed_artifacts: Dict[str, Artifact],
    ) -> str:
        """Build prompt for LLM causal analysis."""
        # Format active steps
        active_info = "\n".join(
            [
                f"  - {step.role}: {step.task[:80]} (lock: {step.lock}, id: {step.id})"
                for step in active_steps[:5]  # Limit to avoid token overflow
            ]
        )

        # Format recent artifacts
        recent_artifacts = list(completed_artifacts.values())[-5:]
        artifact_info = "\n".join(
            [f"  - {art.role}: {art.step_id}" for art in recent_artifacts]
        )

        return f"""Analyze this proposed agent action for potential conflicts:

PROPOSED ACTION:
Role: {proposed_step.role}
Task: {proposed_step.task}
Step ID: {proposed_step.id}
Dependencies: {proposed_step.depends_on or "None"}
Lock Required: {proposed_step.lock or "None"}

CURRENTLY ACTIVE STEPS:
{active_info if active_info else "  None"}

RECENTLY COMPLETED ARTIFACTS:
{artifact_info if artifact_info else "  None"}

Predict potential conflicts, side effects, and opportunities. Return JSON:
{{
  "conflicts": [
    {{
      "type": "RESOURCE_LOCK|ARTIFACT_DEPENDENCY|SEQUENCE_VIOLATION|CAUSAL_SIDE_EFFECT",
      "affected_steps": ["step_id_1", "step_id_2"],
      "confidence": 0.0-1.0,
      "recommendation": "What should be done",
      "reasoning": "Why this conflict might occur"
    }}
  ],
  "opportunities": [
    {{
      "type": "COLLABORATIVE_OPPORTUNITY",
      "affected_steps": ["step_id_1"],
      "confidence": 0.0-1.0,
      "recommendation": "How agents can collaborate"
    }}
  ]
}}

Only include conflicts with confidence >= 0.6. Be specific about WHY conflicts might occur."""

    def _check_resource_conflicts(
        self, proposed: SopStep, active: List[SopStep]
    ) -> Optional[ConflictPrediction]:
        """Check for obvious resource lock conflicts."""
        if not proposed.lock:
            return None

        conflicting_steps = []
        for step in active:
            if step.lock == proposed.lock and step.id != proposed.id:
                conflicting_steps.append(step.id)

        if conflicting_steps:
            return ConflictPrediction(
                conflict_type=ConflictType.RESOURCE_LOCK,
                affected_steps=conflicting_steps,
                confidence=0.95,  # Very high confidence
                recommendation=f"Wait for {proposed.lock} resource to be released by {', '.join(conflicting_steps)}",
            )

        return None

    def _check_artifact_conflicts(
        self, proposed: SopStep, active: List[SopStep], artifacts: Dict[str, Artifact]
    ) -> Optional[ConflictPrediction]:
        """Check for artifact modification conflicts."""
        # Only check if this is a modifying step
        if not self._is_modifying_step(proposed):
            return None

        potentially_conflicting = []
        for step in active:
            if step.role != proposed.role:  # Different agents
                # Simple check: if they both work on similar artifacts
                if self._steps_work_on_similar_artifacts(proposed, step):
                    potentially_conflicting.append(step.id)

        if potentially_conflicting:
            return ConflictPrediction(
                conflict_type=ConflictType.ARTIFACT_DEPENDENCY,
                affected_steps=potentially_conflicting,
                confidence=0.75,  # Medium-high confidence
                recommendation="Coordinate with affected agents before proceeding - artifact modification conflict detected",
            )

        return None

    def _check_learned_patterns(
        self, proposed: SopStep, active: List[SopStep]
    ) -> Optional[ConflictPrediction]:
        """Check against learned conflict patterns."""
        # Use simple pattern matching based on role-task combinations
        current_scenario = (
            f"{proposed.role}:{proposed.task[:20]}"  # First 20 chars of task
        )

        # Check if this scenario has caused conflicts before
        if current_scenario in self.conflict_patterns:
            conflicting_roles = self.conflict_patterns[current_scenario]

            currently_active_roles = {step.role for step in active}
            active_conflicting_roles = currently_active_roles.intersection(
                conflicting_roles
            )

            if active_conflicting_roles:
                conflicting_step_ids = [
                    step.id for step in active if step.role in active_conflicting_roles
                ]
                return ConflictPrediction(
                    conflict_type=ConflictType.SEQUENCE_VIOLATION,
                    affected_steps=conflicting_step_ids,
                    confidence=0.8,
                    recommendation=f"Previous conflicts detected with {list(active_conflicting_roles)} - consider deferring this step",
                )

        return None

    def _is_modifying_step(self, step: SopStep) -> bool:
        """Determine if a step is likely to modify artifacts."""
        modifying_keywords = {
            "modify",
            "change",
            "update",
            "rewrite",
            "refactor",
            "edit",
            "implement",
            "create",
            "write",
            "add",
            "remove",
            "delete",
        }

        task_lower = step.task.lower()
        return any(keyword in task_lower for keyword in modifying_keywords)

    def _steps_work_on_similar_artifacts(self, step1: SopStep, step2: SopStep) -> bool:
        """Simple heuristic to detect if steps work on similar artifacts."""
        # Extract potential artifact types from task descriptions
        step1_artifacts = self._extract_artifact_mentions(step1.task)
        step2_artifacts = self._extract_artifact_mentions(step2.task)

        # Check for overlap
        overlap = step1_artifacts.intersection(step2_artifacts)
        return len(overlap) > 0

    def _extract_artifact_mentions(self, task_description: str) -> Set[str]:
        """Extract likely artifact mentions from task description."""
        # Simple keyword-based extraction
        artifacts: Set[str] = set()
        task_lower = task_description.lower()

        # Common artifact types
        artifact_keywords = {
            "api",
            "database",
            "ui",
            "frontend",
            "backend",
            "test",
            "spec",
            "code",
            "function",
            "file",
            "component",
            "service",
            "endpoint",
            "class",
            "method",
            "interface",
            "model",
            "schema",
            "config",
        }

        for keyword in artifact_keywords:
            if keyword in task_lower:
                artifacts.add(keyword)

        return artifacts

    def _update_resource_usage_history(self, step: SopStep, success: bool) -> None:
        """Update resource usage history for learning.

        Args:
            step: Executed step
            success: Whether step succeeded

        """
        if not step.lock:
            return

        if step.lock not in self.resource_usage_history:
            self.resource_usage_history[step.lock] = []

        usage_entry = {
            "step_id": step.id,
            "role": step.role,
            "timestamp": time.time(),
            "success": success,
        }
        self.resource_usage_history[step.lock].append(usage_entry)

        # Keep only last 50 entries
        if len(self.resource_usage_history[step.lock]) > 50:
            self.resource_usage_history[step.lock] = self.resource_usage_history[
                step.lock
            ][-50:]

    def _infer_role_from_step_id(self, step_id: str) -> Optional[str]:
        """Infer role from step ID using heuristics.

        Args:
            step_id: Step ID to analyze

        Returns:
            Inferred role or None

        """
        step_id_lower = step_id.lower()
        role_keywords = {
            "engineer": "engineer",
            "qa": "qa",
            "product_manager": "product_manager",
        }

        for keyword, role in role_keywords.items():
            if keyword in step_id_lower:
                return role

        return None

    def _extract_conflicting_roles(
        self, conflicts_observed: List[str], active_steps_at_time: List[str]
    ) -> Set[str]:
        """Extract all conflicting roles from observations.

        Args:
            conflicts_observed: Conflict descriptions
            active_steps_at_time: Active step IDs

        Returns:
            Set of conflicting roles

        """
        conflicting_roles: Set[str] = set()

        # Extract from conflict descriptions
        for conflict_desc in conflicts_observed:
            roles = self._extract_conflicting_roles_from_description(conflict_desc)
            conflicting_roles.update(roles)

        # Infer from active steps
        for active_step_id in active_steps_at_time:
            if role := self._infer_role_from_step_id(active_step_id):
                conflicting_roles.add(role)

        return conflicting_roles

    def _learn_conflict_patterns(
        self,
        step: SopStep,
        conflicts_observed: List[str],
        active_steps_at_time: List[str],
    ) -> None:
        """Learn conflict patterns from execution.

        Args:
            step: Executed step
            conflicts_observed: Observed conflicts
            active_steps_at_time: Active steps during execution

        """
        scenario = f"{step.role}:{step.task[:30]}"
        if scenario not in self.conflict_patterns:
            self.conflict_patterns[scenario] = []

        conflicting_roles = self._extract_conflicting_roles(
            conflicts_observed, active_steps_at_time
        )

        # Add to conflict patterns
        for conflicting_role in conflicting_roles:
            if conflicting_role not in self.conflict_patterns[scenario]:
                self.conflict_patterns[scenario].append(conflicting_role)

        logger.info(
            f"Learned conflict pattern for {scenario}: {self.conflict_patterns[scenario]}"
        )

    def _learn_success_patterns(
        self,
        step: SopStep,
        success: bool,
        conflicts_observed: List[str],
        active_steps_at_time: List[str],
    ) -> None:
        """Learn success patterns from execution.

        Args:
            step: Executed step
            success: Whether step succeeded
            conflicts_observed: Observed conflicts
            active_steps_at_time: Active steps during execution

        """
        if success and not conflicts_observed and active_steps_at_time:
            scenario = f"success:{step.role}:{step.task[:20]}"
            if scenario not in self.conflict_patterns:
                self.conflict_patterns[scenario] = []

    def learn_from_execution(
        self,
        step: SopStep,
        success: bool,
        affected_artifacts: List[str],
        conflicts_observed: List[str],
        active_steps_at_time: List[str],
    ) -> None:
        """Learn from actual execution to improve future predictions.

        Args:
            step: The executed step
            success: Whether the step succeeded
            affected_artifacts: Artifacts that were affected
            conflicts_observed: List of conflicts that occurred
            active_steps_at_time: Steps that were active when this executed

        """
        # Update resource usage history
        self._update_resource_usage_history(step, success)

        # Learn from conflicts
        if conflicts_observed:
            self._learn_conflict_patterns(
                step, conflicts_observed, active_steps_at_time
            )

        # Learn success patterns
        self._learn_success_patterns(
            step, success, conflicts_observed, active_steps_at_time
        )

    def _extract_conflicting_roles_from_description(self, conflict_desc: str) -> set:
        """Extract conflicting role names from conflict description."""
        conflicting_roles = set()
        conflict_lower = conflict_desc.lower()

        # Simple keyword-based extraction
        role_keywords = {
            "engineer": ["engineer", "developer", "coder"],
            "qa": ["qa", "tester", "test"],
            "product_manager": ["product_manager", "product manager", "pm"],
            "architect": ["architect", "architecture"],
            "ui_designer": ["ui", "designer", "frontend"],
        }

        for role, keywords in role_keywords.items():
            if any(keyword in conflict_lower for keyword in keywords):
                conflicting_roles.add(role)

        return conflicting_roles

    def _update_performance_stats(
        self, elapsed_ms: float, conflicts_detected: int
    ) -> None:
        """Update performance statistics for monitoring."""
        self.performance_stats["total_checks"] += 1
        self.performance_stats["total_time_ms"] += elapsed_ms
        self.performance_stats["avg_time_ms"] = (
            self.performance_stats["total_time_ms"]
            / self.performance_stats["total_checks"]
        )
        self.performance_stats["conflicts_detected"] += conflicts_detected

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return self.performance_stats.copy()

    def _check_pm_modification_conflict(
        self, step: SopStep, active_steps: List[SopStep]
    ) -> str | None:
        """Check for product manager modification conflicts.

        Args:
            step: Current step
            active_steps: List of active steps

        Returns:
            Recommendation message or None

        """
        if step.role == "engineer":
            pm_steps = [s for s in active_steps if s.role == "product_manager"]
            if any("modify" in s.task.lower() for s in pm_steps):
                return "Consider waiting for product manager to finalize changes"
        return None

    def _check_resource_lock_conflict(
        self, step: SopStep, active_steps: List[SopStep]
    ) -> str | None:
        """Check for resource lock conflicts.

        Args:
            step: Current step
            active_steps: List of active steps

        Returns:
            Recommendation message or None

        """
        if step.lock:
            locked_steps = [s for s in active_steps if s.lock == step.lock]
            if len(locked_steps) > 0:
                return "Resource is in use - consider deferring or coordinating"
        return None

    def _check_high_concurrency(
        self, step: SopStep, active_steps: List[SopStep]
    ) -> str | None:
        """Check for high concurrency scenarios.

        Args:
            step: Current step
            active_steps: List of active steps

        Returns:
            Recommendation message or None

        """
        if self._is_modifying_step(step) and len(active_steps) > 2:
            return "High concurrent activity detected - consider coordinating modifications"
        return None

    def get_safety_recommendations(
        self, step: SopStep, active_steps: List[SopStep]
    ) -> List[str]:
        """Get simple safety recommendations without complex causal analysis."""
        recommendations = []

        if rec := self._check_pm_modification_conflict(step, active_steps):
            recommendations.append(rec)

        if rec := self._check_resource_lock_conflict(step, active_steps):
            recommendations.append(rec)

        if rec := self._check_high_concurrency(step, active_steps):
            recommendations.append(rec)

        return recommendations
