"""Helpers for adapting tool prompts to the current platform."""

import re
import sys


def refine_prompt(prompt: str):
    """Refine the prompt based on the current platform.

    On Windows systems, replaces 'bash' with 'powershell' and 'execute_bash' with 'execute_powershell'
    to ensure commands work correctly on the Windows platform.

    Args:
        prompt: The prompt text to refine

    Returns:
        The refined prompt text.

    """
    if sys.platform == "win32":
        result = re.sub(r"\bexecute_bash\b", "execute_powershell", prompt, flags=re.IGNORECASE)
        return re.sub(r"(?<!execute_)(?<!_)\bbash\b", "powershell", result, flags=re.IGNORECASE)
    return prompt
