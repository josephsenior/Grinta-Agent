from typing import TYPE_CHECKING

from tenacity.stop import stop_base

from openhands.utils.shutdown_listener import should_exit

if TYPE_CHECKING:
    from tenacity import RetryCallState


class stop_if_should_exit(stop_base):
    """Stop if the should_exit flag is set."""

    def __call__(self, retry_state: "RetryCallState") -> bool:
        return should_exit()
