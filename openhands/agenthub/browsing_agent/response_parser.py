from __future__ import annotations

import ast
import re

from openhands.controller.action_parser import ActionParser, ResponseParser
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import Action, BrowseInteractiveAction


class BrowsingResponseParser(ResponseParser):

    def __init__(self) -> None:
        super().__init__()
        self.action_parsers = [BrowsingActionParserMessage()]
        self.default_parser = BrowsingActionParserBrowseInteractive()

    def parse(self, response: str | dict[str, list[dict[str, dict[str, str | None]]]]) -> Action:
        if isinstance(response, str):
            action_str = response
        else:
            action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(self, response: dict[str, list[dict[str, dict[str, str | None]]]]) -> str:
        action_str = response["choices"][0]["message"]["content"]
        if action_str is None:
            return ""
        action_str = action_str.strip()
        if action_str and (not action_str.endswith("```")):
            action_str += "```" if action_str.endswith(")") else ")```"
        logger.debug(action_str)
        return action_str

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


class BrowsingActionParserMessage(ActionParser):
    """Parser action:.

    - BrowseInteractiveAction(browser_actions) - unexpected response format, message back to user.
    """

    def __init__(self) -> None:
        pass

    def check_condition(self, action_str: str) -> bool:
        return "```" not in action_str

    def parse(self, action_str: str) -> Action:
        msg = f'send_msg_to_user("""{action_str}""")'
        return BrowseInteractiveAction(browser_actions=msg, thought=action_str, browsergym_send_msg_to_user=action_str)


class BrowsingActionParserBrowseInteractive(ActionParser):
    """Parser action:.

    - BrowseInteractiveAction(browser_actions) - handle send message to user function call in BrowserGym.
    """

    def __init__(self) -> None:
        pass

    def check_condition(self, action_str: str) -> bool:
        return True

    def parse(self, action_str: str) -> Action:
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
