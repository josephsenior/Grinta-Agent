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
from typing import TYPE_CHECKING, Any, TypedDict, NotRequired

if TYPE_CHECKING:
    from forge.controller.state.state import State
    from forge.events.action import Action
    from forge.events.action.message import SystemMessageAction
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement
    from forge.utils.prompt import PromptManager
from forge.llm.tool_types import make_function_chunk, make_tool_param

from forge.core.config import AgentConfig
from forge.core.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotRegisteredError,
)
from forge.core.logger import forge_logger as logger
from forge.events.event import EventSource


class _FunctionChunkArgs(TypedDict):
    name: str
    description: NotRequired[str]
    parameters: NotRequired[dict[str, Any]]
    strict: NotRequired[bool]


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
        self.mcp_tools: dict[str, Any] = {}
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
                logger.warning(
                    "[%s] Prompt manager not initialized before getting system message",
                    self.name,
                )
                return None
            system_message = self.prompt_manager.get_system_message(
                cli_mode=self.config.cli_mode, config=self.config
            )
            tools = getattr(self, "tools", None)
            # Construct using the canonical class reference imported above. Some
            # test environments appear to load duplicate copies of the action
            # module, leading to identity mismatches for isinstance checks.
            system_message_action = SystemMessageAction(
                content=system_message,
                tools=tools,
                agent_class=self.name,
            )
            # Defensive normalization: if the created instance fails a direct
            # isinstance check against the freshly imported class (edge case
            # of module duplication), rebuild via attribute dict on the currently
            # imported class to unify the identity.
            if type(system_message_action).__name__ != "SystemMessageAction":  # pragma: no cover - defensive
                system_message_action = SystemMessageAction(
                    content=getattr(system_message_action, "content", system_message),
                    tools=getattr(system_message_action, "tools", tools),
                    agent_class=getattr(system_message_action, "agent_class", self.name),
                )
            system_message_action.source = EventSource.AGENT
            try:  # pragma: no cover - diagnostic instrumentation
                logger.debug(
                    "[get_system_message] created instance class=%s module=%s id=%s isinstance=%s ref_equal=%s",
                    system_message_action.__class__.__name__,
                    system_message_action.__class__.__module__,
                    id(system_message_action.__class__),
                    isinstance(system_message_action, SystemMessageAction),
                    system_message_action.__class__ is SystemMessageAction,
                )
            except Exception:
                pass
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
        self._log_tool_update_start(mcp_tools)
        for tool in mcp_tools:
            built_tool = self._build_tool(tool)
            if built_tool is None:
                continue
            tool_name = built_tool["function"]["name"]
            if self._tool_exists(tool_name):
                logger.warning("Tool %s already exists, skipping", tool_name)
                continue
            self._register_tool(built_tool, tool_name)
        self._log_tool_update_end()

    def _log_tool_update_start(self, mcp_tools: list[dict]) -> None:
        try:
            tool_names = [
                tool.get("function", {}).get("name", "<unknown>") for tool in mcp_tools
            ]
        except Exception:
            tool_names = ["<unavailable>"]
        logger.info(
            "Setting %s MCP tools for agent %s: %s",
            len(mcp_tools),
            self.name,
            tool_names,
        )

    def _build_tool(self, tool: dict) -> dict | None:
        normalized_tool = dict(tool)
        function_payload = normalized_tool.get("function")
        if not isinstance(function_payload, dict):
            logger.warning("Skipping tool without callable metadata: %s", tool)
            return None

        chunk_kwargs = self._chunk_args_from_payload(function_payload, tool)
        if chunk_kwargs is None:
            return None

        function_chunk = self._make_function_chunk(chunk_kwargs, tool)
        if function_chunk is None:
            return None

        tool_type = str(normalized_tool.get("type", "function"))
        tool_param = make_tool_param(function=function_chunk, type=tool_type)
        self._attach_additional_fields(tool_param, normalized_tool)
        return tool_param

    def _chunk_args_from_payload(
        self, function_payload: dict, original_tool: dict
    ) -> _FunctionChunkArgs | None:
        name_value = function_payload.get("name")
        if not isinstance(name_value, str) or not name_value:
            logger.warning(
                "Skipping tool with invalid function name: %s", original_tool
            )
            return None

        chunk_kwargs: _FunctionChunkArgs = {"name": name_value}
        description = function_payload.get("description")
        if isinstance(description, str):
            chunk_kwargs["description"] = description
        parameters = function_payload.get("parameters")
        if isinstance(parameters, dict):
            chunk_kwargs["parameters"] = parameters
        strict = function_payload.get("strict")
        if isinstance(strict, bool):
            chunk_kwargs["strict"] = strict
        return chunk_kwargs

    def _make_function_chunk(
        self, chunk_kwargs: _FunctionChunkArgs, original_tool: dict
    ):
        try:
            return make_function_chunk(**chunk_kwargs)
        except TypeError as exc:
            logger.warning(
                "Skipping tool %s due to invalid function payload: %s",
                original_tool,
                exc,
            )
            return None

    @staticmethod
    def _attach_additional_fields(tool_param: dict, normalized_tool: dict) -> None:
        for extra_key, extra_value in normalized_tool.items():
            if extra_key in {"type", "function"}:
                continue
            setattr(tool_param, extra_key, extra_value)

    def _tool_exists(self, tool_name: str) -> bool:
        return tool_name in self.mcp_tools

    def _register_tool(self, tool_param: dict, tool_name: str) -> None:
        self.mcp_tools[tool_name] = tool_param
        self.tools.append(tool_param)

    def _log_tool_update_end(self) -> None:
        logger.info(
            "Tools updated for agent %s, total %s: %s",
            self.name,
            len(self.tools),
            [tool["function"]["name"] for tool in self.tools],
        )
