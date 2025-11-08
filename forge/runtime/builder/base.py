"""Abstract base class for building runtime execution environments."""

from __future__ import annotations

import abc


class RuntimeBuilder(abc.ABC):
    """Abstract builder responsible for preparing runtimes (images, deps)."""

    def __init__(self) -> None:
        """Initialize the runtime builder."""
        super().__init__()

    @abc.abstractmethod
    def image_exists(self, image_name: str, pull_from_repo: bool = True) -> bool:
        """Check if the runtime image exists."""
        raise NotImplementedError

    @abc.abstractmethod
    def build(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
    ) -> str:
        """Build the runtime image and return the primary tag."""
        raise NotImplementedError
