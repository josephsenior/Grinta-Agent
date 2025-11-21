"""Configuration models describing agent-specific settings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import TYPE_CHECKING, Any

# Import CondenserConfig directly - needed for Pydantic validation
from forge.core.config.condenser_config import (
    CondenserConfig,
    ConversationWindowCondenserConfig,
)
from forge.core.logger import forge_logger as logger
from forge.core.config.config_telemetry import config_telemetry

CURRENT_AGENT_CONFIG_SCHEMA_VERSION = "2025-11-14"


if TYPE_CHECKING:
    from forge.core.config.llm_config import LLMConfig
else:
    LLMConfig = Any  # For runtime when TYPE_CHECKING is False


class AgentConfig(BaseModel):
    """Configuration for an agent.

    Attributes:
        name: Name of the agent to use
        llm_config: LLM configuration for the agent
        memory_max_threads: Maximum number of history items to include in context window
        memory_enabled: Whether to enable conversation memory
        condenser_config: Configuration for conversation memory condenser
        enable_prompt_extensions: Whether to allow agent-specific prompt extensions (agent suffix)
        enable_jupyter: Whether to enable Jupyter kernel
        enable_browsing: Whether to enable browser environment
        enable_auto_lint: Whether to enable automatic linting after edits
        confirm_actions: Whether to require user confirmation before executing actions
        llm_draft_config: LLM configuration for draft operations

    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="CodeActAgent")
    llm_config: LLMConfig | None = Field(default=None)
    memory_max_threads: int = Field(default=10)
    memory_enabled: bool = Field(default=True)
    condenser_config: CondenserConfig = Field(
        default_factory=ConversationWindowCondenserConfig
    )
    enable_prompt_extensions: bool = Field(default=True)
    enable_jupyter: bool = Field(default=True)
    enable_browsing: bool = Field(default=True)
    enable_vector_memory: bool = Field(
        default=False, description="Enable persistent vector memory store"
    )
    enable_hybrid_retrieval: bool = Field(
        default=False, description="Enable hybrid retrieval for vector memory"
    )
    enable_prompt_caching: bool = Field(
        default=True, description="Enable prompt caching hints for LLMs"
    )
    disabled_microagents: list[str] = Field(
        default_factory=list, description="List of microagents disabled for this agent"
    )
    enable_auto_lint: bool = Field(default=True)
    confirm_actions: bool = Field(default=False)
    llm_draft_config: LLMConfig | None = Field(default=None)
    auto_retry_on_error: bool = Field(
        default=False, description="Automatically retry actions when recoverable errors occur"
    )
    autonomy_level: str = Field(
        default="balanced",
        description="Autonomy mode: supervised, balanced, or full",
    )

    # Core tool toggles
    enable_cmd: bool = Field(default=True)
    enable_think: bool = Field(default=True)
    enable_finish: bool = Field(default=True)
    enable_condensation_request: bool = Field(default=False)

    # Editor tool toggles
    enable_editor: bool = Field(default=True)
    enable_llm_editor: bool = Field(default=False)
    enable_ultimate_editor: bool = Field(default=False)

    # Advanced capabilities
    enable_history_truncation: bool = Field(default=True)
    enable_plan_mode: bool = Field(
        default=True,
        description="Enable task planning and decomposition (task tracker tool)"
    )
    enable_mcp: bool = Field(default=True)
    enable_auto_planning: bool = Field(
        default=True,
        description="Automatically decompose complex tasks before execution"
    )
    planning_complexity_threshold: int = Field(
        default=3,
        description="Minimum number of distinct requirements to trigger automatic planning"
    )
    enable_reflection: bool = Field(
        default=True,
        description="Enable self-reflection before executing actions"
    )
    enable_planning_middleware: bool = Field(
        default=False,
        description="Enable planning middleware to analyze incoming tasks before execution"
    )
    enable_reflection_middleware: bool = Field(
        default=False,
        description="Enable reflection middleware to verify actions before execution"
    )
    reflection_max_attempts: int = Field(
        default=2,
        description="Maximum self-correction attempts during reflection"
    )
    enable_dynamic_iterations: bool = Field(
        default=True,
        description="Dynamically adjust max_iterations based on task complexity"
    )
    min_iterations: int = Field(
        default=20,
        description="Minimum iterations for simple tasks"
    )
    max_iterations_override: int | None = Field(
        default=None,
        description="Override max_iterations from ForgeConfig (None = use ForgeConfig value)"
    )
    complexity_iteration_multiplier: float = Field(
        default=50.0,
        description="Iterations = complexity_score * multiplier (capped at max_iterations)"
    )
    max_autonomous_iterations: int = Field(
        default=0, description="Maximum self-directed iterations when autonomy is full"
    )
    stuck_detection_enabled: bool = Field(
        default=False,
        description="Enable stuck detection when autonomy is full",
    )
    stuck_threshold_iterations: int = Field(
        default=0,
        description="Number of iterations without progress before triggering stuck handling",
    )
    enable_internal_task_tracker: bool = Field(
        default=True,
        description="Enable the internal task progress tracker tool",
    )

    # Memory features
    enable_som_visual_browsing: bool = Field(default=False)

    # Prompt management
    system_prompt_filename: str = Field(default="system_prompt.j2")
    cli_mode: bool = Field(default=False)

    @property
    def condenser(self) -> CondenserConfig:
        """Backward compatibility alias for condenser_config."""
        return self.condenser_config

    @condenser.setter
    def condenser(self, value: CondenserConfig) -> None:
        self.condenser_config = value

    def get_llm_config(self) -> LLMConfig | None:
        """Get the default LLM configuration for this agent.

        Returns:
            LLM configuration to use when none is specified

        """
        # If a specific LLM config override is provided, use that
        if self.llm_config:
            return self.llm_config
        # Otherwise fall back to the default llm key
        return None

    @property
    def resolved_system_prompt_filename(self) -> str:
        """Return a safe system prompt filename for PromptManager."""
        filename = getattr(self, "system_prompt_filename", None)
        if not filename or not isinstance(filename, str):
            return "system_prompt.j2"
        return filename

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, AgentConfig]:
        """Alias for from_dict for backward compatibility with tests and existing code."""
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> dict[str, AgentConfig]:
        """Build mapping from agent id to agent config.

        {
            "manager": AgentConfig(...)
        }
        """
        agent_mapping: dict[str, AgentConfig] = {}
        base_data, custom_sections = cls._separate_base_and_custom_sections(data)
        schema_version = base_data.pop("schema_version", None)

        if schema_version is None:
            config_telemetry.record_schema_missing()
            logger.warning(
                "Agent configuration missing schema_version; expected %s.",
                CURRENT_AGENT_CONFIG_SCHEMA_VERSION,
            )
        elif str(schema_version) != CURRENT_AGENT_CONFIG_SCHEMA_VERSION:
            config_telemetry.record_schema_mismatch(str(schema_version))
            logger.warning(
                "Agent configuration schema_version mismatch (got %s, expected %s).",
                schema_version,
                CURRENT_AGENT_CONFIG_SCHEMA_VERSION,
            )

        try:
            base_config = cls._create_base_config(base_data)
        except ValueError as exc:
            config_telemetry.record_invalid_base()
            raise ValueError(f"Invalid base agent configuration: {exc}") from exc

        agent_mapping["agent"] = base_config
        errors: list[str] = []

        for name, overrides in custom_sections.items():
            try:
                custom_config = cls._create_custom_config(name, base_config, overrides)
                agent_mapping[name] = custom_config
            except (ValidationError, TypeError, ValueError, KeyError) as e:
                config_telemetry.record_invalid_agent(name)
                errors.append(f"[{name}] {e}")

        if errors:
            combined = "\n - ".join(errors)
            raise ValueError(
                f"Invalid custom agent configuration(s):\n - {combined}"
            )

        return agent_mapping

    @staticmethod
    def _separate_base_and_custom_sections(data: dict) -> tuple[dict, dict[str, dict]]:
        """Separate base agent config from custom agent configs.

        Args:
            data: Raw configuration dictionary

        Returns:
            Tuple of (base_config_dict, {custom_name: overrides_dict})

        """
        base_data = {}
        custom_sections: dict[str, dict] = {}

        for key, value in data.items():
            if isinstance(value, dict) and key not in [
                "llm_config",
                "condenser_config",
                "llm_draft_config",
            ]:
                # This is a custom agent section like [agent.BrowsingAgent]
                custom_sections[key] = value
            else:
                # This is part of the base config
                base_data[key] = value

        return base_data, custom_sections

    @classmethod
    def _create_base_config(cls, base_data: dict) -> AgentConfig:
        """Create the base agent configuration.

        Args:
            base_data: Dictionary containing base configuration values

        Returns:
            AgentConfig instance with base settings

        """
        valid_fields = set(cls.model_fields.keys())
        invalid_fields = {k for k in base_data.keys() if k not in valid_fields}
        if invalid_fields:
            raise ValueError(
                f"Unknown agent config field(s): {sorted(invalid_fields)}"
            )
        try:
            return cls(**base_data)
        except ValidationError as exc:
            raise ValueError("Invalid base agent configuration") from exc

    @classmethod
    def _create_custom_config(
        cls,
        name: str,
        base_config: AgentConfig,
        overrides: dict,
    ) -> AgentConfig:
        """Create a custom agent configuration by merging overrides with base config.

        Args:
            name: Name for the custom agent
            base_config: Base configuration to extend
            overrides: Dictionary of values to override

        Returns:
            AgentConfig with merged settings, or None if invalid

        """
        # Validate that overrides only contain valid fields
        valid_fields = set(cls.model_fields.keys())
        invalid_fields = {k for k in overrides.keys() if k not in valid_fields}

        if invalid_fields:
            raise ValueError(
                f"Unknown field(s) for agent '{name}': {sorted(invalid_fields)}"
            )

        # Start with base config values
        merged = base_config.model_dump()

        # Apply overrides
        for key, value in overrides.items():
            merged[key] = value

        # Set the custom name
        merged["name"] = name

        try:
            return cls(**merged)
        except ValidationError as exc:
            raise ValueError(f"Invalid configuration for agent '{name}'") from exc


# Rebuild the model after all dependencies are loaded to resolve forward references
AgentConfig.model_rebuild()
