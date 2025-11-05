import re
import sys


def refine_prompt(prompt: str):
    """Refines the prompt based on the platform.

    On Windows systems, replaces 'bash' with 'powershell' and 'execute_bash' with 'execute_powershell'
    to ensure commands work correctly on the Windows platform.

    Args:
        prompt: The prompt text to refine

    Returns:
        The refined prompt text
    """
    if sys.platform == "win32":
        result = re.sub("\\bexecute_bash\\b", "execute_powershell", prompt, flags=re.IGNORECASE)
        return re.sub("(?<!execute_)(?<!_)\\bbash\\b", "powershell", result, flags=re.IGNORECASE)
    return prompt
