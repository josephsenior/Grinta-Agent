from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from typing import TYPE_CHECKING

# Import CondenserConfig directly - needed for Pydantic validation
from openhands.core.config.condenser_config import (
    CondenserConfig,
    ConversationWindowCondenserConfig,
)
from openhands.core.config.extended_config import ExtendedConfig
from openhands.core.config.permissions_config import PermissionsConfig
from openhands.core.logger import openhands_logger as logger
from openhands.security.safety_config import SafetyConfig
from openhands.utils.import_utils import get_impl


class AgentConfig(BaseModel):
    cli_mode: bool = Field(default=False)
    "Whether the agent is running in CLI mode. This can be used to disable certain tools that are not supported in CLI mode."
    llm_config: str | None = Field(default=None)
    "The name of the llm config to use. If specified, this will override global llm config."
    classpath: str | None = Field(default=None)
    "The classpath of the agent to use. To be used for custom agents that are not defined in the openhands.agenthub package."
    system_prompt_filename: str = Field(default="system_prompt.j2")
    "Filename of the system prompt template file within the agent's prompt directory. Defaults to 'system_prompt.j2'."
    enable_browsing: bool = Field(default=True)
    "Whether to enable browsing tool.\n    Note: If using CLIRuntime, browsing is not implemented and should be disabled."
    use_ultimate_browsing_agent: bool = Field(default=False)
    "Whether to use the upgraded browsing agent with enhanced capabilities"
    enable_llm_editor: bool = Field(default=False)
    "Whether to enable LLM editor tool"
    enable_ultimate_editor: bool = Field(default=False)
    "Whether to enable tree-sitter powered editor with structure-aware editing for 40+ languages"
    enable_editor: bool = Field(default=True)
    "Whether to enable the standard editor tool (str_replace_editor), only has an effect if enable_llm_editor is False."
    enable_jupyter: bool = Field(default=True)
    "Whether to enable Jupyter tool.\n    Note: If using CLIRuntime, Jupyter use is not implemented and should be disabled."
    enable_cmd: bool = Field(default=True)
    "Whether to enable bash tool"
    enable_think: bool = Field(default=True)
    "Whether to enable think tool"
    enable_finish: bool = Field(default=True)
    "Whether to enable finish tool"
    enable_condensation_request: bool = Field(default=False)
    "Whether to enable condensation request tool"
    enable_prompt_extensions: bool = Field(default=True)
    "Whether to enable prompt extensions"
    enable_mcp: bool = Field(default=True)
    "Whether to enable MCP tools"
    disabled_microagents: list[str] = Field(default_factory=list)
    'A list of microagents to disable (by name, without .py extension, e.g. ["github", "lint"]). Default is None.'
    enable_history_truncation: bool = Field(default=True)
    "Whether history should be truncated to continue the session when hitting LLM context length limit."
    enable_som_visual_browsing: bool = Field(default=True)
    "Whether to enable SoM (Set of Marks) visual browsing."
    enable_plan_mode: bool = Field(default=True)
    "Whether to enable plan mode, which uses the long horizon system message and add the new tool - task_tracker - for planning, tracking and executing complex tasks."

    # Autonomy settings
    autonomy_level: str = Field(default="balanced")
    "Agent autonomy level: 'supervised' (always confirm), 'balanced' (confirm high-risk), 'full' (no confirmations)"
    auto_retry_on_error: bool = Field(default=True)
    "Whether to automatically retry on recoverable errors"
    max_autonomous_iterations: int = Field(default=50)
    "Maximum iterations for autonomous execution without user intervention"
    enable_internal_task_tracker: bool = Field(default=True)
    "Whether to enable internal task tracking for autonomous progress monitoring"
    stuck_detection_enabled: bool = Field(default=True)
    "Whether to enable stuck detection in autonomous mode"
    stuck_threshold_iterations: int = Field(default=5)
    "Number of repeated iterations before considering the agent stuck"

    # Fine-grained permissions
    permissions: PermissionsConfig = Field(default_factory=lambda: PermissionsConfig())
    "Fine-grained permissions configuration for agent actions"
    enable_permissions: bool = Field(default=True)
    "Whether to enforce permission checks on agent actions"

    # Rollback system
    enable_checkpoints: bool = Field(default=True)
    "Whether to enable automatic checkpoints before risky operations"
    checkpoint_before_risky: bool = Field(default=True)
    "Create automatic checkpoints before high-risk operations"
    max_checkpoints: int = Field(default=20)
    "Maximum number of checkpoints to keep"
    checkpoint_retention_hours: int = Field(default=168)
    "How long to keep checkpoints (default: 7 days)"

    # Safety configuration
    safety: SafetyConfig = Field(default_factory=lambda: SafetyConfig())
    "Safety validation configuration for production environments"

    # Task completion validation
    enable_completion_validation: bool = Field(default=False)
    "Whether to validate task completion before accepting AgentFinishAction"
    allow_force_finish: bool = Field(default=False)
    "Whether to allow agents to force finish without validation"
    min_progress_threshold: float = Field(default=0.7)
    "Minimum progress threshold (0.0-1.0) required for task completion"

    # Circuit breaker configuration
    enable_circuit_breaker: bool = Field(default=False)
    "Whether to enable circuit breaker for anomaly detection"
    max_consecutive_errors: int = Field(default=5)
    "Maximum consecutive errors before circuit breaker trips"
    max_high_risk_actions: int = Field(default=10)
    "Maximum high-risk actions before circuit breaker trips"
    max_stuck_detections: int = Field(default=3)
    "Maximum stuck loop detections before circuit breaker trips"
    
    # ACE Framework Configuration
    enable_ace: bool = Field(default=False)
    "Whether to enable ACE (Agentic Context Engineering) framework for self-improving agents"
    ace_max_bullets: int = Field(default=1000)
    "Maximum number of bullets in ACE context playbook"
    ace_multi_epoch: bool = Field(default=True)
    "Whether to enable multi-epoch training for ACE framework"
    ace_num_epochs: int = Field(default=5)
    "Number of training epochs for ACE multi-epoch training"
    ace_reflector_max_iterations: int = Field(default=5)
    "Maximum number of reflection refinement iterations"
    ace_playbook_path: str | None = Field(default=None)
    "Path for saving ACE playbooks (if None, uses default location)"
    ace_enable_online_adaptation: bool = Field(default=True)
    "Whether to enable test-time learning for ACE framework"
    ace_min_helpfulness_threshold: float = Field(default=0.0)
    "Minimum helpfulness score for bullet retrieval"
    ace_max_playbook_content_length: int = Field(default=50)
    "Maximum number of bullets in playbook content for LLM"
    ace_enable_grow_and_refine: bool = Field(default=True)
    "Whether to enable grow-and-refine mechanism for playbook maintenance"
    ace_cleanup_interval_days: int = Field(default=30)
    "Days between playbook cleanup cycles"
    ace_redundancy_threshold: float = Field(default=0.8)
    "Similarity threshold for redundancy detection"

    # Memory System Configuration
    enable_vector_memory: bool = Field(default=False)
    "Whether persistent vector memory system is enabled (ChromaDB/Qdrant with 92% accuracy semantic search)"
    enable_hybrid_retrieval: bool = Field(default=False)
    "Whether hybrid retrieval (vector + lexical BM25 + re-ranking) is enabled"

    # Dynamic Prompt Optimization Settings
    enable_prompt_optimization: bool = Field(default=False)
    "Enable Dynamic Prompt Optimization for CodeAct agent system prompts"
    prompt_opt_storage_path: str = Field(default="~/.openhands/prompt_optimization/codeact/")
    "Storage path for CodeAct prompt optimization data"
    prompt_opt_ab_split: float = Field(default=0.8, ge=0.0, le=1.0)
    "A/B testing split ratio (0.8 = 80% best, 20% experiments)"
    prompt_opt_min_samples: int = Field(default=5, ge=1, le=50)
    "Minimum samples required before switching variants"
    prompt_opt_confidence_threshold: float = Field(default=0.95, ge=0.5, le=1.0)
    "Confidence threshold for statistical significance testing"
    prompt_opt_success_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    "Weight for success rate in composite scoring"
    prompt_opt_time_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    "Weight for execution time in composite scoring"
    prompt_opt_error_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    "Weight for error rate in composite scoring"
    prompt_opt_cost_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    "Weight for token cost in composite scoring"
    prompt_opt_enable_evolution: bool = Field(default=True)
    "Enable LLM-powered prompt evolution"
    prompt_opt_evolution_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    "Composite score threshold below which prompts are evolved"
    prompt_opt_max_variants_per_prompt: int = Field(default=10, ge=1, le=50)
    "Maximum number of variants per prompt"
    prompt_opt_sync_interval: int = Field(default=100, ge=1, le=1000)
    "Number of updates between storage syncs"
    prompt_opt_auto_save: bool = Field(default=True)
    "Automatically save optimization data"

    # Enhanced Context Management
    enable_enhanced_context: bool = Field(default=False)
    "Enable hierarchical memory and decision tracking"
    context_short_term_window: int = Field(default=5, ge=1, le=20)
    "Last N exchanges in short-term memory"
    context_working_size: int = Field(default=50, ge=10, le=200)
    "Active context items in working memory"
    context_long_term_size: int = Field(default=200, ge=50, le=1000)
    "Persistent long-term memory size"
    context_contradiction_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    "Similarity threshold for contradiction detection"
    context_persistence_path: str = Field(default="./.forge/context_state.json")
    "Where to save context state"

    # Performance: Parallel Execution
    max_workers: int = Field(default=3, ge=1, le=12)
    "Concurrent workers for parallel task execution"
    max_async_concurrent: int = Field(default=6, ge=1, le=24)
    "Maximum async operations running concurrently"

    def _get_default_condenser():
        return ConversationWindowCondenserConfig()
    
    condenser: CondenserConfig = Field(default_factory=_get_default_condenser)
    extended: ExtendedConfig = Field(default_factory=lambda: ExtendedConfig({}))
    "Extended configuration for the agent."
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    @property
    def resolved_system_prompt_filename(self) -> str:
        """Returns the appropriate system prompt filename based on the agent configuration.

        When enable_plan_mode is True, automatically uses the long horizon system prompt
        unless a custom system_prompt_filename was explicitly set (not the default).
        """
        if self.enable_plan_mode and self.system_prompt_filename == "system_prompt.j2":
            return "system_prompt_long_horizon.j2"
        return self.system_prompt_filename

    @classmethod
    def _separate_base_and_custom_sections(cls, data: dict) -> tuple[dict, dict[str, dict]]:
        """Separate base configuration from custom agent sections."""
        base_data = {}
        custom_sections: dict[str, dict] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                custom_sections[key] = value
            else:
                base_data[key] = value
        return base_data, custom_sections

    @classmethod
    def _create_base_config(cls, base_data: dict) -> AgentConfig:
        """Create base configuration with error handling."""
        try:
            return cls.model_validate(base_data)
        except ValidationError as e:
            logger.warning("Invalid base agent configuration: %s. Using defaults.", e)
            return cls()

    @classmethod
    def _create_custom_config(cls, name: str, base_config: AgentConfig, overrides: dict) -> AgentConfig | None:
        """Create custom agent configuration with classpath handling."""
        from openhands.core.pydantic_compat import model_dump_with_options

        merged = {**model_dump_with_options(base_config), **overrides}

        if merged.get("classpath"):
            return cls._create_config_from_classpath(merged, cls)
        return cls._create_config_from_agent_name(name, merged, cls)

    @classmethod
    def _create_config_from_classpath(cls, merged: dict, default_cls: type) -> AgentConfig:
        """Create config from custom classpath."""
        from openhands.controller.agent import Agent

        try:
            agent_cls = get_impl(Agent, merged.get("classpath"))
            return agent_cls.config_model.model_validate(merged)
        except Exception as e:
            logger.warning(
                "Failed to load custom agent class [%s]: %s. Using default config model.",
                merged.get("classpath"),
                e,
            )
            return default_cls.model_validate(merged)

    @classmethod
    def _create_config_from_agent_name(cls, name: str, merged: dict, default_cls: type) -> AgentConfig:
        """Create config from agent name."""
        from openhands.controller.agent import Agent

        try:
            agent_cls = Agent.get_cls(name)
            return agent_cls.config_model.model_validate(merged)
        except Exception:
            return default_cls.model_validate(merged)

    def from_toml_section(self, data: dict) -> dict[str, AgentConfig]:
        """Create a mapping of AgentConfig instances from a toml dictionary representing the [agent] section.

        The default configuration is built from all non-dict keys in data.
        Then, each key with a dict value is treated as a custom agent configuration, and its values override
        the default configuration.

        Example:
        Apply generic agent config with custom agent overrides, e.g.
            [agent]
            enable_prompt_extensions = false
            [agent.BrowsingAgent]
            enable_prompt_extensions = true
        results in prompt_extensions being true for BrowsingAgent but false for others.

        Returns:
            dict[str, AgentConfig]: A mapping where the key "agent" corresponds to the default configuration
            and additional keys represent custom configurations.
        """
        agent_mapping: dict[str, AgentConfig] = {}
        base_data, custom_sections = self._separate_base_and_custom_sections(data)

        base_config = self._create_base_config(base_data)
        agent_mapping["agent"] = base_config

        for name, overrides in custom_sections.items():
            try:
                if custom_config := self._create_custom_config(name, base_config, overrides):
                    agent_mapping[name] = custom_config
            except ValidationError as e:
                logger.warning("Invalid agent configuration for [%s]: %s. This section will be skipped.", name, e)
        return agent_mapping
