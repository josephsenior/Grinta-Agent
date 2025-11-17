"""Micro-iteration candidate generation and scoring for MetaSOP."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from forge.core.pydantic_compat import model_dump_with_options

from .models import Artifact, SopStep, StepResult, VerificationResult
from .core.artifacts import build_qa_verification
from .patch_scoring import PatchCandidate, score_candidates
from .diff_utils import compute_diff_fingerprint

if TYPE_CHECKING:
    from .orchestrator import MetaSOPOrchestrator


class CandidateGenerationService:
    """Encapsulates candidate generation, patch scoring, and selection logic."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    def generate_and_select(
        self,
        step: SopStep,
        ctx,
        role_profile: Dict[str, Any],
        retry_policy,
        candidate_count: int,
    ) -> StepResult:
        candidates = self._generate_candidates(
            step, ctx, role_profile, candidate_count
        )
        if not candidates:
            return StepResult(ok=False, error="no_valid_candidates")

        if getattr(self._orch.settings, "patch_scoring_enable", False):
            best = self._select_best_candidate_with_scoring(candidates, step)
            if best:
                return best

        return self._create_step_result_from_candidate(candidates[0], step)

    # ------------------------------------------------------------------ #
    # Legacy helpers moved from MetaSOPOrchestrator
    # ------------------------------------------------------------------ #
    def _generate_candidates(
        self,
        step: SopStep,
        ctx,
        role_profile: Dict[str, Any],
        candidate_count: int,
    ) -> List[StepResult]:
        candidates: List[StepResult] = []
        for _ in range(candidate_count):
            try:
                if self._orch.llm_registry and not hasattr(ctx, "llm_registry"):
                    ctx.llm_registry = self._orch.llm_registry
                candidate = self._orch.step_executor.execute(
                    step,
                    ctx,
                    model_dump_with_options(role_profile),
                    config=self._orch.config,
                )
                if candidate and candidate.ok and candidate.artifact:
                    patch_candidate = self._create_patch_candidate(
                        candidate.artifact, step
                    )
                    candidates.append(patch_candidate)
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
        return candidates

    def _select_best_candidate_with_scoring(
        self, candidates: List[StepResult], step: SopStep
    ) -> StepResult | None:
        try:
            patch_candidates: list[PatchCandidate] = []
            candidate_map: list[StepResult] = []
            for candidate in candidates:
                artifact = candidate.artifact
                if not artifact or not isinstance(artifact.content, dict):
                    continue
                patch_text = artifact.content.get("diff") or artifact.content.get("patch")
                if not patch_text:
                    continue
                meta: dict[str, Any] | None = None
                file_context = artifact.content.get("file_context")
                if file_context:
                    meta = {"file_context": file_context}
                patch_candidates.append(
                    PatchCandidate(
                        content=str(artifact.content),
                        diff=str(patch_text),
                        meta=meta,
                    )
                )
                candidate_map.append(candidate)

            if not patch_candidates:
                return None

            scores = score_candidates(patch_candidates, self._orch.settings)
            if not scores:
                return None

            best_index = max(range(len(scores)), key=lambda i: scores[i].composite)
            return candidate_map[best_index]
        except Exception:
            return None

    def _create_patch_candidate(self, artifact: Artifact, step: SopStep) -> StepResult:
        content = artifact.content or {}
        patch_diff = content.get("diff") or content.get("patch")
        fingerprint = compute_diff_fingerprint(patch_diff) if patch_diff else None
        verification_payload = build_qa_verification(content)
        verification_result: VerificationResult | None = None
        if verification_payload:
            try:
                verification_result = VerificationResult.model_validate(
                    verification_payload
                )
            except Exception:
                verification_result = None

        return StepResult(
            ok=True,
            artifact=Artifact(
                step_id=step.id,
                role=step.role,
                content=content,
            ),
            step_hash=fingerprint,
            verification_result=verification_result,
        )

    def _create_step_result_from_candidate(
        self, candidate: StepResult, step: SopStep
    ) -> StepResult:
        artifact = candidate.artifact
        if artifact:
            artifact.step_id = artifact.step_id or step.id
            artifact.role = artifact.role or step.role
        return candidate


