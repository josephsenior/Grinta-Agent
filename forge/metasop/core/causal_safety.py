from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.causal_reasoning import ConflictPrediction
    from forge.metasop.models import Artifact, SopStep
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class CausalSafetyAdapter:
    """Adapter for causal reasoning engine safety checks and conflict prediction.

    Encapsulates the causal safety pipeline, keeping orchestration logic
    decoupled from the causal engine's internals. This enables future
    extraction into a standalone causal service.
    """

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check_causal_safety(
        self, step: "SopStep", done: Dict[str, "Artifact"]
    ) -> bool:
        """Check if step can proceed safely based on causal analysis.

        Args:
            step: Step to analyze for safety
            done: Completed artifacts from previous steps

        Returns:
            True if step can proceed, False if blocked by high-confidence conflicts

        Side Effects:
            - Emits blocking events if conflicts detected
            - Emits warning events for medium-confidence conflicts
            - Logs analysis results

        """
        if not self._orch.causal_engine:
            return True

        try:
            can_proceed, predictions = self.run_causal_analysis(step, done)

            if not can_proceed:
                self.handle_blocking_predictions(step, predictions)
                return False

            self.handle_warning_predictions(step, predictions)
        except Exception as exc:
            self._orch._logger.warning(f"Causal safety check failed: {exc}")
            return True

        return True

    def run_causal_analysis(
        self, step: "SopStep", done: Dict[str, "Artifact"]
    ) -> Tuple[bool, List["ConflictPrediction"]]:
        """Run causal analysis for step safety.

        Args:
            step: Step to analyze
            done: Completed artifacts from previous steps

        Returns:
            Tuple of (can_proceed, predictions) where:
            - can_proceed: True if step should be allowed to execute
            - predictions: List of conflict predictions from the engine

        """
        causal_engine = self._orch.causal_engine
        if causal_engine is None:
            return True, []

        active_steps = self._get_active_steps()
        current_context = getattr(self._orch, "_ctx", None)

        max_analysis_time_ms = getattr(
            self._orch.settings, "causal_max_analysis_time_ms", 50
        )

        return causal_engine.analyze_step_safety(
            proposed_step=step,
            active_steps=active_steps,
            completed_artifacts=done,
            current_context=current_context,
            max_analysis_time_ms=max_analysis_time_ms,
        )

    def handle_blocking_predictions(
        self, step: "SopStep", predictions: List["ConflictPrediction"]
    ) -> None:
        """Handle high-confidence blocking predictions.

        Emits structured events for predictions with confidence > 0.8,
        indicating the step should be blocked from execution.

        Args:
            step: Step being analyzed
            predictions: List of conflict predictions from causal engine

        Side Effects:
            - Emits "causally_blocked" event with prediction details
            - Logs blocking decision

        """
        blocking_predictions = [p for p in predictions if p.confidence > 0.8]
        if not blocking_predictions:
            return

        self._orch._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "causally_blocked",
                "reason": "predicted_conflicts",
                "predictions": [
                    {
                        "type": pred.conflict_type.value,
                        "affected_steps": pred.affected_steps,
                        "confidence": pred.confidence,
                        "recommendation": pred.recommendation,
                    }
                    for pred in blocking_predictions
                ],
            }
        )
        self._orch._logger.info(f"Step {step.id} blocked due to causal conflicts")

    def handle_warning_predictions(
        self, step: "SopStep", predictions: List["ConflictPrediction"]
    ) -> None:
        """Handle medium-confidence warning predictions.

        Emits advisory events for predictions with confidence between 0.5-0.8,
        indicating potential conflicts that don't warrant blocking.

        Args:
            step: Step being analyzed
            predictions: List of conflict predictions from causal engine

        Side Effects:
            - Emits "causal_warnings" event if warnings present
            - No blocking occurs, step proceeds with advisory

        """
        warning_predictions = [p for p in predictions if 0.5 <= p.confidence <= 0.8]
        if not warning_predictions:
            return

        self._orch._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "causal_warnings",
                "predictions": [
                    {
                        "type": pred.conflict_type.value,
                        "affected_steps": pred.affected_steps,
                        "confidence": pred.confidence,
                        "recommendation": pred.recommendation,
                    }
                    for pred in warning_predictions
                ],
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_active_steps(self) -> List["SopStep"]:
        """Get list of currently executing steps for causal analysis context."""
        return list(self._orch.active_steps.values())


__all__ = ["CausalSafetyAdapter"]

