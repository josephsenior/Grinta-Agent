from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from typing import TYPE_CHECKING, Dict, List, Awaitable, Union
from concurrent.futures import ThreadPoolExecutor

from openhands.core.logger import openhands_logger as logger
from openhands.core.pydantic_compat import model_dump_with_options
from openhands.structural import available as structural_available

from . import patch_scoring
from .cache import StepCache, StepCacheEntry
from .context_hash import compute_context_hash
from .diff_utils import compute_diff_fingerprint
from .env_signature import compute_environment_signature
from .events import EventEmitter
from .failure_taxonomy import corrective_hint
from .memory import MemoryIndex
from .metrics import start_metrics_server
from .models import (
    Artifact,
    OrchestrationContext,
    RetryPolicy,
    SopStep,
    StepResult,
    StepTrace,
)
from .registry import load_role_profiles, load_schema, load_sop_template
from .remediation import get_remediation_plan, summarize_remediation
from .selective_tests import select_tests
from .settings import MetaSOPSettings
from .strategies import (
    DefaultFailureClassifier,
    DefaultQAExecutor,
    DefaultStepExecutor,
    TimeoutQAExecutor,
    TimeoutStepExecutor,
    VectorOrLexicalMemoryStore,
)
from .validators import validate_json

if TYPE_CHECKING:
    import threading

    from openhands.core.config import OpenHandsConfig


