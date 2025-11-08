"""ReadOnlyAgent - A specialized version of CodeActAgent that only uses read-only tools."""

import os
from typing import TYPE_CHECKING

from forge.llm.llm_registry import LLMRegistry

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam

    from forge.events.action import Action
    from forge.llm.llm import ModelResponse
from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.agenthub.readonly_agent import (
    function_calling as readonly_function_calling,
)
from forge.core.config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.utils.prompt import PromptManager


class ReadOnlyAgent(CodeActAgent):
    """Agent variant that restricts actions to read-only interactions."""

    VERSION = "1.0"
    "\n    The ReadOnlyAgent is a specialized version of CodeActAgent that only uses read-only tools.\n\n    This agent is designed for safely exploring codebases without making any changes.\n    It only has access to tools that don't modify the system: grep, glob, view, think, finish, web_read.\n\n    Use this agent when you want to:\n    1. Explore a codebase to understand its structure\n    2. Search for specific patterns or code\n    3. Research without making any changes\n\n    When you're ready to make changes, switch to the regular CodeActAgent.\n    "

    def __init__(self, config: AgentConfig, llm_registry: LLMRegistry) -> None:
        """Initializes a new instance of the ReadOnlyAgent class.

        Parameters:
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(config, llm_registry)
        logger.debug(
            "TOOLS loaded for ReadOnlyAgent: %s",
            ", ".join([tool.get("function").get("name") for tool in self.tools]),
        )

    @property
    def prompt_manager(self) -> PromptManager:
        """Get or create the prompt manager for readonly agent prompts.
        
        Returns:
            PromptManager instance configured for read-only operations

        """
        if self._prompt_manager is None:
            prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
            system_prompt = getattr(self.config, "system_prompt_filename", "system_prompt_ultimate.j2")
            if not os.path.exists(os.path.join(prompt_dir, system_prompt)):
                system_prompt = "system_prompt_ultimate.j2"

            prompt_manager = PromptManager(
                prompt_dir=prompt_dir,
                system_prompt_filename=system_prompt,
            )

            original_get_system_message = prompt_manager.get_system_message

            def get_system_message_with_defaults(**context):
                context.setdefault("config", self.config)
                context.setdefault("cli_mode", getattr(self.config, "cli_mode", False))
                return original_get_system_message(**context)

            prompt_manager.get_system_message = get_system_message_with_defaults  # type: ignore[attr-defined]
            self._prompt_manager = prompt_manager
        return self._prompt_manager

    def _get_tools(self) -> list["ChatCompletionToolParam"]:
        """Get tools available to readonly agent (read, browse, no write operations).
        
        Returns:
            List of read-only tool definitions for LLM function calling

        """
        return readonly_function_calling.get_tools()

    def set_mcp_tools(self, mcp_tools: list[dict]) -> None:
        """Sets the list of MCP tools for the agent.

        Args:
            mcp_tools (list[dict]): The list of MCP tools.

        """
        logger.warning("ReadOnlyAgent does not support MCP tools. MCP tools will be ignored by the agent.")

    def response_to_actions(self, response: "ModelResponse") -> list["Action"]:
        """Convert LLM response into executable readonly actions.
        
        Args:
            response: LLM model response with function calls
            
        Returns:
            List of Action objects parsed from response

        """
        return readonly_function_calling.response_to_actions(response, mcp_tool_names=list(self.mcp_tools.keys()))
