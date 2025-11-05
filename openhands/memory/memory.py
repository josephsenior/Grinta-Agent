from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import openhands
from openhands.core.logger import openhands_logger as logger
from openhands.events.action.agent import RecallAction
from openhands.events.event import Event, EventSource, RecallType
from openhands.events.observation.agent import MicroagentKnowledge, RecallObservation
from openhands.events.observation.empty import NullObservation
from openhands.events.stream import EventStream, EventStreamSubscriber
from openhands.microagent import (
    BaseMicroagent,
    KnowledgeMicroagent,
    RepoMicroagent,
    load_microagents_from_dir,
)
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.utils.prompt import ConversationInstructions, RepositoryInfo, RuntimeInfo

if TYPE_CHECKING:
    from openhands.core.config.mcp_config import MCPConfig
    from openhands.runtime.base import Runtime

GLOBAL_MICROAGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(openhands.__file__)), "microagents")
USER_MICROAGENTS_DIR = Path.home() / ".openhands" / "microagents"


class Memory:
    """Memory is a component that listens to the EventStream for information retrieval actions.

    (a RecallAction) and publishes observations with the content (such as RecallObservation).
    """

    sid: str
    event_stream: EventStream
    status_callback: Callable | None
    loop: asyncio.AbstractEventLoop | None
    repo_microagents: dict[str, RepoMicroagent]
    knowledge_microagents: dict[str, KnowledgeMicroagent]

    def __init__(self, event_stream: EventStream, sid: str, status_callback: Callable | None = None) -> None:
        self.event_stream = event_stream
        self.sid = sid or str(uuid.uuid4())
        self.status_callback = status_callback
        self.loop = None
        self.event_stream.subscribe(EventStreamSubscriber.MEMORY, self.on_event, self.sid)
        self.repo_microagents = {}
        self.knowledge_microagents = {}
        self.repository_info: RepositoryInfo | None = None
        self.runtime_info: RuntimeInfo | None = None
        self.conversation_instructions: ConversationInstructions | None = None
        self._load_global_microagents()
        self._load_user_microagents()

    def on_event(self, event: Event) -> None:
        """Handle an event from the event stream."""
        asyncio.get_event_loop().run_until_complete(self._on_event(event))

    async def _on_event(self, event: Event) -> None:
        """Handle an event from the event stream asynchronously."""
        try:
            if isinstance(event, RecallAction):
                if event.source == EventSource.USER and event.recall_type == RecallType.WORKSPACE_CONTEXT:
                    logger.debug("Workspace context recall")
                    workspace_obs: RecallObservation | NullObservation | None = None
                    workspace_obs = self._on_workspace_context_recall(event)
                    if workspace_obs is None:
                        workspace_obs = NullObservation(content="")
                    workspace_obs._cause = event.id
                    self.event_stream.add_event(workspace_obs, EventSource.ENVIRONMENT)
                    return
                if event.source in [EventSource.USER, EventSource.AGENT] and event.recall_type == RecallType.KNOWLEDGE:
                    logger.debug("Microagent knowledge recall from %s message", event.source)
                    microagent_obs: RecallObservation | NullObservation | None = None
                    microagent_obs = self._on_microagent_recall(event)
                    if microagent_obs is None:
                        microagent_obs = NullObservation(content="")
                    microagent_obs._cause = event.id
                    self.event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)
                    return
        except Exception as e:
            error_str = f"Error: {e.__class__.__name__!s}"
            logger.error(error_str)
            logger.info('MEMORY: about to call set_runtime_status with ERROR_MEMORY (msg="%s")', error_str)
            self.set_runtime_status(RuntimeStatus.ERROR_MEMORY, error_str)
            return

    def _collect_repo_instructions(self) -> str:
        """Collect repository instructions from all repo microagents."""
        repo_instructions = ""
        for microagent in self.repo_microagents.values():
            if repo_instructions:
                repo_instructions += "\n\n"
            repo_instructions += microagent.content
        return repo_instructions

    def _should_create_recall_observation(self, repo_instructions: str, microagent_knowledge: list) -> bool:
        """Check if we should create a recall observation based on available data."""
        return (
            self.repository_info
            or self.runtime_info
            or repo_instructions
            or microagent_knowledge
            or self.conversation_instructions
        )

    def _get_repo_info_fields(self) -> dict[str, str]:
        """Get repository information fields."""
        return {
            "repo_name": (
                self.repository_info.repo_name
                if self.repository_info and self.repository_info.repo_name is not None
                else ""
            ),
            "repo_directory": (
                self.repository_info.repo_directory
                if self.repository_info and self.repository_info.repo_directory is not None
                else ""
            ),
            "repo_branch": (
                self.repository_info.branch_name
                if self.repository_info and self.repository_info.branch_name is not None
                else ""
            ),
        }

    def _get_runtime_info_fields(self) -> dict[str, any]:
        """Get runtime information fields."""
        return {
            "runtime_hosts": (
                self.runtime_info.available_hosts
                if self.runtime_info and self.runtime_info.available_hosts is not None
                else {}
            ),
            "additional_agent_instructions": (
                self.runtime_info.additional_agent_instructions
                if self.runtime_info and self.runtime_info.additional_agent_instructions is not None
                else ""
            ),
            "date": self.runtime_info.date if self.runtime_info is not None else "",
            "custom_secrets_descriptions": (
                self.runtime_info.custom_secrets_descriptions if self.runtime_info is not None else {}
            ),
            "working_dir": self.runtime_info.working_dir if self.runtime_info else "",
        }

    def _get_conversation_instructions(self) -> str:
        """Get conversation instructions content."""
        return self.conversation_instructions.content if self.conversation_instructions is not None else ""

    def _on_workspace_context_recall(self, event: RecallAction) -> RecallObservation | None:
        """Add repository and runtime information to the stream as a RecallObservation.

        This method collects information from all available repo microagents and concatenates their contents.
        Multiple repo microagents are supported, and their contents will be concatenated with newlines between them.
        """
        # Collect repository instructions from microagents
        repo_instructions = self._collect_repo_instructions()

        # Find microagent knowledge based on query
        microagent_knowledge = self._find_microagent_knowledge(event.query)

        # Check if we should create a recall observation
        if not self._should_create_recall_observation(repo_instructions, microagent_knowledge):
            return None

        # Get all required fields
        repo_info = self._get_repo_info_fields()
        runtime_info = self._get_runtime_info_fields()
        conversation_instructions = self._get_conversation_instructions()

        # Create and return the recall observation
        return RecallObservation(
            recall_type=RecallType.WORKSPACE_CONTEXT,
            repo_name=repo_info["repo_name"],
            repo_directory=repo_info["repo_directory"],
            repo_branch=repo_info["repo_branch"],
            repo_instructions=repo_instructions or "",
            runtime_hosts=runtime_info["runtime_hosts"],
            additional_agent_instructions=runtime_info["additional_agent_instructions"],
            microagent_knowledge=microagent_knowledge,
            content="Added workspace context",
            date=runtime_info["date"],
            custom_secrets_descriptions=runtime_info["custom_secrets_descriptions"],
            conversation_instructions=conversation_instructions,
            working_dir=runtime_info["working_dir"],
        )

    def _on_microagent_recall(self, event: RecallAction) -> RecallObservation | None:
        """When a microagent action triggers microagents, create a RecallObservation with structured data."""
        if microagent_knowledge := self._find_microagent_knowledge(event.query):
            return RecallObservation(
                recall_type=RecallType.KNOWLEDGE,
                microagent_knowledge=microagent_knowledge,
                content="Retrieved knowledge from microagents",
            )
        return None

    def _find_microagent_knowledge(self, query: str) -> list[MicroagentKnowledge]:
        """Find microagent knowledge based on a query.

        Args:
            query: The query to search for microagent triggers

        Returns:
            A list of MicroagentKnowledge objects for matched triggers
        """
        recalled_content: list[MicroagentKnowledge] = []
        if not query:
            return recalled_content
        for name, microagent in self.knowledge_microagents.items():
            if trigger := microagent.match_trigger(query):
                logger.info("Microagent '%s' triggered by keyword '%s'", name, trigger)
                recalled_content.append(
                    MicroagentKnowledge(name=microagent.name, trigger=trigger, content=microagent.content),
                )
        return recalled_content

    def load_user_workspace_microagents(self, user_microagents: list[BaseMicroagent]) -> None:
        """This method loads microagents from a user's cloned repo or workspace directory.

        This is typically called from agent_session or setup once the workspace is cloned.
        """
        logger.info("Loading user workspace microagents: %s", [m.name for m in user_microagents])
        for user_microagent in user_microagents:
            if isinstance(user_microagent, KnowledgeMicroagent):
                self.knowledge_microagents[user_microagent.name] = user_microagent
            elif isinstance(user_microagent, RepoMicroagent):
                self.repo_microagents[user_microagent.name] = user_microagent

    def _load_global_microagents(self) -> None:
        """Loads microagents from the global microagents_dir."""
        repo_agents, knowledge_agents = load_microagents_from_dir(GLOBAL_MICROAGENTS_DIR)
        for name, agent_knowledge in knowledge_agents.items():
            self.knowledge_microagents[name] = agent_knowledge
        for name, agent_repo in repo_agents.items():
            self.repo_microagents[name] = agent_repo

    def _load_user_microagents(self) -> None:
        """Loads microagents from the user's home directory (~/.openhands/microagents/).

        Creates the directory if it doesn't exist.
        """
        try:
            os.makedirs(USER_MICROAGENTS_DIR, exist_ok=True)
            repo_agents, knowledge_agents = load_microagents_from_dir(USER_MICROAGENTS_DIR)
            for name, agent_knowledge in knowledge_agents.items():
                self.knowledge_microagents[name] = agent_knowledge
            for name, agent_repo in repo_agents.items():
                self.repo_microagents[name] = agent_repo
        except Exception as e:
            logger.warning("Failed to load user microagents from %s: %s", USER_MICROAGENTS_DIR, str(e))

    def get_microagent_mcp_tools(self) -> list[MCPConfig]:
        """Get MCP tools from all repo microagents (always active).

        Returns:
            A list of MCP tools configurations from microagents
        """
        mcp_configs: list[MCPConfig] = []
        for agent in self.repo_microagents.values():
            if agent.metadata.mcp_tools:
                mcp_configs.append(agent.metadata.mcp_tools)
                logger.debug("Found MCP tools in repo microagent %s: %s", agent.name, agent.metadata.mcp_tools)
        return mcp_configs

    def set_repository_info(self, repo_name: str, repo_directory: str, branch_name: str | None = None) -> None:
        """Store repository info so we can reference it in an observation."""
        if repo_name or repo_directory:
            self.repository_info = RepositoryInfo(repo_name, repo_directory, branch_name)
        else:
            self.repository_info = None

    def set_runtime_info(self, runtime: Runtime, custom_secrets_descriptions: dict[str, str], working_dir: str) -> None:
        """Store runtime info (web hosts, ports, etc.)."""
        utc_now = datetime.now(timezone.utc)
        date = str(utc_now.date())
        if runtime.web_hosts or runtime.additional_agent_instructions:
            self.runtime_info = RuntimeInfo(
                available_hosts=runtime.web_hosts,
                additional_agent_instructions=runtime.additional_agent_instructions,
                date=date,
                custom_secrets_descriptions=custom_secrets_descriptions,
                working_dir=working_dir,
            )
        else:
            self.runtime_info = RuntimeInfo(
                date=date,
                custom_secrets_descriptions=custom_secrets_descriptions,
                working_dir=working_dir,
            )

    def set_conversation_instructions(self, conversation_instructions: str | None) -> None:
        """Set contextual information for conversation.

        This is information the agent may require.
        """
        self.conversation_instructions = ConversationInstructions(content=conversation_instructions or "")

    def set_runtime_status(self, status: RuntimeStatus, message: str) -> None:
        """Sends an error message if the callback function was provided."""
        if self.status_callback:
            try:
                logger.info('MEMORY.set_runtime_status ENTER (status=%s, message="%s")', status, message)
                if self.loop is None:
                    self.loop = asyncio.get_running_loop()
                try:
                    asyncio.run_coroutine_threadsafe(self._set_runtime_status("error", status, message), self.loop)
                except RuntimeError:
                    try:
                        logger.info("MEMORY.set_runtime_status: calling status_callback synchronously")
                        self.status_callback("error", status, message)
                        logger.info("MEMORY.set_runtime_status: status_callback returned")
                    except Exception:
                        asyncio.create_task(self._set_runtime_status("error", status, message))
            except (RuntimeError, KeyError) as e:
                logger.error("Error sending status message: %s", e.__class__.__name__, stack_info=False)

    async def _set_runtime_status(self, msg_type: str, runtime_status: RuntimeStatus, message: str) -> None:
        """Sends a status message to the client."""
        if self.status_callback:
            logger.info(
                "MEMORY._set_runtime_status: invoking status_callback (msg_type=%s, runtime_status=%s)",
                msg_type,
                runtime_status,
            )
            self.status_callback(msg_type, runtime_status, message)
            logger.info("MEMORY._set_runtime_status: status_callback finished")
