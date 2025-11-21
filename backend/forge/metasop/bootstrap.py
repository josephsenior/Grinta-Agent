"""Bootstrap utilities extracted from `MetaSOPOrchestrator`."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from forge.core.config import ForgeConfig

from .cache import StepCache
from .core import (
    ProfileManager,
    RunSetupManager,
    RuntimeAdapter,
    TemplateToolkit,
)
from .core.context import OrchestrationContextManager
from .core.engines import OptionalEnginesFacade
from .core.memory_cache import MemoryCacheManager
from .events import EventEmitter
from .memory import MemoryIndex
from .registry import load_role_profiles, load_schema, load_sop_template
from .settings import MetaSOPSettings
from .strategies import VectorOrLexicalMemoryStore
from .telemetry import initialize_metrics_server

if TYPE_CHECKING:  # pragma: no cover
    from .orchestrator import MetaSOPOrchestrator


class OrchestratorBootstrap:
    """Encapsulates the orchestrator's lifecycle wiring."""

    def __init__(self, orchestrator: MetaSOPOrchestrator):
        self._orch: Any = orchestrator

    def initialize(self, sop_name: str, config: ForgeConfig | None) -> None:
        """Run all initialization phases that previously lived in `MetaSOPOrchestrator`."""

        self._initialize_settings(config)
        self._orch.profile_manager = ProfileManager(self._orch)
        self._orch.run_setup = RunSetupManager(self._orch)
        self._initialize_basic_attributes(sop_name)
        self._orch.runtime_adapter = RuntimeAdapter(self._orch)
        self._orch.template_toolkit = TemplateToolkit(self._orch)
        self._initialize_execution_components()
        self._orch.memory_cache = MemoryCacheManager(self._orch)
        self._orch.optional_engines = OptionalEnginesFacade(self._orch)
        self._orch.context_manager = OrchestrationContextManager(self._orch)
        self._initialize_memory_and_cache()
        initialize_metrics_server(
            self._orch.settings, self._orch.context_manager.running_under_pytest
        )

    # ------------------------------------------------------------------ #
    # Extracted helpers (verbatim from orchestrator)
    # ------------------------------------------------------------------ #
    def _initialize_settings(self, config: ForgeConfig | None) -> None:
        try:
            raw = (
                getattr(getattr(config, "extended", None), "metasop", None)
                if config
                else None
            )
            self._orch.settings = MetaSOPSettings.from_raw(raw)
        except (AttributeError, TypeError, ValueError):
            self._orch.settings = MetaSOPSettings()
        self._orch._validate_micro_iteration_settings()

    def _initialize_basic_attributes(self, sop_name: str) -> None:
        self._orch._emitter = EventEmitter(self._orch.config, sop_name)
        self._orch.step_events = []
        self._orch.traces = []
        self._orch._ctx = None
        self._orch._logger = logging.getLogger("forge")
        self._orch.template = load_sop_template(sop_name)
        self._orch.profiles = load_role_profiles()
        self._orch.schema = load_schema(sop_name)
        self._orch._previous_step_hash = None
        self._orch.failure_handler = None

    def _initialize_execution_components(self) -> None:
        self._orch.runtime_adapter.initialize_execution_components()

    def _initialize_memory_and_cache(self) -> None:
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
        self._orch.step_cache = None
        try:
            if getattr(self._orch.settings, "enable_step_cache", False):
                self._orch.step_cache = StepCache(
                    max_entries=getattr(
                        self._orch.settings, "step_cache_max_entries", 256
                    )
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
        except Exception:
            self._orch.step_cache = None

