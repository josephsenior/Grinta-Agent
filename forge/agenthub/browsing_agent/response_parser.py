"""Utilities for parsing LLM responses into browse actions."""

from __future__ import annotations

import ast
import re

from forge.controller.action_parser import ActionParser, ResponseParser
from forge.core.logger import forge_logger as logger
from forge.events.action import Action, BrowseInteractiveAction


class BrowsingResponseParser(ResponseParser):
    """Parse LLM responses into browsing actions for BrowserGym integration."""

    def __init__(self) -> None:
        """Initialize browsing response parser with action parsers."""
        super().__init__()
        self.action_parsers = [BrowsingActionParserMessage()]
        self.default_parser = BrowsingActionParserBrowseInteractive()

    def parse(self, response: str | dict[str, list[dict[str, dict[str, str | None]]]]) -> Action:
        """Parse LLM response into a browsing action.

        Args:
            response: Raw LLM response (string or dict format)

        Returns:
            Parsed `Action` object for browser interaction.

        """
        if isinstance(response, str):
            action_str = response
        else:
            action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(self, response: dict[str, list[dict[str, dict[str, str | None]]]]) -> str:
        """Extract an action string from a structured LLM response.

        Args:
            response: Structured LLM response with choices.

        Returns:
            Extracted action string with formatting fixes applied.

        """
        action_str = response["choices"][0]["message"]["content"]
        if action_str is None:
            return ""
        action_str = action_str.strip()
        if action_str and (not action_str.endswith("```")):
            action_str += "```" if action_str.endswith(")") else ")```"
        logger.debug(action_str)
        return action_str

    def parse_action(self, action_str: str) -> Action:
        """Parse an action string using the registered parsers.

        Tries each registered parser in order, falling back to the default
        BrowseInteractive parser if no specialized parser matches.

        Args:
            action_str: Action string to parse.

        Returns:
            Parsed `Action` object.

        """
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


class BrowsingActionParserMessage(ActionParser):
    """Parse plain text messages into BrowserGym message actions.

    Handles cases where the LLM response does not contain code blocks,
    treating the entire response as a message to send to the user.
    """

    def __init__(self) -> None:
        """Initialize message parser."""
        pass

    def check_condition(self, action_str: str) -> bool:
        """Check whether the action string is a plain message (no code blocks).

        Args:
            action_str: Action string to check.

        Returns:
            True if the string contains no code block markers.

        """
        return "```" not in action_str

    def parse(self, action_str: str) -> Action:
        """Parse plain text into a `BrowseInteractiveAction` message action.

        Args:
            action_str: Plain text message from the LLM.

        Returns:
            `BrowseInteractiveAction` configured to send a message to the user.

        """
        msg = f'send_msg_to_user("""{action_str}""")'
        return BrowseInteractiveAction(browser_actions=msg, thought=action_str, browsergym_send_msg_to_user=action_str)


class BrowsingActionParserBrowseInteractive(ActionParser):
    """Parse code-block formatted browser actions into browse interactions.

    Extracts browser commands from code blocks and separates them from
    the agent's thoughts. Also extracts any `send_msg_to_user` calls.
    """

    def __init__(self) -> None:
        """Initialize browse interactive parser."""
        pass

    def check_condition(self, action_str: str) -> bool:
        """Return True because this is the fallback parser."""
        return True

    def parse(self, action_str: str) -> Action:
        """Parse browser actions from a code-block formatted response.

        Extracts:
        - Browser actions from code blocks (```)
        - Agent thoughts (text before code block)
        - User messages from `send_msg_to_user()` calls

        Args:
            action_str: LLM response with code blocks.

        Returns:
            `BrowseInteractiveAction` with the extracted components.

        """
        parts = action_str.split("```")
        browser_actions = parts[1].strip() if parts[1].strip() != "" else parts[0].strip()
        thought = parts[0].strip() if parts[1].strip() != "" else ""
        msg_content = ""
        for sub_action in browser_actions.split("\n"):
            if "send_msg_to_user(" in sub_action:
                try:
                    tree = ast.parse(sub_action)
                    args = tree.body[0].value.args
                    msg_content = args[0].value
                except SyntaxError:
                    logger.error("Error parsing action: %s", sub_action)
                    if match := re.search("send_msg_to_user\\(([\"\\'])(.*?)\\1\\)", sub_action):
                        msg_content = match[2]
                    else:
                        msg_content = ""
        return BrowseInteractiveAction(
            browser_actions=browser_actions,
            thought=thought,
            browsergym_send_msg_to_user=msg_content,
        )
