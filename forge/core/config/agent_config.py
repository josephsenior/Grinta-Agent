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

    model_config = ConfigDict(extra="ignore")  # Changed from "forbid" to "ignore" to support config.toml fields during refactoring

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
    enable_vector_memory: bool = Field(default=False, description="Enable persistent vector memory store")
    enable_hybrid_retrieval: bool = Field(default=False, description="Enable hybrid retrieval for vector memory")
    enable_prompt_caching: bool = Field(default=True, description="Enable prompt caching hints for LLMs")
    disabled_microagents: list[str] = Field(default_factory=list, description="List of microagents disabled for this agent")
    enable_auto_lint: bool = Field(default=True)
    confirm_actions: bool = Field(default=False)
    llm_draft_config: LLMConfig | None = Field(default=None)

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
    enable_plan_mode: bool = Field(default=False)
    enable_mcp: bool = Field(default=True)

    # Memory features
    enable_vector_memory: bool = Field(default=False)
    enable_hybrid_retrieval: bool = Field(default=False)
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

        base_config = cls._create_base_config(base_data)
        agent_mapping["agent"] = base_config

        for name, overrides in custom_sections.items():
            try:
                custom_config = cls._create_custom_config(name, base_config, overrides)
                if custom_config:
                    agent_mapping[name] = custom_config
            except (ValidationError, TypeError, ValueError, KeyError) as e:
                logger.warning("Invalid agent configuration for [%s]: %s. This section will be skipped.", name, e)
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
            if isinstance(value, dict) and key not in ["llm_config", "condenser_config", "llm_draft_config"]:
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
        # Filter out invalid fields before creating config
        valid_fields = set(cls.model_fields.keys())
        filtered_data = {k: v for k, v in base_data.items() if k in valid_fields or k in ['llm_config', 'condenser_config']}
        try:
            return cls(**filtered_data)
        except ValidationError as exc:
            logger.warning("Invalid base agent configuration encountered: %s. Reverting to defaults.", exc)
            fallback = cls()
            # Maintain historical defaults for browsing-enabled agents when falling back
            fallback.enable_browsing = True
            fallback.enable_jupyter = True
            return fallback

    @classmethod
    def _create_custom_config(
        cls,
        name: str,
        base_config: AgentConfig,
        overrides: dict,
    ) -> AgentConfig | None:
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
            # Return None for agents with invalid fields (they'll be skipped)
            logger.warning(f"Agent [{name}] has invalid fields: {invalid_fields}. Skipping.")
            return None
        
        # Start with base config values
        merged = base_config.model_dump()

        # Apply overrides
        for key, value in overrides.items():
            merged[key] = value

        # Set the custom name
        merged["name"] = name

        return cls(**merged)


# Rebuild the model after all dependencies are loaded to resolve forward references
AgentConfig.model_rebuild()
