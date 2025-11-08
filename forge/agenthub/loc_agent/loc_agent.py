"""Opinionated CodeAct derivative tuned for light-on-context workflows."""

from typing import TYPE_CHECKING, ClassVar

import forge.agenthub.loc_agent.function_calling as locagent_function_calling
from forge.agenthub.codeact_agent import CodeActAgent
from forge.core.config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.llm.llm_registry import LLMRegistry

if TYPE_CHECKING:
    from forge.events.action import Action
    from forge.llm.llm import ModelResponse


class LocAgent(CodeActAgent):
    """LoC agent specialized with Forge defaults for the agent hub."""

    name: ClassVar[str] = "loc_agent"
    VERSION = "1.0"

    def __init__(self, config: AgentConfig, llm_registry: LLMRegistry) -> None:
        """Initialize the LoCAgent with Forge defaults and tool registry."""
        super().__init__(config, llm_registry)
        self.tools = locagent_function_calling.get_tools()
        logger.debug(
            "TOOLS loaded for LocAgent: %s",
            ", ".join([tool.get("function").get("name") for tool in self.tools]),
        )

    def response_to_actions(self, response: "ModelResponse") -> list["Action"]:
        """Convert an LLM response into executable LoCAgent actions.

        Args:
            response: LLM model response with function calls.

        Returns:
            Parsed list of `Action` objects.

        """
        return locagent_function_calling.response_to_actions(response, mcp_tool_names=list(self.mcp_tools.keys()))
