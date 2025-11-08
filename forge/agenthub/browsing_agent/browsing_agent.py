"""Browser-enabled agent capable of navigating webpages and reporting findings."""

import os

from browsergym.core.action.highlevel import HighLevelActionSet
from browsergym.utils.obs import flatten_axtree_to_str

from forge.agenthub.browsing_agent.response_parser import BrowsingResponseParser
from forge.controller.agent import Agent
from forge.controller.state.state import State
from forge.core.config import AgentConfig
from forge.core.logger import forge_logger as logger
from forge.core.message import Message, TextContent
from forge.events.action import (
    Action,
    AgentFinishAction,
    BrowseInteractiveAction,
    MessageAction,
)
from forge.events.event import EventSource
from forge.events.observation import BrowserOutputObservation
from forge.events.observation.observation import Observation
from forge.llm.llm_registry import LLMRegistry
from forge.runtime.plugins import PluginRequirement

USE_NAV = os.environ.get("USE_NAV", "true") == "true"
USE_CONCISE_ANSWER = os.environ.get("USE_CONCISE_ANSWER", "false") == "true"
EVAL_MODE = not USE_NAV and USE_CONCISE_ANSWER


def get_error_prefix(last_browser_action: str) -> str:
    """Generate error prefix message for incorrect browser actions.

    Args:
        last_browser_action: The last browser action that was incorrect

    Returns:
        Formatted error prefix string

    """
    return f"IMPORTANT! Last action is incorrect:\n{last_browser_action}\nThink again with the current observation of the page.\n"


def get_system_message(goal: str, action_space: str) -> str:
    """Generate system message with goal and available actions.

    Args:
        goal: The goal to accomplish
        action_space: Available action space description

    Returns:
        Formatted system message

    """
    return f"# Instructions\nReview the current state of the page and all other information to find the best\npossible next action to accomplish your goal. Your answer will be interpreted\nand executed by a program, make sure to follow the formatting instructions.\n\n# Goal:\n{goal}\n\n# Action Space\n{action_space}\n"


CONCISE_INSTRUCTION = '\nHere is another example with chain of thought of a valid action when providing a concise answer to user:\n"\nIn order to accomplish my goal I need to send the information asked back to the user. This page list the information of HP Inkjet Fax Machine, which is the product identified in the objective. Its price is $279.49. I will send a message back to user with the answer.\n```send_msg_to_user("$279.49")```\n"\n'


def get_prompt(error_prefix: str, cur_url: str, cur_axtree_txt: str, prev_action_str: str) -> str:
    """Generate prompt for the browsing agent.

    Args:
        error_prefix: Error prefix if last action was incorrect
        cur_url: Current page URL
        cur_axtree_txt: Current accessibility tree text
        prev_action_str: Previous actions string

    Returns:
        Formatted prompt string

    """
    prompt = f'{error_prefix}\n\n# Current Page URL:\n{cur_url}\n\n# Current Accessibility Tree:\n{cur_axtree_txt}\n\n# Previous Actions\n{prev_action_str}\n\nHere is an example with chain of thought of a valid action when clicking on a button:\n"\nIn order to accomplish my goal I need to click on the button with bid 12\n```click("12")```\n"\n'.strip(
    )
    if USE_CONCISE_ANSWER:
        prompt += CONCISE_INSTRUCTION
    return prompt


class BrowsingAgent(Agent):
    """Agent implementation that augments BaseBrowsingAgent with Forge defaults."""

    name = "browsing_agent"
    VERSION = "1.0"
    sandbox_plugins: list[PluginRequirement] = []
    response_parser = BrowsingResponseParser()

    def __init__(
        self,
        config: AgentConfig,
        llm_registry: LLMRegistry,
        plugin_requirements: list[PluginRequirement] | None = None,
    ) -> None:
        """Initialize the browsing agent."""
        super().__init__(config=config, llm_registry=llm_registry)
        self.response_parser = BrowsingResponseParser()
        self.plugin_requirements = plugin_requirements or []

    def reset(self, state: State) -> list[Action]:
        """Reset the agent to the initial state."""
        return [MessageAction(self.get_initial_message(state))]

    def step(self, state: State, observation: Observation) -> list[Action]:
        """Perform a single step in the agent's execution."""
        if EVAL_MODE and len(state.view) == 1:
            return BrowseInteractiveAction(browser_actions="noop()")

        context = self._extract_context_from_state(state)

        if self._should_return_agent_message(context):
            return AgentFinishAction(outputs={"content": context["agent_message"].content})

        if self._should_return_user_message(context):
            return MessageAction(context["last_action"].browsergym_send_msg_to_user)

        if self._should_handle_browser_error(context):
            return self._handle_browser_error(context)

        return self._generate_browsing_action(state, context)

    def _extract_context_from_state(self, state: State) -> dict:
        """Extract context information from state."""
        context = {
            "prev_actions": [],
            "cur_url": "",
            "cur_axtree_txt": "",
            "error_prefix": "",
            "last_obs": None,
            "last_action": None,
            "agent_message": None,
        }

        for event in state.view:
            if isinstance(event, BrowseInteractiveAction):
                context["prev_actions"].append(event.browser_actions)
                context["last_action"] = event
            elif isinstance(event, MessageAction) and event.source == EventSource.AGENT:
                context["agent_message"] = event
            elif isinstance(event, Observation):
                context["last_obs"] = event

        if EVAL_MODE:
            context["prev_actions"] = context["prev_actions"][1:]

        return context

    def _should_return_agent_message(self, context: dict) -> bool:
        """Check if we should return an agent message."""
        return context["agent_message"] is not None

    def _should_return_user_message(self, context: dict) -> bool:
        """Check if we should return a user message."""
        return (
            isinstance(context["last_action"], BrowseInteractiveAction)
            and context["last_action"].browsergym_send_msg_to_user
        )

    def _should_handle_browser_error(self, context: dict) -> bool:
        """Check if we should handle browser error."""
        return isinstance(context["last_obs"], BrowserOutputObservation) and context["last_obs"].error

    def _handle_browser_error(self, context: dict) -> Action:
        """Handle browser error."""
        last_obs = context["last_obs"]
        error_prefix = get_error_prefix(last_obs.last_browser_action)
        self.error_accumulator += 1

        if self.error_accumulator > 5:
            return MessageAction("Too many errors encountered. Task failed.")

        context["error_prefix"] = error_prefix
        context["cur_url"] = last_obs.url

        try:
            context["cur_axtree_txt"] = flatten_axtree_to_str(
                last_obs.axtree_object,
                extra_properties=last_obs.extra_element_properties,
                with_clickable=True,
                filter_visible_only=True,
            )
        except Exception as e:
            logger.error("Error when trying to process the accessibility tree: %s", e)
            return MessageAction("Error encountered when browsing.")

        return None  # Continue with normal processing

    def _generate_browsing_action(self, state: State, context: dict) -> Action:
        """Generate browsing action using LLM."""
        goal, _ = state.get_current_user_intent()
        if goal is None:
            goal = state.inputs["task"]

        system_msg = get_system_message(
            goal,
            self.action_space.describe(with_long_description=False, with_examples=True),
        )
        messages = [Message(role="system", content=[TextContent(text=system_msg)])]

        prev_action_str = "\n".join(context["prev_actions"])
        prompt = get_prompt(context["error_prefix"], context["cur_url"], context["cur_axtree_txt"], prev_action_str)
        messages.append(Message(role="user", content=[TextContent(text=prompt)]))

        response = self.llm.completion(messages=messages, stop=[")```", ")\n```"])
        return self.response_parser.parse(response)
