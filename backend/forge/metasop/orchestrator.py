"""Core MetaSOP orchestrator coordinating step execution, caching, and telemetry."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import time
import uuid
from logging import Logger, LoggerAdapter
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Union,
)

from forge.core.logger import forge_logger as logger
from forge.core.pydantic_compat import model_dump_with_options
from forge.structural import available as structural_available

from . import patch_scoring
from .bootstrap import OrchestratorBootstrap
from .cache import StepCache, StepCacheEntry
from .context_hash import compute_context_hash
from .diff_utils import compute_diff_fingerprint
from .env_signature import compute_environment_signature
from .events import EventEmitter
from .core import (
    CausalSafetyAdapter,
    FailureHandler,
    ProfileManager,
    ReportingToolkit,
    RuntimeAdapter,
    RunSetupManager,
    TemplateToolkit,
)
from .core.artifacts import (
    build_qa_verification,
    extract_qa_outputs,
    verify_expected_outcome_if_specified,
    verify_expected_outcome,
)
from .core.context import OrchestrationContextManager
from .core.execution import ExecutionCoordinator
from .core.execution_steps import StepExecutionManager
from .core.engines import OptionalEnginesFacade
from .core.memory_cache import MemoryCacheManager
from .event_emitter import MetaSOPEventEmitter
from .event_service import MetaSOPEVentService
from .budget_monitor_service import BudgetMonitorService, BudgetStatus
from .step_execution_service import StepExecutionService
from .candidate_service import CandidateGenerationService
from .qa_service import QAStepService
from .retry_service import StepRetryService
from .guardrail_service import GuardrailService
from .memory import MemoryIndex
from .models import (
    Artifact,
    OrchestrationContext,
    RetryPolicy,
    SopStep,
    StepResult,
    StepTrace,
    SopTemplate,
)
from .settings import MetaSOPSettings
from .registry import load_schema
from .strategies import (
    BaseFailureClassifier,
    BaseQAExecutor,
    BaseStepExecutor,
    DefaultFailureClassifier,
    DefaultQAExecutor,
    DefaultStepExecutor,
    TimeoutQAExecutor,
    TimeoutStepExecutor,
    VectorOrLexicalMemoryStore,
)
from .validators import validate_json
from .qa_service import QAStepService
from .telemetry import (
    emit_event,
    initialize_metrics_server,
    setup_logging_and_tracing,
)

if TYPE_CHECKING:
    import threading

    from forge.core.config import ForgeConfig
    from forge.llm.llm_registry import LLMRegistry
    from .ace.ace_framework import ACEFramework
    from .ace.context_playbook import ContextPlaybook
    from .causal_reasoning import CausalReasoningEngine, ConflictPrediction
    from .parallel_execution import ParallelExecutionEngine
    from .predictive_execution import PredictiveExecutionPlanner
    from .collaborative_streaming import ContextAwareStreamingEngine
    from .learning_storage import LearningStorage


class MetaSOPOrchestrator:
    """High-level coordinator that executes MetaSOP steps and manages retries."""

    def __init__(self, sop_name: str, config: ForgeConfig | None = None) -> None:
        """Initialize orchestrator defaults so run() can execute.

        Tests and tools construct with (sop_name, config). We hydrate
        sensible defaults here while allowing callers to override
        components (step_executor, qa_executor, memory_store, etc.).
        """
        self.config: ForgeConfig | None = config
        self.settings: MetaSOPSettings = MetaSOPSettings()
        self.template: SopTemplate | None = None
        self.profiles: dict[str, Any] | None = None
        self.step_executor: BaseStepExecutor = DefaultStepExecutor()
        self.qa_executor: BaseQAExecutor = DefaultQAExecutor()
        self.failure_classifier: BaseFailureClassifier = DefaultFailureClassifier()
        self.llm_registry: Optional["LLMRegistry"] = (
            None  # Will be set by router if available
        )
        self.step_event_callback: Optional[Callable[[str, str, str, int], None]] = (
            None  # Callback for real-time step events
        )
        self.ace_framework: Optional["ACEFramework"] = (
            None  # ACE framework for self-improving agents
        )
        self.prompt_optimizer: Optional[dict[str, Any]] = (
            None  # Dynamic prompt optimization system
        )
        self.causal_engine: Optional["CausalReasoningEngine"] = (
            None  # Causal reasoning engine for conflict prediction
        )
        self.parallel_engine: Optional["ParallelExecutionEngine"] = (
            None  # Parallel execution engine for intelligent step scheduling
        )
        self.predictive_planner: Optional["PredictiveExecutionPlanner"] = (
            None  # Predictive execution planner for optimization
        )
        self.collaborative_streaming: Optional["ContextAwareStreamingEngine"] = (
            None  # Context-aware collaborative streaming engine
        )
        self.memory_cache: Any = None
        self.optional_engines: Any = None
        self.profile_manager: Any = None
        self.run_setup: Any = None
        self.runtime_adapter: Any = None
        self.template_toolkit: Any = None
        self.context_manager: Any = None
        self.memory_index: Any = None
        self.memory_store: Any = None
        self.step_cache: Any = None
        self.schema: dict[str, Any] | None = None
        self._previous_step_hash: str | None = None
        self.step_execution_service: Any = None
        self.candidate_service: Any = None
        self.qa_service: Any = None
        self.retry_service: Any = None
        self.event_service: Any = None
        self.step_execution: Any = None
        self.execution_coordinator: Any = None
        self.reporting: Any = None
        self.causal_safety: Any = None

        # Learning and feedback tracking
        self.active_steps: Dict[str, SopStep] = {}  # Track currently executing steps
        self.learning_storage: Optional["LearningStorage"] = (
            None  # Persistent learning storage
        )

        # Event/reporting helpers used across modules
        self._emitter: Any = None
        self.step_events: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []
        self._ctx: Optional[OrchestrationContext] = None
        self._logger: Logger | LoggerAdapter = logger
        self.failure_handler: Optional[FailureHandler] = None

        # Initialize core components via bootstrap helper
        self.bootstrap = OrchestratorBootstrap(self)
        self.bootstrap.initialize(sop_name, config)
        self.event_service = MetaSOPEVentService(self.runtime_adapter)
        self.budget_monitor = BudgetMonitorService(
            self.event_service,
            default_soft_limit=getattr(self.settings, "token_budget_soft", 0) or 0,
            default_hard_limit=getattr(self.settings, "token_budget_hard", 0) or 0,
        )
        self._budget_halt_requested = False
        self.guardrails = GuardrailService(self)
        self.step_execution_service = StepExecutionService(self)
        self.candidate_service = CandidateGenerationService(self)
        self.qa_service = QAStepService(self)
        self.retry_service = StepRetryService(self)
        self._initialize_learning_storage()
        self._initialize_causal_engine()
        self.causal_safety = CausalSafetyAdapter(self)
        self._initialize_parallel_engine()
        self._initialize_predictive_planner()
        self._initialize_collaborative_streaming()
        self._check_agent_tool_persistence()

        # Coordinators / helpers
        self.step_execution = StepExecutionManager(self)
        self.execution_coordinator = ExecutionCoordinator(self)
        self.reporting = ReportingToolkit(self)

    def _hash_dict(self, data: dict) -> str:
        """Compute deterministic SHA256 hash of a dictionary for caching and comparison.

        Args:
            data: Dictionary to hash, must be JSON-serializable

        Returns:
            str: SHA256 hex digest of JSON-serialized and sorted dictionary

        Side Effects:
            None - Pure function with no state changes

        Notes:
            - Uses JSON serialization with sorted keys for determinism across runs
            - Falls back to repr() if dictionary contains non-JSON-serializable objects
            - Ensures consistent hashing for context-based step caching and deduplication

        Example:
            >>> orch = MetaSOPOrchestrator("my_sop")
            >>> hash1 = orch._hash_dict({"step": "1", "role": "coder"})
            >>> hash2 = orch._hash_dict({"role": "coder", "step": "1"})
            >>> hash1 == hash2  # Order doesn't matter due to sorted_keys
            True

        """
        try:
            encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        except (TypeError, ValueError):
            # Handle JSON serialization errors (non-serializable objects, encoding issues)
            encoded = repr(data).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    # ------------------------------------------------------------------ #
    # Event emission helpers
    # ------------------------------------------------------------------ #
    def set_event_emitter(self, emitter: MetaSOPEventEmitter | None) -> None:
        """Attach a MetaSOPEventEmitter used to emit structured status events."""
        self._emitter = emitter
        self.event_service.set_event_emitter(emitter)


    def _initialize_settings(self, config: ForgeConfig | None) -> None:
        """Initialize settings from config with fallback to defaults.

        Attempts to extract MetaSOP settings from the provided ForgeConfig object.
        Handles missing, malformed, or inaccessible configuration gracefully by
        falling back to default MetaSOPSettings.

        Args:
            config: Optional ForgeConfig containing extended.metasop settings, or None

        Side Effects:
            - Sets self.settings to MetaSOPSettings instance
            - Calls _validate_micro_iteration_settings() to ensure valid state

        Raises:
            None - All exceptions are caught and defaults are used

        Example:
            >>> from forge.core.config import ForgeConfig
            >>> orch = MetaSOPOrchestrator("basic_sop")
            >>> isinstance(orch.settings, MetaSOPSettings)
            True

        """
        try:
            raw = (
                getattr(getattr(config, "extended", None), "metasop", None)
                if config
                else None
            )
            self.settings = MetaSOPSettings.from_raw(raw)
        except (AttributeError, TypeError, ValueError):
            self.settings = MetaSOPSettings()

        # Ensure micro-iteration candidate count is at least 1
        self._validate_micro_iteration_settings()

    def _validate_micro_iteration_settings(self) -> None:
        """Validate and fix micro-iteration settings for safety.

        Enforces that micro_iteration_candidate_count is at least 1 to prevent
        zero-candidate edge cases during orchestration. This is a defensive
        validation step to ensure orchestrator can always iterate.

        Side Effects:
            - Modifies self.settings.micro_iteration_candidate_count if < 1

        Raises:
            None - All exceptions are caught and passed silently

        Note:
            This is called during __init__ to ensure valid orchestrator state.
            Micro-iterations with 0 candidates would cause orchestration to fail.

        """
        try:
            candidate_count = getattr(
                self.settings, "micro_iteration_candidate_count", None
            )
            if candidate_count is not None and candidate_count < 1:
                self.settings.micro_iteration_candidate_count = 1
        except (AttributeError, TypeError):
            pass

    def _get_failure_handler(self) -> FailureHandler:
        """Return the failure handler, creating or syncing it on demand."""
        return self.runtime_adapter.get_failure_handler()

    def _initialize_ace_framework(self) -> None:
        """Initialize ACE framework if enabled."""
        self.optional_engines.initialize_ace_framework()

    def _initialize_prompt_optimization(self) -> None:
        """Initialize prompt optimization system if enabled."""
        self.optional_engines.initialize_prompt_optimization()

    def _initialize_causal_engine(self) -> None:
        """Initialize causal reasoning engine if enabled."""
        self.optional_engines.initialize_causal_engine()

    def _initialize_parallel_engine(self) -> None:
        """Initialize parallel execution engine if enabled."""
        self.optional_engines.initialize_parallel_engine()

    def _initialize_predictive_planner(self) -> None:
        """Initialize predictive execution planner if enabled."""
        self.optional_engines.initialize_predictive_planner()

    def _initialize_collaborative_streaming(self) -> None:
        """Initialize context-aware collaborative streaming engine if enabled."""
        self.optional_engines.initialize_collaborative_streaming()

    def _initialize_learning_storage(self) -> None:
        """Initialize learning storage system if enabled."""
        self.optional_engines.initialize_learning_storage()

    def _apply_prompt_optimization(self, step: SopStep, role_profile) -> dict:
        """Apply prompt optimization to role profile if enabled."""
        return self.optional_engines.apply_prompt_optimization(step, role_profile)

    def _track_prompt_performance(
        self,
        step: SopStep,
        result: StepResult,
        execution_time: float,
        token_cost: float = 0.0,
    ):
        """Track prompt performance for optimization."""
        self.optional_engines.track_prompt_performance(
            step, result, execution_time, token_cost
        )

    def _handle_budget_status(self, status: BudgetStatus, step: SopStep) -> None:
        """React to budget monitor status updates."""
        if status == BudgetStatus.HARD_LIMIT:
            self._budget_halt_requested = True
            self._emit_event(
                {
                    "type": "budget_monitor_halt",
                    "step_id": step.id,
                    "role": step.role,
                    "consumed_tokens": self.budget_monitor.consumed_tokens,
                    "hard_limit": self.budget_monitor.hard_limit or None,
                }
            )
    def _reflect_and_update_ace(
        self,
        step: SopStep,
        result: StepResult,
        artifact: Artifact,
        verification: dict | None,
    ) -> None:
        """Reflect on step execution and update ACE playbook."""
        self.context_manager.reflect_and_update_ace(step, result, artifact, verification)

    def _save_ace_playbook(self) -> None:
        """Save ACE playbook to disk."""
        self.optional_engines.save_ace_playbook()


    def set_step_event_callback(self, callback) -> None:
        """Set callback function for real-time step events."""
        self.runtime_adapter.set_step_event_callback(callback)

    def _collect_causal_feedback(
        self,
        step: SopStep,
        success: bool,
        artifacts: dict[str, Artifact],
        active_steps_at_time: list[SopStep],
    ) -> None:
        """Collect feedback for causal reasoning engine.

        Args:
            step: Step that was executed
            success: Whether execution succeeded
            artifacts: Artifacts produced
            active_steps_at_time: Active steps during execution

        """
        self.optional_engines.collect_causal_feedback(
            step, success, artifacts, active_steps_at_time
        )

    def _save_causal_patterns(self) -> None:
        """Save causal patterns to storage."""
        self.optional_engines.save_causal_patterns()

    def _collect_execution_feedback(
        self,
        step: SopStep,
        success: bool,
        artifacts: dict[str, Artifact],
        active_steps_at_time: list[SopStep],
    ) -> None:
        """Collect execution feedback for learning and optimization."""
        self.optional_engines.collect_execution_feedback(
            step, success, artifacts, active_steps_at_time
        )

    def _check_agent_tool_persistence(self) -> None:
        """Check for agent tool persistent state and emit advisory if found."""
        self.optional_engines.check_agent_tool_persistence()

    def _emit_event(self, event: dict[str, Any]) -> None:
        """Emit orchestration event via telemetry helper."""
        self.event_service.emit_event(event)

    def _handle_stuck_thread(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        worker: threading.Thread,
        timeout_seconds: float,
    ) -> None:
        """Best-effort handling for worker threads that remain alive after a timeout."""
        self.runtime_adapter.handle_stuck_thread(step, ctx, worker, timeout_seconds)

    def _capture_thread_stacks(self) -> dict:
        """Capture thread stack frames."""
        return self.runtime_adapter.capture_thread_stacks()

    def _truncate_stacks(self, stacks: dict) -> dict:
        """Truncate large stack traces."""
        return self.runtime_adapter.truncate_stacks(stacks)

    def _emit_stuck_thread_event(
        self,
        step: SopStep,
        timeout_seconds: float,
        worker: threading.Thread,
        stacks: dict,
    ) -> None:
        """Emit stuck thread event."""
        self.event_service.emit_stuck_thread_event(
            step, timeout_seconds, worker, stacks
        )

    def _handle_stuck_thread_error(self, error: Exception) -> None:
        """Handle errors in stuck thread handling."""
        self.event_service.handle_stuck_thread_error(error)

    def _compute_artifact_hash(self, artifact: Artifact | None) -> str | None:
        """Compute deterministic hash of artifact content for provenance tracking.

        Args:
            artifact: Artifact to hash, or None

        Returns:
            str: SHA256 hash of artifact (step_id + role + content) or None if artifact is None

        Side Effects:
            None - Pure function

        Notes:
            - Uses _hash_dict internally for deterministic JSON-based hashing
            - Used in caching to detect re-execution of identical steps
            - Part of step provenance chain for artifact lineage tracking

        Example:
            >>> artifact = Artifact(step_id="step1", role="coder", content="fixed bug")
            >>> hash_val = orch._compute_artifact_hash(artifact)
            >>> type(hash_val)
            <class 'str'>

        """
        if not artifact:
            return None
        base = {
            "step_id": artifact.step_id,
            "role": artifact.role,
            "content": artifact.content,
        }
        return self._hash_dict(base)

    def _compute_step_hash(
        self, artifact_hash: str | None, rationale: str | None
    ) -> str:
        """Compute hash of step's position in execution sequence.

        Args:
            artifact_hash: Hash of step's output artifact (from _compute_artifact_hash)
            rationale: Step's rationale/explanation text

        Returns:
            str: SHA256 hash incorporating previous step hash, current artifact hash, and rationale

        Side Effects:
            Reads self._previous_step_hash to include sequence context

        Notes:
            - Creates a chain hash linking current step to previous step
            - Enables detection of execution plan divergence
            - Part of MetaSOP's deterministic orchestration tracking

        Example:
            >>> art_hash = orch._compute_artifact_hash(artifact)
            >>> step_hash = orch._compute_step_hash(art_hash, "Implemented feature")
            >>> # step_hash now includes lineage information

        """
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

    def _compute_diff_fingerprint_safe(
        self, artifact: Artifact, prev_text: str | None
    ) -> str | None:
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

    def _compute_unified_diff_safe(self, prev_text: str | None, new_text: str) -> str:
        """Safely compute unified diff between previous and new text."""
        if not (
            isinstance(prev_text, str)
            and isinstance(new_text, str)
            and prev_text != new_text
        ):
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

    def _compute_fingerprint_from_diff_or_text(
        self, unified: str, new_text: str
    ) -> str | None:
        """Compute fingerprint from diff or fallback to text hash."""
        try:
            # Try diff fingerprint first
            if unified and unified.strip():
                return compute_diff_fingerprint(unified)

            # Fallback to text hash
            return hashlib.sha256((new_text or "").encode("utf-8")).hexdigest()[:16]
        except (TypeError, ValueError, AttributeError):
            return None

    def _attach_provenance_to_artifact(
        self, artifact: Artifact, art_hash: str | None, fp: str | None
    ) -> None:
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

    def _log_execution_attempt(
        self, step: SopStep, attempt: int, attempts: int
    ) -> None:
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

    def _execute_single_attempt(
        self, step: SopStep, ctx: OrchestrationContext, role_profile
    ) -> StepResult:
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

    def _record_successful_attempt(
        self, step: SopStep, ctx: OrchestrationContext, attempt: int
    ) -> None:
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

    def _compute_retry_delay(
        self, retry_policy: RetryPolicy | None, attempt: int
    ) -> float:
        """Compute retry delay from policy."""
        try:
            return retry_policy.compute_sleep(attempt) if retry_policy else 0
        except (AttributeError, TypeError, ValueError):
            return 0

    def _log_retry_attempt(self, step: SopStep, attempt: int, delay: float) -> None:
        """Log retry attempt with error handling."""
        try:
            self._logger.info(
                f"metasop: retrying step_id={step.id} after failure attempt={attempt} delay={delay}"
            )
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(
                    f"metasop: retrying step_id={step.id} after failure attempt={attempt} delay={delay}"
                )


    def _setup_logging_and_tracing(self, ctx: OrchestrationContext) -> None:
        """Setup logging and tracing for the orchestration run."""
        # Generate and bind a trace_id for this orchestration run for correlation
        try:
            trace_id = str(uuid.uuid4())
            ctx.extra["trace_id"] = trace_id
            try:
                from forge.core.logger import (
                    bind_context,
                    FORGE_logger,
                )

                self._logger = bind_context(FORGE_logger, trace_id=trace_id)
            except (AttributeError, RuntimeError, ImportError):
                # Handle logger binding errors
                self._logger = logging.getLogger("forge")
            try:
                # Also set global trace context for the TraceContextFilter to pick up
                from forge.core.logger import set_trace_context, get_trace_context

                existing = get_trace_context()
                existing.update({"trace_id": trace_id})
                set_trace_context(existing)
            except (ImportError, AttributeError, RuntimeError):
                pass

            # Bridge thread-local trace_id into an OpenTelemetry span (conversation.run)
            if os.getenv(
                "OTEL_INSTRUMENT_ORCHESTRATION", os.getenv("OTEL_ENABLED", "false")
            ).lower() in ("true", "1", "yes"):
                try:
                    from opentelemetry import trace as _otel_trace  # type: ignore
                    from opentelemetry.trace import SpanKind as _SpanKind  # type: ignore

                    tracer = _otel_trace.get_tracer("forge.orchestration")
                    span = tracer.start_span(
                        name="conversation.run", kind=_SpanKind.INTERNAL
                    )
                    # Set attributes for correlation
                    span.set_attribute("forge.trace_id", trace_id)
                    if hasattr(ctx, "run_id"):
                        span.set_attribute(
                            "conversation.run_id", getattr(ctx, "run_id")
                        )
                    if hasattr(ctx, "conversation_id"):
                        span.set_attribute(
                            "conversation.id", getattr(ctx, "conversation_id", "")
                        )
                    # Store span in context for later child operations (best-effort)
                    ctx.extra["_otel_root_span"] = span
                except Exception:
                    pass
        except (AttributeError, RuntimeError):
            # Handle logger initialization errors
            self._logger = logging.getLogger("forge")

    def _initialize_memory(self, ctx: OrchestrationContext) -> None:
        """Initialize memory index and bind memory store for the run."""
        self.run_setup.initialize_memory(ctx)

    def _discover_models(self) -> list[str]:
        """Discover available LLM models from configuration."""
        return self.run_setup.discover_models()

    def _extract_models_from_config(self) -> list[str]:
        """Extract models from configuration."""
        return self.run_setup.extract_models_from_config()

    def _extract_models_from_llms_map(self, llms_map: dict) -> list[str]:
        """Extract models from llms configuration map."""
        return self.run_setup.extract_models_from_llms_map(llms_map)

    def _extract_model_names_from_configs(self, configs) -> list[str]:
        """Extract model names from configuration objects."""
        return self.run_setup.extract_model_names_from_configs(configs)

    def _extract_models_from_legacy_config(self) -> list[str]:
        """Extract models from legacy configuration format."""
        return self.run_setup.extract_models_from_legacy_config()

    def _handle_model_discovery_error(self, error: Exception) -> None:
        """Handle model discovery errors."""
        self.run_setup.handle_model_discovery_error(error)

    def _setup_environment_and_validate_models(
        self, models: list[str], ctx: OrchestrationContext
    ) -> bool:
        """Setup environment signature and validate available LLM models, returning False if invalid."""
        return self.run_setup.setup_environment_and_validate_models(models, ctx)

    def _setup_budgets_retry_and_taxonomy(
        self,
        max_retries: int,
    ) -> tuple[dict[str, Artifact], int, int, int, bool, RetryPolicy, int]:
        """Setup token budgets, retry policy, and taxonomy flag."""
        done: dict[str, Artifact] = {}
        soft_budget = int(getattr(self.settings, "token_budget_soft", 0) or 0)
        hard_budget = int(getattr(self.settings, "token_budget_hard", 0) or 0)
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
                self._logger.info(
                    f"metasop: retry_policy={retry_policy} effective_max_retries={max_retries}"
                )
            except (AttributeError, RuntimeError):
                # Handle logger access errors
                logging.info(
                    f"metasop: retry_policy={retry_policy} effective_max_retries={max_retries}"
                )
        except (AttributeError, RuntimeError):
            # Handle fallback logging errors
            pass
        taxonomy_enabled = self.settings.enable_failure_taxonomy

        self.budget_monitor.configure_run(soft_budget, hard_budget)
        self._budget_halt_requested = False

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
    ) -> tuple[bool, OrchestrationContext | None, dict[str, Any]]:
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
            candidate_count = getattr(
                self.settings, "micro_iteration_candidate_count", None
            )
            if isinstance(candidate_count, int) and candidate_count < 1:
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

        setup_data: dict[str, Any] = {
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
        done: dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Process all orchestration steps with intelligent parallel execution."""
        return self.template_toolkit.process_orchestration_steps(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

    def _process_steps_parallel(
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
        """Process orchestration steps using intelligent parallel execution."""
        return self.template_toolkit.process_steps_parallel(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

    def _process_steps_sequential(
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
        """Process orchestration steps sequentially (original implementation)."""
        return self.template_toolkit.process_steps_sequential(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

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
        """Process all orchestration steps with true async parallel execution."""
        return await self.template_toolkit.process_orchestration_steps_async(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
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
        return await self.template_toolkit.process_steps_sequential_async(
            ctx,
            done,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

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

        if self._budget_halt_requested:
            logger.warning(
                "Budget hard limit already reached; skipping step %s", step.id
            )
            return False, {}

        # Perform memory retrieval for context
        self._perform_memory_retrieval(step, ctx)

        role_profile = self.profile_manager.resolve_role_profile(step)
        if role_profile is not None:
            # Add to active tracking before execution
            self._add_active_step(step)

            success = False
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
                self._remove_active_step(step.id, success=success)
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

        if self._budget_halt_requested:
            logger.warning(
                "Budget hard limit already reached; skipping step %s", step.id
            )
            return False, {}

        # Perform memory retrieval for context
        if hasattr(self, "_perform_memory_retrieval_async"):
            await self._perform_memory_retrieval_async(step, ctx)
        else:
            self._perform_memory_retrieval(step, ctx)

        role_profile = self.profile_manager.resolve_role_profile(step)
        if role_profile is not None:
            # Add to active tracking before execution
            self._add_active_step(step)

            success = False
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
                self._remove_active_step(step.id, success=success)
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
        if hasattr(self, "_execute_step_with_retry"):
            return await loop.run_in_executor(
                None,
                self._execute_step_with_retry,
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
        else:
            # Fallback: simulate execution (this needs to be connected to actual execution later)
            logger.warning(
                f"Async execution fallback for step {step.id} - sync method not found"
            )
            return True, {}

    def _log_step_entry(self, step: SopStep) -> None:
        """Log step entry with error handling."""
        self.context_manager.log_step_entry(step)

    def _check_capability_matrix(
        self, step: SopStep, done: dict[str, Artifact]
    ) -> bool:
        """Check capability matrix requirements."""
        return self.profile_manager.check_capability_matrix(step, done)

    def _check_dependencies_and_conditions(
        self, step: SopStep, done: dict[str, Artifact]
    ) -> bool:
        """Check step dependencies and conditions."""
        if not self.context_manager.check_dependencies_and_conditions(step, done):
            return False

        # Check causal safety if enabled
        if self.causal_engine:
            try:
                can_proceed = self.causal_safety.check_causal_safety(step, done)
                if not can_proceed:
                    return False
            except Exception as e:
                self._logger.warning(
                    f"Causal reasoning check failed: {e}, proceeding with original logic"
                )

        self._logger.info("Step %s passed dependency and condition checks", step.id)
        return True

    def _run_causal_analysis(
        self,
        step: SopStep,
        done: dict[str, Artifact],
    ) -> tuple[bool, list["ConflictPrediction"]]:
        """(Legacy) Delegate to causal safety adapter."""
        return self.causal_safety.run_causal_analysis(step, done)

    def _handle_blocking_predictions(self, step: SopStep, predictions: list) -> None:
        """(Legacy) Delegate to causal safety adapter."""
        self.causal_safety.handle_blocking_predictions(step, predictions)

    def _handle_warning_predictions(self, step: SopStep, predictions: list) -> None:
        """(Legacy) Delegate to causal safety adapter."""
        self.causal_safety.handle_warning_predictions(step, predictions)

    def _check_causal_safety(self, step: SopStep, done: dict[str, Artifact]) -> bool:
        """(Legacy) Delegate to causal safety adapter."""
        return self.causal_safety.check_causal_safety(step, done)

    def _get_currently_active_steps(self) -> list[SopStep]:
        """Get list of currently executing steps."""
        return list(self.active_steps.values())

    def _add_active_step(self, step: SopStep) -> None:
        """Add step to active tracking."""
        self.guardrails.on_step_start(step)

    def _remove_active_step(
        self, step_id: str, *, success: bool | None = None
    ) -> None:
        """Remove step from active tracking."""
        self.guardrails.on_step_complete(step_id, success=success)

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
        if pre_context_hash:
            if cached_result := self.memory_cache.check_step_cache(step, pre_context_hash):
                return True, cached_result

        # Handle QA role specially
        if step.role.strip().lower() == "qa":
            return self.qa_service.run(step, ctx, done, pre_context_hash)

        # Execute step with retry logic
        success, artifacts = self.step_execution_service.execute_with_retries(
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
        return self.memory_cache.compute_pre_context_hash(step, ctx, done)

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
                return self._handle_successful_qa_execution(
                    step, qa_artifact, done, validation_result["data"]
                )
            return self._handle_failed_qa_execution(
                step, qa_artifact, validation_result["error"]
            )

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
        return (
            isinstance(qa_artifact.content, dict)
            and qa_artifact.content.get("timeout") is True
        )

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
            "verification_result": build_qa_verification(qa_artifact.content),
        }

        # Add coverage data if available
        if isinstance(qa_artifact.content, dict):
            if qa_artifact.content.get("coverage"):
                event_data["coverage_overall"] = qa_artifact.content.get(
                    "coverage", {}
                ).get("overall_percent")
            if qa_artifact.content.get("coverage_delta"):
                event_data["coverage_delta_files"] = qa_artifact.content.get(
                    "coverage_delta"
                )

        self._emit_event(event_data)

    def _handle_failed_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        error: str,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle failed QA execution."""
        stdout, stderr = extract_qa_outputs(qa_artifact)

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

    def _get_micro_iteration_config(self) -> dict:
        """Get micro-iteration configuration settings."""
        return {
            "candidate_count": getattr(
                self.settings, "micro_iteration_candidate_count", 1
            )
            or 1,
            "speculative_enabled": getattr(
                self.settings, "speculative_execution_enable", False
            ),
            "patch_scoring_enabled": getattr(
                self.settings, "patch_scoring_enable", False
            ),
        }

    def _is_step_execution_successful(self, result: StepResult) -> bool:
        """Check if step execution was successful."""
        return bool(result and result.ok and result.artifact is not None)

    def _handle_successful_execution(
        self,
        step: SopStep,
        result: StepResult,
        done: dict[str, Artifact],
        retries: int,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Handle successful step execution."""
        artifact = result.artifact
        if artifact is None:
            return False, {}
        self._ensure_artifact_provenance(artifact, step)
        done[step.id] = artifact

        # Track prompt performance for optimization
        execution_time = getattr(result, "execution_time", 0.0)
        token_cost = getattr(result, "token_cost", 0.0)
        self._track_prompt_performance(step, result, execution_time, token_cost)

        # Update step hash
        art_hash = self._compute_artifact_hash(artifact)
        self._previous_step_hash = self._compute_step_hash(art_hash, None)

        # Ingest artifact into memory
        self._ingest_artifact_to_memory(step, artifact)

        # Verify expected outcome if specified
        verification = verify_expected_outcome_if_specified(step, artifact)

        # Emit success event
        self._emit_success_event(step, retries, verification)

        # ACE reflection and update
        self._reflect_and_update_ace(step, result, artifact, verification)

        return True, {step.id: artifact}

    def _emit_success_event(
        self, step: SopStep, retries: int, verification: dict | None
    ) -> None:
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
            candidates = self._generate_candidates(
                step, ctx, role_profile, candidate_count
            )

            if not candidates:
                return StepResult(ok=False, error="no_valid_candidates")

            # Score and select best candidate if scoring is enabled
            if getattr(self.settings, "patch_scoring_enable", False):
                if best_candidate := self._select_best_candidate_with_scoring(
                    candidates, step
                ):
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
                    patch_candidate = self._create_patch_candidate(
                        candidate.artifact, step
                    )
                    candidates.append(patch_candidate)

            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue

        return candidates

    def _select_best_candidate_with_scoring(
        self, candidates: list, step: SopStep
    ) -> StepResult | None:
        """Select best candidate using patch scoring."""
        try:
            scores = patch_scoring.score_candidates(candidates, self.settings)
            if not scores:
                return None

            best_idx = max(range(len(scores)), key=lambda i: scores[i].composite)
            best_candidate = candidates[best_idx]

            return self._create_step_result_from_candidate(best_candidate, step)
        except (TypeError, ValueError, AttributeError, RuntimeError):
            return None

    def _create_step_result_from_candidate(
        self, candidate, step: SopStep
    ) -> StepResult:
        """Create StepResult from patch candidate."""
        artifact = Artifact(
            step_id=step.id,
            role=step.role,
            content=candidate.content,
        )
        return StepResult(ok=True, artifact=artifact)

    def _create_patch_candidate(
        self, artifact: Artifact, step: SopStep
    ) -> patch_scoring.PatchCandidate:
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
        if structural_available() and diff:
            try:
                diff_fp = compute_diff_fingerprint(diff)
                meta["diff_fingerprint"] = diff_fp
            except (TypeError, ValueError, AttributeError):
                pass

        # Add artifact provenance
        if hasattr(artifact, "provenance"):
            meta["provenance"] = artifact.provenance

        return meta

    def _create_error_patch_candidate(
        self, artifact: Artifact, error: Exception
    ) -> patch_scoring.PatchCandidate:
        """Create patch candidate with error information."""
        return patch_scoring.PatchCandidate(
            content=str(artifact.content) if artifact.content else "",
            diff="",
            meta={"error": str(error)},
        )

    def _build_qa_verification(self, qa_content: Mapping[str, Any] | None) -> dict:
        """Build verification result from QA artifact content."""
        return build_qa_verification(qa_content)

    def _verify_expected_outcome(
        self, expected_outcome: str | None, artifact_content: dict | str | None
    ) -> dict:
        """Verify if the artifact content matches the expected outcome."""
        return verify_expected_outcome(expected_outcome, artifact_content)

    def get_verification_report(self) -> dict:
        """Get verification report for executed steps."""
        return self.reporting.get_verification_report()

    def _perform_memory_retrieval(
        self, step: SopStep, ctx: OrchestrationContext
    ) -> None:
        """Perform memory retrieval for step context."""
        memory_store = getattr(self, "memory_store", None)
        if memory_store is None:
            return

        stats = memory_store.stats()
        lexical_records = stats.get("lexical", {}).get("records", 0)
        vector_records = stats.get("vector", {}).get("records", 0)
        if lexical_records + vector_records <= 0:
            return

        try:
            ctx_request = self._ctx.user_request if self._ctx else ""
            query = f"{step.task}\n{ctx_request}"[:500]
            retrieval_key = f"retrieval::{step.id}"

            hits = []
            if hasattr(memory_store, "search"):
                if (
                    self.settings.enable_hybrid_retrieval
                    and self.settings.enable_vector_memory
                ):
                    hits = self._perform_hybrid_retrieval(query)
                else:
                    hits = memory_store.search(query, k=3)

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
        memory_store = getattr(self, "memory_store", None)
        if memory_store is None:
            return []

        stats = memory_store.stats()

        # Get vector and lexical hits
        vector_hits = self._get_vector_hits(memory_store, query, stats)
        lexical_hits = self._get_lexical_hits(memory_store, query, stats)

        return self._fuse_retrieval_results(vector_hits, lexical_hits)

    def _get_vector_hits(
        self, store: VectorOrLexicalMemoryStore, query: str, stats: dict
    ) -> list:
        """Get vector search hits."""
        try:
            if stats.get("vector"):
                vector_store = getattr(store, "_vector_store", None)
                if vector_store:
                    return vector_store.search(query, k=5)
        except (AttributeError, RuntimeError, ValueError):
            pass
        return []

    def _get_lexical_hits(
        self, store: VectorOrLexicalMemoryStore, query: str, stats: dict
    ) -> list:
        """Get lexical search hits."""
        try:
            if stats.get("lexical"):
                lex_store = getattr(store, "_lex_store", None)
                if lex_store:
                    return lex_store.search(query, k=5)
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
        lw = (
            self.settings.hybrid_lexical_weight
            if self.settings.hybrid_lexical_weight is not None
            else (1 - vw)
        )
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

    def _perform_selective_tests(
        self, step: SopStep, ctx: OrchestrationContext
    ) -> tuple[list[str] | None, str | None]:
        """Perform selective test selection for QA steps."""
        return self.memory_cache.perform_selective_tests(step, ctx)

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

    def _store_step_in_cache(
        self, step: SopStep, artifacts: dict[str, Artifact], pre_context_hash: str
    ) -> None:
        """Store step results in cache."""
        try:
            artifact = artifacts.get(step.id)
            if not artifact:
                return

            cache = self.step_cache
            if cache is None:
                return

            entry = StepCacheEntry(
                context_hash=pre_context_hash,
                step_id=step.id,
                role=step.role,
                artifact_content=artifact.content,
                artifact_hash=self._compute_artifact_hash(artifact),
                step_hash=self._compute_step_hash(
                    self._compute_artifact_hash(artifact), None
                ),
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
            cache.put(entry)
        except (AttributeError, TypeError, ValueError):
            pass

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
        return self.execution_coordinator.run(user_request, repo_root, max_retries)

    async def run_async(
        self,
        user_request: str,
        repo_root: str | None = None,
        max_retries: int = 2,
    ) -> tuple[bool, dict[str, Artifact]]:
        """Async run method - enables true async concurrency for massive performance gains."""
        return await self.execution_coordinator.run_async(
            user_request, repo_root, max_retries
        )

    def _setup_orchestration(self, user_request, repo_root, max_retries):
        """(Legacy) Delegate to the execution coordinator."""
        return self.execution_coordinator._setup_orchestration(
            user_request, repo_root, max_retries
        )

    def _execute_orchestration_steps(self, ctx, retry_policy, repo_root):
        """(Legacy) Delegate to the execution coordinator."""
        return self.execution_coordinator._execute_orchestration_steps(
            ctx, retry_policy, repo_root
        )

    async def _execute_orchestration_steps_async(self, ctx, retry_policy, repo_root):
        """(Legacy) Delegate to the execution coordinator."""
        return await self.execution_coordinator._execute_orchestration_steps_async(
            ctx, retry_policy, repo_root
        )

    def _initialize_orchestration_context(self, user_request, repo_root):
        """Initialize orchestration context and setup logging."""
        return self.context_manager.initialize_orchestration_context(user_request, repo_root)

    def _setup_logging_and_trace_context(self, ctx) -> None:
        """Setup logging and trace context for the orchestration."""
        self.context_manager.setup_logging_and_trace_context(ctx)

    def _setup_micro_iteration_settings(self) -> None:
        """Setup micro-iteration settings."""
        self.context_manager.setup_micro_iteration_settings()

    def _setup_memory_and_models(self, ctx):
        """Setup memory index and discover models."""
        return self.run_setup.setup_memory_and_models(ctx)

    def _setup_memory_index(self, ctx) -> bool:
        """Setup memory index for this run."""
        return self.run_setup.setup_memory_index(ctx)

    def _discover_and_validate_models(self, ctx):
        """Discover and validate LLM models."""
        return self.run_setup.discover_and_validate_models(ctx)

    def _validate_llm_models_available(self, ctx) -> bool:
        """Validate that LLM models are available."""
        return self.run_setup.validate_llm_models_available(ctx)

    def _setup_retry_policy(self, max_retries):
        """Setup retry policy for the orchestration."""
        return self.context_manager.setup_retry_policy(max_retries)

    def export_run_manifest(self, output_dir: str | None = None) -> str | None:
        """Export run manifest for reproducibility."""
        return self.reporting.export_run_manifest(output_dir)


def create_metasop_runner(
    *,
    template_name: str = "feature_delivery_full",
    emit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> MetaSOPOrchestrator:
    """Create a MetaSOPOrchestrator with optional event emission support."""
    orchestrator = MetaSOPOrchestrator(template_name)
    if emit_callback:
        orchestrator.set_event_emitter(MetaSOPEventEmitter(emit_callback))
    return orchestrator


async def run_metasop_orchestration(
    user_request: str,
    *,
    template_name: str = "feature_delivery_full",
    repo_root: str | None = None,
    max_retries: int = 2,
    emit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run MetaSOP orchestration with a canonical entry point."""
    orchestrator = create_metasop_runner(
        template_name=template_name, emit_callback=emit_callback
    )
    success, artifacts = await orchestrator.run_async(
        user_request=user_request,
        repo_root=repo_root,
        max_retries=max_retries,
    )
    return {
        "success": success,
        "artifacts": artifacts,
        "template": template_name,
        "steps_executed": len(artifacts),
    }
