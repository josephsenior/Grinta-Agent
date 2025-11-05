from __future__ import annotations

import io
import re
from itertools import chain
from pathlib import Path
from typing import ClassVar

import frontmatter
from pydantic import BaseModel

from openhands.core.exceptions import MicroagentValidationError
from openhands.core.logger import openhands_logger as logger
from openhands.microagent.types import InputMetadata, MicroagentMetadata, MicroagentType


def _finalize_loaded_microagent(metadata_dict, path):
    """Finalize the loaded microagent metadata by ensuring proper types.

    Args:
        metadata_dict: Dictionary containing microagent metadata.
        path: Path to the microagent file.

    Returns:
        MicroagentMetadata: Finalized metadata object.
    """
    if "version" in metadata_dict and (not isinstance(metadata_dict["version"], str)):
        metadata_dict["version"] = str(metadata_dict["version"])
    return MicroagentMetadata(**metadata_dict)


def _infer_microagent_type(metadata):
    """Infer the microagent type from metadata.

    Args:
        metadata: The microagent metadata.

    Returns:
        MicroagentType: The inferred type of the microagent.
    """
    inferred_type: MicroagentType
    if metadata.inputs:
        inferred_type = MicroagentType.TASK
        trigger = f"/{metadata.name}"
        if not metadata.triggers:
            metadata.triggers = [trigger]
        elif trigger not in metadata.triggers:
            metadata.triggers.append(trigger)
    elif metadata.triggers:
        inferred_type = MicroagentType.KNOWLEDGE
    else:
        inferred_type = MicroagentType.REPO_KNOWLEDGE
    return inferred_type


class BaseMicroagent(BaseModel):
    """Base class for all microagents."""

    name: str
    content: str
    metadata: MicroagentMetadata
    source: str
    type: MicroagentType
    PATH_TO_THIRD_PARTY_MICROAGENT_NAME: ClassVar[dict[str, str]] = {
        ".cursorrules": "cursorrules",
        "agents.md": "agents",
        "agent.md": "agents",
    }

    @classmethod
    def _handle_third_party(cls, path: Path, file_content: str) -> RepoMicroagent | None:
        microagent_name = cls.PATH_TO_THIRD_PARTY_MICROAGENT_NAME.get(path.name.lower())
        if microagent_name is not None:
            return RepoMicroagent(
                name=microagent_name,
                content=file_content,
                metadata=MicroagentMetadata(name=microagent_name),
                source=str(path),
                type=MicroagentType.REPO_KNOWLEDGE,
            )
        return None

    @classmethod
    def _resolve_path(cls, path: Path) -> Path:
        """Safely resolve path."""
        try:
            return path.resolve()
        except Exception:
            return Path(path)

    @classmethod
    def _derive_microagent_name(cls, path: Path, microagent_dir: Path) -> str | None:
        """Derive microagent name from path relative to microagent_dir."""
        third_party_name = cls.PATH_TO_THIRD_PARTY_MICROAGENT_NAME.get(path.name.lower())
        if third_party_name is not None:
            return third_party_name

        # Try relative path
        try:
            rel = path.relative_to(microagent_dir).with_suffix("")
            return str(rel).replace("\\", "/")
        except Exception:
            pass

        # Try os.path.relpath as fallback
        import os

        try:
            rel = os.path.relpath(str(path), start=str(microagent_dir))
            rel = os.path.splitext(rel)[0]
            return rel.replace("\\", "/")
        except Exception:
            return None

    @classmethod
    def _load_file_content(cls, path: Path, file_content: str | None) -> str:
        """Load file content from path if not provided."""
        if file_content is not None:
            return file_content
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()

    @classmethod
    def _create_microagent_instance(
        cls,
        derived_name: str | None,
        content: str,
        metadata: MicroagentMetadata,
        path: Path,
        inferred_type: MicroagentType,
    ) -> BaseMicroagent:
        """Create appropriate microagent instance based on type."""
        subclass_map = {
            MicroagentType.KNOWLEDGE: KnowledgeMicroagent,
            MicroagentType.REPO_KNOWLEDGE: RepoMicroagent,
            MicroagentType.TASK: TaskMicroagent,
        }

        if inferred_type not in subclass_map:
            msg = f"Could not determine microagent type for: {path}"
            raise ValueError(msg)

        agent_name = derived_name if derived_name is not None else metadata.name
        agent_class = subclass_map[inferred_type]
        return agent_class(name=agent_name, content=content, metadata=metadata, source=str(path), type=inferred_type)

    @classmethod
    def load(
        cls,
        path: str | Path,
        microagent_dir: Path | None = None,
        file_content: str | None = None,
    ) -> BaseMicroagent:
        """Load a microagent from a markdown file with frontmatter.

        The agent's name is derived from its path relative to the microagent_dir.
        """
        path = Path(path) if isinstance(path, str) else path
        path = cls._resolve_path(path)

        # Derive name from directory structure
        derived_name = None
        if microagent_dir is not None:
            microagent_dir = cls._resolve_path(microagent_dir)
            derived_name = cls._derive_microagent_name(path, microagent_dir)

        # Load file content
        file_content = cls._load_file_content(path, file_content)

        # Handle legacy repo instructions
        if path.name == ".openhands_instructions":
            return RepoMicroagent(
                name="repo_legacy",
                content=file_content,
                metadata=MicroagentMetadata(name="repo_legacy"),
                source=str(path),
                type=MicroagentType.REPO_KNOWLEDGE,
            )

        # Handle third-party agents
        third_party_agent = cls._handle_third_party(path, file_content)
        if third_party_agent is not None:
            return third_party_agent

        # Parse frontmatter and create microagent
        file_io = io.StringIO(file_content)
        loaded = frontmatter.load(file_io)
        content = loaded.content
        metadata_dict = loaded.metadata or {}
        if "version" in metadata_dict and (not isinstance(metadata_dict["version"], str)):
            metadata_dict["version"] = str(metadata_dict["version"])
        metadata = _finalize_loaded_microagent(metadata_dict, path)
        inferred_type = _infer_microagent_type(metadata)

        return cls._create_microagent_instance(derived_name, content, metadata, path, inferred_type)


