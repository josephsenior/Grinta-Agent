from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, Dict, Iterable, List

from ..env_signature import compute_environment_signature
from ..memory import MemoryIndex
from ..registry import load_role_profiles, load_sop_template

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import OrchestrationContext
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class RunSetupManager:
    """Handles run bootstrapping: templates, memory stores, and model discovery."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Template / profile loading
    # ------------------------------------------------------------------
    def load_template_and_profiles(self, sop_name: str) -> None:
        """Load SOP template and role profiles with graceful fallbacks."""
        try:
            template = load_sop_template(sop_name)
        except (FileNotFoundError, ImportError, ValueError, KeyError):
            template = None

        self._orch.template = template
        self._orch.profiles = load_role_profiles()

    # ------------------------------------------------------------------
    # Memory setup helpers
    # ------------------------------------------------------------------
    def initialize_memory(self, ctx: "OrchestrationContext") -> None:
        """Instantiate memory index and bind memory stores for the run."""
        if not self._orch.settings.enable_vector_memory:
            try:
                self._orch.memory_index = MemoryIndex(
                    run_id=ctx.run_id,
                    max_records=self._orch.settings.memory_max_records,
                )
            except (OSError, ValueError, RuntimeError, AttributeError) as exc:
                self._orch._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "suppressed_error",
                        "reason": "memory_init_failed",
                        "error": str(exc)[:400],
                    },
                )
                if self._orch.settings.strict_mode:
                    raise
                self._orch.memory_index = None

        try:
            self._orch.memory_store.bind_run(ctx.run_id)
        except (AttributeError, RuntimeError, ValueError):
            pass

    def setup_memory_and_models(self, ctx: "OrchestrationContext") -> bool:
        """Setup memory index and discover models for this run."""
        if not self.setup_memory_index(ctx):
            return False
        return self.discover_and_validate_models(ctx)

    def setup_memory_index(self, ctx: "OrchestrationContext") -> bool:
        """Ensure memory index exists and bind memory store to the run."""
        if not self._orch.settings.enable_vector_memory:
            try:
                self._orch.memory_index = MemoryIndex(
                    run_id=ctx.run_id,
                    max_records=self._orch.settings.memory_max_records,
                )
            except Exception as exc:  # pragma: no cover - mirrors legacy broad handling
                self._orch._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "suppressed_error",
                        "reason": "memory_init_failed",
                        "error": str(exc)[:400],
                    },
                )
                if self._orch.settings.strict_mode:
                    raise
                self._orch.memory_index = None

        memory_store = self._orch.memory_store
        if memory_store:
            with contextlib.suppress(Exception):
                memory_store.bind_run(ctx.run_id)

        return True

    # ------------------------------------------------------------------
    # Model discovery helpers
    # ------------------------------------------------------------------
    def discover_and_validate_models(self, ctx: "OrchestrationContext") -> bool:
        """Discover configured models and ensure they are usable."""
        models = self.discover_models()
        return self.setup_environment_and_validate_models(models, ctx)

    def validate_llm_models_available(self, ctx: "OrchestrationContext") -> bool:
        """Validate that at least one LLM model is available for execution."""
        try:
            environment = ctx.extra.get("environment", {})
            llm_models = environment.get("llm_models") if isinstance(environment, dict) else None

            if not llm_models and isinstance(self._orch.profiles, dict) and self._orch.profiles:
                llm_models = list(self._orch.profiles.keys())

            if not llm_models:
                self._orch._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "failed",
                        "reason": "no_llm_models_configured",
                        "message": (
                            "No LLM models found in configuration. Ensure your LLM profiles or API keys are configured (e.g., in config.toml or env vars)."
                        ),
                    },
                )
                return False
        except Exception:
            pass

        return True

    def discover_models(self) -> List[str]:
        """Discover available LLM models from orchestrator configuration."""
        try:
            if not getattr(self._orch, "config", None):
                return []
            return self.extract_models_from_config()
        except (AttributeError, TypeError, KeyError, RuntimeError) as exc:
            self.handle_model_discovery_error(exc)
            return []

    def extract_models_from_config(self) -> List[str]:
        """Extract models from modern or legacy configuration fields."""
        try:
            llms_map = getattr(self._orch.config, "llms", None)
            if isinstance(llms_map, dict) and llms_map:
                return self.extract_models_from_llms_map(llms_map)
            return self.extract_models_from_legacy_config()
        except (AttributeError, TypeError, KeyError):
            return []

    def extract_models_from_llms_map(self, llms_map: Dict[str, Any]) -> List[str]:
        """Extract models from the structured llms map."""
        profile_keys = list(llms_map.keys())
        model_names = self.extract_model_names_from_configs(llms_map.values())
        return sorted(set(profile_keys + model_names))

    def extract_model_names_from_configs(self, configs: Iterable[Any]) -> List[str]:
        """Extract model names from per-profile configuration objects."""
        model_names: List[str] = []
        for cfg in configs:
            try:
                model_name = getattr(cfg, "model", None)
                if isinstance(model_name, str) and model_name:
                    model_names.append(model_name)
            except (AttributeError, TypeError):
                continue
        return model_names

    def extract_models_from_legacy_config(self) -> List[str]:
        """Extract models from the legacy configuration layout."""
        models_cfg = getattr(self._orch.config, "models", None)
        return list(models_cfg.keys()) if isinstance(models_cfg, dict) else []

    def handle_model_discovery_error(self, error: Exception) -> None:
        """Emit structured event for model discovery failures."""
        self._orch._emit_event(
            {
                "step_id": "__bootstrap__",
                "role": "system",
                "status": "suppressed_error",
                "reason": "model_discovery_failed",
                "error": str(error)[:300],
            },
        )
        if self._orch.settings.strict_mode:
            raise

    def setup_environment_and_validate_models(
        self, models: List[str], ctx: "OrchestrationContext"
    ) -> bool:
        """Bind environment metadata to context and ensure models are present."""
        try:
            env_sig, env_payload = compute_environment_signature(models)
            ctx.extra["environment_signature"] = env_sig
            ctx.extra["environment"] = env_payload
        except Exception:
            ctx.extra["environment_signature"] = None

        return self.validate_llm_models_available(ctx)


__all__ = ["RunSetupManager"]
