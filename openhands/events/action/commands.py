from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from openhands.core.schema import ActionType
from openhands.events.action.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
)


@dataclass
class CmdRunAction(Action):
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
        return f"Running command: {self.command}"

    def __str__(self) -> str:
        ret = f"**CmdRunAction (source={self.source}, is_input={self.is_input})**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        ret += f"COMMAND:\n{self.command}"
        return ret

    __test__ = False


@dataclass
class IPythonRunCellAction(Action):
    code: str
    thought: str = ""
    include_extra: bool = True
    action: str = ActionType.RUN_IPYTHON
    runnable: ClassVar[bool] = True
    confirmation_state: ActionConfirmationStatus = ActionConfirmationStatus.CONFIRMED
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN
    kernel_init_code: str = ""

    def __str__(self) -> str:
        ret = "**IPythonRunCellAction**\n"
        if self.thought:
            ret += f"THOUGHT: {self.thought}\n"
        ret += f"CODE:\n{self.code}"
        return ret

    @property
    def message(self) -> str:
        return f"Running Python code interactively: {self.code}"

    __test__ = False