class KnowledgeMicroagent(BaseMicroagent):
    """Knowledge micro-agents provide specialized expertise that's triggered by keywords in conversations.

    They help with:
    - Language best practices
    - Framework guidelines
    - Common patterns
    - Tool usage
    """

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.type not in [MicroagentType.KNOWLEDGE, MicroagentType.TASK]:
            msg = "KnowledgeMicroagent must have type KNOWLEDGE or TASK"
            raise ValueError(msg)

    def match_trigger(self, message: str) -> str | None:
        """Match a trigger in the message.

        It returns the first trigger that matches the message.
        """
        message = message.lower()
        return next((trigger for trigger in self.triggers if trigger.lower() in message), None)

    @property
    def triggers(self) -> list[str]:
        return self.metadata.triggers


class RepoMicroagent(BaseMicroagent):
    """Microagent specialized for repository-specific knowledge and guidelines.

    RepoMicroagents are loaded from `.openhands/microagents/repo.md` files within repositories
    and contain private, repository-specific instructions that are automatically loaded when
    working with that repository. They are ideal for:
        - Repository-specific guidelines
        - Team practices and conventions
        - Project-specific workflows
        - Custom documentation references
    """

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.type != MicroagentType.REPO_KNOWLEDGE:
            msg = f"RepoMicroagent initialized with incorrect type: {self.type}"
            raise ValueError(msg)


class TaskMicroagent(KnowledgeMicroagent):
    """TaskMicroagent is a special type of KnowledgeMicroagent that requires user input.

    These microagents are triggered by a special format: "/{agent_name}"
    and will prompt the user for any required inputs before proceeding.
    """

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.type != MicroagentType.TASK:
            msg = f"TaskMicroagent initialized with incorrect type: {self.type}"
            raise ValueError(msg)
        self._append_missing_variables_prompt()

    def _append_missing_variables_prompt(self) -> None:
        """Append a prompt to ask for missing variables."""
        if not self.requires_user_input() and (not self.metadata.inputs):
            return
        prompt = "\n\nIf the user didn't provide any of these variables, ask the user to provide them first before the agent can proceed with the task."
        self.content += prompt

    def extract_variables(self, content: str) -> list[str]:
        """Extract variables from the content.

        Variables are in the format ${variable_name}.
        """
        pattern = "\\$\\{([a-zA-Z_][a-zA-Z0-9_]*)\\}"
        return re.findall(pattern, content)

    def requires_user_input(self) -> bool:
        """Check if this microagent requires user input.

        Returns True if the content contains variables in the format ${variable_name}.
        """
        variables = self.extract_variables(self.content)
        logger.debug("This microagent requires user input: %s", variables)
        return len(variables) > 0

    @property
    def inputs(self) -> list[InputMetadata]:
        """Get the inputs for this microagent."""
        return self.metadata.inputs


