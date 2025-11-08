from abc import ABC, abstractmethod
from pydantic import BaseModel
from forge.events.event import Event
from forge.runtime.base import Runtime


class TestResult(BaseModel):
    success: bool
    reason: str | None = None


class BaseIntegrationTest(ABC):
    """Base class for integration tests."""

    INSTRUCTION: str

    @classmethod
    @abstractmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        """Initialize the runtime for the test to run."""

    @classmethod
    @abstractmethod
    def verify_result(cls, runtime: Runtime, histories: list[Event]) -> TestResult:
        """Verify the result of the test.

        This method will be called after the agent performs the task on the runtime.
        """
