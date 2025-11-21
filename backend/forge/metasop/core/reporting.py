from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .artifacts import build_verification_report

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import OrchestrationContext, SopTemplate, StepTrace
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class ReportingToolkit:
    """Handles run reporting, manifest generation, and verification summaries."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Manifest export
    # ------------------------------------------------------------------
    def export_run_manifest(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Export run manifest for reproducibility and audit trails.

        Creates a comprehensive manifest containing:
        - Run metadata (ID, timestamp, SOP name)
        - Environment signature
        - Step execution details
        - Provenance chain
        - Efficiency metrics
        - Memory statistics

        Args:
            output_dir: Optional directory path to write manifest file.
                       If None, returns JSON string instead.

        Returns:
            Path to manifest file if output_dir provided, else JSON string.
            Returns None if template is missing or export fails.

        """
        try:
            if not self._orch.template:
                return None

            manifest = {
                "version": "1.0",
                "run_id": getattr(self._orch, "_run_id", str(uuid.uuid4())),
                "sop_name": getattr(self._orch.template, "name", "unknown"),
                "timestamp": time.time(),
                "environment_signature": getattr(
                    self._orch._ctx, "environment_signature", ""
                )
                if self._orch._ctx
                else "",
                "steps": self.build_steps_manifest(),
                "provenance": self.build_provenance_manifest(),
                "efficiency": self.build_efficiency_manifest(),
                "memory_stats": self.build_memory_stats_manifest(),
            }

            manifest["manifest_hash"] = self._hash_dict(manifest)

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                manifest_path = os.path.join(
                    output_dir, f"run_manifest_{manifest['run_id']}.json"
                )
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
                return manifest_path

            return json.dumps(manifest, indent=2)

        except (OSError, TypeError, ValueError, AttributeError) as exc:
            self._orch._emit_event(
                {
                    "status": "error",
                    "reason": "manifest_export_failed",
                    "error": str(exc)[:300],
                },
            )
            return None

    def build_steps_manifest(self) -> List[Dict[str, Any]]:
        """Build steps section of manifest with execution details.

        Returns:
            List of step manifest dictionaries containing:
            - step_id, role, status, duration_ms, retries
            - artifact_hash, step_hash (if available)
            - failure_type, remediation (if failed)

        """
        steps_manifest: List[Dict[str, Any]] = []

        for trace in self._orch.traces:
            step_manifest: Dict[str, Any] = {
                "step_id": trace.step_id,
                "role": trace.role,
                "status": "executed",
                "duration_ms": trace.duration_ms,
                "retries": trace.retries,
            }

            if hasattr(trace, "artifact_hash"):
                step_manifest["artifact_hash"] = trace.artifact_hash

            if hasattr(trace, "step_hash"):
                step_manifest["step_hash"] = trace.step_hash

            failed_events = [
                e
                for e in self._orch.step_events
                if e.get("step_id") == trace.step_id and e.get("status") == "failed"
            ]

            if failed_events:
                step_manifest["status"] = "failed"
                failure_analysis = failed_events[0].get("failure_analysis", {})
                step_manifest["failure_type"] = failure_analysis.get("failure_type")
                step_manifest["remediation"] = failed_events[0].get("remediation")

            steps_manifest.append(step_manifest)

        return steps_manifest

    def build_provenance_manifest(self) -> Dict[str, Optional[str]]:
        """Build provenance section tracking execution chain.

        Returns:
            Dictionary with chain_root and final_step_hash.

        """
        previous_hash = getattr(self._orch, "_previous_step_hash", None)
        return {
            "chain_root": previous_hash,
            "final_step_hash": previous_hash,
        }

    def build_efficiency_manifest(self) -> Dict[str, Any]:
        """Build efficiency metrics section.

        Returns:
            Dictionary with token usage and execution efficiency metrics.

        """
        total_tokens = sum(t.total_tokens or 0 for t in self._orch.traces)
        successful_steps = [
            e for e in self._orch.step_events if e.get("status") == "executed"
        ]
        successful_token_sum = sum(
            e.get("total_tokens") or 0 for e in successful_steps
        )

        return {
            "total_tokens": total_tokens or None,
            "executed_steps": len(successful_steps),
            "tokens_per_successful_step": (
                round(successful_token_sum / len(successful_steps), 2)
                if successful_steps
                else None
            ),
        }

    def build_memory_stats_manifest(self) -> Dict[str, Any]:
        """Build memory statistics section.

        Returns:
            Dictionary with lexical/vector record counts, or empty dict if no memory store.

        """
        if not self._orch.memory_store:
            return {}

        try:
            stats = self._orch.memory_store.stats()
            lexical_records = stats.get("lexical", {}).get("records", 0)
            vector_records = stats.get("vector", {}).get("records", 0)
            return {
                "lexical_records": lexical_records,
                "vector_records": vector_records,
                "total_records": lexical_records + vector_records,
            }
        except (AttributeError, TypeError, ValueError):
            return {}

    # ------------------------------------------------------------------
    # Verification reports
    # ------------------------------------------------------------------
    def get_verification_report(self) -> Dict[str, Any]:
        """Get verification report for executed steps.

        Delegates to artifacts module to build comprehensive verification
        report including executed steps, skipped steps, and efficiency metrics.

        Returns:
            Dictionary containing verification report data.

        """
        return build_verification_report(
            self._orch.traces, self._orch.step_events, self._orch.template
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_dict(data: Dict[str, Any]) -> str:
        """Compute deterministic SHA256 hash of a dictionary.

        Args:
            data: Dictionary to hash, must be JSON-serializable

        Returns:
            SHA256 hex digest of JSON-serialized and sorted dictionary

        Notes:
            - Uses JSON serialization with sorted keys for determinism
            - Falls back to repr() if dictionary contains non-JSON-serializable objects

        """
        try:
            encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        except (TypeError, ValueError):
            encoded = repr(data).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


__all__ = ["ReportingToolkit"]

