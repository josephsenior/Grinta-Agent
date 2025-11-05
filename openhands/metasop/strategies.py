"""Strategy interfaces for MetaSOP orchestration.

This layer decouples the orchestrator from concrete execution / QA /
failure classification / memory storage implementations so future
customization or experimentation does not require editing the main
control loop.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from .adapters.engineer_codeact import run_engineer_with_codeact
from .adapters.openhands import run_step_with_openhands
from .failure_taxonomy import classify_failure
from .memory import MemoryIndex
from .models import Artifact, OrchestrationContext, SopStep, StepResult
from .qa import run_pytest
from .vector_memory import VectorMemoryStore

if TYPE_CHECKING:
    from openhands.core.config import OpenHandsConfig


class BaseStepExecutor(ABC):

    @abstractmethod
    def execute(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile: dict[str, Any],
        config: OpenHandsConfig | None,
    ) -> StepResult:
        """Execute a non-QA step and return a StepResult."""


class DefaultStepExecutor(BaseStepExecutor):

    def execute(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile: dict[str, Any],
        config: OpenHandsConfig | None,
    ) -> StepResult:
        role_l = step.role.strip().lower()
        if role_l == "engineer":
            return run_engineer_with_codeact(step, ctx, role_profile, config)
        # Use the orchestrator's LLM registry if available
        llm_registry = getattr(ctx, "llm_registry", None)
        return run_step_with_openhands(step, ctx, role_profile, config=config, llm_registry=llm_registry)


class TimeoutStepExecutor(BaseStepExecutor):
    """Wrap another executor adding a hard wall clock timeout.

    Implementation uses a worker thread because underlying adapters are
    synchronous. Cancellation is cooperative (work may continue in the
    background, but we discard result after timeout). Optionally accepts
    a stuck_callback which will be invoked if the worker thread remains
    alive for longer than `stuck_threshold` seconds after the initial
    timeout.
    """

    def __init__(
        self,
        inner: BaseStepExecutor,
        timeout_seconds: int | None,
        stuck_callback: Callable[[SopStep, OrchestrationContext, threading.Thread, float], None] | None = None,
        stuck_threshold: float | None = None,
    ) -> None:
        self.inner = inner
        self.timeout = timeout_seconds
        self._stuck_callback = stuck_callback
        self._stuck_threshold = (
            stuck_threshold if stuck_threshold is not None else self.timeout * 2 if self.timeout else 30
        )

    def execute(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile: dict[str, Any],
        config: OpenHandsConfig | None,
    ) -> StepResult:
        if not self.timeout or self.timeout <= 0:
            return self.inner.execute(step, ctx, role_profile, config)
        result_container: dict[str, Any] = {}

        def run_inner() -> None:
            result_container["result"] = self.inner.execute(step, ctx, role_profile, config)

        th = threading.Thread(target=run_inner, daemon=True)
        th.start()
        th.join(self.timeout)
        if th.is_alive():
            try:
                if self._stuck_callback:

                    def _watcher(
                        worker: threading.Thread,
                        step_arg: SopStep,
                        ctx_arg: OrchestrationContext,
                        timeout_val: float,
                        threshold: float,
                    ) -> None:
                        try:
                            time.sleep(threshold)
                            if worker.is_alive():
                                try:
                                    self._stuck_callback(step_arg, ctx_arg, worker, timeout_val)
                                except Exception:
                                    logging.exception("stuck_callback raised")
                        except Exception:
                            logging.exception("stuck watcher crashed")

                    watcher = threading.Thread(
                        target=_watcher,
                        args=(th, step, ctx, self.timeout, self._stuck_threshold),
                        daemon=True,
                    )
                    watcher.start()
            except Exception:
                logging.exception("Failed to start stuck watcher")
            return StepResult(ok=False, error=f"step_timeout_after_{self.timeout}s")
        return result_container.get("result") or StepResult(ok=False, error="unknown_execution_failure")


class BaseQAExecutor(ABC):

    @abstractmethod
    def run_qa(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        repo_root: str | None,
        selected_tests: list[str] | None = None,
    ) -> Artifact:
        """Execute QA step (tests + shaping) returning an Artifact."""


class DefaultQAExecutor(BaseQAExecutor):

    def run_qa(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        repo_root: str | None,
        selected_tests: list[str] | None = None,
    ) -> Artifact:
        return run_pytest(repo_root)


class TimeoutQAExecutor(BaseQAExecutor):

    def __init__(
        self,
        inner: BaseQAExecutor,
        timeout_seconds: int | None,
        stuck_callback: Callable[[SopStep, OrchestrationContext, threading.Thread, float], None] | None = None,
        stuck_threshold: float | None = None,
    ) -> None:
        self.inner = inner
        self.timeout = timeout_seconds
        self._stuck_callback = stuck_callback
        self._stuck_threshold = (
            stuck_threshold if stuck_threshold is not None else self.timeout * 2 if self.timeout else 30
        )

    def run_qa(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        repo_root: str | None,
        selected_tests: list[str] | None = None,
    ) -> Artifact:
        if not self.timeout or self.timeout <= 0:
            return self.inner.run_qa(step, ctx, repo_root, selected_tests)
        result_container: dict[str, Any] = {}

        def run_inner() -> None:
            result_container["artifact"] = self.inner.run_qa(step, ctx, repo_root, selected_tests)

        th = threading.Thread(target=run_inner, daemon=True)
        th.start()
        th.join(self.timeout)
        if th.is_alive():
            try:
                if self._stuck_callback:

                    def _watcher(
                        worker: threading.Thread,
                        step_arg: SopStep,
                        ctx_arg: OrchestrationContext,
                        timeout_val: float,
                        threshold: float,
                    ) -> None:
                        try:
                            time.sleep(threshold)
                            if worker.is_alive():
                                try:
                                    self._stuck_callback(step_arg, ctx, worker, timeout_val)
                                except Exception:
                                    logging.exception("stuck_callback raised")
                        except Exception:
                            logging.exception("stuck watcher crashed")

                    watcher = threading.Thread(
                        target=_watcher,
                        args=(th, step, ctx, self.timeout, self._stuck_threshold),
                        daemon=True,
                    )
                    watcher.start()
            except Exception:
                logging.exception("Failed to start stuck watcher")
            return Artifact(step_id=step.id, role=step.role, content={"ok": False, "timeout": True})
        return result_container.get("artifact") or Artifact(
            step_id=step.id,
            role=step.role,
            content={"ok": False, "error": "qa_unknown_failure"},
        )


class BaseFailureClassifier(ABC):

    @abstractmethod
    def classify(self, step_id: str, role: str, **kwargs: Any) -> tuple[str | None, dict | None]:
        """Return (failure_type, meta) or (None, None)."""


class DefaultFailureClassifier(BaseFailureClassifier):

    def classify(self, step_id: str, role: str, **kwargs: Any) -> tuple[str | None, dict | None]:
        return classify_failure(step_id, role, **kwargs)


class BaseMemoryStore(ABC):

    @abstractmethod
    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
    ) -> None: ...

    @abstractmethod
    def search(self, query: str, k: int = 3) -> list[dict]: ...

    @abstractmethod
    def stats(self) -> dict: ...


class MemoryIndexStore(BaseMemoryStore):
    """Adapter wrapper around existing MemoryIndex for uniform interface."""

    def __init__(self, index: MemoryIndex | None) -> None:
        self._index = index

    def add(self, step_id: str, role: str, artifact_hash: str | None, rationale: str | None, content_text: str) -> None:
        if not self._index:
            return
        self._index.add(step_id, role, artifact_hash, rationale, content_text)

    def search(self, query: str, k: int = 3) -> list[dict]:
        return self._index.search(query, k=k) if self._index else []

    def stats(self) -> dict:
        return self._index.stats() if self._index else {}


class VectorOrLexicalMemoryStore(BaseMemoryStore):
    """Dispatches to either a VectorMemoryStore (semantic) or MemoryIndex (lexical).

    Selection decided at construction. Provides the same interface for orchestrator.
    """

    def __init__(self, vector_enabled: bool, dim: int | None, max_records: int | None) -> None:
        self._vector_enabled = vector_enabled
        self._vector_store: VectorMemoryStore | None = None
        self._lex_store: MemoryIndex | None = MemoryIndex(run_id="__transient__", max_records=max_records)
        if vector_enabled:
            self._vector_store = VectorMemoryStore(dim=dim or 256, max_records=max_records or 500)

    def bind_run(self, run_id: str) -> None:
        with contextlib.suppress(Exception):
            self._lex_store = MemoryIndex(
                run_id=run_id,
                max_records=self._lex_store._max_records if self._lex_store else 500,
            )

    def add(self, step_id: str, role: str, artifact_hash: str | None, rationale: str | None, content_text: str) -> None:
        if self._vector_store:
            with contextlib.suppress(Exception):
                self._vector_store.add(step_id, role, artifact_hash, rationale, content_text)
        if self._lex_store:
            with contextlib.suppress(Exception):
                self._lex_store.add(step_id, role, artifact_hash, rationale, content_text)

    def search(self, query: str, k: int = 3) -> list[dict]:
        """Search using vector and/or lexical stores.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of search results
        """
        if self._vector_store and self._lex_store:
            return self._hybrid_search(query, k)
        if self._vector_store:
            return self._vector_store.search(query, k=k)
        if self._lex_store:
            return self._lex_store.search(query, k=k)
        return []

    def _hybrid_search(self, query: str, k: int) -> list[dict]:
        """Perform hybrid search combining vector and lexical results.

        Args:
            query: Search query
            k: Number of results

        Returns:
            Merged and deduped results
        """
        v_hits = self._vector_store.search(query, k=k)
        l_hits = self._lex_store.search(query, k=k)

        return self._merge_results(v_hits, l_hits, k)

    def _merge_results(self, v_hits: list[dict], l_hits: list[dict], k: int) -> list[dict]:
        """Merge and deduplicate search results.

        Args:
            v_hits: Vector search results
            l_hits: Lexical search results
            k: Max results to return

        Returns:
            Merged results limited to k items
        """
        seen = set()
        merged = []

        for h in v_hits + l_hits:
            sid = h.get("step_id")
            if sid and sid not in seen:
                seen.add(sid)
                merged.append(h)

        return merged[:k]

    def stats(self) -> dict:
        meta = {}
        if self._vector_store:
            meta["vector"] = self._vector_store.stats()
        if self._lex_store:
            meta["lexical"] = self._lex_store.stats()
        if self._vector_store and self._lex_store:
            meta["mode"] = "hybrid"
        elif self._vector_store:
            meta["mode"] = "vector"
        elif self._lex_store:
            meta["mode"] = "lexical"
        else:
            meta["mode"] = "disabled"
        return meta


__all__ = [
    "BaseFailureClassifier",
    "BaseMemoryStore",
    "BaseQAExecutor",
    "BaseStepExecutor",
    "DefaultFailureClassifier",
    "DefaultQAExecutor",
    "DefaultStepExecutor",
    "MemoryIndexStore",
    "TimeoutQAExecutor",
    "TimeoutStepExecutor",
    "VectorOrLexicalMemoryStore",
]
