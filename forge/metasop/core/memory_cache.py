from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from forge.metasop.cache import StepCache, StepCacheEntry
from forge.metasop.context_hash import compute_context_hash
from forge.metasop.diff_utils import compute_diff_fingerprint
from forge.metasop.memory import MemoryIndex
from forge.metasop.models import Artifact, OrchestrationContext, SopStep
from forge.metasop.strategies import VectorOrLexicalMemoryStore
from forge.metasop.selective_tests import select_tests
from forge.structural import available as structural_available
from forge.metasop.validators import validate_json
from forge.metasop.registry import load_schema

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.orchestrator import MetaSOPOrchestrator

logger = logging.getLogger(__name__)


class MemoryCacheManager:
    """Encapsulates memory store, retrieval, and step cache logic."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def initialize_memory_and_cache(self) -> None:
        self._initialize_memory_store()
        self._orch.memory_index = None
        self._initialize_step_cache()

    def _initialize_memory_store(self) -> None:
        try:
            self._orch.memory_store = VectorOrLexicalMemoryStore(
                self._orch.settings.enable_vector_memory,
                self._orch.settings.vector_embedding_dim,
                self._orch.settings.memory_max_records,
            )
        except (ImportError, OSError, ValueError, RuntimeError):
            self._orch.memory_store = VectorOrLexicalMemoryStore(False, None, None)

    def _initialize_step_cache(self) -> None:
        try:
            if getattr(self._orch.settings, "enable_step_cache", False):
                self._orch.step_cache = StepCache(
                    max_entries=getattr(self._orch.settings, "step_cache_max_entries", 256)
                    or 256,
                    cache_dir=getattr(self._orch.settings, "step_cache_dir", None),
                    ttl_seconds=getattr(
                        self._orch.settings, "step_cache_allow_stale_seconds", None
                    ),
                    min_tokens_threshold=getattr(
                        self._orch.settings, "step_cache_min_tokens_saved", None
                    ),
                    exclude_roles=getattr(
                        self._orch.settings, "step_cache_exclude_roles", None
                    ),
                )
            else:
                self._orch.step_cache = None
        except (OSError, ValueError, TypeError):
            self._orch.step_cache = None

    # ------------------------------------------------------------------
    # Artifact provenance helpers
    # ------------------------------------------------------------------
    def compute_artifact_hash(self, artifact: Optional[Artifact]) -> Optional[str]:
        if not artifact:
            return None
        base = {
            "step_id": artifact.step_id,
            "role": artifact.role,
            "content": artifact.content,
        }
        return self._orch._hash_dict(base)

    def compute_step_hash(
        self, artifact_hash: Optional[str], rationale: Optional[str]
    ) -> str:
        material = {
            "prev": self._orch._previous_step_hash,
            "artifact_hash": artifact_hash,
            "rationale": rationale,
        }
        return self._orch._hash_dict(material)

    def ensure_artifact_provenance(
        self, artifact: Optional[Artifact], step: Optional[SopStep] = None, prev_text: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        if not artifact:
            return None, None
        try:
            art_hash = self.compute_artifact_hash_safe(artifact)
            fp = self._compute_diff_fingerprint_safe(artifact, prev_text)
            self._attach_provenance_to_artifact(artifact, art_hash, fp)
            return art_hash, fp
        except (TypeError, ValueError, AttributeError):
            return None, None

    def compute_artifact_hash_safe(self, artifact: Artifact) -> Optional[str]:
        try:
            return self.compute_artifact_hash(artifact)
        except (TypeError, ValueError, AttributeError):
            return None

    def _compute_diff_fingerprint_safe(
        self, artifact: Artifact, prev_text: Optional[str]
    ) -> Optional[str]:
        try:
            new_text = self._extract_artifact_text_safe(artifact)
            if not new_text:
                return None
            unified = self._compute_unified_diff_safe(prev_text, new_text)
            return self._compute_fingerprint_from_diff_or_text(unified, new_text)
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _extract_artifact_text_safe(artifact: Artifact) -> Optional[str]:
        try:
            content: Any = artifact.content
            if isinstance(content, dict):
                return (
                    content.get("content")
                    or content.get("text")
                    or json.dumps(content, sort_keys=True)
                )
            return str(content)
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _compute_unified_diff_safe(prev_text: Optional[str], new_text: str) -> str:
        if not (isinstance(prev_text, str) and prev_text != new_text):
            return ""
        try:
            import difflib

            diff = difflib.unified_diff(
                prev_text.splitlines(),
                new_text.splitlines(),
                fromfile="prev",
                tofile="new",
                lineterm="",
            )
            return "\n".join(diff)
        except (TypeError, AttributeError, ImportError):
            return ""

    @staticmethod
    def _compute_fingerprint_from_diff_or_text(unified: str, new_text: str) -> Optional[str]:
        try:
            if unified and unified.strip():
                return compute_diff_fingerprint(unified)
            return hashlib.sha256((new_text or "").encode("utf-8")).hexdigest()[:16]
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _attach_provenance_to_artifact(
        artifact: Artifact, art_hash: Optional[str], fp: Optional[str]
    ) -> None:
        try:
            if isinstance(artifact.content, dict):
                prov = artifact.content.setdefault("_provenance", {})
                if art_hash and "artifact_hash" not in prov:
                    prov["artifact_hash"] = art_hash
                if fp and "diff_fingerprint" not in prov:
                    prov["diff_fingerprint"] = fp
        except (TypeError, AttributeError, KeyError):
            pass

    # ------------------------------------------------------------------
    # Memory ingestion & retrieval
    # ------------------------------------------------------------------
    def ingest_artifact_to_memory(self, step: SopStep, artifact: Artifact) -> None:
        if not self._orch.memory_index:
            return
        try:
            artifact_hash = self.compute_artifact_hash(artifact)
            content_text = (
                json.dumps(artifact.content, sort_keys=True)
                if isinstance(artifact.content, dict)
                else str(artifact.content)
            )
            self._orch.memory_index.add(
                step.id,
                step.role,
                artifact_hash,
                None,
                content_text,
            )
        except (TypeError, ValueError, AttributeError):
            pass

    def perform_memory_retrieval(self, step: SopStep, ctx: OrchestrationContext) -> None:
        memory_store = getattr(self._orch, "memory_store", None)
        if memory_store is None:
            return

        stats = memory_store.stats()
        lexical_records = stats.get("lexical", {}).get("records", 0)
        vector_records = stats.get("vector", {}).get("records", 0)
        if lexical_records + vector_records <= 0:
            return

        try:
            ctx_request = self._orch._ctx.user_request if self._orch._ctx else ""
            query = f"{step.task}\n{ctx_request}"[:500]
            retrieval_key = f"retrieval::{step.id}"

            hits: list[dict[str, Any]] = []
            if hasattr(memory_store, "search"):
                if (
                    getattr(self._orch.settings, "enable_hybrid_retrieval", False)
                    and getattr(self._orch.settings, "enable_vector_memory", False)
                ):
                    hits = self._perform_hybrid_retrieval(query)
                else:
                    hits = memory_store.search(query, k=3)

            if shaped_hits := self._shape_retrieval_hits(hits):
                ctx.extra[retrieval_key] = shaped_hits
                ctx.extra.setdefault("retrieval_keys", []).append(retrieval_key)
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "suppressed_error",
                    "reason": "retrieval_failed",
                    "error": str(exc)[:300],
                }
            )
            if getattr(self._orch.settings, "strict_mode", False):
                raise

    def _perform_hybrid_retrieval(self, query: str) -> list[dict[str, Any]]:
        memory_store = getattr(self._orch, "memory_store", None)
        if memory_store is None:
            return []
        stats = memory_store.stats()
        vector_hits = self._get_vector_hits(memory_store, query, stats)
        lexical_hits = self._get_lexical_hits(memory_store, query, stats)
        return self._fuse_retrieval_results(vector_hits, lexical_hits)

    @staticmethod
    def _get_vector_hits(store, query: str, stats: dict) -> list:
        try:
            if stats.get("vector"):
                vector_store = getattr(store, "_vector_store", None)
                if vector_store:
                    return vector_store.search(query, k=5)
        except (AttributeError, RuntimeError, ValueError):
            pass
        return []

    @staticmethod
    def _get_lexical_hits(store, query: str, stats: dict) -> list:
        try:
            if stats.get("lexical"):
                lex_store = getattr(store, "_lex_store", None)
                if lex_store:
                    return lex_store.search(query, k=5)
        except (AttributeError, RuntimeError, ValueError):
            pass
        return []

    def _fuse_retrieval_results(self, vector_hits: list, lexical_hits: list) -> list:
        v_norm = self._normalize_hits(vector_hits)
        l_norm = self._normalize_hits(lexical_hits)
        combined = self._combine_normalized_hits(v_norm, l_norm)
        vw, lw = self._get_fusion_weights()
        fused = self._create_fused_results(combined, vw, lw)
        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:3]

    @staticmethod
    def _normalize_hits(hits: list) -> list:
        if not hits:
            return []
        max_score = max((h.get("score") or 0) for h in hits) or 1
        return [(h.get("step_id"), h, (h.get("score") or 0) / max_score) for h in hits]

    @staticmethod
    def _combine_normalized_hits(v_norm: list, l_norm: list) -> dict:
        combined: dict[str, dict[str, Any]] = {
            sid: {"hit": h, "v": score, "l": 0.0}
            for sid, h, score in v_norm
            if sid
        }
        for sid, h, score in l_norm:
            if not sid:
                continue
            if sid in combined:
                combined[sid]["l"] = max(combined[sid]["l"], score)
            else:
                combined[sid] = {"hit": h, "v": 0.0, "l": score}
        return combined

    def _get_fusion_weights(self) -> tuple[float, float]:
        vw = getattr(self._orch.settings, "hybrid_vector_weight", None) or 0.6
        lw_setting = getattr(self._orch.settings, "hybrid_lexical_weight", None)
        lw = lw_setting if lw_setting is not None else (1 - vw)
        return vw, lw

    @staticmethod
    def _create_fused_results(combined: dict, vw: float, lw: float) -> list:
        fused = []
        for meta in combined.values():
            fused_score = vw * meta["v"] + lw * meta["l"]
            hit = dict(meta["hit"])
            hit["score"] = round(fused_score, 4)
            hit["vector_component"] = round(meta["v"], 4)
            hit["lexical_component"] = round(meta["l"], 4)
            fused.append(hit)
        return fused

    @staticmethod
    def _shape_retrieval_hits(hits: Iterable[dict]) -> list:
        return [
            {
                "step_id": hit.get("step_id"),
                "role": hit.get("role"),
                "score": hit.get("score"),
                "rationale": (hit.get("rationale") or "")[:300],
                "excerpt": (hit.get("excerpt") or "")[:400],
            }
            for hit in hits
        ]

    # ------------------------------------------------------------------
    # Step cache helpers
    # ------------------------------------------------------------------
    def compute_pre_context_hash(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
    ) -> Optional[str]:
        if not getattr(self._orch.settings, "enable_context_hash", False):
            return None
        try:
            retrieval_hits = self._get_retrieval_hits(step, ctx)
            prior_artifacts = self._get_prior_artifacts_meta(done)
            env_sig = getattr(getattr(self._orch, "_ctx", None), "extra", {}).get(
                "environment_signature"
            )
            return compute_context_hash(
                step_id=step.id,
                role=step.role,
                retrieval_hits=retrieval_hits,
                prior_artifacts=prior_artifacts,
                role_capabilities=(
                    self._orch.profile_manager.get_role_capabilities(step.role)
                ),
                env_signature=env_sig,
                model_name=None,
                executor_name=type(self._orch.step_executor).__name__,
                truncate_bytes=self._orch.settings.context_hash_truncate_artifact_bytes,
            )
        except (TypeError, ValueError, AttributeError):
            return None

    def _get_retrieval_hits(
        self, step: SopStep, ctx: OrchestrationContext
    ) -> list[Dict[str, Any]]:
        rkey = f"retrieval::{step.id}"
        extra = getattr(ctx, "extra", None)
        if isinstance(extra, dict):
            hits = extra.get(rkey, [])
            if isinstance(hits, list):
                return list(hits)
        return []

    def _get_prior_artifacts_meta(
        self, done: Dict[str, Artifact]
    ) -> list[Dict[str, Any]]:
        prior_artifacts_meta: list[Dict[str, Any]] = []
        for sid, art in done.items():
            with contextlib.suppress(TypeError, ValueError, AttributeError):
                prior_artifacts_meta.append(
                    {
                        "step_id": sid,
                        "artifact_hash": self.compute_artifact_hash(art),
                        "role": art.role,
                    }
                )
        return prior_artifacts_meta

    def check_step_cache(
        self, step: SopStep, pre_context_hash: Optional[str]
    ) -> Optional[Dict[str, Artifact]]:
        cache = getattr(self._orch, "step_cache", None)
        if cache is None or pre_context_hash is None:
            return None
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            hit = cache.get(pre_context_hash, step.role)
            if hit:
                return self.process_cache_hit(step, hit)
        return None

    def process_cache_hit(self, step: SopStep, hit) -> Dict[str, Artifact]:
        cached_artifact = Artifact(
            step_id=step.id,
            role=step.role,
            content=hit.artifact_content,
        )
        self._orch._previous_step_hash = hit.step_hash or self._orch._previous_step_hash
        self.emit_cache_hit_event(step)
        return {step.id: cached_artifact}

    def emit_cache_hit_event(self, step: SopStep) -> None:
        self._orch._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "executed_cached",
                "duration_ms": 0,
                "retries": 0,
            }
        )

    def store_step_in_cache(
        self, step: SopStep, artifacts: Dict[str, Artifact], pre_context_hash: str
    ) -> None:
        try:
            artifact = artifacts.get(step.id)
            if not artifact:
                return
            cache = getattr(self._orch, "step_cache", None)
            if cache is None:
                return
            entry = StepCacheEntry(
                context_hash=pre_context_hash,
                step_id=step.id,
                role=step.role,
                artifact_content=artifact.content,
                artifact_hash=self.compute_artifact_hash(artifact),
                step_hash=self.compute_step_hash(self.compute_artifact_hash(artifact), None),
                rationale=None,
                model_name=None,
                total_tokens=None,
                diff_fingerprint=(
                    artifact.content.get("_provenance", {}).get("diff_fingerprint")
                    if isinstance(artifact.content, dict)
                    else None
                ),
                created_ts=time.time(),
            )
            cache.put(entry)
        except (AttributeError, TypeError, ValueError):
            pass

    # ------------------------------------------------------------------
    # QA selective tests
    # ------------------------------------------------------------------
    def perform_selective_tests(
        self, step: SopStep, ctx: OrchestrationContext
    ) -> tuple[Optional[list[str]], Optional[str]]:
        if not getattr(self._orch.settings, "qa_selective_tests_enable", False):
            return None, None
        try:
            repo_root_abs = getattr(ctx, "repo_root", None) or "."
            changed_paths: list[str] = []
            mode = getattr(self._orch.settings, "qa_selective_tests_mode", None) or "imports"
            max_sel = getattr(self._orch.settings, "qa_selective_tests_max", None)
            selected = select_tests(
                changed_paths,
                repo_root_abs,
                mode=mode,
                max_tests=max_sel,
            )
            if selected:
                self._orch._emit_event(
                    {
                        "step_id": step.id,
                        "role": step.role,
                        "status": "advisory",
                        "reason": "qa_selective_tests_applied",
                        "meta": {
                            "tests": selected[:10],
                            "total": len(selected),
                            "mode": mode,
                        },
                    }
                )
                return selected, f"mode={mode} count={len(selected)}"
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "advisory",
                    "reason": "qa_selective_tests_fallback_full",
                    "meta": {"mode": mode},
                }
            )
            return None, None
        except (OSError, ValueError, AttributeError, RuntimeError) as exc:
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "suppressed_error",
                    "reason": "qa_selective_tests_error",
                    "error": str(exc)[:300],
                }
            )
            return None, None


__all__ = ["MemoryCacheManager"]
