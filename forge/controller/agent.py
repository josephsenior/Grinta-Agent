"""Agent controller and execution management.

Classes:
    Agent

Functions:
    prompt_manager
    get_system_message
    complete
    step
    reset
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from forge.controller.state.state import State
    from forge.events.action import Action
    from forge.events.action.message import SystemMessageAction
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement
    from forge.utils.prompt import PromptManager
from litellm import ChatCompletionToolParam

from forge.core.config import AgentConfig
from forge.core.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotRegisteredError,
)
from forge.core.logger import forge_logger as logger
from forge.events.event import EventSource


class Agent(ABC):
    """Abstract base class for agents that execute instructions with human interaction.
    
    Tracks execution status and maintains interaction history. Agents are registered
    in a class registry for dynamic instantiation.
    
    Attributes:
        DEPRECATED: Whether this agent class is deprecated
        _registry: Class registry mapping agent names to classes
        sandbox_plugins: Required sandbox plugins for this agent
        config_model: Configuration model class for this agent

    """

    DEPRECATED = False
    _registry: dict[str, type[Agent]] = {}
    sandbox_plugins: list[PluginRequirement] = []
    config_model: type[AgentConfig] = AgentConfig
    "Class field that specifies the config model to use for the agent. Subclasses may override with a derived config model if needed."

    def __init__(self, config: AgentConfig, llm_registry: LLMRegistry) -> None:
        """Initialize the agent with its configuration and LLM registry."""
        self.llm = llm_registry.get_llm_from_agent_config("agent", config)
        self.llm_registry = llm_registry
        self.config = config
        self._complete = False
        self._prompt_manager: PromptManager | None = None
        self.mcp_tools: dict[str, ChatCompletionToolParam] = {}
        self.tools: list = []

    @property
    def prompt_manager(self) -> PromptManager:
        """Get prompt manager for loading agent system prompts.
        
        Returns:
            PromptManager instance
            
        Raises:
            ValueError: If prompt manager not initialized

        """
        if self._prompt_manager is None:
            msg = f"Prompt manager not initialized for agent {self.name}"
            raise ValueError(msg)
        return self._prompt_manager

    def get_system_message(self) -> SystemMessageAction | None:
        """Return a `SystemMessageAction` containing the system message and tools.

        This will be added to the event stream as the first message.

        Returns:
            SystemMessageAction: The system message action with content and tools
            None: If there was an error generating the system message

        """
        from forge.events.action.message import SystemMessageAction

        try:
            if not self.prompt_manager:
                logger.warning("[%s] Prompt manager not initialized before getting system message", self.name)
                return None
            system_message = self.prompt_manager.get_system_message(cli_mode=self.config.cli_mode, config=self.config)
            tools = getattr(self, "tools", None)
            system_message_action = SystemMessageAction(content=system_message, tools=tools, agent_class=self.name)
            system_message_action.source = EventSource.AGENT
            return system_message_action
        except Exception as e:
            logger.warning("[%s] Failed to generate system message: %s", self.name, e)
            return None

    @property
    def complete(self) -> bool:
        """Indicates whether the current instruction execution is complete.

        Returns:
        - complete (bool): True if execution is complete; False otherwise.

        """
        return self._complete

    @abstractmethod
    def step(self, state: State) -> Action:
        """Start the execution of the assigned instruction."""
        raise NotImplementedError

    def reset(self) -> None:
        """Reset the agent to its initial state."""
        self._complete = False

    @property
    def name(self) -> str:
        """Get agent class name.
        
        Returns:
            Agent class name

        """
        return self.__class__.__name__

    @classmethod
    def register(cls, name: str, agent_cls: type[Agent]) -> None:
        """Register a new agent class in the registry."""
        if name in cls._registry:
            raise AgentAlreadyRegisteredError(name)
        cls._registry[name] = agent_cls

    @classmethod
    def get_cls(cls, name: str) -> type[Agent]:
        """Retrieve the agent class with the given name.

        Parameters:
        - name (str): The name of the class to retrieve

        Returns:
        - agent_cls (Type['Agent']): The class registered under the specified name.

        Raises:
        - AgentNotRegisteredError: If name not registered

        """
        if name not in cls._registry:
            raise AgentNotRegisteredError(name)
        return cls._registry[name]

    @classmethod
    def list_agents(cls) -> list[str]:
        """Return the list of registered agents."""
        if not bool(cls._registry):
            raise AgentNotRegisteredError
        return list(cls._registry.keys())

    def set_mcp_tools(self, mcp_tools: list[dict]) -> None:
        """Set the MCP tools for the agent."""
        logger.info(
            "Setting %s MCP tools for agent %s: %s",
            len(mcp_tools),
            self.name,
            [tool["function"]["name"] for tool in mcp_tools],
        )
        for tool in mcp_tools:
            _tool = ChatCompletionToolParam(**tool)
            if _tool["function"]["name"] in self.mcp_tools:
                logger.warning("Tool %s already exists, skipping", _tool["function"]["name"])
                continue
            self.mcp_tools[_tool["function"]["name"]] = _tool
            self.tools.append(_tool)
        logger.info(
            "Tools updated for agent %s, total %s: %s",
            self.name,
            len(self.tools),
            [tool["function"]["name"] for tool in self.tools],
        )