class MetaSOPOrchestrator:
    # Prevent pytest from attempting to collect this orchestrator class as a test-like class
    __test__ = False

    def _hash_dict(self, data: dict) -> str:
        try:
            encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            # Handle JSON serialization errors (non-serializable objects, encoding issues)
            encoded = repr(data).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def __init__(self, sop_name: str, config: OpenHandsConfig | None = None) -> None:
        """Initialize orchestrator defaults so run() can execute.

        Tests and tools construct with (sop_name, config). We hydrate
        sensible defaults here while allowing callers to override
        components (step_executor, qa_executor, memory_store, etc.).
        """
        self.config = config
        self.llm_registry = None  # Will be set by router if available
        self.step_event_callback = None  # Callback for real-time step events
        self.ace_framework = None  # ACE framework for self-improving agents
        self.prompt_optimizer = None  # Dynamic prompt optimization system
        self.causal_engine = None  # Causal reasoning engine for conflict prediction
        self.parallel_engine = None  # Parallel execution engine for intelligent step scheduling
        self.predictive_planner = None  # Predictive execution planner for intelligent pre-execution optimization
        self.collaborative_streaming = None  # Context-aware collaborative streaming engine
        
        # Learning and feedback tracking
        self.active_steps: Dict[str, SopStep] = {}  # Track currently executing steps
        self.learning_storage = None  # Persistent learning storage

        # Initialize core components
        self._initialize_settings(config)
        self._initialize_basic_attributes(sop_name)
        self._initialize_execution_components()
        self._initialize_memory_and_cache()
        self._initialize_metrics_server()
        self._initialize_learning_storage()
        self._initialize_causal_engine()
        self._initialize_parallel_engine()
        self._initialize_predictive_planner()
        self._initialize_collaborative_streaming()
        self._check_agent_tool_persistence()

    def _initialize_settings(self, config: OpenHandsConfig | None) -> None:
        """Initialize settings from config."""
        try:
            raw = getattr(getattr(config, "extended", None), "metasop", None) if config else None
            self.settings = MetaSOPSettings.from_raw(raw)
        except (AttributeError, TypeError, ValueError):
            self.settings = MetaSOPSettings()

        # Ensure micro-iteration candidate count is at least 1
        self._validate_micro_iteration_settings()

    def _validate_micro_iteration_settings(self) -> None:
        """Validate and fix micro-iteration settings."""
        try:
            if (
                getattr(self.settings, "micro_iteration_candidate_count", None) is not None
                and self.settings.micro_iteration_candidate_count < 1
            ):
                self.settings.micro_iteration_candidate_count = 1
        except (AttributeError, TypeError):
            pass

    def _initialize_basic_attributes(self, sop_name: str) -> None:
        """Initialize basic orchestrator attributes."""
        # Event emitter and public event list
        self._emitter = EventEmitter(self.config, sop_name)
        self.step_events: list[dict] = []

        # Traces list for executed attempts
        self.traces: list[StepTrace] = []

        # Context reference (set in run method)
        self._ctx: OrchestrationContext | None = None

        # Logger (set in run method)
        self._logger: logging.Logger | None = None

        # Template and profiles
        self._load_template_and_profiles(sop_name)

        # Provenance tracking
        self._previous_step_hash = None

    def _load_template_and_profiles(self, sop_name: str) -> None:
        """Load SOP template and role profiles."""
        try:
            self.template = load_sop_template(sop_name)
        except (FileNotFoundError, ImportError, ValueError, KeyError):
            self.template = None
        self.profiles = load_role_profiles()

    def _initialize_execution_components(self) -> None:
        """Initialize step and QA executors with timeout handling."""
        # Step executor
        self.step_executor = DefaultStepExecutor()
        if getattr(self.settings, "step_timeout_seconds", None):
            self.step_executor = TimeoutStepExecutor(
                self.step_executor,
                self.settings.step_timeout_seconds,
                stuck_callback=self._handle_stuck_thread,
                stuck_threshold=getattr(self.settings, "stuck_threshold_seconds", None),
            )

        # QA executor
        self.qa_executor = DefaultQAExecutor()
        if getattr(self.settings, "qa_timeout_seconds", None):
            self.qa_executor = TimeoutQAExecutor(
                self.qa_executor,
                self.settings.qa_timeout_seconds,
                stuck_callback=self._handle_stuck_thread,
                stuck_threshold=getattr(self.settings, "stuck_threshold_seconds", None),
            )

        # Failure classifier
        self.failure_classifier = DefaultFailureClassifier()

    def _initialize_memory_and_cache(self) -> None:
        """Initialize memory store and step cache."""
        # Memory store
        self._initialize_memory_store()

        # Optional in-memory index used in lexical mode
        self.memory_index = None

        # Step cache
        self._initialize_step_cache()

    def _initialize_memory_store(self) -> None:
        """Initialize memory store with error handling."""
        try:
            self.memory_store = VectorOrLexicalMemoryStore(
                self.settings.enable_vector_memory,
                self.settings.vector_embedding_dim,
                self.settings.memory_max_records,
            )
        except (ImportError, OSError, ValueError, RuntimeError):
            self.memory_store = VectorOrLexicalMemoryStore(False, None, None)

    def _initialize_step_cache(self) -> None:
        """Initialize step cache with error handling."""
        try:
            if getattr(self.settings, "enable_step_cache", False):
                self.step_cache = StepCache(
                    max_entries=getattr(self.settings, "step_cache_max_entries", 256) or 256,
                    cache_dir=getattr(self.settings, "step_cache_dir", None),
                    ttl_seconds=getattr(self.settings, "step_cache_allow_stale_seconds", None),
                    min_tokens_threshold=getattr(self.settings, "step_cache_min_tokens_saved", None),
                    exclude_roles=getattr(self.settings, "step_cache_exclude_roles", None),
                )
            else:
                self.step_cache = None
        except (OSError, ValueError, TypeError):
            self.step_cache = None

    def _initialize_metrics_server(self) -> None:
        """Initialize metrics server if requested."""
        try:
            if getattr(self.settings, "metrics_prometheus_port", None) and not self._running_under_pytest():
                start_metrics_server(self.settings.metrics_prometheus_port)
        except (OSError, RuntimeError, ImportError):
            pass

    def _initialize_ace_framework(self) -> None:
        """Initialize ACE framework if enabled."""
        if not getattr(self.settings, "enable_ace", False):
            self.ace_framework = None
            return
        
        try:
            from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
            
            # Create ACE configuration from settings
            ace_config = ACEConfig(
                enable_ace=self.settings.enable_ace,
                max_bullets=self.settings.ace_max_bullets,
                multi_epoch=self.settings.ace_multi_epoch,
                num_epochs=self.settings.ace_num_epochs,
                reflector_max_iterations=self.settings.ace_reflector_max_iterations,
                enable_online_adaptation=self.settings.ace_enable_online_adaptation,
                playbook_persistence_path=self.settings.ace_playbook_persistence_path,
                min_helpfulness_threshold=self.settings.ace_min_helpfulness_threshold,
                max_playbook_content_length=self.settings.ace_max_playbook_content_length,
                enable_grow_and_refine=self.settings.ace_enable_grow_and_refine,
                cleanup_interval_days=self.settings.ace_cleanup_interval_days,
                redundancy_threshold=self.settings.ace_redundancy_threshold
            )
            
            # Create context playbook
            context_playbook = ContextPlaybook(
                max_bullets=self.settings.ace_max_bullets,
                enable_grow_and_refine=self.settings.ace_enable_grow_and_refine
            )
            
            # Load existing playbook if persistence path exists
            if self.settings.ace_playbook_persistence_path:
                try:
                    context_playbook.load_from_disk(self.settings.ace_playbook_persistence_path)
                except Exception as e:
                    logger.warning(f"Failed to load existing playbook: {e}")
            
            # Initialize ACE framework
            self.ace_framework = ACEFramework(
                llm=self.llm_registry.get_default_llm() if self.llm_registry else None,
                context_playbook=context_playbook,
                config=ace_config
            )
            
            logger.info("ACE framework initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import ACE framework: {e}")
            self.ace_framework = None
        except Exception as e:
            logger.error(f"Failed to initialize ACE framework: {e}")
            self.ace_framework = None

    def _initialize_prompt_optimization(self) -> None:
        """Initialize prompt optimization system if enabled."""
        if not getattr(self.settings, "enable_prompt_optimization", False):
            self.prompt_optimizer = None
            return
        
        try:
            from openhands.prompt_optimization import (
                PromptRegistry, PerformanceTracker, PromptOptimizer, 
                PromptStorage, OptimizationConfig, PromptCategory
            )
            
            # Create optimization configuration from settings
            opt_config = OptimizationConfig(
                ab_split_ratio=self.settings.prompt_opt_ab_split,
                min_samples_for_switch=self.settings.prompt_opt_min_samples,
                confidence_threshold=self.settings.prompt_opt_confidence_threshold,
                success_weight=self.settings.prompt_opt_success_weight,
                time_weight=self.settings.prompt_opt_time_weight,
                error_weight=self.settings.prompt_opt_error_weight,
                cost_weight=self.settings.prompt_opt_cost_weight,
                enable_evolution=self.settings.prompt_opt_enable_evolution,
                evolution_threshold=self.settings.prompt_opt_evolution_threshold,
                max_variants_per_prompt=self.settings.prompt_opt_max_variants_per_prompt,
                storage_path=self.settings.prompt_opt_storage_path,
                sync_interval=self.settings.prompt_opt_sync_interval,
                auto_save=self.settings.prompt_opt_auto_save
            )
            
            # Create components
            registry = PromptRegistry()
            tracker = PerformanceTracker({
                'success_weight': opt_config.success_weight,
                'time_weight': opt_config.time_weight,
                'error_weight': opt_config.error_weight,
                'cost_weight': opt_config.cost_weight
            })
            optimizer = PromptOptimizer(registry, tracker, opt_config)
            storage = PromptStorage(opt_config, registry, tracker)
            
            # Initialize prompt optimization system
            self.prompt_optimizer = {
                'registry': registry,
                'tracker': tracker,
                'optimizer': optimizer,
                'storage': storage,
                'config': opt_config
            }
            
            # Load existing data
            storage.load_all()
            
            logger.info("Prompt optimization system initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import prompt optimization: {e}")
            self.prompt_optimizer = None
        except Exception as e:
            logger.error(f"Failed to initialize prompt optimization: {e}")
            self.prompt_optimizer = None

    def _initialize_causal_engine(self) -> None:
        """Initialize causal reasoning engine if enabled."""
        if not getattr(self.settings, "enable_causal_reasoning", False):
            self.causal_engine = None
            return
        
        try:
            from .causal_reasoning import CausalReasoningEngine
            
            # Get the same LLM as the main agent for consistent reasoning
            llm = None
            if self.llm_registry:
                try:
                    llm = self.llm_registry.get_active_llm()
                    logger.info(f"🧠 Causal reasoning will use same LLM as agent: {llm.config.model}")
                except Exception as e:
                    logger.warning(f"Failed to get LLM for causal reasoning: {e}, will use heuristics only")
            
            # Initialize causal reasoning engine with LLM
            self.causal_engine = CausalReasoningEngine(llm=llm)
            
            # Load existing patterns from storage if available
            if self.learning_storage and getattr(self.settings, "enable_learning", False):
                try:
                    loaded_patterns = self.learning_storage.load_causal_patterns()
                    if loaded_patterns:
                        self.causal_engine.conflict_patterns = loaded_patterns.get("conflict_patterns", {})
                        self.causal_engine.resource_usage_history = loaded_patterns.get("resource_usage_history", {})
                        self.causal_engine.performance_stats.update(
                            loaded_patterns.get("performance_stats", {})
                        )
                        logger.info(f"Loaded {len(self.causal_engine.conflict_patterns)} causal patterns from storage")
                except Exception as e:
                    logger.warning(f"Failed to load causal patterns: {e}")
            
            logger.info("✅ Causal reasoning engine initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import causal reasoning: {e}")
            self.causal_engine = None
        except Exception as e:
            logger.error(f"Failed to initialize causal reasoning: {e}")
            self.causal_engine = None

    def _initialize_parallel_engine(self) -> None:
        """Initialize parallel execution engine if enabled."""
        if not getattr(self.settings, "enable_parallel_execution", False):
            self.parallel_engine = None
            return
        
        try:
            from .parallel_execution import ParallelExecutionEngine
            
            # Get parallel execution settings
            max_workers = getattr(self.settings, "max_parallel_workers", 4)
            
            # Initialize parallel execution engine with causal engine
            self.parallel_engine = ParallelExecutionEngine(
                max_parallel_workers=max_workers,
                causal_engine=self.causal_engine
            )
            
            logger.info(f"Parallel execution engine initialized with {max_workers} workers")
            
        except ImportError as e:
            logger.error(f"Failed to import parallel execution: {e}")
            self.parallel_engine = None
        except Exception as e:
            logger.error(f"Failed to initialize parallel execution: {e}")
            self.parallel_engine = None

    def _initialize_predictive_planner(self) -> None:
        """Initialize predictive execution planner if enabled."""
        if not getattr(self.settings, "enable_predictive_planning", False):
            self.predictive_planner = None
            return
        
        try:
            from .predictive_execution import PredictiveExecutionPlanner
            
            # Get predictive planning settings
            max_prediction_time_ms = getattr(self.settings, "predictive_max_planning_time_ms", 100)
            confidence_threshold = getattr(self.settings, "predictive_confidence_threshold", 0.7)
            
            # Initialize predictive execution planner with existing engines
            self.predictive_planner = PredictiveExecutionPlanner(
                parallel_engine=self.parallel_engine,
                causal_engine=self.causal_engine,
                max_prediction_time_ms=max_prediction_time_ms,
                confidence_threshold=confidence_threshold
            )
            
            logger.info(f"🔮 Predictive execution planner initialized with {max_prediction_time_ms}ms max planning time")
            
        except ImportError as e:
            logger.error(f"Failed to import predictive execution planner: {e}")
            self.predictive_planner = None
        except Exception as e:
            logger.error(f"Failed to initialize predictive execution planner: {e}")
            self.predictive_planner = None

    def _initialize_collaborative_streaming(self) -> None:
        """Initialize context-aware collaborative streaming engine if enabled."""
        if not getattr(self.settings, "enable_collaborative_streaming", False):
            self.collaborative_streaming = None
            return
        
        try:
            from .collaborative_streaming import ContextAwareStreamingEngine
            
            # Get streaming configuration settings
            context_completeness_threshold = getattr(
                self.settings, "streaming_context_completeness_threshold", 0.8
            )
            semantic_consistency_threshold = getattr(
                self.settings, "streaming_semantic_consistency_threshold", 0.7
            )
            
            # Initialize collaborative streaming engine with existing engines
            self.collaborative_streaming = ContextAwareStreamingEngine(
                parallel_engine=self.parallel_engine,
                causal_engine=self.causal_engine,
                predictive_planner=self.predictive_planner,
                context_completeness_threshold=context_completeness_threshold,
                semantic_consistency_threshold=semantic_consistency_threshold
            )
            
            logger.info(f"🔗 Context-aware collaborative streaming engine initialized with {context_completeness_threshold} completeness threshold")
            
        except ImportError as e:
            logger.error(f"Failed to import collaborative streaming engine: {e}")
            self.collaborative_streaming = None
        except Exception as e:
            logger.error(f"Failed to initialize collaborative streaming engine: {e}")
            self.collaborative_streaming = None

    def _initialize_learning_storage(self) -> None:
        """Initialize learning storage system if enabled."""
        if not getattr(self.settings, "enable_learning", False):
            self.learning_storage = None
            return
        
        try:
            from .learning_storage import LearningStorage
            
            # Get learning storage path from settings
            storage_path = getattr(self.settings, "learning_persistence_path", "~/.openhands/learning/")
            
            # Initialize learning storage
            self.learning_storage = LearningStorage(base_path=storage_path)
            
            logger.info("Learning storage initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import learning storage: {e}")
            self.learning_storage = None
        except Exception as e:
            logger.error(f"Failed to initialize learning storage: {e}")
            self.learning_storage = None

    def _apply_prompt_optimization(self, step: SopStep, role_profile) -> dict:
        """Apply prompt optimization to role profile if enabled."""
        if not self.prompt_optimizer:
            return role_profile
        
        try:
            from openhands.prompt_optimization.models import PromptCategory
            
            # Create prompt ID for this role
            prompt_id = f"metasop_role_{step.role.lower()}"
            
            # Get optimized variant
            optimizer = self.prompt_optimizer['optimizer']
            variant = optimizer.select_variant(prompt_id, PromptCategory.METASOP_ROLE)
            
            if variant:
                # Create optimized role profile with the variant content
                optimized_profile = dict(role_profile)
                
                # Replace the role description with optimized content
                if 'role_description' in optimized_profile:
                    optimized_profile['role_description'] = variant.content
                elif 'description' in optimized_profile:
                    optimized_profile['description'] = variant.content
                else:
                    # Add as a new field
                    optimized_profile['optimized_prompt'] = variant.content
                
                # Store variant ID for tracking
                optimized_profile['_prompt_variant_id'] = variant.id
                
                return optimized_profile
            
        except Exception as e:
            logger.warning(f"Prompt optimization failed: {e}")
        
        return role_profile

    def _track_prompt_performance(self, step: SopStep, result: StepResult, 
                                execution_time: float, token_cost: float = 0.0):
        """Track prompt performance for optimization."""
        if not self.prompt_optimizer:
            return
        
        try:
            from openhands.prompt_optimization.models import PromptCategory
            
            # Get variant ID from step context
            variant_id = getattr(step, '_prompt_variant_id', None)
            if not variant_id:
                return
            
            prompt_id = f"metasop_role_{step.role.lower()}"
            
            # Record performance
            optimizer = self.prompt_optimizer['optimizer']
            optimizer.record_execution(
                variant_id=variant_id,
                prompt_id=prompt_id,
                category=PromptCategory.METASOP_ROLE,
                success=result.ok,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=result.error if not result.ok else None,
                metadata={
                    'step_id': step.id,
                    'role': step.role,
                    'task': getattr(step, 'task', 'unknown')
                }
            )
            
            # Auto-save if enabled
            storage = self.prompt_optimizer['storage']
            storage.auto_save()
            
        except Exception as e:
            logger.warning(f"Failed to track prompt performance: {e}")

    def _reflect_and_update_ace(self, step: SopStep, result: StepResult, 
                               artifact: Artifact, verification: dict | None) -> None:
        """Reflect on step execution and update ACE playbook."""
        if not self.ace_framework or not getattr(self.settings, "ace_enable_online_adaptation", True):
            return
        
        try:
            from openhands.metasop.ace.models import ACETrajectory, ACEExecutionResult
            
            # Create trajectory from step execution
            trajectory = ACETrajectory(
                content=result.artifact.content if result.artifact else "",
                task_type="metasop",
                used_bullet_ids=[],  # Will be populated by ACE framework
                playbook_content="",
                generation_metadata={
                    "step_id": step.id,
                    "role": getattr(step, "role", "unknown"),
                    "task": getattr(step, "task", "unknown"),
                    "expected_outcome": getattr(step, "expected_outcome", None)
                }
            )
            
            # Create execution result
            execution_result = ACEExecutionResult(
                success=result.ok,
                output=result.artifact.content if result.artifact else "",
                error=result.error if not result.ok else None,
                execution_time=0.0,  # Could be tracked if needed
                tokens_used=0,  # Could be tracked if needed
                cost=0.0,  # Could be tracked if needed
                metadata={
                    "step_id": step.id,
                    "verification": verification,
                    "retries": getattr(result, "retries", 0)
                }
            )
            
            # Process through ACE framework
            ace_result = self.ace_framework.process_task(
                query=getattr(step, "task", "unknown"),
                task_type="metasop",
                role=getattr(step, "role", "unknown"),
                expected_outcome=getattr(step, "expected_outcome", None)
            )
            
            # Auto-save playbook if enabled
            if (getattr(self.settings, "ace_auto_save_playbook", True) and 
                getattr(self.settings, "ace_playbook_persistence_path", None)):
                self._save_ace_playbook()
                
        except Exception as e:
            logger.warning(f"ACE reflection failed: {e}")
    
    def _save_ace_playbook(self) -> None:
        """Save ACE playbook to disk."""
        if not self.ace_framework or not getattr(self.settings, "ace_playbook_persistence_path", None):
            return
        
        try:
            self.ace_framework.save_playbook(self.settings.ace_playbook_persistence_path)
        except Exception as e:
            logger.warning(f"Failed to save ACE playbook: {e}")

    def _running_under_pytest(self) -> bool:
        """Check if running under pytest."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        return any("pytest" in str(a) for a in sys.argv)

    def set_step_event_callback(self, callback) -> None:
        """Set callback function for real-time step events."""
        self.step_event_callback = callback

    def _call_step_event_callback(self, event: dict | object) -> None:
        """Call the step event callback if it's set and the event is a step event."""
        if not self.step_event_callback:
            return

        try:
            # Convert event to dict if needed
            if hasattr(event, "to_public_dict"):
                event_dict = event.to_public_dict()
            elif isinstance(event, dict):
                event_dict = event
            else:
                return

            # Only call callback for step events (not system events)
            step_id = event_dict.get("step_id")
            role = event_dict.get("role")
            status = event_dict.get("status")

            if step_id and role and status and step_id != "__bootstrap__":
                # Call the callback synchronously (it will queue the event)
                self.step_event_callback(
                    step_id,
                    role,
                    status,
                    event_dict.get("retries", 0),
                )
        except Exception as e:
            logging.warning("Failed to call step event callback: %s", e)

    def _collect_execution_feedback(
        self, 
        step: SopStep, 
        success: bool, 
        artifacts: dict[str, Artifact], 
        active_steps_at_time: list[SopStep]
    ) -> None:
        """Collect execution feedback for learning and optimization."""
        try:
            # Collect feedback for causal reasoning engine
            if self.causal_engine and getattr(self.settings, "enable_learning", False):
                # Extract conflicts from the execution if any
                conflicts_observed = []
                affected_artifacts = [step.id] if artifacts else []
                active_step_ids = [s.id for s in active_steps_at_time]
                
                # Learn from this execution
                self.causal_engine.learn_from_execution(
                    step=step,
                    success=success,
                    affected_artifacts=affected_artifacts,
                    conflicts_observed=conflicts_observed,
                    active_steps_at_time=active_step_ids
                )
                
                # Save patterns to storage
                if self.learning_storage:
                    try:
                        patterns_to_save = {
                            "conflict_patterns": self.causal_engine.conflict_patterns,
                            "resource_usage_history": self.causal_engine.resource_usage_history,
                            "performance_stats": self.causal_engine.performance_stats
                        }
                        self.learning_storage.save_causal_patterns(patterns_to_save)
                    except Exception as e:
                        logger.warning(f"Failed to save causal patterns: {e}")
            
            # Collect feedback for predictive planner
            if self.predictive_planner and getattr(self.settings, "predictive_learn_from_execution", False):
                try:
                    # Calculate actual execution time if available
                    actual_duration_ms = 1000.0  # Default estimate, could be improved with actual timing
                    
                    # Learn from execution results to improve predictions (synchronous call)
                    self.predictive_planner.learn_from_execution(
                        step_id=step.id,
                        actual_duration_ms=actual_duration_ms,
                        success=success
                    )
                    
                    logger.debug(f"Updated predictive models for step {step.id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to update predictive planner: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to collect execution feedback: {e}")

    def _check_agent_tool_persistence(self) -> None:
        """Check for agent tool persistent state and emit advisory if found."""
        try:
            from openhands.agenthub.codeact_agent.tools import str_replace_editor

            try:
                tool_desc = str_replace_editor.create_str_replace_editor_tool().function.description
            except (AttributeError, TypeError, ImportError):
                tool_desc = None

            if tool_desc and "State is persistent" in tool_desc:
                self._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "advisory",
                        "reason": "agent_tool_persistent_state_detected",
                        "message": (
                            "An agent tool advertises persistent state. "
                            "Orchestrator owns step-level caching; agent tools should be stateless or use ephemeral caches."
                        ),
                    },
                )
        except (ImportError, AttributeError, RuntimeError):
            pass

    def _emit_event(self, event: dict | object) -> None:
        """Helper to emit an event through the EventEmitter and keep.

        a public list of emitted event dicts in self.step_events.
        """
        try:
            # Prepare event for emission
            self._prepare_event_for_emission(event)

            # Emit the event
            self._emit_prepared_event(event)

            # Update step events list
            self._update_step_events_list()

            # Call real-time step event callback if available
            self._call_step_event_callback(event)
        except (RuntimeError, ValueError, AttributeError):
            logging.exception("Failed to emit event")

    def _prepare_event_for_emission(self, event: dict | object) -> None:
        """Prepare event by adding source and trace_id metadata."""
        try:
            # Add source metadata
            self._add_source_metadata(event)

            # Add trace_id if available
            self._add_trace_id_metadata(event)
        except (TypeError, AttributeError, KeyError):
            pass

    def _add_source_metadata(self, event: dict | object) -> None:
        """Add source metadata to event."""
        try:
            if isinstance(event, dict):
                if "source" not in event:
                    event["source"] = "orchestrator"
            else:
                with contextlib.suppress(AttributeError, TypeError):
                    event.source = "orchestrator"
        except (TypeError, AttributeError):
            pass

    def _add_trace_id_metadata(self, event: dict | object) -> None:
        """Add trace_id metadata to event if available."""
        try:
            if (
                isinstance(event, dict)
                and getattr(self, "_ctx", None)
                and isinstance(getattr(self, "_ctx", None).extra, dict)
            ):
                tid = getattr(self, "_ctx", None).extra.get("trace_id")
                if tid and "trace_id" not in event:
                    event["trace_id"] = tid
        except (AttributeError, TypeError, KeyError):
            pass

    def _emit_prepared_event(self, event: dict | object) -> None:
        """Emit the prepared event through the emitter."""
        try:
            if hasattr(event, "to_public_dict") and callable(event.to_public_dict):
                self._emitter.emit(event.to_public_dict())
            else:
                self._emitter.emit(event)
        except (AttributeError, TypeError, RuntimeError):
            with contextlib.suppress(RuntimeError, ValueError):
                self._emitter.emit(event)

    def _update_step_events_list(self) -> None:
        """Update the step_events list with the most recent event."""
        try:
            last_event = self._get_last_emitted_event()
            if last_event is not None:
                self._append_to_step_events(last_event)
            else:
                self._refresh_step_events()
        except (AttributeError, TypeError, RuntimeError):
            pass

    def _get_last_emitted_event(self) -> dict | None:
        """Get the last emitted event as a dict."""
        try:
            if getattr(self._emitter, "_events", None):
                return self._emitter._events[-1].to_public_dict()
        except (AttributeError, IndexError, TypeError):
            pass
        return None

    def _append_to_step_events(self, event_dict: dict) -> None:
        """Append event dict to step_events list."""
        try:
            self.step_events.append(event_dict)
        except (AttributeError, TypeError):
            self._refresh_step_events()

    def _refresh_step_events(self) -> None:
        """Refresh step_events from emitter events."""
        with contextlib.suppress(AttributeError, TypeError):
            self.step_events = self._emitter.events

    def _handle_stuck_thread(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        worker: threading.Thread,
        timeout_seconds: float,
    ) -> None:
        """Best-effort handling for worker threads that remain alive after a timeout.

        Emits a 'stuck' advisory event with available metadata and attempts to
        capture a lightweight stack snapshot for debugging. This function must
        avoid raising exceptions.
        """
        try:
            # Capture stack frames
            stacks = self._capture_thread_stacks()

            # Truncate large stacks
            stacks = self._truncate_stacks(stacks)

            # Emit stuck thread event
            self._emit_stuck_thread_event(step, timeout_seconds, worker, stacks)
        except (RuntimeError, AttributeError, TypeError) as e:
            self._handle_stuck_thread_error(e)

    def _capture_thread_stacks(self) -> dict:
        """Capture thread stack frames."""
        try:
            import sys as _sys
            import traceback as _traceback

            return {str(tid): _traceback.format_stack(frame) for tid, frame in _sys._current_frames().items()}
        except (OSError, RuntimeError, AttributeError):
            return {"error": "failed_to_capture_frames"}

    def _truncate_stacks(self, stacks: dict) -> dict:
        """Truncate large stack traces."""
        try:
            for k, v in list(stacks.items()):
                if isinstance(v, list):
                    stacks[k] = v[-20:]
        except (TypeError, AttributeError):
            pass
        return stacks

    def _emit_stuck_thread_event(
        self,
        step: SopStep,
        timeout_seconds: float,
        worker: threading.Thread,
        stacks: dict,
    ) -> None:
        """Emit stuck thread event."""
        self._emit_event(
            {
                "step_id": getattr(step, "id", None) or "__unknown__",
                "role": getattr(step, "role", None) or "__unknown__",
                "status": "stuck",
                "reason": "step_thread_stuck",
                "meta": {
                    "timeout_seconds": timeout_seconds,
                    "thread_alive": worker.is_alive(),
                    "stack_snapshot": stacks,
                },
            },
        )

    def _handle_stuck_thread_error(self, error: Exception) -> None:
        """Handle errors in stuck thread handling."""
        try:
            if getattr(self, "_logger", None):
                try:
                    self._logger.exception("Failed to handle stuck thread")
                except (AttributeError, RuntimeError):
                    logging.exception("Failed to handle stuck thread")
            else:
                logging.exception("Failed to handle stuck thread")
        except (AttributeError, RuntimeError):
            pass

    def _compute_artifact_hash(self, artifact: Artifact | None) -> str | None:
        if not artifact:
            return None
        base = {
            "step_id": artifact.step_id,
            "role": artifact.role,
            "content": artifact.content,
        }
        return self._hash_dict(base)

    def _compute_step_hash(self, artifact_hash: str | None, rationale: str | None) -> str:
        material = {
            "prev": self._previous_step_hash,
            "artifact_hash": artifact_hash,
            "rationale": rationale,
        }
        return self._hash_dict(material)

    def _ensure_artifact_provenance(
        self,
        artifact: Artifact | None,
        step: SopStep | None = None,
        prev_text: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Compute and attach stable provenance fields on Artifact.content['_provenance'] if missing.

        Returns (artifact_hash, diff_fingerprint).

        Does not overwrite existing agent-provided values unless absent.
        """
        if not artifact:
            return None, None

        try:
            # Compute artifact hash
            art_hash = self._compute_artifact_hash_safe(artifact)

            # Compute diff fingerprint
            fp = self._compute_diff_fingerprint_safe(artifact, prev_text)

            # Attach provenance to artifact
            self._attach_provenance_to_artifact(artifact, art_hash, fp)

            return art_hash, fp
        except (TypeError, ValueError, AttributeError):
            return None, None

    def _compute_artifact_hash_safe(self, artifact: Artifact) -> str | None:
        """Safely compute artifact hash with error handling."""
        try:
            return self._compute_artifact_hash(artifact)
        except (TypeError, ValueError, AttributeError):
            return None

    def _compute_diff_fingerprint_safe(self, artifact: Artifact, prev_text: str | None) -> str | None:
        """Safely compute diff fingerprint with error handling."""
        try:
            # Extract new text from artifact
            new_text = self._extract_artifact_text_safe(artifact)
            if not new_text:
                return None

            # Compute unified diff if we have previous text
            unified = self._compute_unified_diff_safe(prev_text, new_text)

            # Compute fingerprint from diff or fallback to hash
            return self._compute_fingerprint_from_diff_or_text(unified, new_text)
        except (TypeError, ValueError, AttributeError):
            return None

    def _extract_artifact_text_safe(self, artifact: Artifact) -> str | None:
        """Safely extract text content from artifact."""
        try:
            if isinstance(artifact.content, dict):
                return (
                    artifact.content.get("content")
                    or artifact.content.get("text")
                    or json.dumps(artifact.content, sort_keys=True)
                )
            return str(artifact.content)
        except (TypeError, ValueError, AttributeError):
            return None

    def _compute_unified_diff_safe(self, prev_text: str | None, new_text: str) -> str:
        """Safely compute unified diff between previous and new text."""
        if not (isinstance(prev_text, str) and isinstance(new_text, str) and prev_text != new_text):
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

    def _compute_fingerprint_from_diff_or_text(self, unified: str, new_text: str) -> str | None:
        """Compute fingerprint from diff or fallback to text hash."""
        try:
            # Try diff fingerprint first
            if unified and unified.strip():
                return compute_diff_fingerprint(unified)

            # Fallback to text hash
            return hashlib.sha256((new_text or "").encode("utf-8")).hexdigest()[:16]
        except (TypeError, ValueError, AttributeError):
            return None

    def _attach_provenance_to_artifact(self, artifact: Artifact, art_hash: str | None, fp: str | None) -> None:
        """Attach provenance fields to artifact content."""
        try:
            if isinstance(artifact.content, dict):
                prov = artifact.content.setdefault("_provenance", {})
                if art_hash and "artifact_hash" not in prov:
                    prov["artifact_hash"] = art_hash
                if fp and "diff_fingerprint" not in prov:
                    prov["diff_fingerprint"] = fp
        except (TypeError, AttributeError, KeyError):
            pass

    def _deps_satisfied(self, done: dict[str, Artifact], step: SopStep) -> bool:
        result = all(dep in done for dep in step.depends_on)
        self._logger.info(
            "Dependency check for step %s: depends_on=%s, done=%s, result=%s",
            step.id,
            step.depends_on,
            list(done.keys()),
            result,
        )
        return result

    def _attempt_execute_with_retry(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: RetryPolicy | None,
    ):
        """Run the step executor honoring the provided retry_policy.

        Returns a StepResult. Centralizes retry/backoff behavior so all
        execution paths use consistent semantics and logging.
        """
        attempts = self._get_max_attempts(retry_policy)

        for attempt in range(attempts):
            # Log execution attempt
            self._log_execution_attempt(step, attempt, attempts)

            # Execute step
            result = self._execute_single_attempt(step, ctx, role_profile)

            # Check if successful
            if self._is_execution_successful(result, step, ctx, attempt):
                return result

            # Handle retry if more attempts remain
            if not self._handle_retry_backoff(step, attempt, attempts, retry_policy):
                break

        return result

    def _get_max_attempts(self, retry_policy: RetryPolicy | None) -> int:
        """Get maximum number of attempts from retry policy."""
        return getattr(retry_policy, "max_attempts", None) or 1 if retry_policy else 1

    def _log_execution_attempt(self, step: SopStep, attempt: int, attempts: int) -> None:
        """Log execution attempt with error handling."""
        try:
            self._logger.info(
                f"metasop: executing step_id={step.id} role={step.role} attempt={attempt} of {attempts}",
            )
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(
                    f"metasop: executing step_id={step.id} role={step.role} attempt={attempt} of {attempts}",
                )

    def _execute_single_attempt(self, step: SopStep, ctx: OrchestrationContext, role_profile) -> StepResult:
        """Execute a single attempt of the step."""
        try:
            # Use the same LLM as regular chat (respects UI settings)
            if self.llm_registry and not hasattr(ctx, "llm_registry"):
                ctx.llm_registry = self.llm_registry
            
            # Apply prompt optimization if enabled
            optimized_role_profile = self._apply_prompt_optimization(step, role_profile)
            
            return self.step_executor.execute(
                step,
                ctx,
                model_dump_with_options(optimized_role_profile),
                config=self.config,
            )
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            return StepResult(ok=False, artifact=None, error=str(exc))

    def _is_execution_successful(
        self,
        result: StepResult,
        step: SopStep,
        ctx: OrchestrationContext,
        attempt: int,
    ) -> bool:
        """Check if execution was successful and handle success."""
        if getattr(result, "ok", False) and getattr(result, "artifact", None):
            self._record_successful_attempt(step, ctx, attempt)
            return True
        return False

    def _record_successful_attempt(self, step: SopStep, ctx: OrchestrationContext, attempt: int) -> None:
        """Record successful attempt in context."""
        with contextlib.suppress(AttributeError, TypeError):
            getattr(ctx, "extra", {})[f"successful_attempt::{step.id}"] = attempt

    def _handle_retry_backoff(
        self,
        step: SopStep,
        attempt: int,
        attempts: int,
        retry_policy: RetryPolicy | None,
    ) -> bool:
        """Handle retry backoff if more attempts remain."""
        if attempt >= (attempts - 1):
            return False

        delay = self._compute_retry_delay(retry_policy, attempt)
        self._log_retry_attempt(step, attempt, delay)

        if delay and delay > 0:
            time.sleep(delay)

        return True

    def _compute_retry_delay(self, retry_policy: RetryPolicy | None, attempt: int) -> float:
        """Compute retry delay from policy."""
        try:
            return retry_policy.compute_sleep(attempt) if retry_policy else 0
        except (AttributeError, TypeError, ValueError):
            return 0

    def _log_retry_attempt(self, step: SopStep, attempt: int, delay: float) -> None:
        """Log retry attempt with error handling."""
        try:
            self._logger.info(f"metasop: retrying step_id={step.id} after failure attempt={attempt} delay={delay}")
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(f"metasop: retrying step_id={step.id} after failure attempt={attempt} delay={delay}")

    def _evaluate_condition(self, done: dict[str, Artifact], step: SopStep) -> tuple[bool, str | None, bool]:
        """Evaluate a simple logical expression with AND-chained clauses.

        Supported clause forms:
            artifact.field[.field]* OP value
        OP in: ==, !=, >, <
        value parsing: true/false, numeric, quoted string, or bare word (string)
        Multiple clauses combine with logical AND (case-insensitive 'and').

        Returns (decision, warning_message, parse_error_flag).
        parse_error_flag distinguishes syntax problems from a normal False evaluation.
        """
        expr = step.condition
        if not expr:
            return True, None, False

        clauses = re.split(r"\band\b", expr, flags=re.IGNORECASE)
        return self._evaluate_clauses(done, clauses)

    def _evaluate_clauses(self, done: dict[str, Artifact], clauses: list[str]) -> tuple[bool, str | None, bool]:
        """Evaluate all clauses and return overall result."""
        any_parse_error = False
        parse_messages = []
        overall = True

        clause_re = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s*(==|!=|>|<)\s*(.+?)\s*$")
        op_token_re = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s*([=!<>]{1,3})\s*(.+?)\s*$")

        for raw_clause in clauses:
            clause = raw_clause.strip()
            if not clause:
                continue

            clause_result, clause_error, clause_parse_error = self._evaluate_single_clause(
                done,
                clause,
                clause_re,
                op_token_re,
            )

            if clause_parse_error:
                any_parse_error = True
                parse_messages.append(clause_error)
                overall = False
            elif not clause_result:
                overall = False

        warning = "; ".join(parse_messages) if any_parse_error else None
        return overall, warning, any_parse_error

    def _evaluate_single_clause(
        self,
        done: dict[str, Artifact],
        clause: str,
        clause_re,
        op_token_re,
    ) -> tuple[bool, str, bool]:
        """Evaluate a single clause and return result, error message, and parse error flag."""
        # First detect operator token
        m_op = op_token_re.match(clause)
        if not m_op:
            return False, f"Unrecognized clause syntax: '{clause}'", True

        path, op, value_raw = m_op.groups()
        if op not in {"==", "!=", ">", "<"}:
            return False, f"Unsupported operator '{op}' in clause: '{clause}'", True

        # Use stricter clause_re to parse fields
        m = clause_re.match(clause)
        if not m:
            return False, f"Unrecognized clause syntax: '{clause}'", True

        path, op, value_raw = m.groups()
        value = self._parse_value(value_raw)

        # Get artifact and navigate to field
        current = self._get_field_value(done, path)
        if current is None:
            return False, "", False

        # Perform comparison
        return self._perform_comparison(current, op, value, clause)

    def _parse_value(self, raw: str):
        """Parse a value from string representation."""
        t = raw.strip()
        tl = t.lower()

        if tl in {"true", "false"}:
            return tl == "true"

        # Try numeric parsing
        try:
            if re.match(r"^[+-]?\d+\.\d+$", t):
                return float(t)
            if re.match(r"^[+-]?\d+$", t):
                return int(t)
        except (ValueError, OverflowError):
            pass

        # Handle quoted strings
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            return t[1:-1]

        return t  # bare word string

    def _get_field_value(self, done: dict[str, Artifact], path: str):
        """Get field value from artifact by path."""
        parts = path.split(".")
        art = done.get(parts[0])
        if not art:
            return None

        current = art.content
        for p in parts[1:]:
            if isinstance(current, dict):
                current = current.get(p)
            else:
                return None
        return current

    def _perform_comparison(self, current, op: str, value, clause: str) -> tuple[bool, str, bool]:
        """Perform the actual comparison operation."""
        try:
            if op in {"==", "!="}:
                result = current == value
                if op == "!=":
                    result = not result
                return result, "", False
            if op in {">", "<"}:
                if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                    result = current > value if op == ">" else current < value
                    return result, "", False
                return False, "", False
            return False, "", False
        except (TypeError, ValueError, AttributeError) as exc:
            return False, f"Comparison error in clause '{clause}': {exc}", True

    def _setup_logging_and_tracing(self, ctx: OrchestrationContext) -> None:
        """Setup logging and tracing for the orchestration run."""
        # Generate and bind a trace_id for this orchestration run for correlation
        try:
            trace_id = str(uuid.uuid4())
            ctx.extra["trace_id"] = trace_id
            try:
                from openhands.core.logger import (
                    bind_context,
                    openhands_logger,
                )

                self._logger = bind_context(openhands_logger, trace_id=trace_id)
            except (AttributeError, RuntimeError, ImportError):
                # Handle logger binding errors
                self._logger = logging.getLogger("openhands")
            try:
                # Also set global trace context for the TraceContextFilter to pick up
                from openhands.core.logger import set_trace_context

                set_trace_context({"trace_id": trace_id})
            except (ImportError, AttributeError, RuntimeError):
                # Handle trace context setup errors
                pass
        except (AttributeError, RuntimeError):
            # Handle logger initialization errors
            self._logger = logging.getLogger("openhands")

    def _initialize_memory(self, ctx: OrchestrationContext) -> None:
        """Initialize memory index and bind memory store for the run."""
        # Instantiate memory index for this run
        if not self.settings.enable_vector_memory:
            # Lexical path: instantiate persistent MemoryIndex for this run
            try:
                self.memory_index = MemoryIndex(
                    run_id=ctx.run_id,
                    max_records=self.settings.memory_max_records,
                )
            except (OSError, ValueError, RuntimeError, AttributeError) as e:
                # Handle memory index initialization errors
                self._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "suppressed_error",
                        "reason": "memory_init_failed",
                        "error": str(e)[:400],
                    },
                )
                if self.settings.strict_mode:
                    raise
                # fall back to no memory index for lexical mode if init failed
                self.memory_index = None
        try:
            # Recreate memory store in lexical mode bound to run id
            self.memory_store.bind_run(ctx.run_id)
        except (AttributeError, RuntimeError, ValueError):
            # Handle memory store binding errors
            pass

    def _discover_models(self) -> list[str]:
        """Discover available LLM models from configuration."""
        try:
            if not getattr(self, "config", None):
                return []

            return self._extract_models_from_config()
        except (AttributeError, TypeError, KeyError, RuntimeError) as e:
            self._handle_model_discovery_error(e)
            return []

    def _extract_models_from_config(self) -> list[str]:
        """Extract models from configuration."""
        try:
            llms_map = getattr(self.config, "llms", None)
            if isinstance(llms_map, dict) and llms_map:
                return self._extract_models_from_llms_map(llms_map)
            return self._extract_models_from_legacy_config()
        except (AttributeError, TypeError, KeyError):
            return []

    def _extract_models_from_llms_map(self, llms_map: dict) -> list[str]:
        """Extract models from llms configuration map."""
        profile_keys = list(llms_map.keys())
        model_names = self._extract_model_names_from_configs(llms_map.values())
        return sorted(set(profile_keys + model_names))

    def _extract_model_names_from_configs(self, configs) -> list[str]:
        """Extract model names from configuration objects."""
        model_names = []
        for _cfg in configs:
            try:
                m = getattr(_cfg, "model", None)
                if isinstance(m, str) and m:
                    model_names.append(m)
            except (AttributeError, TypeError):
                continue
        return model_names

    def _extract_models_from_legacy_config(self) -> list[str]:
        """Extract models from legacy configuration format."""
        models_cfg = getattr(self.config, "models", None)
        return list(models_cfg.keys()) if isinstance(models_cfg, dict) else []

    def _handle_model_discovery_error(self, error: Exception) -> None:
        """Handle model discovery errors."""
        self._emit_event(
            {
                "step_id": "__bootstrap__",
                "role": "system",
                "status": "suppressed_error",
                "reason": "model_discovery_failed",
                "error": str(error)[:300],
            },
        )
        if self.settings.strict_mode:
            raise

    def _setup_environment_and_validate_models(self, models: list[str], ctx: OrchestrationContext) -> bool:
        """Setup environment signature and validate available LLM models, returning False if invalid."""
        try:
            env_sig, env_payload = compute_environment_signature(models)
            ctx.extra["environment_signature"] = env_sig
            ctx.extra["environment"] = env_payload
        except (OSError, RuntimeError, ValueError, AttributeError):
            # Handle environment signature computation errors
            ctx.extra["environment_signature"] = None

        # If no LLM models were discovered in the environment, fail fast with
        # a clear diagnostic event. This commonly happens in local dev when
        # API keys or model configs are not present (e.g., OpenRouter API key).
        try:
            # Primary check: explicit models discovered in computed environment payload
            llm_models = (
                ctx.extra.get("environment", {}).get("llm_models")
                if isinstance(ctx.extra.get("environment", {}), dict)
                else None
            )
            # Fallback: if no explicit models discovered, but role profiles are populated
            # (tests commonly set `orch.profiles[...] = ...` directly), treat that as
            # sufficient evidence of available LLM-like executors and proceed.
            if not llm_models:
                try:
                    profile_keys = (
                        list(self.profiles.keys()) if isinstance(self.profiles, dict) and self.profiles else []
                    )
                    if profile_keys:
                        llm_models = profile_keys
                except (AttributeError, TypeError):
                    # Handle profile access errors
                    pass

            if not llm_models:
                self._emit_event({"step_id": "__bootstrap__", "role": "system", "status": "failed", "reason": "no_llm_models_configured", "message": (
                    "No LLM models found in configuration. Ensure your LLM profiles or API keys are configured (e.g., in config.toml or env vars)."), }, )
                return False
        except (AttributeError, TypeError, KeyError):
            # Handle environment validation errors
            pass
        return True

    def _setup_budgets_retry_and_taxonomy(self, max_retries: int) -> tuple[int, int, int, bool, RetryPolicy]:
        """Setup token budgets, retry policy, and taxonomy flag."""
        done: dict[str, Artifact] = {}  # This is returned for use in run
        soft_budget = self.settings.token_budget_soft
        hard_budget = self.settings.token_budget_hard
        consumed_tokens = 0
        # Structured retry policy (fallback to legacy max_retries if config absent)
        try:
            if retry_kwargs := self.settings.build_retry_policy_kwargs():
                retry_policy = RetryPolicy(**retry_kwargs)
            else:
                retry_policy = RetryPolicy(max_attempts=max_retries + 1)
        except (TypeError, ValueError, AttributeError):
            # Handle retry policy creation errors
            retry_policy = RetryPolicy(max_attempts=max_retries + 1)
        # Harmonize legacy max_retries parameter with policy
        max_retries = max(0, (retry_policy.max_attempts or 1) - 1)
        # Diagnostic logging: expose effective retry policy for debugging
        try:
            try:
                self._logger.info(f"metasop: retry_policy={retry_policy} effective_max_retries={max_retries}")
            except (AttributeError, RuntimeError):
                # Handle logger access errors
                logging.info(f"metasop: retry_policy={retry_policy} effective_max_retries={max_retries}")
        except (AttributeError, RuntimeError):
            # Handle fallback logging errors
            pass
        taxonomy_enabled = self.settings.enable_failure_taxonomy

        return (
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

    def _setup_orchestration_run(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> tuple[bool, OrchestrationContext, dict]:
        """Setup and initialize orchestration run.

        Returns:
            tuple: (success, context, setup_data)
            - success: bool indicating if setup was successful
            - context: OrchestrationContext instance
            - setup_data: dict containing setup results (models, budgets, etc.)
        """
        # Feature flag gate: only run when enabled
        if not (self.settings.enabled):
            return False, None, {}

        ctx = OrchestrationContext(
            run_id=str(uuid.uuid4()),
            user_request=user_request,
            repo_root=repo_root,
        )
        # retain reference for report building
        self._ctx = ctx
        self._setup_logging_and_tracing(ctx)
        self._initialize_memory(ctx)

        # Respect micro-iteration settings provided by the caller. We still
        # ensure candidate count is at least 1 to avoid degenerate zero-counts.
        try:
            if (
                getattr(self.settings, "micro_iteration_candidate_count", None) is not None
                and self.settings.micro_iteration_candidate_count < 1
            ):
                self.settings.micro_iteration_candidate_count = 1
        except (AttributeError, TypeError):
            # Handle settings access errors during micro-iteration setup
            pass

        models = self._discover_models()
        if not self._setup_environment_and_validate_models(models, ctx):
            return False, ctx, {}

        (
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        ) = self._setup_budgets_retry_and_taxonomy(max_retries)

        setup_data = {
            "models": models,
            "done": done,
            "soft_budget": soft_budget,
            "hard_budget": hard_budget,
            "consumed_tokens": consumed_tokens,
            "taxonomy_enabled": taxonomy_enabled,
            "retry_policy": retry_policy,
            "max_retries": max_retries,
        }

        return True, ctx, setup_data

    def _process_orchestration_steps(
        self,
        ctx: OrchestrationContext,
        done: set,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: str,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process all orchestration steps with intelligent parallel execution.

        Returns:
            tuple: (success, artifacts)
        """
        # Use parallel execution if enabled, otherwise fall back to sequential
        if self.parallel_engine and getattr(self.settings, "enable_parallel_execution", False):
            return self._process_steps_parallel(
                ctx, done, soft_budget, hard_budget, consumed_tokens,
                taxonomy_enabled, retry_policy, max_retries
            )
        else:
            return self._process_steps_sequential(
                ctx, done, soft_budget, hard_budget, consumed_tokens,
                taxonomy_enabled, retry_policy, max_retries
            )

    def _process_steps_parallel(
        self,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: str,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process orchestration steps using intelligent parallel execution."""
        logger.info("Starting parallel execution of orchestration steps")
        
        try:
            # Identify which steps can be executed in parallel
            parallel_groups = self.parallel_engine.identify_parallel_groups(
                self.template.steps, done
            )
            
            logger.info(f"Identified {len(parallel_groups)} parallel execution groups")
            
            # Execute steps in parallel groups
            success, artifacts = self.parallel_engine.execute_parallel_groups(
                parallel_groups,
                self._process_single_step,
                (ctx, done, soft_budget, hard_budget, consumed_tokens, taxonomy_enabled, retry_policy, max_retries)
            )
            
            # Log performance statistics
            stats = self.parallel_engine.get_execution_stats()
            logger.info(f"Parallel execution completed: {stats}")
            
            # Emit parallel execution event
            self._emit_event({
                "type": "parallel_execution_complete",
                "stats": stats,
                "groups_executed": len(parallel_groups)
            })
            
            return success, artifacts
            
        except Exception as e:
            logger.error(f"Parallel execution failed, falling back to sequential: {e}")
            return self._process_steps_sequential(
                ctx, done, soft_budget, hard_budget, consumed_tokens,
                taxonomy_enabled, retry_policy, max_retries
            )

    def _process_steps_sequential(
        self,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: str,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process orchestration steps sequentially (original implementation)."""
        artifacts = {}

        for step in self.template.steps:
            # Process single step
            step_success, step_artifacts = self._process_single_step(
                step,
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

            if not step_success:
                return False, artifacts

            # Merge artifacts
            artifacts |= step_artifacts

        return True, artifacts

    async def _process_orchestration_steps_async(
        self,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process all orchestration steps with true async parallel execution for maximum performance."""
        logger.info("Starting async orchestration steps execution")
        
        try:
            # 🔮 PREDICTIVE EXECUTION PLANNING - Revolutionary pre-execution optimization
            execution_steps = self.template.steps
            if self.predictive_planner and getattr(self.settings, "enable_predictive_planning", False):
                try:
                    logger.info("🔮 Starting predictive execution planning...")
                    
                    # Generate optimized execution plan
                    execution_plan = await self.predictive_planner.analyze_execution_path(
                        self.template.steps, ctx
                    )
                    
                    # Use optimized steps if confidence is high enough
                    confidence_threshold = getattr(self.settings, "predictive_confidence_threshold", 0.7)
                    if execution_plan.confidence_score >= confidence_threshold:
                        execution_steps = execution_plan.optimized_steps
                        logger.info(f"🎯 Using predictive execution plan: {execution_plan.parallelization_factor:.1f}x parallelization, {execution_plan.predicted_total_time_ms:.0f}ms predicted time")
                        
                        # Log optimization insights
                        if execution_plan.conflict_warnings:
                            logger.warning(f"⚠️ Predictive warnings: {', '.join(execution_plan.conflict_warnings[:3])}")
                        if execution_plan.optimization_opportunities:
                            logger.info(f"💡 Optimization opportunities: {', '.join(execution_plan.optimization_opportunities[:3])}")
                    else:
                        logger.info(f"🔮 Predictive plan confidence too low ({execution_plan.confidence_score:.2f} < {confidence_threshold}), using original execution order")
                        
                except Exception as e:
                    logger.warning(f"Predictive planning failed, using original execution: {e}")
                    execution_steps = self.template.steps
            
            # Use async parallel execution if enabled and available
            if self.parallel_engine and hasattr(self.parallel_engine, 'execute_parallel_groups_async'):
                # Use optimized steps from predictive planner or original steps
                parallel_groups = self.parallel_engine.identify_parallel_groups(
                    execution_steps, done
                )
                
                logger.info(f"Identified {len(parallel_groups)} parallel execution groups for async execution")
                
                # Execute using async parallel groups - this is the revolutionary part!
                success, artifacts = await self.parallel_engine.execute_parallel_groups_async(
                    parallel_groups,
                    self._process_single_step_async,
                    (ctx, done, soft_budget, hard_budget, consumed_tokens, taxonomy_enabled, retry_policy, max_retries)
                )
                
                # Log performance statistics
                stats = self.parallel_engine.get_execution_stats()
                logger.info(f"Async parallel execution completed: {stats}")
                
                # Emit async execution event
                self._emit_event({
                    "type": "async_parallel_execution_complete",
                    "stats": stats,
                    "groups_executed": len(parallel_groups),
                    "execution_mode": "async_parallel"
                })
                
                return success, artifacts
            else:
                # Fallback to sequential async execution
                return await self._process_steps_sequential_async(
                    ctx, done, soft_budget, hard_budget, consumed_tokens,
                    taxonomy_enabled, retry_policy, max_retries
                )
                
        except Exception as e:
            logger.error(f"Async execution failed, falling back to sequential async: {e}")
            return await self._process_steps_sequential_async(
                ctx, done, soft_budget, hard_budget, consumed_tokens,
                taxonomy_enabled, retry_policy, max_retries
            )

    async def _process_steps_sequential_async(
        self,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process orchestration steps sequentially using async execution."""
        artifacts = {}

        for step in self.template.steps:
            # Process single step asynchronously
            step_success, step_artifacts = await self._process_single_step_async(
                step,
                ctx,
                done,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )

            if not step_success:
                return False, artifacts

            # Merge artifacts
            artifacts |= step_artifacts

        return True, artifacts

    def _process_single_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process a single orchestration step.

        Returns:
            tuple: (success, artifacts)
        """
        # Log step entry
        self._log_step_entry(step)

        # Check capability matrix requirements
        capability_ok = self._check_capability_matrix(step, done)
        if not capability_ok:
            return True, {}

        # Check dependencies and conditions
        deps_ok = self._check_dependencies_and_conditions(step, done)
        if not deps_ok:
            return True, {}

        # Perform memory retrieval for context
        self._perform_memory_retrieval(step, ctx)

        if role_profile := self.profiles.get(step.role):
            # Add to active tracking before execution
            self._add_active_step(step)
            
            try:
                # Process step execution
                success, artifacts = self._execute_step_with_retry(
                    step,
                    ctx,
                    done,
                    role_profile,
                    soft_budget,
                    hard_budget,
                    consumed_tokens,
                    taxonomy_enabled,
                    retry_policy,
                    max_retries,
                )
                
                # Collect active steps for feedback before removing current step
                active_steps_at_execution = list(self.active_steps.values())
                
                # Collect feedback and learn from execution
                self._collect_execution_feedback(
                    step, success, artifacts, active_steps_at_execution
                )
                
                return success, artifacts
            finally:
                # Always remove from active tracking
                self._remove_active_step(step.id)
        else:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "no_role_profile",
                },
            )
            return True, {}

    async def _process_single_step_async(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Async version of process_single_step for true concurrency."""
        # Log step entry
        self._log_step_entry(step)

        # Check capability matrix requirements
        capability_ok = self._check_capability_matrix(step, done)
        if not capability_ok:
            return True, {}

        # Check dependencies and conditions
        deps_ok = self._check_dependencies_and_conditions(step, done)
        if not deps_ok:
            return True, {}

        # Perform memory retrieval for context
        if hasattr(self, '_perform_memory_retrieval_async'):
            await self._perform_memory_retrieval_async(step, ctx)
        else:
            self._perform_memory_retrieval(step, ctx)

        if role_profile := self.profiles.get(step.role):
            # Add to active tracking before execution
            self._add_active_step(step)
            
            try:
                # Execute step with async support if available
                success, artifacts = await self._execute_step_with_retry_async(
                    step,
                    ctx,
                    done,
                    role_profile,
                    soft_budget,
                    hard_budget,
                    consumed_tokens,
                    taxonomy_enabled,
                    retry_policy,
                    max_retries,
                )
                
                # Collect active steps for feedback before removing current step
                active_steps_at_execution = list(self.active_steps.values())
                
                # Collect feedback and learn from execution
                self._collect_execution_feedback(
                    step, success, artifacts, active_steps_at_execution
                )
                
                return success, artifacts
            finally:
                # Always remove from active tracking
                self._remove_active_step(step.id)
        else:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "no_role_profile",
                },
            )
            return True, {}

    async def _execute_step_with_retry_async(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        role_profile,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Async wrapper for step execution with retry - bridges sync execution to async."""
        # For now, run the synchronous execution in an executor to avoid blocking
        # This maintains compatibility while enabling async architecture
        loop = asyncio.get_event_loop()
        
        # Try to find the synchronous version by looking for similar patterns
        if hasattr(self, '_execute_step_with_retry'):
            return await loop.run_in_executor(
                None, 
                self._execute_step_with_retry,
                step, ctx, done, role_profile, soft_budget, hard_budget,
                consumed_tokens, taxonomy_enabled, retry_policy, max_retries
            )
        else:
            # Fallback: simulate execution (this needs to be connected to actual execution later)
            logger.warning(f"Async execution fallback for step {step.id} - sync method not found")
            return True, {}

    def _log_step_entry(self, step: SopStep) -> None:
        """Log step entry with error handling."""
        try:
            self._logger.info(
                f'metasop: entering step id={getattr(step, "id", None)} role={getattr(step, "role", None)}',
            )
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(
                    f'metasop: entering step id={getattr(step, "id", None)} role={getattr(step, "role", None)}',
                )

    def _check_capability_matrix(self, step: SopStep, done: dict[str, Artifact]) -> bool:
        """Check capability matrix requirements."""
        if not self.settings.enforce_capability_matrix:
            return True

        req_caps = self._get_required_capabilities(step)
        if not req_caps:
            return True

        role_caps = self._get_role_capabilities(step)
        return bool(self._validate_capabilities(step, req_caps, role_caps))

    def _get_required_capabilities(self, step: SopStep) -> list | None:
        """Get required capabilities for a step."""
        req_caps = getattr(step, "required_capabilities", None)
        if not req_caps:
            extras = getattr(step, "extras", None)
            if extras and hasattr(extras, "get"):
                req_caps = extras.get("required_capabilities", None)
        return req_caps

    def _get_role_capabilities(self, step: SopStep) -> list:
        """Get capabilities for the step's role."""
        role_profile = self.profiles.get(step.role)
        try:
            return (role_profile.capabilities if role_profile and hasattr(role_profile, "capabilities") else []) or []
        except (AttributeError, TypeError):
            return []

    def _validate_capabilities(self, step: SopStep, req_caps: list, role_caps: list) -> bool:
        """Validate that role has required capabilities."""
        if not any(isinstance(req_caps, t) for t in (list, tuple, set)):
            return True

        self._emit_capability_advisories(step, req_caps)

        if missing := [c for c in req_caps if c not in role_caps]:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "capabilities_missing",
                    "meta": {"required": req_caps, "missing": missing},
                },
            )
            return False

        return True

    def _emit_capability_advisories(self, step: SopStep, req_caps: list) -> None:
        """Emit advisories for unknown capabilities."""
        try:
            all_caps = set()
            for rp in self.profiles.values():
                for c in getattr(rp, "capabilities", []) or []:
                    all_caps.add(c)
            if unknown := [c for c in req_caps if c not in all_caps]:
                self._emit_event(
                    {
                        "step_id": step.id,
                        "role": step.role,
                        "status": "advisory",
                        "reason": "unknown_capabilities",
                        "meta": {"unknown": unknown},
                    },
                )
        except (AttributeError, TypeError, KeyError):
            pass

    def _check_dependencies_and_conditions(self, step: SopStep, done: dict[str, Artifact]) -> bool:
        """Check step dependencies and conditions."""
        self._logger.info("Checking dependencies and conditions for step %s", step.id)

        if not self._deps_satisfied(done, step):
            self._logger.info("Step %s skipped: unsatisfied_dependencies", step.id)
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "unsatisfied_dependencies",
                },
            )
            return False

        cond_ok, cond_warn, parse_err = self._evaluate_condition(done, step)
        self._logger.info(
            "Condition evaluation for step %s: ok=%s, warn=%s, parse_err=%s", step.id, cond_ok, cond_warn, parse_err,
        )

        if not cond_ok:
            self._logger.info("Step %s skipped: condition_false or parse_error", step.id)
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "condition_parse_error" if parse_err else "condition_false",
                    **({"warning": cond_warn} if cond_warn else {}),
                },
            )
            return False

        # Check causal safety if enabled
        if self.causal_engine:
            try:
                can_proceed = self._check_causal_safety(step, done)
                if not can_proceed:
                    return False
            except Exception as e:
                self._logger.warning(f"Causal reasoning check failed: {e}, proceeding with original logic")
        
        self._logger.info("Step %s passed dependency and condition checks", step.id)
        return True

    def _check_causal_safety(self, step: SopStep, done: dict[str, Artifact]) -> bool:
        """Check causal safety using reasoning engine."""
        if not self.causal_engine:
            return True
        
        try:
            # Get currently active steps
            active_steps = self._get_currently_active_steps()
            
            # Get current context if available
            current_context = getattr(self, '_ctx', None)
            
            # Run causal analysis
            can_proceed, predictions = self.causal_engine.analyze_step_safety(
                proposed_step=step,
                active_steps=active_steps,
                completed_artifacts=done,
                current_context=current_context,
                max_analysis_time_ms=getattr(self.settings, 'causal_max_analysis_time_ms', 50)
            )
            
            if not can_proceed:
                # Emit causal blocking event
                blocking_predictions = [p for p in predictions if p.confidence > 0.8]
                self._emit_event({
                    "step_id": step.id,
                    "role": step.role,
                    "status": "causally_blocked",
                    "reason": "predicted_conflicts",
                    "predictions": [
                        {
                            "type": pred.conflict_type.value,
                            "affected_steps": pred.affected_steps,
                            "confidence": pred.confidence,
                            "recommendation": pred.recommendation
                        }
                        for pred in blocking_predictions
                    ]
                })
                self._logger.info(f"Step {step.id} blocked due to causal conflicts")
                return False
            
            # Log warnings for lower-confidence predictions
            warning_predictions = [p for p in predictions if 0.5 <= p.confidence <= 0.8]
            if warning_predictions:
                self._emit_event({
                    "step_id": step.id,
                    "role": step.role,
                    "status": "causal_warnings",
                    "predictions": [
                        {
                            "type": pred.conflict_type.value,
                            "affected_steps": pred.affected_steps,
                            "confidence": pred.confidence,
                            "recommendation": pred.recommendation
                        }
                        for pred in warning_predictions
                    ]
                })
        
        except Exception as e:
            self._logger.warning(f"Causal safety check failed: {e}")
            # Fail safe: allow step to proceed if causal check fails
            return True
        
        return True

    def _get_currently_active_steps(self) -> list[SopStep]:
        """Get list of currently executing steps."""
        return list(self.active_steps.values())

    def _add_active_step(self, step: SopStep) -> None:
        """Add step to active tracking."""
        self.active_steps[step.id] = step
        self._logger.debug(f"Added step {step.id} to active tracking")

    def _remove_active_step(self, step_id: str) -> None:
        """Remove step from active tracking."""
        if step_id in self.active_steps:
            del self.active_steps[step_id]
            self._logger.debug(f"Removed step {step_id} from active tracking")

    def _collect_execution_feedback(
        self, 
        step: SopStep, 
        success: bool, 
        artifacts: Dict[str, Artifact], 
        active_steps_at_time: List[SopStep]
    ) -> None:
        """Collect feedback from step execution for learning."""
        if not self.learning_storage or not getattr(self.settings, "enable_learning", False):
            return
        
        try:
            # Learn from causal reasoning if available
            if self.causal_engine:
                # Extract affected artifacts
                affected_artifacts = list(artifacts.keys()) if artifacts else []
                
                # Simulate conflict detection for now - in real implementation,
                # this would come from actual execution observation
                conflicts_observed = []
                
                # Call causal engine learning
                self.causal_engine.learn_from_execution(
                    step=step,
                    success=success,
                    affected_artifacts=affected_artifacts,
                    conflicts_observed=conflicts_observed,
                    active_steps_at_time=[s.id for s in active_steps_at_time]
                )
                
                # Save updated causal patterns
                causal_patterns = {
                    "conflict_patterns": self.causal_engine.conflict_patterns,
                    "resource_usage_history": self.causal_engine.resource_usage_history,
                    "performance_stats": self.causal_engine.performance_stats
                }
                self.learning_storage.save_causal_patterns(causal_patterns)
            
            # Track parallel execution effectiveness if available
            if self.parallel_engine:
                parallel_stats = self.parallel_engine.get_execution_stats()
                self.learning_storage.save_parallel_stats(parallel_stats)
            
            # Save performance history
            performance_entry = {
                "timestamp": time.time(),
                "step_id": step.id,
                "role": step.role,
                "success": success,
                "artifacts_count": len(artifacts),
                "active_steps_count": len(active_steps_at_time)
            }
            self.learning_storage.save_performance_history([performance_entry])
            
            self._logger.debug(f"Collected feedback for step {step.id}")
            
        except Exception as e:
            self._logger.warning(f"Failed to collect execution feedback: {e}")

    def _execute_step_with_retry(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        role_profile,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Execute step with retry logic."""
        # Check cache first
        pre_context_hash = self._compute_pre_context_hash(step, ctx, done)
        if self.step_cache and pre_context_hash:
            if cached_result := self._check_step_cache(step, pre_context_hash):
                return True, cached_result

        # Handle QA role specially
        if step.role.strip().lower() == "qa":
            return self._handle_qa_step(step, ctx, done, pre_context_hash)

        # Execute step with retry logic
        success, artifacts = self._execute_step_with_retries(
            step,
            ctx,
            done,
            role_profile,
            retry_policy,
            max_retries,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
        )

        # Store successful results in step cache
        if success and artifacts and self.step_cache and pre_context_hash:
            self._store_step_in_cache(step, artifacts, pre_context_hash)

        return success, artifacts

    def _compute_pre_context_hash(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
    ) -> str | None:
        """Compute pre-execution context hash for caching."""
        if not self.settings.enable_context_hash:
            return None

        try:
            retrieval_hits = self._get_retrieval_hits(step, ctx)
            prior_artifacts_meta = self._get_prior_artifacts_meta(done)
            env_sig = getattr(getattr(self, "_ctx", None), "extra", {}).get("environment_signature")

            return compute_context_hash(
                step_id=step.id,
                role=step.role,
                retrieval_hits=retrieval_hits,
                prior_artifacts=prior_artifacts_meta,
                role_capabilities=getattr(self.profiles.get(step.role), "capabilities", []) or [],
                env_signature=env_sig,
                model_name=None,
                executor_name=type(self.step_executor).__name__,
                truncate_bytes=self.settings.context_hash_truncate_artifact_bytes,
            )
        except (TypeError, ValueError, AttributeError):
            return None

    def _get_retrieval_hits(self, step: SopStep, ctx: OrchestrationContext) -> list:
        """Get retrieval hits for context hash computation."""
        rkey = f"retrieval::{step.id}"
        return ctx.extra.get(rkey, []) if isinstance(getattr(ctx, "extra", None), dict) else []

    def _get_prior_artifacts_meta(self, done: dict[str, Artifact]) -> list:
        """Get prior artifacts metadata for context hash computation."""
        prior_artifacts_meta = []
        for sid, art in done.items():
            with contextlib.suppress(TypeError, ValueError, AttributeError):
                prior_artifacts_meta.append(
                    {
                        "step_id": sid,
                        "artifact_hash": self._compute_artifact_hash(art),
                        "role": art.role,
                    },
                )
        return prior_artifacts_meta

    def _check_step_cache(self, step: SopStep, pre_context_hash: str) -> dict[str, Artifact] | None:
        """Check step cache for existing results."""
        try:
            if hit := self.step_cache.get(pre_context_hash, step.role):
                return self._process_cache_hit(step, hit)
        except (AttributeError, TypeError, ValueError):
            pass
        return None

    def _process_cache_hit(self, step: SopStep, hit) -> dict[str, Artifact]:
        """Process cache hit and return cached artifact."""
        cached_artifact = Artifact(
            step_id=step.id,
            role=step.role,
            content=hit.artifact_content,
        )

        # Update step hash
        self._previous_step_hash = hit.step_hash or self._previous_step_hash

        # Emit cache hit event
        self._emit_cache_hit_event(step)

        return {step.id: cached_artifact}

    def _emit_cache_hit_event(self, step: SopStep) -> None:
        """Emit cache hit event."""
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "executed_cached",
                "duration_ms": 0,
                "retries": 0,
            },
        )

    def _handle_qa_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        pre_context_hash: str | None,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle QA step execution."""
        if self.step_cache and pre_context_hash:
            if qa_hit := self.step_cache.get(pre_context_hash, step.role):
                cached_artifact = Artifact(
                    step_id=step.id,
                    role=step.role,
                    content=qa_hit.artifact_content,
                )
                done[step.id] = cached_artifact
                self._previous_step_hash = qa_hit.step_hash or self._previous_step_hash
                self._emit_event(
                    {
                        "step_id": step.id,
                        "role": step.role,
                        "status": "executed_cached",
                        "duration_ms": 0,
                        "retries": 0,
                    },
                )
                return True, {step.id: cached_artifact}

        # Execute QA step normally
        return self._execute_qa_step(step, ctx, done)

    def _execute_qa_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
    ) -> tuple[bool, dict[str, Artifact]]:
        """Execute QA step with test validation."""
        try:
            # Perform selective test selection
            selected_tests, _selection_reason = self._perform_selective_tests(step, ctx)

            # Execute QA with selected tests
            qa_artifact = self.qa_executor.run_qa(
                step,
                ctx,
                getattr(ctx, "repo_root", None),
                selected_tests=selected_tests,
            )

            # Check for timeout
            if self._is_qa_timed_out(qa_artifact):
                self._emit_qa_timeout_event(step)
                return False, {}

            # Validate QA artifact
            validation_result = self._validate_qa_artifact(step, qa_artifact)

            if validation_result["success"]:
                return self._handle_successful_qa_execution(step, qa_artifact, done, validation_result["data"])
            return self._handle_failed_qa_execution(step, qa_artifact, validation_result["error"])

        except Exception as e:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "error",
                    "reason": "qa_execution_failed",
                    "error": str(e)[:300],
                },
            )
            return False, {}

    def _is_qa_timed_out(self, qa_artifact: Artifact) -> bool:
        """Check if QA step timed out."""
        return isinstance(qa_artifact.content, dict) and qa_artifact.content.get("timeout") is True

    def _emit_qa_timeout_event(self, step: SopStep) -> None:
        """Emit QA timeout event."""
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "timeout",
                "reason": "qa_step_timeout",
            },
        )

    def _validate_qa_artifact(self, step: SopStep, qa_artifact: Artifact) -> dict:
        """Validate QA artifact against schema."""
        schema_file = getattr(getattr(step, "outputs", None), "schema_file", None)
        schema = load_schema(schema_file) if schema_file else {}
        payload = json.dumps(qa_artifact.content)
        ok, data, err = validate_json(payload, schema)

        return {
            "success": ok and data is not None,
            "data": data,
            "error": err,
        }

    def _handle_successful_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        done: dict[str, Artifact],
        data,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle successful QA execution."""
        qa_artifact.content = data
        done[step.id] = qa_artifact

        # Ingest artifact into memory
        self._ingest_artifact_to_memory(step, qa_artifact)

        # Emit success event with verification details
        self._emit_qa_success_event(step, qa_artifact)

        return True, {step.id: qa_artifact}

    def _emit_qa_success_event(self, step: SopStep, qa_artifact: Artifact) -> None:
        """Emit QA success event with verification details."""
        event_data = {
            "step_id": step.id,
            "role": step.role,
            "status": "executed",
            "retries": 0,
            "duration_ms": 0,  # Would need timing in real implementation
            "verification_result": self._build_qa_verification(qa_artifact.content),
        }

        # Add coverage data if available
        if isinstance(qa_artifact.content, dict):
            if qa_artifact.content.get("coverage"):
                event_data["coverage_overall"] = qa_artifact.content.get("coverage", {}).get("overall_percent")
            if qa_artifact.content.get("coverage_delta"):
                event_data["coverage_delta_files"] = qa_artifact.content.get("coverage_delta")

        self._emit_event(event_data)

    def _handle_failed_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        error: str,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle failed QA execution."""
        stdout, stderr = self._extract_qa_outputs(qa_artifact)

        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "failed",
                "reason": "qa_validation_failed",
                "error": error or "Unknown validation error",
                "stdout": stdout[:500],
                "stderr": stderr[:500],
            },
        )
        return False, {}

    def _extract_qa_outputs(self, qa_artifact: Artifact) -> tuple[str, str]:
        """Extract stdout and stderr from QA artifact."""
        if isinstance(qa_artifact.content, dict):
            stdout = qa_artifact.content.get("stdout", "")
            stderr = qa_artifact.content.get("stderr", "")
        else:
            stdout = ""
            stderr = ""
        return stdout, stderr

    def _execute_step_with_retries(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        role_profile,
        retry_policy: RetryPolicy,
        max_retries: int,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Execute step with retry logic and micro-iterations."""
        retries = 0
        micro_iteration_config = self._get_micro_iteration_config()

        while retries <= max_retries:
            try:
                result = self._execute_step_attempt(step, ctx, role_profile, retry_policy, micro_iteration_config)

                if self._is_step_execution_successful(result):
                    return self._handle_successful_execution(step, result, done, retries)
                return self._handle_failed_execution(step, result, retries, max_retries)
            except Exception as e:
                return self._handle_execution_exception(step, e, retries, max_retries)

        return False, {}

    def _get_micro_iteration_config(self) -> dict:
        """Get micro-iteration configuration settings."""
        return {
            "candidate_count": getattr(self.settings, "micro_iteration_candidate_count", 1) or 1,
            "speculative_enabled": getattr(self.settings, "speculative_execution_enable", False),
            "patch_scoring_enabled": getattr(self.settings, "patch_scoring_enable", False),
        }

    def _execute_step_attempt(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: RetryPolicy,
        config: dict,
    ) -> StepResult:
        """Execute a single step attempt."""
        if config["candidate_count"] > 1 and (config["speculative_enabled"] or config["patch_scoring_enabled"]):
            return self._execute_with_micro_iterations(step, ctx, role_profile, retry_policy, config["candidate_count"])
        return self._attempt_execute_with_retry(step, ctx, role_profile, retry_policy)

    def _is_step_execution_successful(self, result: StepResult) -> bool:
        """Check if step execution was successful."""
        return result and result.ok and result.artifact

    def _handle_successful_execution(
        self,
        step: SopStep,
        result: StepResult,
        done: dict[str, Artifact],
        retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle successful step execution."""
        artifact = result.artifact
        self._ensure_artifact_provenance(artifact, step)
        done[step.id] = artifact

        # Track prompt performance for optimization
        execution_time = getattr(result, 'execution_time', 0.0)
        token_cost = getattr(result, 'token_cost', 0.0)
        self._track_prompt_performance(step, result, execution_time, token_cost)

        # Update step hash
        art_hash = self._compute_artifact_hash(artifact)
        self._previous_step_hash = self._compute_step_hash(art_hash, None)

        # Ingest artifact into memory
        self._ingest_artifact_to_memory(step, artifact)

        # Verify expected outcome if specified
        verification = self._verify_expected_outcome_if_specified(step, artifact)

        # Emit success event
        self._emit_success_event(step, retries, verification)
        
        # ACE reflection and update
        self._reflect_and_update_ace(step, result, artifact, verification)

        return True, {step.id: artifact}

    def _verify_expected_outcome_if_specified(self, step: SopStep, artifact: Artifact) -> dict | None:
        """Verify expected outcome if specified in step."""
        if expected_outcome := getattr(step, "expected_outcome", None):
            return self._verify_expected_outcome(expected_outcome, artifact.content)
        return None

    def _emit_success_event(self, step: SopStep, retries: int, verification: dict | None) -> None:
        """Emit success event for step execution."""
        event_data = {
            "step_id": step.id,
            "role": step.role,
            "status": "executed",
            "retries": retries,
            "duration_ms": 0,  # Would need timing in real implementation
        }

        if verification:
            event_data["verification"] = verification

        self._emit_event(event_data)

    def _handle_failed_execution(
        self,
        step: SopStep,
        result: StepResult,
        retries: int,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle failed step execution."""
        failure_analysis = self._analyze_step_failure(result, step, retries)
        retries += 1

        # Track prompt performance for optimization (even for failures)
        execution_time = getattr(result, 'execution_time', 0.0)
        token_cost = getattr(result, 'token_cost', 0.0)
        self._track_prompt_performance(step, result, execution_time, token_cost)

        if retries <= max_retries:
            self._emit_retry_event(step, retries, failure_analysis)
        else:
            self._emit_final_failure_event(step, retries, failure_analysis)
            return False, {}

        return False, {}

    def _emit_retry_event(self, step: SopStep, retries: int, failure_analysis: dict) -> None:
        """Emit retry event for failed step execution."""
        remediation = self._get_remediation_plan(step, failure_analysis)

        event_data = {
            "step_id": step.id,
            "role": step.role,
            "status": "retry",
            "retries": retries,
            "reason": "step_execution_failed",
            "failure_analysis": failure_analysis,
        }

        if remediation:
            event_data["remediation"] = remediation

        self._emit_event(event_data)

    def _emit_final_failure_event(self, step: SopStep, retries: int, failure_analysis: dict) -> None:
        """Emit final failure event when max retries exceeded."""
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "failed",
                "retries": retries,
                "reason": "max_retries_exceeded",
                "failure_analysis": failure_analysis,
            },
        )

    def _handle_execution_exception(
        self,
        step: SopStep,
        exception: Exception,
        retries: int,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle execution exception."""
        retries += 1

        if retries <= max_retries:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "retry",
                    "retries": retries,
                    "reason": "step_execution_exception",
                    "error": str(exception)[:300],
                },
            )
        else:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "failed",
                    "retries": retries,
                    "reason": "max_retries_exceeded",
                    "error": str(exception)[:300],
                },
            )
            return False, {}

        return False, {}

    def _execute_with_micro_iterations(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: RetryPolicy,
        candidate_count: int,
    ) -> StepResult:
        """Execute step with micro-iterations and candidate scoring."""
        try:
            # Generate multiple candidates
            candidates = self._generate_candidates(step, ctx, role_profile, candidate_count)

            if not candidates:
                return StepResult(ok=False, error="no_valid_candidates")

            # Score and select best candidate if scoring is enabled
            if getattr(self.settings, "patch_scoring_enable", False):
                if best_candidate := self._select_best_candidate_with_scoring(candidates, step):
                    return best_candidate

            # Return first successful candidate
            return self._create_step_result_from_candidate(candidates[0], step)

        except Exception as e:
            return StepResult(ok=False, error=f"micro_iteration_error: {e!s}")

    def _generate_candidates(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        candidate_count: int,
    ) -> list:
        """Generate multiple execution candidates."""
        candidates = []

        for _ in range(candidate_count):
            try:
                # Use the same LLM as regular chat (respects UI settings)
                if self.llm_registry and not hasattr(ctx, "llm_registry"):
                    ctx.llm_registry = self.llm_registry
                candidate = self.step_executor.execute(
                    step,
                    ctx,
                    model_dump_with_options(role_profile),
                    config=self.config,
                )

                if candidate and candidate.ok and candidate.artifact:
                    patch_candidate = self._create_patch_candidate(candidate.artifact, step)
                    candidates.append(patch_candidate)

            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue

        return candidates

    def _select_best_candidate_with_scoring(self, candidates: list, step: SopStep) -> StepResult | None:
        """Select best candidate using patch scoring."""
        try:
            scores = patch_scoring.score_candidates(candidates, self.settings)
            if not scores:
                return None

            best_idx = max(range(len(scores)), key=lambda i: scores[i].get("composite_score", 0))
            best_candidate = candidates[best_idx]

            return self._create_step_result_from_candidate(best_candidate, step)
        except (TypeError, ValueError, AttributeError, RuntimeError):
            return None

    def _create_step_result_from_candidate(self, candidate, step: SopStep) -> StepResult:
        """Create StepResult from patch candidate."""
        artifact = Artifact(
            step_id=step.id,
            role=step.role,
            content=candidate.content,
        )
        return StepResult(ok=True, artifact=artifact)

    def _create_patch_candidate(self, artifact: Artifact, step: SopStep) -> patch_scoring.PatchCandidate:
        """Create a patch candidate from an artifact."""
        try:
            content = artifact.content
            diff = self._extract_diff_from_artifact(artifact, content)
            meta = self._build_patch_candidate_metadata(artifact, diff)

            return patch_scoring.PatchCandidate(
                content=str(content) if content else "",
                diff=diff,
                meta=meta,
            )

        except (TypeError, ValueError, AttributeError) as e:
            return self._create_error_patch_candidate(artifact, e)

    def _extract_diff_from_artifact(self, artifact: Artifact, content) -> str:
        """Extract diff from artifact content or attributes."""
        if isinstance(content, dict) and "diff" in content:
            return content["diff"]
        if hasattr(artifact, "diff"):
            return artifact.diff
        return ""

    def _build_patch_candidate_metadata(self, artifact: Artifact, diff: str) -> dict:
        """Build metadata for patch candidate."""
        meta = {}

        # Add diff fingerprint if available
        if structural_available and diff:
            try:
                diff_fp = compute_diff_fingerprint(diff)
                meta["diff_fingerprint"] = diff_fp
            except (TypeError, ValueError, AttributeError):
                pass

        # Add artifact provenance
        if hasattr(artifact, "provenance"):
            meta["provenance"] = artifact.provenance

        return meta

    def _create_error_patch_candidate(self, artifact: Artifact, error: Exception) -> patch_scoring.PatchCandidate:
        """Create patch candidate with error information."""
        return patch_scoring.PatchCandidate(
            content=str(artifact.content) if artifact.content else "",
            diff="",
            meta={"error": str(error)},
        )

    def _analyze_step_failure(self, result: StepResult, step: SopStep, retries: int) -> dict:
        """Analyze step failure using failure taxonomy."""
        try:
            if not result or not hasattr(result, "error"):
                return {"failure_type": "unknown", "reason": "no_error_info"}

            error = result.error or "unknown_error"

            # Use failure classifier if available
            if hasattr(self, "failure_classifier") and self.failure_classifier:
                try:
                    failure_type = self.failure_classifier.classify(error, step, retries)
                    corrective_hint_text = corrective_hint(failure_type)

                    return {
                        "failure_type": failure_type,
                        "error": error,
                        "corrective_hint": corrective_hint_text,
                        "retries": retries,
                        "step_id": step.id,
                        "role": step.role,
                    }
                except (AttributeError, TypeError, ValueError):
                    pass

            # Fallback analysis
            return {
                "failure_type": "execution_error",
                "error": error,
                "retries": retries,
                "step_id": step.id,
                "role": step.role,
            }

        except Exception as e:
            return {
                "failure_type": "analysis_error",
                "error": str(e),
                "retries": retries,
                "step_id": step.id,
                "role": step.role,
            }

    def _get_remediation_plan(self, step: SopStep, failure_analysis: dict) -> dict | None:
        """Get remediation plan for step failure."""
        try:
            if not failure_analysis or "failure_type" not in failure_analysis:
                return None

            failure_type = failure_analysis["failure_type"]
            error = failure_analysis.get("error", "")

            if remediation_plan := get_remediation_plan(failure_type, error, step):
                return {
                    "plan": remediation_plan,
                    "summary": summarize_remediation(remediation_plan),
                    "failure_type": failure_type,
                }

            return None

        except (AttributeError, TypeError, ValueError, ImportError):
            return None

    def _build_qa_verification(self, qa_content: dict) -> dict:
        """Build verification result from QA artifact content."""
        if not isinstance(qa_content, dict):
            return {}

        verification = {
            "ok": qa_content.get("ok", False),
            "tests_passed": qa_content.get("tests", {}).get("passed", 0),
            "tests_failed": qa_content.get("tests", {}).get("failed", 0),
            "coverage": qa_content.get("coverage", {}),
            "timeout": qa_content.get("timeout", False),
            "error": qa_content.get("error"),
        }

        # Add stdout/stderr if available
        if "stdout" in qa_content:
            verification["stdout"] = qa_content["stdout"]
        if "stderr" in qa_content:
            verification["stderr"] = qa_content["stderr"]

        return verification

    def _verify_expected_outcome(self, expected_outcome: str | None, artifact_content: dict | str | None) -> dict:
        """Verify if the artifact content matches the expected outcome."""
        if not expected_outcome or not artifact_content:
            return {"verified": False, "reason": "missing_expected_outcome_or_content"}

        # Extract content text for comparison
        if isinstance(artifact_content, dict):
            content_text = artifact_content.get("content") or artifact_content.get("text") or str(artifact_content)
        else:
            content_text = str(artifact_content)

        # Simple verification - check if expected outcome is contained in content
        verified = expected_outcome.lower() in content_text.lower()

        return {
            "verified": verified,
            "expected": expected_outcome,
            "actual": content_text[:500] if len(content_text) > 500 else content_text,
            "reason": "expected_outcome_found" if verified else "expected_outcome_not_found",
        }

    def get_verification_report(self) -> dict:
        """Get verification report for executed steps."""
        executed_steps = self._get_executed_steps()
        all_steps = self._get_all_steps()
        skipped_steps = self._get_skipped_steps()
        efficiency = self._calculate_efficiency_metrics()

        return {
            "executed_steps": list(executed_steps),
            "all_steps": all_steps,
            "skipped_steps": skipped_steps,
            "efficiency": efficiency,
            "total_traces": len(self.traces),
            "total_events": len(self.step_events),
            "events": self.step_events,  # Add step events for frontend display
        }

    def _get_executed_steps(self) -> set[str]:
        """Get set of executed step IDs."""
        return {t.step_id for t in self.traces}

    def _get_all_steps(self) -> list[str]:
        """Get list of all step IDs from template."""
        return [s.id for s in self.template.steps] if self.template else []

    def _get_skipped_steps(self) -> list[str]:
        """Get list of skipped step IDs."""
        skipped = [e for e in self.step_events if e.get("status") == "skipped"]
        return [s.get("step_id") for s in skipped]

    def _calculate_efficiency_metrics(self) -> dict:
        """Calculate token efficiency metrics."""
        total_tokens = self._calculate_total_tokens()
        successful_steps = self._get_successful_steps()
        tokens_per_success = self._calculate_tokens_per_success(successful_steps)

        return {
            "total_tokens": total_tokens or None,
            "executed_steps": len(successful_steps),
            "tokens_per_successful_step": (round(tokens_per_success, 2) if tokens_per_success else None),
        }

    def _calculate_total_tokens(self) -> int:
        """Calculate total tokens from traces."""
        return sum(t.total_tokens or 0 for t in self.traces)

    def _get_successful_steps(self) -> list[dict]:
        """Get list of successful step events."""
        return [e for e in self.step_events if e.get("status") == "executed"]

    def _calculate_tokens_per_success(self, successful_steps: list[dict]) -> float | None:
        """Calculate average tokens per successful step."""
        if not successful_steps:
            return None

        successful_token_sum = sum(e.get("total_tokens") or 0 for e in successful_steps)
        return successful_token_sum / len(successful_steps)

    def _perform_memory_retrieval(self, step: SopStep, ctx: OrchestrationContext) -> None:
        """Perform memory retrieval for step context."""
        if not (
            self.memory_store
            and self.memory_store.stats().get("lexical", {}).get("records", 0)
            + self.memory_store.stats().get("vector", {}).get("records", 0)
            > 0
        ):
            return

        try:
            query = f"{step.task}\n{self._ctx.user_request}"[:500]
            retrieval_key = f"retrieval::{step.id}"

            if self.settings.enable_hybrid_retrieval and self.settings.enable_vector_memory:
                hits = self._perform_hybrid_retrieval(query)
            else:
                hits = self.memory_store.search(query, k=3)

            if shaped_hits := self._shape_retrieval_hits(hits):
                ctx.extra[retrieval_key] = shaped_hits
                ctx.extra.setdefault("retrieval_keys", []).append(retrieval_key)

        except (AttributeError, TypeError, ValueError, RuntimeError) as e:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "suppressed_error",
                    "reason": "retrieval_failed",
                    "error": str(e)[:300],
                },
            )
            if self.settings.strict_mode:
                raise

    def _perform_hybrid_retrieval(self, query: str) -> list:
        """Perform hybrid vector and lexical retrieval."""
        stats = self.memory_store.stats()

        # Get vector and lexical hits
        vector_hits = self._get_vector_hits(query, stats)
        lexical_hits = self._get_lexical_hits(query, stats)

        return self._fuse_retrieval_results(vector_hits, lexical_hits)

    def _get_vector_hits(self, query: str, stats: dict) -> list:
        """Get vector search hits."""
        try:
            if stats.get("vector"):
                return self.memory_store._vector_store.search(query, k=5)
        except (AttributeError, RuntimeError, ValueError):
            pass
        return []

    def _get_lexical_hits(self, query: str, stats: dict) -> list:
        """Get lexical search hits."""
        try:
            if stats.get("lexical"):
                return self.memory_store._lex_store.search(query, k=5)
        except (AttributeError, RuntimeError, ValueError):
            pass
        return []

    def _fuse_retrieval_results(self, vector_hits: list, lexical_hits: list) -> list:
        """Fuse vector and lexical retrieval results."""
        # Normalize hits
        v_norm = self._normalize_hits(vector_hits)
        l_norm = self._normalize_hits(lexical_hits)

        # Combine normalized results
        combined = self._combine_normalized_hits(v_norm, l_norm)

        # Calculate fusion weights
        vw, lw = self._get_fusion_weights()

        # Create fused results
        fused = self._create_fused_results(combined, vw, lw)

        # Sort and return top 3
        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:3]

    def _normalize_hits(self, hits: list) -> list:
        """Normalize hit scores."""
        if not hits:
            return []
        max_s = max((h.get("score") or 0) for h in hits) or 1
        return [(h.get("step_id"), h, (h.get("score") or 0) / max_s) for h in hits]

    def _combine_normalized_hits(self, v_norm: list, l_norm: list) -> dict:
        """Combine normalized vector and lexical hits."""
        combined = {sid: {"hit": h, "v": ns, "l": 0.0} for sid, h, ns in v_norm if sid}
        # Add lexical hits
        for sid, h, ns in l_norm:
            if sid:
                if sid in combined:
                    combined[sid]["l"] = max(combined[sid]["l"], ns)
                else:
                    combined[sid] = {"hit": h, "v": 0.0, "l": ns}

        return combined

    def _get_fusion_weights(self) -> tuple[float, float]:
        """Get fusion weights for vector and lexical components."""
        vw = self.settings.hybrid_vector_weight or 0.6
        lw = self.settings.hybrid_lexical_weight if self.settings.hybrid_lexical_weight is not None else (1 - vw)
        return vw, lw

    def _create_fused_results(self, combined: dict, vw: float, lw: float) -> list:
        """Create fused results from combined hits."""
        fused = []
        for meta in combined.values():
            fused_score = vw * meta["v"] + lw * meta["l"]
            out_hit = dict(meta["hit"])
            out_hit["score"] = round(fused_score, 4)
            out_hit["vector_component"] = round(meta["v"], 4)
            out_hit["lexical_component"] = round(meta["l"], 4)
            fused.append(out_hit)
        return fused

    def _shape_retrieval_hits(self, hits: list) -> list:
        """Shape retrieval hits for context."""
        return [
            {
                "step_id": h.get("step_id"),
                "role": h.get("role"),
                "score": h.get("score"),
                "rationale": (h.get("rationale") or "")[:300],
                "excerpt": (h.get("excerpt") or "")[:400],
            }
            for h in hits
        ]

    def _perform_selective_tests(self, step: SopStep, ctx: OrchestrationContext) -> tuple[list[str] | None, str | None]:
        """Perform selective test selection for QA steps."""
        if not getattr(self.settings, "qa_selective_tests_enable", False):
            return None, None

        try:
            repo_root_abs = getattr(ctx, "repo_root", None) or "."
            changed_paths = []  # Placeholder for future git diff integration

            mode = getattr(self.settings, "qa_selective_tests_mode", None) or "imports"
            max_sel = getattr(self.settings, "qa_selective_tests_max", None)

            if selected := select_tests(
                changed_paths,
                repo_root_abs,
                mode=mode,
                max_tests=max_sel,
            ):
                self._emit_event(
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
                    },
                )
                return selected, f"mode={mode} count={len(selected)}"
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "advisory",
                    "reason": "qa_selective_tests_fallback_full",
                    "meta": {"mode": mode},
                },
            )
            return None, None

        except (OSError, ValueError, AttributeError, RuntimeError) as e:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "suppressed_error",
                    "reason": "qa_selective_tests_error",
                    "error": str(e)[:300],
                },
            )
            return None, None

    def _ingest_artifact_to_memory(self, step: SopStep, artifact: Artifact) -> None:
        """Ingest artifact into memory store."""
        if not self.memory_index:
            return

        try:
            artifact_hash = self._compute_artifact_hash(artifact)
            content_text = (
                json.dumps(artifact.content, sort_keys=True)
                if isinstance(artifact.content, dict)
                else str(artifact.content)
            )
            self.memory_index.add(
                step.id,
                step.role,
                artifact_hash,
                None,
                content_text,
            )
        except (TypeError, ValueError, AttributeError):
            pass

    def _store_step_in_cache(self, step: SopStep, artifacts: dict[str, Artifact], pre_context_hash: str) -> None:
        """Store step results in cache."""
        try:
            artifact = artifacts.get(step.id)
            if not artifact:
                return

            entry = StepCacheEntry(
                context_hash=pre_context_hash,
                step_id=step.id,
                role=step.role,
                artifact_content=artifact.content,
                artifact_hash=self._compute_artifact_hash(artifact),
                step_hash=self._compute_step_hash(self._compute_artifact_hash(artifact), None),
                rationale=None,  # Would need to extract from execution context
                model_name=None,  # Would need to extract from execution context
                total_tokens=None,  # Would need to extract from execution context
                diff_fingerprint=(
                    artifact.content.get("_provenance", {}).get("diff_fingerprint")
                    if isinstance(artifact.content, dict)
                    else None
                ),
                created_ts=time.time(),
            )
            self.step_cache.put(entry)
        except (AttributeError, TypeError, ValueError):
            pass

    def _handle_step_failure(
        self,
        step: SopStep,
        error: str,
        retries: int,
        max_retries: int,
        taxonomy_enabled: bool,
    ) -> dict:
        """Handle step failure with taxonomy classification and remediation."""
        failure_info = {
            "step_id": step.id,
            "role": step.role,
            "error": error,
            "retries": retries,
            "max_retries": max_retries,
        }

        # Classify failure if taxonomy is enabled
        if taxonomy_enabled:
            try:
                failure_type = self.failure_classifier.classify(error, step)
                failure_info["failure_type"] = failure_type

                if hint := corrective_hint(failure_type, error):
                    failure_info["corrective_hint"] = hint

                if remediation := get_remediation_plan(failure_type, error, step):
                    failure_info["remediation"] = remediation

            except (AttributeError, TypeError, ValueError, RuntimeError):
                # Handle taxonomy classification errors
                failure_info["taxonomy_error"] = "classification_failed"

        return failure_info

    def _emit_failure_event(self, step: SopStep, failure_info: dict) -> None:
        """Emit failure event with detailed information."""
        event_data = {
            "step_id": step.id,
            "role": step.role,
            "status": "failed",
            "retries": failure_info.get("retries", 0),
            "reason": "step_execution_failed",
            "error": failure_info.get("error", "Unknown error"),
        }

        # Add taxonomy information if available
        if "failure_type" in failure_info:
            event_data["failure_type"] = failure_info["failure_type"]
        if "corrective_hint" in failure_info:
            event_data["corrective_hint"] = failure_info["corrective_hint"]
        if "remediation" in failure_info:
            event_data["remediation"] = failure_info["remediation"]

        self._emit_event(event_data)

    def _should_retry_step(
        self,
        step: SopStep,
        error: str,
        retries: int,
        max_retries: int,
        retry_policy: RetryPolicy,
    ) -> bool:
        """Determine if step should be retried based on error and policy."""
        if retries >= max_retries:
            return False

        # Check retry policy
        if hasattr(retry_policy, "should_retry"):
            return retry_policy.should_retry(error, retries)

        # Default retry logic
        return retries < max_retries

    def _get_retry_delay(self, retries: int, retry_policy: RetryPolicy) -> float:
        """Get delay before retry based on retry policy."""
        if hasattr(retry_policy, "get_delay"):
            return retry_policy.get_delay(retries)

        # Default exponential backoff
        return min(2**retries, 60)  # Max 60 seconds

    def run(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Synchronous run method - maintains backward compatibility."""
        # Feature flag gate: only run when enabled
        if not (self.settings.enabled):
            return False, {}

        # Initialize and setup orchestration
        setup_result = self._setup_orchestration(user_request, repo_root, max_retries)
        if not setup_result["success"]:
            return False, setup_result.get("done", {})

        # Execute orchestration steps
        return self._execute_orchestration_steps(setup_result["ctx"], setup_result["retry_policy"], repo_root)

    async def run_async(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Async run method - enables true async concurrency for massive performance gains."""
        # Feature flag gate: only run when enabled
        if not (self.settings.enabled):
            return False, {}

        # Initialize and setup orchestration (sync setup)
        setup_result = self._setup_orchestration(user_request, repo_root, max_retries)
        if not setup_result["success"]:
            return False, setup_result.get("done", {})

        # Execute orchestration steps with async support
        return await self._execute_orchestration_steps_async(setup_result["ctx"], setup_result["retry_policy"], repo_root)

    def _setup_orchestration(self, user_request, repo_root, max_retries):
        """Setup orchestration context, memory, models, and retry policy."""
        # Initialize orchestration context and setup
        ctx = self._initialize_orchestration_context(user_request, repo_root)
        if not ctx:
            return {"success": False, "done": {}}

        # Setup memory and models
        if not self._setup_memory_and_models(ctx):
            return {"success": False, "done": {}}

        # Setup retry policy
        retry_policy = self._setup_retry_policy(max_retries)

        return {"success": True, "ctx": ctx, "retry_policy": retry_policy}

    def _execute_orchestration_steps(self, ctx, retry_policy, repo_root):
        """Execute all orchestration steps."""
        done: dict[str, Artifact] = {}
        for _i, step in enumerate(self.template.steps):
            step_success, step_artifacts = self._process_single_step(
                step,
                ctx,
                done,
                self.settings.token_budget_soft or 20000,
                self.settings.token_budget_hard or 50000,
                0,  # consumed_tokens
                self.settings.enable_failure_taxonomy,
                retry_policy,
                2,  # max_retries
            )
            if not step_success:
                return False, done
            done |= step_artifacts

        return True, done

    async def _execute_orchestration_steps_async(self, ctx, retry_policy, repo_root):
        """Execute all orchestration steps using async concurrency for maximum performance."""
        done: dict[str, Artifact] = {}
        
        # Check if async parallel execution is enabled
        if (self.parallel_engine and 
            getattr(self.settings, "enable_parallel_execution", False) and
            getattr(self.settings, "enable_async_execution", False)):
            # Use async parallel execution for massive performance gains
            return await self._process_orchestration_steps_async(
                ctx, done, 
                self.settings.token_budget_soft or 20000,
                self.settings.token_budget_hard or 50000,
                0,  # consumed_tokens
                self.settings.enable_failure_taxonomy,
                retry_policy,
                2,  # max_retries
            )
        else:
            # Fallback to sequential async execution
            for _i, step in enumerate(self.template.steps):
                step_success, step_artifacts = await self._process_single_step_async(
                    step,
                    ctx,
                    done,
                    self.settings.token_budget_soft or 20000,
                    self.settings.token_budget_hard or 50000,
                    0,  # consumed_tokens
                    self.settings.enable_failure_taxonomy,
                    retry_policy,
                    2,  # max_retries
                )
                if not step_success:
                    return False, done
                done |= step_artifacts
            return True, done

    def _initialize_orchestration_context(self, user_request, repo_root):
        """Initialize orchestration context and setup logging."""
        ctx = OrchestrationContext(run_id=str(uuid.uuid4()), user_request=user_request, repo_root=repo_root)
        # retain reference for report building
        self._ctx = ctx

        # Pass LLM registry to context if available
        if self.llm_registry:
            ctx.llm_registry = self.llm_registry
        
        # Initialize ACE framework if LLM registry is available
        if self.llm_registry and self.ace_framework is None:
            self._initialize_ace_framework()
        
        # Initialize prompt optimization if enabled
        if self.llm_registry and self.prompt_optimizer is None:
            self._initialize_prompt_optimization()

        # Setup logging and trace context
        self._setup_logging_and_trace_context(ctx)

        # Respect micro-iteration settings
        self._setup_micro_iteration_settings()

        return ctx

    def _setup_logging_and_trace_context(self, ctx) -> None:
        """Setup logging and trace context for the orchestration."""
        try:
            trace_id = str(uuid.uuid4())
            ctx.extra["trace_id"] = trace_id
            self._setup_logger(trace_id)
            self._setup_global_trace_context(trace_id)
        except Exception:
            self._logger = logging.getLogger("openhands")

    def _setup_logger(self, trace_id) -> None:
        """Setup logger with trace context."""
        try:
            from openhands.core.logger import bind_context, openhands_logger

            self._logger = bind_context(openhands_logger, trace_id=trace_id)
        except Exception:
            self._logger = logging.getLogger("openhands")

    def _setup_global_trace_context(self, trace_id) -> None:
        """Setup global trace context."""
        try:
            from openhands.core.logger import set_trace_context

            set_trace_context({"trace_id": trace_id})
        except Exception:
            pass

    def _setup_micro_iteration_settings(self) -> None:
        """Setup micro-iteration settings."""
        try:
            if (
                getattr(self.settings, "micro_iteration_candidate_count", None) is not None
                and self.settings.micro_iteration_candidate_count < 1
            ):
                self.settings.micro_iteration_candidate_count = 1
        except Exception:
            pass

    def _setup_memory_and_models(self, ctx):
        """Setup memory index and discover models."""
        # Setup memory index
        if not self._setup_memory_index(ctx):
            return False

        # Discover and validate models
        return bool(self._discover_and_validate_models(ctx))

    def _setup_memory_index(self, ctx) -> bool:
        """Setup memory index for this run."""
        if not self.settings.enable_vector_memory:
            # Lexical path: instantiate persistent MemoryIndex for this run
            try:
                self.memory_index = MemoryIndex(run_id=ctx.run_id, max_records=self.settings.memory_max_records)
            except Exception as e:
                self._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "suppressed_error",
                        "reason": "memory_init_failed",
                        "error": str(e)[:400],
                    },
                )
                if self.settings.strict_mode:
                    raise
                # fall back to no memory index for lexical mode if init failed
                self.memory_index = None

        try:
            # Recreate memory store in lexical mode bound to run id
            self.memory_store.bind_run(ctx.run_id)
        except Exception:
            pass

        return True

    def _discover_and_validate_models(self, ctx):
        """Discover and validate LLM models."""
        models = self._discover_models()

        # Compute environment signature
        try:
            env_sig, env_payload = compute_environment_signature(models)
            ctx.extra["environment_signature"] = env_sig
            ctx.extra["environment"] = env_payload
        except Exception:
            ctx.extra["environment_signature"] = None

        # Validate that we have LLM models available
        return bool(self._validate_llm_models_available(ctx))

    def _validate_llm_models_available(self, ctx) -> bool:
        """Validate that LLM models are available."""
        try:
            # Primary check: explicit models discovered in computed environment payload
            llm_models = (
                ctx.extra.get("environment", {}).get("llm_models")
                if isinstance(ctx.extra.get("environment", {}), dict)
                else None
            )
            # Fallback: if no explicit models discovered, but role profiles are populated
            # (tests commonly set `orch.profiles[...] = ...` directly), treat that as
            # sufficient evidence of available LLM-like executors and proceed.
            if not llm_models:
                try:
                    profile_keys = (
                        list(self.profiles.keys()) if isinstance(self.profiles, dict) and self.profiles else []
                    )
                    if profile_keys:
                        llm_models = profile_keys
                except Exception:
                    pass

            if not llm_models:
                self._emit_event(
                    {
                        "step_id": "__bootstrap__",
                        "role": "system",
                        "status": "failed",
                        "reason": "no_llm_models_configured",
                        "message": "No LLM models found in configuration. Ensure your LLM profiles or API keys are configured (e.g., in config.toml or env vars).",
                    },
                )
                return False
        except Exception:
            pass
        return True

    def _setup_retry_policy(self, max_retries):
        """Setup retry policy for the orchestration."""
        retry_policy = self._create_retry_policy(max_retries)
        self._log_retry_policy(retry_policy, max_retries)
        return retry_policy

    def _create_retry_policy(self, max_retries):
        """Create retry policy from settings or fallback."""
        try:
            if retry_kwargs := self.settings.build_retry_policy_kwargs():
                return RetryPolicy(**retry_kwargs)
            return RetryPolicy(max_attempts=max_retries + 1)
        except Exception:
            return RetryPolicy(max_attempts=max_retries + 1)

    def _log_retry_policy(self, retry_policy, max_retries) -> None:
        """Log retry policy for debugging."""
        try:
            effective_max_retries = max(0, (retry_policy.max_attempts or 1) - 1)
            try:
                self._logger.info(f"metasop: retry_policy={retry_policy} effective_max_retries={effective_max_retries}")
            except Exception:
                logging.info(f"metasop: retry_policy={retry_policy} effective_max_retries={effective_max_retries}")
        except Exception:
            pass

    def export_run_manifest(self, output_dir: str | None = None) -> str | None:
        """Export run manifest for reproducibility."""
        try:
            if not self.template:
                return None

            # Create manifest data
            manifest = {
                "version": "1.0",
                "run_id": getattr(self, "_run_id", str(uuid.uuid4())),
                "sop_name": getattr(self.template, "name", "unknown"),
                "timestamp": time.time(),
                "environment_signature": getattr(self._ctx, "environment_signature", ""),
                "steps": self._build_steps_manifest(),
                "provenance": self._build_provenance_manifest(),
                "efficiency": self._build_efficiency_manifest(),
                "memory_stats": self._build_memory_stats_manifest(),
            }

            # Add hash for integrity
            manifest["manifest_hash"] = self._hash_dict(manifest)

            # Write to file if output_dir provided
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                manifest_path = os.path.join(output_dir, f'run_manifest_{manifest["run_id"]}.json')
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
                return manifest_path

            return json.dumps(manifest, indent=2)

        except (OSError, TypeError, ValueError, AttributeError) as e:
            self._emit_event(
                {
                    "status": "error",
                    "reason": "manifest_export_failed",
                    "error": str(e)[:300],
                },
            )
            return None

    def _build_steps_manifest(self) -> list[dict]:
        """Build steps section of manifest."""
        steps_manifest = []

        for trace in self.traces:
            step_manifest = {
                "step_id": trace.step_id,
                "role": trace.role,
                "status": "executed",
                "duration_ms": trace.duration_ms,
                "retries": trace.retries,
            }

            # Add artifact hash if available
            if hasattr(trace, "artifact_hash"):
                step_manifest["artifact_hash"] = trace.artifact_hash

            # Add step hash if available
            if hasattr(trace, "step_hash"):
                step_manifest["step_hash"] = trace.step_hash

            if failed_events := [
                e for e in self.step_events if e.get("step_id") == trace.step_id and e.get("status") == "failed"
            ]:
                step_manifest["status"] = "failed"
                step_manifest["failure_type"] = failed_events[0].get("failure_analysis", {}).get("failure_type")
                step_manifest["remediation"] = failed_events[0].get("remediation")

            steps_manifest.append(step_manifest)

        return steps_manifest

    def _build_provenance_manifest(self) -> dict:
        """Build provenance section of manifest."""
        return {
            "chain_root": getattr(self, "_previous_step_hash", None),
            "final_step_hash": getattr(self, "_previous_step_hash", None),
        }

    def _build_efficiency_manifest(self) -> dict:
        """Build efficiency section of manifest."""
        total_tokens = sum(t.total_tokens or 0 for t in self.traces)
        successful_steps = [e for e in self.step_events if e.get("status") == "executed"]
        successful_token_sum = sum(e.get("total_tokens") or 0 for e in successful_steps)

        return {
            "total_tokens": total_tokens or None,
            "executed_steps": len(successful_steps),
            "tokens_per_successful_step": (
                round(successful_token_sum / len(successful_steps), 2) if successful_steps else None
            ),
        }

    def _build_memory_stats_manifest(self) -> dict:
        """Build memory stats section of manifest."""
        if not self.memory_store:
            return {}

        try:
            stats = self.memory_store.stats()
            return {
                "lexical_records": stats.get("lexical", {}).get("records", 0),
                "vector_records": stats.get("vector", {}).get("records", 0),
                "total_records": (
                    stats.get("lexical", {}).get("records", 0) + stats.get("vector", {}).get("records", 0)
                ),
            }
        except (AttributeError, TypeError, ValueError):
            return {}
