"""This class is similar to the RuntimeStatus defined in the runtime api. (When this class was defined.

a RuntimeStatus class already existed in OpenHands which serves a completely different purpose) Some of
the status definitions do not match up.

STOPPED/paused - the runtime is not running but may be restarted
ARCHIVED/stopped - the runtime is not running and will not restart due to deleted files.
"""

from enum import Enum


class ConversationStatus(Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ARCHIVED = "ARCHIVED"
    ERROR = "ERROR"
    __test__ = False