def _collect_special_files(repo_root: Path) -> list[Path]:
    """Collect special configuration files from the repository root.

    Args:
        repo_root: The repository root path.

    Returns:
        list[Path]: List of special files found.
    """
    special_files = []

    # Add .cursorrules if it exists
    if (repo_root / ".cursorrules").exists():
        special_files.append(repo_root / ".cursorrules")

    # Add agents markdown files if they exist
    for agents_filename in ["AGENTS.md", "agents.md", "AGENT.md", "agent.md"]:
        agents_path = repo_root / agents_filename
        if agents_path.exists():
            special_files.append(agents_path)
            break

    return special_files


def _collect_markdown_files(microagent_dir: Path) -> list[Path]:
    """Collect markdown files from the microagent directory.

    Args:
        microagent_dir: The microagent directory path.

    Returns:
        list[Path]: List of markdown files found.
    """
    if not microagent_dir.exists():
        return []

    return [f for f in microagent_dir.rglob("*.md") if f.name != "README.md"]


def _load_single_microagent(file: Path, microagent_dir: Path) -> BaseMicroagent:
    """Load a single microagent from a file.

    Args:
        file: The file path to load from.
        microagent_dir: The microagent directory path.

    Returns:
        BaseMicroagent: The loaded microagent.

    Raises:
        MicroagentValidationError: If validation fails.
        ValueError: If loading fails.
    """
    try:
        return BaseMicroagent.load(file, microagent_dir)
    except MicroagentValidationError as e:
        error_msg = f"Error loading microagent from {file}: {e!s}"
        raise MicroagentValidationError(error_msg) from e
    except Exception as e:
        error_msg = f"Error loading microagent from {file}: {e!s}"
        raise ValueError(error_msg) from e


def _categorize_agent(agent: BaseMicroagent) -> tuple[str, BaseMicroagent]:
    """Categorize an agent by its type.

    Args:
        agent: The agent to categorize.

    Returns:
        tuple[str, BaseMicroagent]: Agent type and the agent itself.
    """
    if isinstance(agent, RepoMicroagent):
        return ("repo", agent)
    if isinstance(agent, KnowledgeMicroagent):
        return ("knowledge", agent)
    return ("unknown", agent)


def load_microagents_from_dir(
    microagent_dir: str | Path,
) -> tuple[dict[str, RepoMicroagent], dict[str, KnowledgeMicroagent]]:
    """Load all microagents from the given directory.

    Note, legacy repo instructions will not be loaded here.

    Args:
        microagent_dir: Path to the microagents directory (e.g. .openhands/microagents)

    Returns:
        tuple[dict[str, RepoMicroagent], dict[str, KnowledgeMicroagent]]: Tuple of (repo_agents, knowledge_agents) dictionaries
    """
    if isinstance(microagent_dir, str):
        microagent_dir = Path(microagent_dir)

    repo_agents = {}
    knowledge_agents = {}
    logger.debug("Loading agents from %s", microagent_dir)

    # Collect files to process
    repo_root = microagent_dir.parent.parent
    special_files = _collect_special_files(repo_root)
    md_files = _collect_markdown_files(microagent_dir)

    # Load agents from all files
    for file in chain(special_files, md_files):
        agent = _load_single_microagent(file, microagent_dir)
        agent_type, agent = _categorize_agent(agent)

        if agent_type == "repo":
            repo_agents[agent.name] = agent
        elif agent_type == "knowledge":
            knowledge_agents[agent.name] = agent

    logger.debug(
        "Loaded %s microagents: %s",
        len(repo_agents) + len(knowledge_agents),
        [*repo_agents.keys(), *knowledge_agents.keys()],
    )
    return (repo_agents, knowledge_agents)
