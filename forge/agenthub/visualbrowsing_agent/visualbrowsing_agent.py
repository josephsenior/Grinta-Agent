"""Visual browsing agent capable of reasoning over screenshots and AX trees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from browsergym.core.action.highlevel import HighLevelActionSet
from browsergym.utils.obs import flatten_axtree_to_str

from forge.agenthub.browsing_agent.response_parser import BrowsingResponseParser
from forge.controller.agent import Agent
from forge.core.logger import forge_logger as logger
from forge.core.message import ImageContent, Message, TextContent
from forge.events.action import (
    Action,
    AgentFinishAction,
    BrowseInteractiveAction,
    MessageAction,
)
from forge.events.event import EventSource
from forge.events.observation import BrowserOutputObservation
from forge.events.observation.observation import Observation

if TYPE_CHECKING:
    from forge.controller.state.state import State
    from forge.core.config import AgentConfig
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement


def get_error_prefix(obs: BrowserOutputObservation) -> str:
    """Generate error prefix from browser observation.

    Args:
        obs: Browser output observation

    Returns:
        Error prefix string or empty if timeout

    """
    if "timeout" in obs.last_browser_action_error:
        return ""
    return f"## Error from previous action:\n{obs.last_browser_action_error}\n"


def create_goal_prompt(goal: str, image_urls: list[str] | None) -> tuple[str, list[str]]:
    """Create goal prompt with optional images.

    Args:
        goal: The goal to accomplish
        image_urls: Optional list of goal image URLs

    Returns:
        Tuple of (goal_text, goal_image_urls)

    """
    goal_txt: str = (
        f"# Instructions\nReview the current state of the page and all other information to find the best possible next action to accomplish your goal. Your answer will be interpreted and executed by a program, make sure to follow the formatting instructions.\n\n## Goal:\n{goal}\n"
    )
    goal_image_urls = []
    if image_urls is not None:
        for idx, url in enumerate(image_urls):
            goal_txt = f"{goal_txt}Images: Goal input image ({idx + 1})\n"
            goal_image_urls.append(url)
    goal_txt += "\n"
    return (goal_txt, goal_image_urls)


def create_observation_prompt(
    axtree_txt: str,
    tabs: str,
    focused_element: str,
    error_prefix: str,
    som_screenshot: str | None,
) -> tuple[str, str | None]:
    """Create observation prompt with accessibility tree and screenshot.

    Args:
        axtree_txt: Accessibility tree text
        tabs: Open tabs information
        focused_element: Currently focused element info
        error_prefix: Error prefix from previous action
        som_screenshot: Optional screenshot URL

    Returns:
        Tuple of (observation_text, screenshot_url)

    """
    txt_observation = f"\n# Observation of current step:\n{tabs}{axtree_txt}{focused_element}{error_prefix}\n"
    screenshot_url = None
    if som_screenshot is not None and len(som_screenshot) > 0:
        txt_observation += "Image: Current page screenshot (Note that only visible portion of webpage is present in the screenshot. You may need to scroll to view the remaining portion of the web-page.\n"
        screenshot_url = som_screenshot
    else:
        logger.info("SOM Screenshot not present in observation!")
    txt_observation += "\n"
    return (txt_observation, screenshot_url)


def get_tabs(obs: BrowserOutputObservation) -> str:
    """Generate tabs information prompt.

    Args:
        obs: Browser output observation

    Returns:
        Formatted tabs information string

    """
    prompt_pieces = ["\n## Currently open tabs:"]
    for page_index, page_url in enumerate(obs.open_pages_urls):
        active_or_not = " (active tab)" if page_index == obs.active_page_index else ""
        prompt_piece = f"Tab {page_index}{active_or_not}:\nURL: {page_url}\n"
        prompt_pieces.append(prompt_piece)
    return "\n".join(prompt_pieces) + "\n"


def get_axtree(axtree_txt: str) -> str:
    """Format accessibility tree with usage instructions.

    Adds explanatory notes about bid identifiers and element visibility.

    Args:
        axtree_txt: Raw accessibility tree text

    Returns:
        Formatted AXTree prompt with instructions

    """
    bid_info = "Note: [bid] is the unique alpha-numeric identifier at the beginning of lines for each element in the AXTree. Always use bid to refer to elements in your actions.\n\n"
    visible_tag_info = 'Note: You can only interact with visible elements. If the "visible" tag is not present, the element is not visible on the page.\n\n'
    return f"\n## AXTree:\n{bid_info}{visible_tag_info}{axtree_txt}\n"


def get_action_prompt(action_set: HighLevelActionSet) -> str:
    """Generate action space prompt with available actions.

    Args:
        action_set: High-level action set configuration

    Returns:
        Formatted action space prompt

    """
    action_set_generic_info = "Note: This action set allows you to interact with your environment. Most of them are python function executing playwright code. The primary way of referring to elements in the page is through bid which are specified in your observations.\n\n"
    action_description = action_set.describe(with_long_description=False, with_examples=False)
    return f"# Action space:\n{action_set_generic_info}{action_description}\n"


def get_history_prompt(prev_actions: list[BrowseInteractiveAction]) -> str:
    """Generate history prompt from previous browser actions.

    Args:
        prev_actions: List of previous browse interactive actions

    Returns:
        Formatted history prompt

    """
    history_prompt = ["# History of all previous interactions with the task:\n"]
    for i in range(len(prev_actions)):
        history_prompt.extend(
            (
                f"## step {
                    i + 1}",
                f"\nOuput thought and action: {
                    prev_actions[i].thought} ```{
                    prev_actions[i].browser_actions}```\n",
            ),
        )
    return "\n".join(history_prompt) + "\n"


class VisualBrowsingAgent(Agent):
    """Agent that integrates visual browsing tools with standard browsing behaviours."""

    name = "visual_browsing_agent"
    VERSION = "1.0"
    sandbox_plugins: list[PluginRequirement] = []
    response_parser = BrowsingResponseParser()

    def __init__(self, config: AgentConfig, llm_registry: LLMRegistry) -> None:
        """Initialize the visual browsing agent with action subsets."""
        super().__init__(config, llm_registry)
        action_subsets = ["chat", "bid", "nav", "tab", "infeas"]
        self.action_space = HighLevelActionSet(subsets=action_subsets, strict=False, multiaction=False)
        self.action_prompt = get_action_prompt(self.action_space)
        self.abstract_example = f"\n# Abstract Example\n\nHere is an abstract version of the answer with description of the content of each tag. Make sure you follow this structure, but replace the content with your answer:\n\nYou must mandatorily think step by step. If you need to make calculations such as coordinates, write them here. Describe the effect that your previous action had on the current content of the page. In summary the next action I will perform is ```{
            self.action_space.example_action(
                abstract=True)}```\n"
        self.concrete_example = "\n# Concrete Example\n\nHere is a concrete example of how to format your answer. Make sure to generate the action in the correct format ensuring that the action is present inside ``````:\n\nLet's think step-by-step. From previous action I tried to set the value of year to \"2022\", using select_option, but it doesn't appear to be in the form. It may be a dynamic dropdown, I will try using click with the bid \"324\" and look at the response from the page. In summary the next action I will perform is ```click('324')```\n"
        self.hints = "\nNote:\n* Make sure to use bid to identify elements when using commands.\n* Interacting with combobox, dropdowns and auto-complete fields can be tricky, sometimes you need to use select_option, while other times you need to use fill or click and wait for the reaction of the page.\n\n"
        self.reset()

    def reset(self) -> None:
        """Reset the agent's internal state."""
        super().reset()
        self.error_accumulator = 0

    def _handle_initial_state(self, state: State) -> Action | None:
        """Handle initial state with noop action."""
        if len(state.view) == 1:
            return BrowseInteractiveAction(browser_actions="noop(1000)", return_axtree=True)
        return None

    def _process_events(self, state: State) -> tuple[list, Action | None, Observation | None]:
        """Process events from state view and extract relevant information."""
        prev_actions = []
        last_obs = None
        last_action = None

        for event in state.view:
            if isinstance(event, BrowseInteractiveAction):
                prev_actions.append(event)
                last_action = event
            elif isinstance(event, MessageAction) and event.source == EventSource.AGENT:
                return [], AgentFinishAction(outputs={"content": event.content}), None
            elif isinstance(event, Observation) and isinstance(event, BrowserOutputObservation):
                last_obs = event

        if prev_actions:
            prev_actions = prev_actions[1:]

        return prev_actions, last_action, last_obs

    def _handle_user_message_action(self, last_action: Action) -> Action | None:
        """Handle user message action from last action."""
        if isinstance(last_action, BrowseInteractiveAction) and last_action.browsergym_send_msg_to_user:
            return MessageAction(last_action.browsergym_send_msg_to_user)
        return None

    def _process_browser_observation(self, last_obs: Observation) -> tuple[str, str, str, str, str]:
        """Process browser observation and extract relevant information."""
        error_prefix = ""
        focused_element = "## Focused element:\nNone\n"
        tabs = ""
        cur_axtree_txt = ""
        set_of_marks = None

        if isinstance(last_obs, BrowserOutputObservation):
            if last_obs.error:
                error_prefix = get_error_prefix(last_obs)
                if len(error_prefix) > 0:
                    self.error_accumulator += 1
                    if self.error_accumulator > 5:
                        msg = "Too many errors encountered. Task failed."
                        raise RuntimeError(msg)

            if last_obs.focused_element_bid is not None:
                focused_element = f"## Focused element:\nbid='{last_obs.focused_element_bid}'\n"

            tabs = get_tabs(last_obs)

            try:
                cur_axtree_txt = flatten_axtree_to_str(
                    last_obs.axtree_object,
                    extra_properties=last_obs.extra_element_properties,
                    with_visible=True,
                    with_clickable=True,
                    with_center_coords=False,
                    with_bounding_box_coords=False,
                    filter_visible_only=False,
                    filter_with_bid_only=False,
                    filter_som_only=False,
                )
                cur_axtree_txt = get_axtree(axtree_txt=cur_axtree_txt)
            except Exception as e:
                logger.error("Error when trying to process the accessibility tree: %s", e)
                msg = "Error encountered when browsing."
                raise RuntimeError(msg)

            set_of_marks = last_obs.set_of_marks

        return error_prefix, focused_element, tabs, cur_axtree_txt, set_of_marks

    def _build_human_prompt(
        self,
        state: State,
        cur_axtree_txt: str,
        tabs: str,
        focused_element: str,
        error_prefix: str,
        set_of_marks: str,
        history_prompt: str,
    ) -> list[TextContent | ImageContent]:
        """Build human prompt for LLM."""
        goal, image_urls = state.get_current_user_intent()
        if goal is None:
            goal = state.inputs["task"]

        goal_txt, goal_images = create_goal_prompt(goal, image_urls)
        observation_txt, som_screenshot = create_observation_prompt(
            cur_axtree_txt,
            tabs,
            focused_element,
            error_prefix,
            set_of_marks,
        )

        human_prompt: list[TextContent | ImageContent] = [TextContent(type="text", text=goal_txt)]

        if len(goal_images) > 0:
            human_prompt.append(ImageContent(image_urls=goal_images))

        human_prompt.append(TextContent(type="text", text=observation_txt))

        if som_screenshot is not None:
            human_prompt.append(ImageContent(image_urls=[som_screenshot]))

        remaining_content = f"\n{history_prompt}{
            self.action_prompt}{
            self.hints}{
            self.abstract_example}{
                self.concrete_example}"
        human_prompt.append(TextContent(type="text", text=remaining_content))

        return human_prompt

    def step(self, state: State) -> Action:
        """Perform one step of visual browsing using the latest environment state."""
        # Handle initial state
        initial_action = self._handle_initial_state(state)
        if initial_action:
            return initial_action

        # Process events from state view
        prev_actions, last_action, last_obs = self._process_events(state)

        # Handle user message action
        user_message_action = self._handle_user_message_action(last_action)
        if user_message_action:
            return user_message_action

        # Process browser observation
        try:
            error_prefix, focused_element, tabs, cur_axtree_txt, set_of_marks = self._process_browser_observation(
                last_obs,
            )
        except Exception as e:
            return MessageAction(str(e))

        # Build prompts and get LLM response
        history_prompt = get_history_prompt(prev_actions)
        human_prompt = self._build_human_prompt(
            state,
            cur_axtree_txt,
            tabs,
            focused_element,
            error_prefix,
            set_of_marks,
            history_prompt,
        )

        system_msg = "You are an agent trying to solve a web task based on the content of the page and user instructions. You can interact with the page and explore, and send messages to the user when you finish the task. Each time you submit an action it will be sent to the browser and you will receive a new page.\n".strip()

        messages = [
            Message(role="system", content=[TextContent(text=system_msg)]),
            Message(role="user", content=human_prompt),
        ]

        response = self.llm.completion(messages=messages, temperature=0.0, stop=[")```", ")\n```"])
        return self.response_parser.parse(response)
