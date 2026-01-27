"""Runtime memory coordinator for handling recall actions and microagent context."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast

import forge
from forge.core.logger import forge_logger as logger
from forge.events.action.agent import RecallAction
from forge.events.event import Event, EventSource, RecallType
from forge.events.observation.agent import (
    MicroagentKnowledge,
    RecallObservation,
    RecallFailureObservation,
)
from forge.knowledge_base import KnowledgeBaseManager
from forge.events.observation.empty import NullObservation
from forge.events.stream import EventStream, EventStreamSubscriber
from forge.runtime.runtime_status import RuntimeStatus
from forge.utils.prompt import ConversationInstructions, RepositoryInfo, RuntimeInfo

if TYPE_CHECKING:
    from forge.core.config.mcp_config import MCPConfig
    from forge.storage.data_models.knowledge_base import KnowledgeBaseSettings
    from forge.microagent import (
        BaseMicroagent,
        KnowledgeMicroagent,
        RepoMicroagent,
    )
    from forge.runtime.base import Runtime

GLOBAL_MICROAGENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(forge.__file__)), "microagents"
)
USER_MICROAGENTS_DIR = Path.home() / ".Forge" / "microagents"


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
    user_id: str | None

    def __init__(
        self,
        event_stream: EventStream,
        sid: str,
        status_callback: Callable | None = None,
        user_id: str | None = None,
    ) -> None:
        """Subscribe to the event stream and load microagents for the given session ID."""
        self.event_stream = event_stream
        self.sid = sid or str(uuid.uuid4())
        self.user_id = user_id
        self.status_callback = status_callback
        self.loop = None
        self.event_stream.subscribe(
            EventStreamSubscriber.MEMORY, self.on_event, self.sid
        )
        self.repo_microagents = {}
        self.knowledge_microagents = {}
        self.repository_info: RepositoryInfo | None = None
        self.runtime_info: RuntimeInfo | None = None
        self.conversation_instructions: ConversationInstructions | None = None
        self._load_global_microagents()
        self._load_user_microagents()
        self._kb_manager = KnowledgeBaseManager(user_id=user_id or "default")

    def on_event(self, event: Event) -> None:
        """Handle an event from the event stream."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            loop.create_task(self._on_event(event))
            return

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            loop.create_task(self._on_event(event))
        else:
            if loop is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(self._on_event(event))

    async def _on_event(self, event: Event) -> None:
        """Handle an event from the event stream asynchronously."""
        try:
            if not isinstance(event, RecallAction):
                return
            observation = await self._process_recall_with_retry(event)
            if observation is None:
                observation = cast(
                    RecallObservation, self._build_failure_observation(event)
                )
            observation.cause = event.id
            self.event_stream.add_event(observation, EventSource.ENVIRONMENT)
        except Exception as exc:
            await self._handle_recall_exception(event, exc)

    async def _process_recall_with_retry(
        self, event: RecallAction, max_attempts: int = 3
    ) -> RecallObservation | None:
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                result = self._process_recall_once(event, attempt)
                if result is not None:
                    return result
                break
            except Exception as exc:  # pragma: no cover - defensive
                if not self._is_transient_error(exc):
                    logger.warning(
                        "Permanent recall error encountered on attempt %s: %s",
                        attempt,
                        exc,
                    )
                    break
                await self._backoff_retry(attempt, exc)
        return None

    def _process_recall_once(
        self,
        event: RecallAction,
        attempt: int,
    ) -> RecallObservation | None:
        if event.recall_type == RecallType.WORKSPACE_CONTEXT and event.source == EventSource.USER:
            logger.debug("Workspace context recall (attempt %s)", attempt)
            return self._on_workspace_context_recall(event)
        if event.recall_type == RecallType.KNOWLEDGE and event.source in (
            EventSource.USER,
            EventSource.AGENT,
        ):
            logger.debug(
                "Microagent knowledge recall from %s message (attempt %s)",
                event.source,
                attempt,
            )
            return self._on_microagent_recall(event)
        return None

    async def _backoff_retry(self, attempt: int, exc: Exception) -> None:
        backoff = min(0.8, 0.2 * (2 ** (attempt - 1)))
        jitter = 0.05 * attempt
        sleep_time = backoff + jitter
        logger.warning(
            "Transient recall attempt %s failed: %s; backoff %.2fs",
            attempt,
            exc,
            sleep_time,
        )
        await asyncio.sleep(sleep_time)

    def _build_failure_observation(self, event: RecallAction) -> RecallFailureObservation:
        return RecallFailureObservation(
            recall_type=event.recall_type,
            error_message="Recall failed after retries",
            content="Recall failure",
        )

    async def _handle_recall_exception(self, event: Event, exc: Exception) -> None:
        error_str = f"Recall error: {exc.__class__.__name__}: {exc}"[:500]
        logger.error(error_str)
        self.set_runtime_status(RuntimeStatus.ERROR_MEMORY, error_str)
        failure_obs = RecallFailureObservation(
            recall_type=getattr(event, "recall_type", None),
            error_message=error_str,
            content=error_str,
        )
        failure_obs.cause = getattr(event, "id", None)
        try:
            self.event_stream.add_event(failure_obs, EventSource.ENVIRONMENT)
        except Exception:
            pass

    @staticmethod
    def _is_transient_error(e: Exception) -> bool:
        """Best-effort classification of transient recall errors for retry policy."""
        transient_types = (
            TimeoutError,
            ConnectionError,
        )
        if isinstance(e, transient_types):
            return True
        msg = str(e).lower()
        return any(
            key in msg
            for key in (
                "timeout",
                "rate limit",
                "temporarily unavailable",
                "try again",
                "connection reset",
            )
        )

    def _collect_repo_instructions(self) -> str:
        """Collect repository instructions from all repo microagents."""
        repo_instructions = ""
        for microagent in self.repo_microagents.values():
            if repo_instructions:
                repo_instructions += "\n\n"
            repo_instructions += microagent.content
        return repo_instructions

    def _should_create_recall_observation(
        self,
        repo_instructions: str,
        microagent_knowledge: list[MicroagentKnowledge],
    ) -> bool:
        """Check if we should create a recall observation based on available data."""
        return any(
            [
                self.repository_info is not None,
                self.runtime_info is not None,
                bool(repo_instructions),
                bool(microagent_knowledge),
                self.conversation_instructions is not None,
            ],
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
                if self.repository_info
                and self.repository_info.repo_directory is not None
                else ""
            ),
            "repo_branch": (
                self.repository_info.branch_name
                if self.repository_info and self.repository_info.branch_name is not None
                else ""
            ),
        }

    def _get_runtime_info_fields(self) -> dict[str, Any]:
        """Get runtime information fields."""
        runtime_hosts: dict[str, int] = {}
        additional_instructions = ""
        custom_secrets: dict[str, str] = {}
        working_dir = ""
        date = ""

        if self.runtime_info is not None:
            runtime_hosts = self.runtime_info.available_hosts
            additional_instructions = self.runtime_info.additional_agent_instructions
            custom_secrets = self.runtime_info.custom_secrets_descriptions
            working_dir = self.runtime_info.working_dir
            date = self.runtime_info.date

        return {
            "runtime_hosts": runtime_hosts,
            "additional_agent_instructions": additional_instructions,
            "date": date,
            "custom_secrets_descriptions": custom_secrets,
            "working_dir": working_dir,
        }

    def _get_conversation_instructions(self) -> str:
        """Get conversation instructions content."""
        return (
            self.conversation_instructions.content
            if self.conversation_instructions is not None
            else ""
        )

    def _on_workspace_context_recall(
        self, event: RecallAction
    ) -> RecallObservation | None:
        """Add repository and runtime information to the stream as a RecallObservation.

        This method collects information from all available repo microagents and concatenates their contents.
        Multiple repo microagents are supported, and their contents will be concatenated with newlines between them.
        """
        # Collect repository instructions from microagents
        repo_instructions = self._collect_repo_instructions()

        # Find microagent knowledge based on query
        microagent_knowledge = self._find_microagent_knowledge(event.query)

        # Check if we should create a recall observation
        if not self._should_create_recall_observation(
            repo_instructions, microagent_knowledge
        ):
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
        microagent_knowledge = self._find_microagent_knowledge(event.query)
        
        # Also search Knowledge Base
        kb_results = []
        try:
            # Check if KB search is enabled and should be performed
            kb_enabled = True
            kb_threshold = 0.7
            kb_top_k = 5
            kb_collections = None
            
            # Use settings if available
            if hasattr(self, "_kb_settings") and self._kb_settings:
                kb_enabled = self._kb_settings.auto_search
                kb_threshold = self._kb_settings.relevance_threshold
                kb_top_k = self._kb_settings.search_top_k
                kb_collections = self._kb_settings.active_collection_ids

            if kb_enabled:
                # We use a relatively high threshold by default for auto-search
                kb_results = self._kb_manager.search(
                    query=event.query,
                    relevance_threshold=kb_threshold,
                    top_k=kb_top_k,
                    collection_ids=kb_collections
                )
        except Exception as e:
            logger.error(f"Error searching knowledge base during recall: {e}")

        if microagent_knowledge or kb_results:
            return RecallObservation(
                recall_type=RecallType.KNOWLEDGE,
                microagent_knowledge=microagent_knowledge,
                knowledge_base_results=kb_results,
                content="Retrieved knowledge from microagents and knowledge base",
            )
        return None

    def set_knowledge_base_settings(self, settings: KnowledgeBaseSettings) -> None:
        """Update knowledge base settings for this memory instance."""
        self._kb_settings = settings
        logger.info(f"Knowledge base settings updated for session {self.sid}")

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
                    MicroagentKnowledge(
                        name=microagent.name,
                        trigger=trigger,
                        content=microagent.content,
                    ),
                )
        return recalled_content

    def load_user_workspace_microagents(
        self, user_microagents: list[BaseMicroagent]
    ) -> None:
        """This method loads microagents from a user's cloned repo or workspace directory.

        This is typically called from agent_session or setup once the workspace is cloned.
        """
        from forge.microagent import KnowledgeMicroagent, RepoMicroagent
        logger.info(
            "Loading user workspace microagents: %s", [m.name for m in user_microagents]
        )
        for user_microagent in user_microagents:
            if isinstance(user_microagent, KnowledgeMicroagent):
                self.knowledge_microagents[user_microagent.name] = user_microagent
            elif isinstance(user_microagent, RepoMicroagent):
                self.repo_microagents[user_microagent.name] = user_microagent

    def _load_global_microagents(self) -> None:
        """Loads microagents from the global microagents_dir."""
        from forge.microagent import load_microagents_from_dir
        repo_agents, knowledge_agents = load_microagents_from_dir(
            GLOBAL_MICROAGENTS_DIR
        )
        for name, agent_knowledge in knowledge_agents.items():
            self.knowledge_microagents[name] = agent_knowledge
        for name, agent_repo in repo_agents.items():
            self.repo_microagents[name] = agent_repo

    def _load_user_microagents(self) -> None:
        """Loads microagents from the user's home directory (~/.Forge/microagents/).

        Creates the directory if it doesn't exist.
        """
        from forge.microagent import load_microagents_from_dir
        try:
            os.makedirs(USER_MICROAGENTS_DIR, exist_ok=True)
            repo_agents, knowledge_agents = load_microagents_from_dir(
                USER_MICROAGENTS_DIR
            )
            for name, agent_knowledge in knowledge_agents.items():
                self.knowledge_microagents[name] = agent_knowledge
            for name, agent_repo in repo_agents.items():
                self.repo_microagents[name] = agent_repo
        except Exception as e:
            logger.warning(
                "Failed to load user microagents from %s: %s",
                USER_MICROAGENTS_DIR,
                str(e),
            )

    def get_microagent_mcp_tools(self) -> list[MCPConfig]:
        """Get MCP tools from all repo microagents (always active).

        Returns:
            A list of MCP tools configurations from microagents

        """
        mcp_configs: list[MCPConfig] = []
        for agent in self.repo_microagents.values():
            if agent.metadata.mcp_tools:
                mcp_configs.append(agent.metadata.mcp_tools)
                logger.debug(
                    "Found MCP tools in repo microagent %s: %s",
                    agent.name,
                    agent.metadata.mcp_tools,
                )
        return mcp_configs

    def set_repository_info(
        self, repo_name: str, repo_directory: str, branch_name: str | None = None
    ) -> None:
        """Store repository info so we can reference it in an observation."""
        if repo_name or repo_directory:
            self.repository_info = RepositoryInfo(
                repo_name, repo_directory, branch_name
            )
        else:
            self.repository_info = None

    def set_runtime_info(
        self,
        runtime: Runtime,
        custom_secrets_descriptions: dict[str, str],
        working_dir: str,
    ) -> None:
        """Store runtime info (web hosts, ports, etc.)."""
        utc_now = datetime.now(timezone.utc)
        date = str(utc_now.date())

        web_hosts_attr = getattr(runtime, "web_hosts", None)
        web_hosts: dict[str, int] = {}
        if isinstance(web_hosts_attr, dict):
            web_hosts = {
                str(host): int(port)
                for host, port in web_hosts_attr.items()
                if isinstance(host, (str, int)) and isinstance(port, int)
            }

        additional_instructions_attr = getattr(
            runtime, "additional_agent_instructions", None
        )
        additional_instructions_result: Any
        if callable(additional_instructions_attr):
            additional_instructions_result = additional_instructions_attr()
        else:
            additional_instructions_result = additional_instructions_attr

        if isinstance(additional_instructions_result, str):
            additional_instructions = additional_instructions_result
        elif additional_instructions_result is None:
            additional_instructions = ""
        else:
            additional_instructions = str(additional_instructions_result)

        if web_hosts or additional_instructions:
            self.runtime_info = RuntimeInfo(
                available_hosts=web_hosts,
                additional_agent_instructions=additional_instructions,
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

    def set_conversation_instructions(
        self, conversation_instructions: str | None
    ) -> None:
        """Set contextual information for conversation.

        This is information the agent may require.
        """
        self.conversation_instructions = ConversationInstructions(
            content=conversation_instructions or ""
        )

    def set_runtime_status(self, status: RuntimeStatus, message: str) -> None:
        """Sends an error message if the callback function was provided."""
        if self.status_callback:
            try:
                logger.info(
                    'MEMORY.set_runtime_status ENTER (status=%s, message="%s")',
                    status,
                    message,
                )
                if self.loop is None:
                    self.loop = asyncio.get_running_loop()
                try:
                    asyncio.run_coroutine_threadsafe(
                        self._set_runtime_status("error", status, message), self.loop
                    )
                except RuntimeError:
                    try:
                        logger.info(
                            "MEMORY.set_runtime_status: calling status_callback synchronously"
                        )
                        self.status_callback("error", status, message)
                        logger.info(
                            "MEMORY.set_runtime_status: status_callback returned"
                        )
                    except Exception:
                        asyncio.create_task(
                            self._set_runtime_status("error", status, message)
                        )
            except (RuntimeError, KeyError) as e:
                logger.error(
                    "Error sending status message: %s",
                    e.__class__.__name__,
                    stack_info=False,
                )

    async def _set_runtime_status(
        self, msg_type: str, runtime_status: RuntimeStatus, message: str
    ) -> None:
        """Sends a status message to the client."""
        if self.status_callback:
            logger.info(
                "MEMORY._set_runtime_status: invoking status_callback (msg_type=%s, runtime_status=%s)",
                msg_type,
                runtime_status,
            )
            self.status_callback(msg_type, runtime_status, message)
            logger.info("MEMORY._set_runtime_status: status_callback finished")
