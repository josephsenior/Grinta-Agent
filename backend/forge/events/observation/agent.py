"""Agent-scoped observation types emitted by Forge event stream."""

from dataclasses import dataclass, field
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from forge.storage.data_models.knowledge_base import KnowledgeBaseSearchResult

from forge.core.schemas import ObservationType
from forge.events.event import RecallType
from forge.events.observation.observation import Observation


@dataclass
class AgentStateChangedObservation(Observation):
    """This data class represents an observation of an agent's state change."""

    agent_state: str
    reason: str = ""
    observation: ClassVar[str] = ObservationType.AGENT_STATE_CHANGED

    @property
    def message(self) -> str:
        """Get message (empty for state change observations)."""
        return ""

    __test__ = False


@dataclass
class AgentCondensationObservation(Observation):
    """The output of a condensation action."""

    observation: ClassVar[str] = ObservationType.CONDENSE

    @property
    def message(self) -> str:
        """Get condensation result message."""
        return self.content

    __test__ = False


@dataclass
class AgentThinkObservation(Observation):
    """The output of a think action.

    In practice, this is a no-op, since it will just reply a static message to the agent
    acknowledging that the thought has been logged.
    """

    observation: ClassVar[str] = ObservationType.THINK

    @property
    def message(self) -> str:
        """Get acknowledgment message."""
        return self.content

    __test__ = False


@dataclass
class MicroagentKnowledge:
    """Represents knowledge from a triggered microagent.

    Attributes:
        name: The name of the microagent that was triggered
        trigger: The word that triggered this microagent
        content: The actual content/knowledge from the microagent

    """

    name: str
    trigger: str
    content: str
    __test__ = False


@dataclass
class RecallObservation(Observation):
    """The retrieval of content from a microagent or more microagents."""

    recall_type: RecallType
    repo_name: str = ""
    repo_directory: str = ""
    repo_branch: str = ""
    repo_instructions: str = ""
    runtime_hosts: dict[str, int] = field(default_factory=dict)
    additional_agent_instructions: str = ""
    date: str = ""
    custom_secrets_descriptions: dict[str, str] = field(default_factory=dict)
    conversation_instructions: str = ""
    working_dir: str = ""
    microagent_knowledge: list[MicroagentKnowledge] = field(default_factory=list)
    knowledge_base_results: list["KnowledgeBaseSearchResult"] = field(
        default_factory=list
    )
    '\n    A list of MicroagentKnowledge objects, each containing information from a triggered microagent.\n\n    Example:\n    [\n        MicroagentKnowledge(\n            name="python_best_practices",\n            trigger="python",\n            content="Always use virtual environments for Python projects."\n        ),\n        MicroagentKnowledge(\n            name="git_workflow",\n            trigger="git",\n            content="Create a new branch for each feature or bugfix."\n        )\n    ]\n    '
    observation: ClassVar[str] = ObservationType.RECALL

    @property
    def message(self) -> str:
        """Get recall completion message based on recall type."""
        return (
            "Added workspace context"
            if self.recall_type == RecallType.WORKSPACE_CONTEXT
            else "Added microagent knowledge"
        )

    def __str__(self) -> str:
        """Return a readable summary of the recall payload."""
        fields = []
        if self.recall_type == RecallType.WORKSPACE_CONTEXT:
            fields.extend(
                [
                    f"recall_type={self.recall_type}",
                    f"repo_name={self.repo_name}",
                    f"repo_instructions={self.repo_instructions[:20]}...",
                    f"runtime_hosts={self.runtime_hosts}",
                    f"additional_agent_instructions={self.additional_agent_instructions[:20]}...",
                    f"date={self.date}custom_secrets_descriptions={self.custom_secrets_descriptions}",
                    f"conversation_instructions={self.conversation_instructions[:20]}...",
                ],
            )
        else:
            fields.extend([f"recall_type={self.recall_type}"])
        if self.microagent_knowledge:
            fields.extend(
                [
                    f"microagent_knowledge={', '.join([m.name for m in self.microagent_knowledge])}"
                ]
            )
        return f"**RecallObservation**\n{', '.join(fields)}"

    __test__ = False


@dataclass
class RecallFailureObservation(Observation):
    """Represents a failure to complete a recall request (workspace or knowledge).

    Provides structured fields to help downstream components distinguish recall failures
    from generic errors and clear pending recall actions without altering iteration semantics.
    """

    recall_type: RecallType | None = None
    error_message: str = ""
    observation: ClassVar[str] = ObservationType.RECALL_FAILURE

    @property
    def message(self) -> str:
        return self.error_message or self.content

    __test__ = False
