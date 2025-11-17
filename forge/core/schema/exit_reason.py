"""Enumeration describing why an agent session terminated."""

from enum import Enum


class ExitReason(Enum):
    """Enum defining reasons why agent execution ended.

    Used to distinguish between normal completion, interruption, and errors.
    """

    INTENTIONAL = "intentional"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    __test__ = False
