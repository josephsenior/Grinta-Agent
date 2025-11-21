from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import Artifact, SopStep, StepResult
    from forge.metasop.orchestrator import MetaSOPOrchestrator

# Placeholders so tests can patch these without importing heavy deps eagerly.
LearningStorage = None
CausalReasoningEngine = None
ACEConfig = None
ContextPlaybook = None
ACEFramework = None
OptimizationConfig = None
PromptRegistry = None
PerformanceTracker = None
PromptOptimizer = None
PromptStorage = None
str_replace_editor = None
ParallelExecutionEngine = None
PredictiveExecutionPlanner = None
ContextAwareStreamingEngine = None

class OptionalEnginesFacade:
    """Encapsulates initialization and upkeep of optional orchestration engines."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    def initialize_learning_storage(self) -> None:
        """Initialize learning storage when persistence is enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_learning", False):
            orch.learning_storage = None
            return

        try:
            from forge.metasop.learning_storage import LearningStorage

            storage_path = getattr(
                settings, "learning_persistence_path", "~/.Forge/learning/"
            )
            orch.learning_storage = LearningStorage(base_path=storage_path)
            logger.info("Learning storage initialized successfully")
        except ImportError as exc:
            logger.error("Failed to import learning storage: %s", exc)
            orch.learning_storage = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize learning storage: %s", exc)
            orch.learning_storage = None

    def initialize_causal_engine(self) -> None:
        """Initialize causal reasoning engine when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_causal_reasoning", False):
            orch.causal_engine = None
            return

        try:
            from forge.metasop.causal_reasoning import CausalReasoningEngine

            llm = None
            if orch.llm_registry:
                with contextlib.suppress(Exception):
                    llm = orch.llm_registry.get_active_llm()
                    if llm is not None:
                        logger.info(
                            "🧠 Causal reasoning will use same LLM as agent: %s",
                            getattr(llm.config, "model", "unknown"),
                        )

            orch.causal_engine = CausalReasoningEngine(llm=llm)

            learning_storage = orch.learning_storage
            if learning_storage and getattr(settings, "enable_learning", False):
                with contextlib.suppress(Exception):
                    loaded = learning_storage.load_causal_patterns()
                    if loaded:
                        orch.causal_engine.conflict_patterns = loaded.get(
                            "conflict_patterns", {}
                        )
                        orch.causal_engine.resource_usage_history = loaded.get(
                            "resource_usage_history", {}
                        )
                        orch.causal_engine.performance_stats.update(
                            loaded.get("performance_stats", {})
                        )
                        logger.info(
                            "Loaded %s causal patterns from storage",
                            len(orch.causal_engine.conflict_patterns),
                        )

            logger.info("✅ Causal reasoning engine initialized successfully")
        except ImportError as exc:
            logger.error("Failed to import causal reasoning: %s", exc)
            orch.causal_engine = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize causal reasoning: %s", exc)
            orch.causal_engine = None

    def initialize_ace_framework(self) -> None:
        """Initialize ACE framework when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_ace", False):
            orch.ace_framework = None
            return

        try:
            from forge.metasop.ace import ACEFramework, ACEConfig, ContextPlaybook

            llm = None
            if orch.llm_registry:
                with contextlib.suppress(Exception):
                    llm = orch.llm_registry.get_active_llm()
            if llm is None:
                logger.warning(
                    "ACE framework enabled but no default LLM available; skipping initialization"
                )
                orch.ace_framework = None
                return

            ace_config = ACEConfig(
                enable_ace=settings.enable_ace,
                max_bullets=settings.ace_max_bullets,
                multi_epoch=settings.ace_multi_epoch,
                num_epochs=settings.ace_num_epochs,
                reflector_max_iterations=settings.ace_reflector_max_iterations,
                enable_online_adaptation=settings.ace_enable_online_adaptation,
                playbook_persistence_path=settings.ace_playbook_persistence_path,
                min_helpfulness_threshold=settings.ace_min_helpfulness_threshold,
                max_playbook_content_length=settings.ace_max_playbook_content_length,
                enable_grow_and_refine=settings.ace_enable_grow_and_refine,
                cleanup_interval_days=settings.ace_cleanup_interval_days,
                redundancy_threshold=settings.ace_redundancy_threshold,
            )

            context_playbook = ContextPlaybook(
                max_bullets=settings.ace_max_bullets,
                enable_grow_and_refine=settings.ace_enable_grow_and_refine,
            )

            persistence_path = settings.ace_playbook_persistence_path
            if persistence_path:
                path = Path(persistence_path).expanduser()
                if path.is_file():
                    with contextlib.suppress(Exception):
                        data = json.loads(path.read_text(encoding="utf-8"))
                        context_playbook.import_playbook(data)

            orch.ace_framework = ACEFramework(
                llm=llm,
                context_playbook=context_playbook,
                config=ace_config,
            )
            logger.info("ACE framework initialized successfully")
        except ImportError as exc:
            logger.error("Failed to import ACE framework: %s", exc)
            orch.ace_framework = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize ACE framework: %s", exc)
            orch.ace_framework = None

    def initialize_prompt_optimization(self) -> None:
        """Initialize prompt optimization pipeline when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_prompt_optimization", False):
            orch.prompt_optimizer = None
            return

        try:
            from forge.prompt_optimization.models import OptimizationConfig
            from forge.prompt_optimization.optimizer import PromptOptimizer
            from forge.prompt_optimization.registry import PromptRegistry
            from forge.prompt_optimization.storage import PromptStorage
            from forge.prompt_optimization.tracker import PerformanceTracker

            opt_config = OptimizationConfig(
                ab_split_ratio=settings.prompt_opt_ab_split,
                min_samples_for_switch=settings.prompt_opt_min_samples,
                confidence_threshold=settings.prompt_opt_confidence_threshold,
                success_weight=settings.prompt_opt_success_weight,
                time_weight=settings.prompt_opt_time_weight,
                error_weight=settings.prompt_opt_error_weight,
                cost_weight=settings.prompt_opt_cost_weight,
                enable_evolution=settings.prompt_opt_enable_evolution,
                evolution_threshold=settings.prompt_opt_evolution_threshold,
                max_variants_per_prompt=settings.prompt_opt_max_variants_per_prompt,
                storage_path=settings.prompt_opt_storage_path,
                sync_interval=settings.prompt_opt_sync_interval,
                auto_save=settings.prompt_opt_auto_save,
                prompt_history_path=settings.prompt_opt_history_path,
                prompt_history_auto_flush=settings.prompt_opt_history_auto_flush,
            )

            registry = PromptRegistry()
            tracker = PerformanceTracker(
                {
                    "success_weight": opt_config.success_weight,
                    "time_weight": opt_config.time_weight,
                    "error_weight": opt_config.error_weight,
                    "cost_weight": opt_config.cost_weight,
                },
                history_path=opt_config.prompt_history_path,
                history_auto_flush=opt_config.prompt_history_auto_flush,
            )
            optimizer = PromptOptimizer(registry, tracker, opt_config)
            storage = PromptStorage(opt_config, registry, tracker)

            orch.prompt_optimizer = {
                "registry": registry,
                "tracker": tracker,
                "optimizer": optimizer,
                "storage": storage,
                "config": opt_config,
            }

            storage.load_all()
            logger.info("Prompt optimization system initialized successfully")
        except ImportError as exc:
            logger.error("Failed to import prompt optimization: %s", exc)
            orch.prompt_optimizer = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize prompt optimization: %s", exc)
            orch.prompt_optimizer = None

    def initialize_parallel_engine(self) -> None:
        """Initialize parallel execution engine when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_parallel_execution", False):
            orch.parallel_engine = None
            return

        try:
            from forge.metasop.parallel_execution import ParallelExecutionEngine

            max_workers = getattr(settings, "max_parallel_workers", 4)
            orch.parallel_engine = ParallelExecutionEngine(
                max_parallel_workers=max_workers,
                causal_engine=orch.causal_engine,
            )
            logger.info(
                "Parallel execution engine initialized with %s workers",
                max_workers,
            )
        except ImportError as exc:
            logger.error("Failed to import parallel execution: %s", exc)
            orch.parallel_engine = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize parallel execution: %s", exc)
            orch.parallel_engine = None

    def initialize_predictive_planner(self) -> None:
        """Initialize predictive planner when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_predictive_planning", False):
            orch.predictive_planner = None
            return

        try:
            from forge.metasop.predictive_execution import PredictiveExecutionPlanner

            max_prediction_time_ms = getattr(
                settings, "predictive_max_planning_time_ms", 100
            )
            confidence_threshold = getattr(
                settings, "predictive_confidence_threshold", 0.7
            )

            orch.predictive_planner = PredictiveExecutionPlanner(
                parallel_engine=orch.parallel_engine,
                causal_engine=orch.causal_engine,
                max_prediction_time_ms=max_prediction_time_ms,
                confidence_threshold=confidence_threshold,
            )
            logger.info(
                "🔮 Predictive planner initialized with %sms planning window",
                max_prediction_time_ms,
            )
        except ImportError as exc:
            logger.error(
                "Failed to import predictive execution planner: %s",
                exc,
            )
            orch.predictive_planner = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize predictive planner: %s", exc)
            orch.predictive_planner = None

    def initialize_collaborative_streaming(self) -> None:
        """Initialize collaborative streaming engine when enabled."""
        orch = self._orch
        settings = orch.settings

        if not getattr(settings, "enable_collaborative_streaming", False):
            orch.collaborative_streaming = None
            return

        try:
            from forge.metasop.collaborative_streaming import (
                ContextAwareStreamingEngine,
            )

            context_threshold = getattr(
                settings, "streaming_context_completeness_threshold", 0.8
            )
            semantic_threshold = getattr(
                settings, "streaming_semantic_consistency_threshold", 0.7
            )

            orch.collaborative_streaming = ContextAwareStreamingEngine(
                parallel_engine=orch.parallel_engine,
                causal_engine=orch.causal_engine,
                predictive_planner=orch.predictive_planner,
                context_completeness_threshold=context_threshold,
                semantic_consistency_threshold=semantic_threshold,
            )
            logger.info(
                "🔗 Collaborative streaming initialized with %.2f completeness threshold",
                context_threshold,
            )
        except ImportError as exc:
            logger.error(
                "Failed to import collaborative streaming engine: %s",
                exc,
            )
            orch.collaborative_streaming = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Failed to initialize collaborative streaming engine: %s",
                exc,
            )
            orch.collaborative_streaming = None

    # ------------------------------------------------------------------
    # Prompt optimization helpers
    # ------------------------------------------------------------------
    def apply_prompt_optimization(
        self, step: "SopStep", role_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return an optimized role profile when prompt optimization is enabled."""
        orch = self._orch
        prompt_state = orch.prompt_optimizer
        if not prompt_state:
            return role_profile

        try:
            from forge.prompt_optimization.models import PromptCategory

            optimizer = prompt_state["optimizer"]
            prompt_id = f"metasop_role_{step.role.lower()}"
            variant = optimizer.select_variant(prompt_id, PromptCategory.METASOP_ROLE)
            if not variant:
                return role_profile

            optimized_profile = dict(role_profile)
            if "role_description" in optimized_profile:
                optimized_profile["role_description"] = variant.content
            elif "description" in optimized_profile:
                optimized_profile["description"] = variant.content
            else:
                optimized_profile["optimized_prompt"] = variant.content

            optimized_profile["_prompt_variant_id"] = variant.id
            return optimized_profile
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Prompt optimization failed: %s", exc)
            return role_profile

    def track_prompt_performance(
        self,
        step: "SopStep",
        result: "StepResult",
        execution_time: float,
        token_cost: float,
    ) -> None:
        """Record prompt performance metrics for optimization feedback."""
        orch = self._orch
        prompt_state = orch.prompt_optimizer
        if not prompt_state:
            return

        try:
            from forge.prompt_optimization.models import PromptCategory

            variant_id = getattr(step, "_prompt_variant_id", None)
            if not variant_id:
                return

            prompt_id = f"metasop_role_{step.role.lower()}"
            optimizer = prompt_state["optimizer"]
            optimizer.record_execution(
                variant_id=variant_id,
                prompt_id=prompt_id,
                category=PromptCategory.METASOP_ROLE,
                success=result.ok,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=result.error if not result.ok else None,
                metadata={
                    "step_id": step.id,
                    "role": step.role,
                    "task": getattr(step, "task", "unknown"),
                },
            )

            storage = prompt_state["storage"]
            with contextlib.suppress(Exception):
                storage.auto_save()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to track prompt performance: %s", exc)

    # ------------------------------------------------------------------
    # Learning & feedback helpers
    # ------------------------------------------------------------------
    def collect_causal_feedback(
        self,
        step: "SopStep",
        success: bool,
        artifacts: Dict[str, "Artifact"],
        active_steps_at_time: List["SopStep"],
    ) -> None:
        """Forward execution outcomes to the causal reasoning engine."""
        orch = self._orch
        settings = orch.settings
        if not (orch.causal_engine and getattr(settings, "enable_learning", False)):
            return

        conflicts_observed: List[str] = []
        affected_artifacts = [step.id] if artifacts else []
        active_step_ids = [s.id for s in active_steps_at_time]

        orch.causal_engine.learn_from_execution(
            step=step,
            success=success,
            affected_artifacts=affected_artifacts,
            conflicts_observed=conflicts_observed,
            active_steps_at_time=active_step_ids,
        )
        self.save_causal_patterns()

    def save_causal_patterns(self) -> None:
        """Persist causal reasoning artifacts if storage is configured."""
        orch = self._orch
        if not orch.learning_storage or not orch.causal_engine:
            return

        try:
            payload = {
                "conflict_patterns": orch.causal_engine.conflict_patterns,
                "resource_usage_history": orch.causal_engine.resource_usage_history,
                "performance_stats": orch.causal_engine.performance_stats,
            }
            orch.learning_storage.save_causal_patterns(payload)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to save causal patterns: %s", exc)

    def collect_execution_feedback(
        self,
        step: "SopStep",
        success: bool,
        artifacts: Dict[str, "Artifact"],
        active_steps_at_time: List["SopStep"],
    ) -> None:
        """Record execution feedback across auxiliary engines."""
        orch = self._orch
        settings = orch.settings
        learning_storage = orch.learning_storage

        try:
            self.collect_causal_feedback(step, success, artifacts, active_steps_at_time)

            planner = orch.predictive_planner
            if planner and getattr(settings, "predictive_learn_from_execution", False):
                with contextlib.suppress(Exception):
                    actual_duration_ms = 1000.0  # Placeholder until timing wired
                    planner.learn_from_execution(
                        step_id=step.id,
                        actual_duration_ms=actual_duration_ms,
                        success=success,
                    )

            if learning_storage and getattr(settings, "enable_learning", False):
                parallel_engine = orch.parallel_engine
                if parallel_engine:
                    with contextlib.suppress(Exception):
                        stats = parallel_engine.get_execution_stats()
                        learning_storage.save_parallel_stats(stats)

                performance_entry = {
                    "timestamp": time.time(),
                    "step_id": step.id,
                    "role": step.role,
                    "success": success,
                    "artifacts_count": len(artifacts),
                    "active_steps_count": len(active_steps_at_time),
                }
                with contextlib.suppress(Exception):
                    learning_storage.save_performance_history([performance_entry])
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to collect execution feedback: %s", exc)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def save_ace_playbook(self) -> None:
        """Persist ACE playbook to disk when configured."""
        orch = self._orch
        if not orch.ace_framework or not getattr(
            orch.settings, "ace_playbook_persistence_path", None
        ):
            return

        try:
            path = getattr(orch.settings, "ace_playbook_persistence_path", None)
            if path:
                orch.ace_framework.save_playbook(path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to save ACE playbook: %s", exc)

    def check_agent_tool_persistence(self) -> None:
        """Emit advisory when agent tool persistent state is detected."""
        orch = self._orch
        try:
            from forge.agenthub.codeact_agent.tools import str_replace_editor

            tool_desc = None
            with contextlib.suppress(AttributeError, TypeError, ImportError):
                tool = str_replace_editor.create_str_replace_editor_tool()
                function_obj = getattr(tool, "function", None)
                tool_desc = getattr(function_obj, "description", None)

            if tool_desc and "State is persistent" in tool_desc:
                orch._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "advisory",
                        "reason": "agent_tool_persistent_state_detected",
                        "message": (
                            "An agent tool advertises persistent state. "
                            "Orchestrator owns step-level caching; agent tools should "
                            "be stateless or use ephemeral caches."
                        ),
                    }
                )
        except ImportError:
            logger.debug("AgentHub optional dependency not available; skipping checks")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to check agent tool persistence: %s", exc)


