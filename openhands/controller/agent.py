from __future__ import annotations

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


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.controller.state.state import State
    from openhands.events.action import Action
    from openhands.events.action.message import SystemMessageAction
    from openhands.llm.llm_registry import LLMRegistry
    from openhands.runtime.plugins import PluginRequirement
    from openhands.utils.prompt import PromptManager
from litellm import ChatCompletionToolParam

from openhands.core.config import AgentConfig
from openhands.core.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotRegisteredError,
)
from openhands.core.logger import openhands_logger as logger
from openhands.events.event import EventSource


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
        self.llm = llm_registry.get_llm_from_agent_config("agent", config)
        self.llm_registry = llm_registry
        self.config = config
        self._complete = False
        self._prompt_manager: PromptManager | None = None
        self.mcp_tools: dict[str, ChatCompletionToolParam] = {}
        self.tools: list = []

    @property
    def prompt_manager(self) -> PromptManager:
        if self._prompt_manager is None:
            msg = f"Prompt manager not initialized for agent {self.name}"
            raise ValueError(msg)
        return self._prompt_manager

    def get_system_message(self) -> SystemMessageAction | None:
        """Returns a SystemMessageAction containing the system message and tools.

        This will be added to the event stream as the first message.

        Returns:
            SystemMessageAction: The system message action with content and tools
            None: If there was an error generating the system message
        """
        from openhands.events.action.message import SystemMessageAction

        try:
            if not self.prompt_manager:
                logger.warning("[%s] Prompt manager not initialized before getting system message", self.name)
                return None
            system_message = self.prompt_manager.get_system_message(cli_mode=self.config.cli_mode, config=self.config)
            tools = getattr(self, "tools", None)
            system_message_action = SystemMessageAction(content=system_message, tools=tools, agent_class=self.name)
            system_message_action._source = EventSource.AGENT
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
        """Starts the execution of the assigned instruction.

        This method should be implemented by subclasses to define the specific execution logic.
        """

    def reset(self) -> None:
        """Resets the agent's execution status."""
        self._complete = False

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @classmethod
    def register(cls, name: str, agent_cls: type[Agent]) -> None:
        """Registers an agent class in the registry.

        Parameters:
        - name (str): The name to register the class under.
        - agent_cls (Type['Agent']): The class to register.

        Raises:
        - AgentAlreadyRegisteredError: If name already registered
        """
        if name in cls._registry:
            raise AgentAlreadyRegisteredError(name)
        cls._registry[name] = agent_cls

    @classmethod
    def get_cls(cls, name: str) -> type[Agent]:
        """Retrieves an agent class from the registry.

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
        """Retrieves the list of all agent names from the registry.

        Raises:
        - AgentNotRegisteredError: If no agent is registered
        """
        if not bool(cls._registry):
            raise AgentNotRegisteredError
        return list(cls._registry.keys())

    def set_mcp_tools(self, mcp_tools: list[dict]) -> None:
        """Sets the list of MCP tools for the agent.

        Args:
            mcp_tools (list[dict]): The list of MCP tools.
        """
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
