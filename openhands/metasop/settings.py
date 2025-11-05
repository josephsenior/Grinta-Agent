"""Typed configuration schema for MetaSOP extension.

This introduces a Pydantic model that validates and normalizes the
`[metasop]` section found in `config.toml` (ingested presently as a raw
dictionary under `config.extended.metasop`).  The orchestrator will
hydrate one instance early and fall back gracefully when invalid.

Backward compatibility: all fields are optional and defaults preserve
previous behaviour. Additional / unknown keys are ignored (so that
future expansion in the raw TOML does not break older code).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RetrySettings(BaseModel):
    """Retry policy sub-structure.

    Mirrors (a subset of) the existing `RetryPolicy` model but is kept
    separate so the user config remains decoupled from runtime policy
    evolution. The orchestrator will translate this into a `RetryPolicy`
    instance. All values are optional; absence defers to legacy defaults.
    """

    max_attempts: int | None = Field(default=None, ge=1, description="Total attempts including the first execution")
    initial_delay: float | None = Field(default=0.5, ge=0, description="Initial backoff delay in seconds")
    backoff_factor: float | None = Field(default=1.5, ge=1.0, description="Multiplicative backoff factor")
    max_delay: float | None = Field(default=30.0, ge=0, description="Upper bound for any computed delay")

    @field_validator("max_attempts")
    @classmethod
    def _cap_attempts(cls, v: int | None) -> int | None:
        return 10 if v is not None and v > 10 else v

    __test__ = False


class MetaSOPSettings(BaseModel):
    enabled: bool = Field(default=False, description="Master feature flag gate for MetaSOP orchestration")
    default_sop: str | None = Field(
        default="feature_delivery",
        description="Default SOP template when not provided explicitly",
    )
    token_budget_soft: int | None = Field(default=None, ge=1)
    token_budget_hard: int | None = Field(default=None, ge=1)
    enable_failure_taxonomy: bool = Field(default=True, description="Toggle failure taxonomy enrichment events")
    log_events_jsonl: bool = Field(default=False, description="Emit raw event stream to ~/.openhands/runs as JSONL")
    retry: RetrySettings | None = Field(default=None, description="Structured retry settings")
    strict_mode: bool = Field(
        default=False,
        description="If true, unexpected internal exceptions propagate instead of being suppressed",
    )
    step_timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Global per-step wall clock timeout in seconds (non-QA)",
    )
    qa_timeout_seconds: int | None = Field(default=None, ge=1, description="Timeout for QA step execution in seconds")
    enable_vector_memory: bool = Field(
        default=False,
        description="Use vector semantic memory store (hash embeddings) instead of lexical TF-IDF",
    )
    vector_embedding_dim: int | None = Field(
        default=256,
        ge=32,
        le=2048,
        description="Dimension for hash-based embedding when vector memory enabled",
    )
    memory_max_records: int | None = Field(
        default=500,
        ge=10,
        description="Cap on number of memory records retained in-process (FIFO eviction)",
    )
    metrics_prometheus_port: int | None = Field(
        default=None,
        ge=1024,
        le=65535,
        description="If set, start a lightweight Prometheus /metrics server on this port",
    )
    enable_hybrid_retrieval: bool = Field(
        default=False,
        description="Fuse vector + lexical scores when both memory modes available",
    )
    enforce_capability_matrix: bool = Field(
        default=False,
        description="If true, roles must declare capabilities to run restricted steps",
    )
    hybrid_vector_weight: float | None = Field(
        default=0.6,
        ge=0,
        le=1,
        description="Weight of vector score in hybrid fusion (lexical weight = 1 - this unless hybrid_lexical_weight set)",
    )
    hybrid_lexical_weight: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional explicit lexical weight; if None uses 1 - hybrid_vector_weight",
    )
    enable_self_remediation: bool = Field(
        default=False,
        description="Attempt one automatic remediation run after retries exhausted using failure taxonomy & remediation plan",
    )
    enable_context_hash: bool = Field(
        default=True,
        description="Compute deterministic context hash for each step attempt (enables future caching & replay stability checks)",
    )
    context_hash_truncate_artifact_bytes: int = Field(
        default=4096,
        ge=256,
        description="Max bytes of each artifact content snippet included in context hash material",
    )
    enable_micro_iterations: bool = Field(
        default=False,
        description="Enable micro-iteration refinement loop inside implementation steps (engineer role)",
    )
    micro_iteration_max_loops: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Maximum micro-iteration cycles per eligible step",
    )
    micro_iteration_no_change_limit: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Stop after this many consecutive no-diff iterations",
    )
    enable_step_cache: bool = Field(default=True, description="Enable context-hash based step execution caching")
    step_cache_max_entries: int | None = Field(default=256, ge=1, description="Max cached step results (LRU eviction)")
    step_cache_dir: str | None = Field(
        default=None,
        description="Optional directory for persistent cache entries (if unset, in-memory only)",
    )
    step_cache_exclude_roles: list[str] | None = Field(
        default=None,
        description="Roles excluded from caching (e.g., ['qa'])",
    )
    step_cache_allow_stale_seconds: int | None = Field(
        default=None,
        ge=1,
        description="TTL in seconds for cache entries (None = no expiry)",
    )
    step_cache_min_tokens_saved: int | None = Field(
        default=None,
        ge=1,
        description="Only cache steps whose total_tokens >= this threshold if set",
    )
    qa_selective_tests_enable: bool = Field(
        default=False,
        description="Enable selective test execution to narrow pytest scope",
    )
    qa_selective_tests_mode: str | None = Field(
        default="imports",
        description="Selection mode: imports|changed|hybrid (future extensions)",
    )
    qa_selective_tests_max: int | None = Field(
        default=None,
        ge=1,
        description="Hard cap on number of tests to run when selection enabled",
    )
    micro_iteration_candidate_count: int | None = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of candidate patches to generate before scoring ( >1 enables scoring phase )",
    )
    patch_scoring_enable: bool = Field(
        default=True,
        description="Enable patch scoring when multiple candidates generated",
    )
    patch_score_weight_complexity: float | None = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Weight of (inverse) cyclomatic complexity in composite score",
    )
    patch_score_weight_lint: float | None = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Weight of lint cleanliness (fewer issues higher score)",
    )
    patch_score_weight_diffsize: float | None = Field(
        default=0.2,
        ge=0,
        le=1,
        description="Weight of smaller diff size (smaller is better)",
    )
    patch_score_weight_length: float | None = Field(
        default=0.2,
        ge=0,
        le=1,
        description="Weight of shorter content length (acts as heuristic for minimal change)",
    )
    patch_score_normalize: bool = Field(
        default=True,
        description="Normalize individual feature scores before weighting",
    )
    adaptive_micro_iteration: bool = Field(
        default=True,
        description="Enable heuristic gating to avoid unnecessary micro-iteration expansion",
    )
    micro_iteration_accept_score_threshold: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="If best candidate composite score >= this, skip further micro-iterations",
    )
    speculative_execution_enable: bool = Field(
        default=False,
        description="Execute multiple candidate generation calls in parallel and short-circuit on the first valid result",
    )
    speculative_candidate_count: int | None = Field(
        default=2,
        ge=1,
        le=8,
        description="Number of speculative parallel candidate generations to run when speculative_execution_enable is true",
    )
    speculative_timeout_seconds: int | None = Field(
        default=20,
        ge=1,
        description="Per-candidate speculative generation timeout in seconds",
    )
    
    # ACE Framework Settings
    enable_ace: bool = Field(
        default=False,
        description="Enable ACE (Agentic Context Engineering) framework for self-improving agents"
    )
    ace_max_bullets: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of bullets in ACE context playbook"
    )
    ace_multi_epoch: bool = Field(
        default=True,
        description="Enable multi-epoch training for ACE framework"
    )
    ace_num_epochs: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of training epochs for ACE multi-epoch training"
    )
    ace_reflector_max_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of reflection refinement iterations"
    )
    ace_playbook_persistence_path: str | None = Field(
        default=None,
        description="Path for saving ACE playbooks (if None, uses default location)"
    )
    ace_enable_online_adaptation: bool = Field(
        default=True,
        description="Enable test-time learning for ACE framework"
    )
    ace_min_helpfulness_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum helpfulness score for bullet retrieval"
    )
    ace_max_playbook_content_length: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of bullets in playbook content for LLM"
    )
    ace_enable_grow_and_refine: bool = Field(
        default=True,
        description="Enable grow-and-refine mechanism for playbook maintenance"
    )
    ace_cleanup_interval_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days between playbook cleanup cycles"
    )
    ace_redundancy_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for redundancy detection"
    )
    ace_auto_save_playbook: bool = Field(
        default=True,
        description="Automatically save playbook after each update"
    )
    ace_playbook_save_interval: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of updates between automatic playbook saves"
    )

    # Dynamic Prompt Optimization Settings
    enable_prompt_optimization: bool = Field(
        default=False,
        description="Enable Dynamic Prompt Optimization for self-improving prompts"
    )
    prompt_opt_ab_split: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="A/B testing split ratio (0.8 = 80% best, 20% experiments)"
    )
    prompt_opt_min_samples: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Minimum samples required before switching variants"
    )
    prompt_opt_confidence_threshold: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Confidence threshold for statistical significance testing"
    )
    prompt_opt_success_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for success rate in composite scoring"
    )
    prompt_opt_time_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for execution time in composite scoring"
    )
    prompt_opt_error_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for error rate in composite scoring"
    )
    prompt_opt_cost_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for token cost in composite scoring"
    )
    prompt_opt_enable_evolution: bool = Field(
        default=True,
        description="Enable LLM-powered prompt evolution"
    )
    prompt_opt_evolution_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Composite score threshold below which prompts are evolved"
    )
    prompt_opt_max_variants_per_prompt: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of variants per prompt"
    )
    prompt_opt_storage_path: str = Field(
        default="~/.openhands/prompt_optimization/",
        description="Storage path for prompt optimization data"
    )
    prompt_opt_sync_interval: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of updates between storage syncs"
    )
    prompt_opt_auto_save: bool = Field(
        default=True,
        description="Automatically save optimization data"
    )

    # Causal Reasoning Settings
    enable_causal_reasoning: bool = Field(
        default=False,
        description="Enable causal reasoning for conflict prediction and prevention"
    )
    causal_confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for causal conflict detection"
    )
    causal_max_analysis_time_ms: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum time allowed for causal analysis per step in milliseconds"
    )

    # Parallel Execution Settings
    enable_parallel_execution: bool = Field(
        default=False,
        description="Enable intelligent parallel execution of independent steps"
    )
    max_parallel_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of parallel worker threads for step execution"
    )
    parallel_dependency_analysis: bool = Field(
        default=True,
        description="Enable dependency-aware parallel grouping"
    )
    parallel_lock_management: bool = Field(
        default=True,
        description="Enable intelligent lock management for parallel execution"
    )

    # Async Execution Settings
    enable_async_execution: bool = Field(
        default=False,
        description="Enable true async/await execution for massive performance gains with async parallel execution"
    )
    async_max_concurrent_steps: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of steps that can run concurrently in async mode"
    )

    # Learning and Feedback Settings
    enable_learning: bool = Field(
        default=True,
        description="Enable learning from execution feedback and persistent pattern storage"
    )
    learning_persistence_path: str = Field(
        default="~/.openhands/learning/",
        description="Path for storing learned patterns and performance data"
    )
    learning_min_samples: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Minimum number of executions before applying learned patterns"
    )
    learning_confidence_decay: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        description="Decay factor for old patterns over time"
    )

    # Predictive Execution Planning Settings
    enable_predictive_planning: bool = Field(
        default=False,
        description="Enable predictive execution planning for intelligent pre-execution optimization"
    )
    predictive_max_planning_time_ms: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum time allowed for predictive planning in milliseconds"
    )
    predictive_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for accepting predictive execution plans"
    )
    predictive_learn_from_execution: bool = Field(
        default=True,
        description="Enable learning from actual execution results to improve future predictions"
    )

    # Context-Aware Collaborative Streaming Settings
    enable_collaborative_streaming: bool = Field(
        default=False,
        description="Enable context-aware collaborative streaming between agents with partial context protection"
    )
    streaming_context_completeness_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum context completeness threshold for safe agent consumption of streamed data"
    )
    streaming_semantic_consistency_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum semantic consistency threshold for preventing contradictory information"
    )
    streaming_enable_real_time_collaboration: bool = Field(
        default=True,
        description="Enable real-time agent collaboration through validated streaming"
    )

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> MetaSOPSettings:
        if raw is None:
            return cls()
        try:
            if isinstance(raw, dict):
                raw_dict = raw
            elif hasattr(raw, "model_dump") and callable(raw.model_dump):
                from openhands.core.pydantic_compat import model_dump_with_options

                raw_dict = model_dump_with_options(raw)
            else:
                try:
                    raw_dict = dict(raw)
                except Exception:
                    return cls()
            return cls(**raw_dict)
        except Exception:
            return cls()

    __test__ = False

    def build_retry_policy_kwargs(self) -> dict[str, Any]:
        if not self.retry:
            return {}
        from openhands.core.pydantic_compat import model_dump_with_options

        return model_dump_with_options(self.retry, exclude_none=True)


__all__ = ["MetaSOPSettings", "RetrySettings"]
