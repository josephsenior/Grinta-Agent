"""Action types for executing shell and IPython commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from forge.core.schema import ActionType
from forge.events.action.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
)


@dataclass
class CmdRunAction(Action):
    """Action to run a shell command.
    
    Attributes:
        command: Shell command to execute
        is_input: Whether command is user input (for stdin)
        thought: Agent's reasoning for this action
        blocking: Whether to wait for command to complete
        is_static: Whether command is static (from static analysis)
        cwd: Working directory for command
        hidden: Whether to hide command from user

    """
    command: str
    is_input: bool = False
    thought: str = ""
    blocking: bool = False
    is_static: bool = False
    cwd: str | None = None
    hidden: bool = False
    action: str = ActionType.RUN
    runnable: ClassVar[bool] = True
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN

    @property
    def message(self) -> str:
        """Get command execution message."""
        return f"Running command: {self.command}"

    def __str__(self) -> str:
        """Return a readable summary including command metadata."""
        ret = f"**CmdRunAction (source={self.source}, is_input={self.is_input})**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        ret += f"COMMAND:\n{self.command}"
        return ret

    __test__ = False


@dataclass
class IPythonRunCellAction(Action):
    """Action to run Python code in Jupyter kernel.
    
    Attributes:
        code: Python code to execute
        thought: Agent's reasoning for this action
        include_extra: Whether to include extra output (plots, etc.)
        kernel_init_code: Code to run before executing main code

    """
    code: str
    thought: str = ""
    include_extra: bool = True
    action: str = ActionType.RUN_IPYTHON
    runnable: ClassVar[bool] = True
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN
    kernel_init_code: str = ""

    def __str__(self) -> str:
        """Return a readable summary including thought and code snippet."""
        ret = "**IPythonRunCellAction**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        ret += f"CODE:\n{self.code}"
        return ret

    @property
    def message(self) -> str:
        """Get IPython execution message."""
        return f"Running Python code interactively: {self.code}"

    __test__ = False
