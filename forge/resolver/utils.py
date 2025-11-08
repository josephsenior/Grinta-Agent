"""Shared utility helpers for resolver workflows and agent interactions."""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import re
from typing import TYPE_CHECKING, Callable

from pydantic import SecretStr

from forge.core.logger import get_console_handler
from forge.core.logger import forge_logger as logger
from forge.events.action import Action
from forge.events.action.message import MessageAction
from forge.integrations.utils import validate_provider_token

if TYPE_CHECKING:
    from forge.controller.state.state import State
    from forge.integrations.service_types import ProviderType


async def identify_token(token: str, base_domain: str | None) -> ProviderType:
    """Identifies whether a token belongs to GitHub, GitLab, or Bitbucket.

    Parameters:
        token (str): The personal access token to check.
        base_domain (str): Custom base domain for provider (e.g GitHub Enterprise).
    """
    provider = await validate_provider_token(SecretStr(token), base_domain)
    if not provider:
        msg = "Token is invalid."
        raise ValueError(msg)
    return provider


def codeact_user_response(
    state: State,
    encapsulate_solution: bool = False,
    try_parse: Callable[[Action | None], str] | None = None,
) -> str:
    """Generate a user response for CodeAct agent interaction.

    Args:
        state: The current agent state
        encapsulate_solution: Whether to request solution encapsulation in tags
        try_parse: Optional function to parse the last action and determine if task is complete

    Returns:
        The user response message to continue or exit the interaction

    """
    base_msg = _build_base_message(encapsulate_solution)

    if not state.history:
        return base_msg

    # Check if task is complete via try_parse
    if try_parse and _is_task_complete(state, try_parse):
        return "/exit"

    # Add give-up option if multiple user messages
    return _add_giveup_option(base_msg, state)


def _build_base_message(encapsulate_solution: bool) -> str:
    """Build the base continuation message.

    Args:
        encapsulate_solution: Whether to include solution encapsulation instructions

    Returns:
        Base message string

    """
    encaps_str = (
        "Please encapsulate your final answer (answer ONLY) within <solution> and </solution>.\n"
        "For example: The answer to the question is <solution> 42 </solution>.\n"
        if encapsulate_solution
        else ""
    )

    return (
        "Please continue working on the task on whatever approach you think is suitable.\n"
        "If you think you have solved the task, please first send your answer to user through message and then finish the interaction.\n"
        f"{encaps_str}IMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n"
    )


def _is_task_complete(state: State, try_parse: Callable) -> bool:
    """Check if task is complete using try_parse function.

    Args:
        state: Current agent state
        try_parse: Function to parse completion

    Returns:
        True if task is complete

    """
    last_action = next((event for event in reversed(state.history) if isinstance(event, Action)), None)
    ans = try_parse(last_action)
    return ans is not None


def _add_giveup_option(base_msg: str, state: State) -> str:
    """Add give-up option if multiple user messages exist.

    Args:
        base_msg: Base message
        state: Current agent state

    Returns:
        Message with or without give-up option

    """
    user_msgs = [event for event in state.history if isinstance(event, MessageAction) and event.source == "user"]

    if len(user_msgs) >= 2:
        return base_msg + "If you want to give up, run: <execute_bash> exit </execute_bash>.\n"

    return base_msg


def cleanup() -> None:
    """Clean up child processes created during resolver execution.

    This function terminates all active child processes and waits for them to complete.
    """
    logger.info("Cleaning up child processes...")
    for process in mp.active_children():
        logger.info("Terminating child process: %s", process.name)
        process.terminate()
        process.join()


def reset_logger_for_multiprocessing(logger: logging.Logger, instance_id: str, log_dir: str) -> None:
    """Reset the logger for multiprocessing.

    Save logs to a separate file for each process, instead of trying to write to the
    same file/console from multiple processes.
    """
    log_file = os.path.join(log_dir, f"instance_{instance_id}.log")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.addHandler(get_console_handler())
    logger.info(
        'Starting resolver for instance %s.\nHint: run "tail -f %s" to see live logs in a separate shell',
        instance_id,
        log_file,
    )
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)


def extract_image_urls(issue_body: str) -> list[str]:
    """Extract image URLs from markdown-formatted issue body text.

    Args:
        issue_body: The issue body text containing markdown image references.

    Returns:
        list[str]: List of extracted image URLs.

    """
    image_pattern = "!\\[.*?\\]\\((https?://[^\\s)]+)\\)"
    return re.findall(image_pattern, issue_body)


def extract_issue_references(body: str) -> list[int]:
    """Extract issue reference numbers from text body.

    Args:
        body: The text body that may contain issue references like #123.

    Returns:
        list[int]: List of extracted issue reference numbers.

    """
    body = re.sub("```.*?```", "", body, flags=re.DOTALL)
    body = re.sub("`[^`]*`", "", body)
    body = re.sub("https?://[^\\s)]*#\\d+[^\\s)]*", "", body)
    pattern = "(?:^|[\\s\\[({]|[^\\w#])#(\\d+)(?=[\\s,.\\])}]|$)"
    return [int(match) for match in re.findall(pattern, body)]


def get_unique_uid(start_uid: int = 1000) -> int:
    """Generate a unique UID starting from the specified value.

    Args:
        start_uid: The starting UID value (default: 1000).

    Returns:
        int: A unique UID that hasn't been used before.

    """
    existing_uids = set()
    with open("/etc/passwd", encoding="utf-8") as passwd_file:
        for line in passwd_file:
            parts = line.split(":")
            if len(parts) > 2:
                try:
                    existing_uids.add(int(parts[2]))
                except ValueError:
                    continue
    while start_uid in existing_uids:
        start_uid += 1
    return start_uid
