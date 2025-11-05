from typing import TYPE_CHECKING

from tenacity.stop import stop_base

from openhands.utils.shutdown_listener import should_exit

if TYPE_CHECKING:
    from tenacity import RetryCallState


class stop_if_should_exit(stop_base):
    """Stop if the should_exit flag is set."""

    def __call__(self, retry_state: "RetryCallState") -> bool:
        """Check if retry should stop based on shutdown flag.

        Args:
            retry_state: The retry call state from tenacity.

        Returns:
            bool: True if retry should stop, False otherwise.
        """
        return bool(should_exit())
