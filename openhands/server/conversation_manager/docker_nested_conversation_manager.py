from __future__ import annotations

import asyncio
import hashlib
import os
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, NoReturn, cast

import docker
import httpx

from openhands.controller.agent import Agent
from openhands.core.logger import openhands_logger as logger
from openhands.core.pydantic_compat import model_dump_with_options
from openhands.events.nested_event_store import NestedEventStore
from openhands.events.stream import EventStream
from openhands.experiments.experiment_manager import ExperimentManagerImpl
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE, ProviderHandler
from openhands.runtime import get_runtime_cls
from openhands.runtime.impl.docker.docker_runtime import DockerRuntime
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.server.constants import ROOM_KEY
from openhands.server.conversation_manager.conversation_manager import (
    ConversationManager,
)
from openhands.server.data_models.agent_loop_info import AgentLoopInfo
from openhands.server.session.conversation_init_data import ConversationInitData
from openhands.server.session.session import Session
from openhands.storage.conversation.conversation_store import ConversationStore
from openhands.storage.data_models.conversation_status import ConversationStatus
from openhands.storage.locations import get_conversation_dir
from openhands.utils.async_utils import call_sync_from_async
from openhands.utils.import_utils import get_impl
from openhands.utils.utils import create_registry_and_conversation_stats

if TYPE_CHECKING:
    import socketio
    from docker.models.containers import Container

    from openhands.core.config import OpenHandsConfig
    from openhands.core.config.llm_config import LLMConfig
    from openhands.events.action import MessageAction
    from openhands.server.config.server_config import ServerConfig
    from openhands.server.monitoring import MonitoringListener
    from openhands.server.session.conversation import ServerConversation
    from openhands.storage.data_models.conversation_metadata import ConversationMetadata
    from openhands.storage.data_models.settings import Settings
    from openhands.storage.files import FileStore


@dataclass
class DockerNestedConversationManager(ConversationManager):
    """ServerConversation manager where the agent loops exist inside the docker containers."""

    sio: socketio.AsyncServer
    config: OpenHandsConfig
    server_config: ServerConfig
    file_store: FileStore
    docker_client: docker.DockerClient = field(default_factory=docker.from_env)
    _conversation_store_class: type[ConversationStore] | None = None
    _starting_conversation_ids: set[str] = field(default_factory=set)
    _runtime_container_image: str | None = None
    _health_monitors: dict[str, asyncio.Task] = field(default_factory=dict)
    _conversation_locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    async def __aenter__(self):
        runtime_cls = get_runtime_cls(self.config.runtime)
        runtime_cls.setup(self.config)

    async def __aexit__(self, exc_type, exc_value, traceback):
        runtime_cls = get_runtime_cls(self.config.runtime)
        runtime_cls.teardown(self.config)

    async def attach_to_conversation(self, sid: str, user_id: str | None = None) -> ServerConversation | None:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def detach_from_conversation(self, conversation: ServerConversation) -> NoReturn:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def join_conversation(
        self,
        sid: str,
        connection_id: str,
        settings: Settings,
        user_id: str | None,
    ) -> AgentLoopInfo:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def get_running_agent_loops(
        self,
        user_id: str | None = None,
        filter_to_sids: set[str] | None = None,
    ) -> set[str]:
        """Get the running agent loops directly from docker."""
        containers: list[Container] = self.docker_client.containers.list()
        names = (container.name or "" for container in containers)
        conversation_ids = {
            name[len("openhands-runtime-"):] for name in names if name.startswith("openhands-runtime-")
        }
        if filter_to_sids is not None:
            conversation_ids = {
                conversation_id for conversation_id in conversation_ids if conversation_id in filter_to_sids
            }
        return conversation_ids

    async def get_connections(
        self,
        user_id: str | None = None,
        filter_to_sids: set[str] | None = None,
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        return results

    async def maybe_start_agent_loop(
        self,
        sid: str,
        settings: Settings,
        user_id: str | None,
        initial_user_msg: MessageAction | None = None,
        replay_json: str | None = None,
    ) -> AgentLoopInfo:
        if not await self.is_agent_loop_running(sid):
            await self._start_agent_loop(sid, settings, user_id, initial_user_msg, replay_json)
        nested_url = self._get_nested_url(sid)
        session_api_key = self._get_session_api_key_for_conversation(sid)
        return AgentLoopInfo(
            conversation_id=sid,
            url=nested_url,
            session_api_key=session_api_key,
            event_store=NestedEventStore(
                base_url=nested_url,
                sid=sid,
                user_id=user_id,
                session_api_key=session_api_key,
            ),
            status=(
                ConversationStatus.STARTING if sid in self._starting_conversation_ids else ConversationStatus.RUNNING
            ),
        )

    async def _start_agent_loop(
        self,
        sid: str,
        settings: Settings,
        user_id: str | None,
        initial_user_msg: MessageAction | None,
        replay_json: str | None,
    ) -> None:
        logger.info("starting_agent_loop:%s", sid, extra={"session_id": sid})
        
        # 🔒 CRITICAL FIX: Use asyncio.Lock to prevent race conditions
        # Multiple concurrent requests for the same conversation could cause duplicate containers
        if sid not in self._conversation_locks:
            self._conversation_locks[sid] = asyncio.Lock()
        
        async with self._conversation_locks[sid]:
            # Check if conversation is already starting (race condition protection)
            if sid in self._starting_conversation_ids:
                logger.info(f"Conversation {sid} already starting, skipping duplicate initialization")
                return
            
            await self.ensure_num_conversations_below_limit(sid, user_id)
            runtime = await self._create_runtime(sid, user_id, settings)
            self._starting_conversation_ids.add(sid)
            
            try:
                await call_sync_from_async(runtime.maybe_build_runtime_container_image)
                self._runtime_container_image = runtime.runtime_container_image
                if await self._start_existing_container(runtime):
                    self._starting_conversation_ids.discard(sid)
                    # Start health monitor if not already running
                    if sid not in self._health_monitors:
                        self._health_monitors[sid] = asyncio.create_task(self._monitor_runtime_health(sid))
                        logger.debug(f"Started health monitor for conversation {sid}")
                    return
                await call_sync_from_async(runtime.init_container)
                
                # Start health monitor for new container
                if sid not in self._health_monitors:
                    self._health_monitors[sid] = asyncio.create_task(self._monitor_runtime_health(sid))
                    logger.debug(f"Started health monitor for conversation {sid}")
                
                asyncio.create_task(
                    self._start_conversation(sid, settings, runtime, initial_user_msg, replay_json, runtime.api_url),
                )
            except Exception:
                self._starting_conversation_ids.discard(sid)
                raise

    async def _start_conversation(
        self,
        sid: str,
        settings: Settings,
        runtime: DockerRuntime,
        initial_user_msg: MessageAction | None,
        replay_json: str | None,
        api_url: str,
    ) -> None:
        """Start a conversation in a nested Docker runtime.

        Args:
            sid: Session/conversation ID
            settings: User settings
            runtime: Docker runtime instance
            initial_user_msg: Initial message from user
            replay_json: Optional replay data
            api_url: API URL for the nested runtime
        """
        try:
            await call_sync_from_async(runtime.wait_until_alive)
            await call_sync_from_async(runtime.setup_initial_env)

            async with httpx.AsyncClient(
                headers={"X-Session-API-Key": self._get_session_api_key_for_conversation(sid)},
            ) as client:
                await self._send_settings(client, api_url, settings)
                await self._send_provider_tokens(client, api_url, settings)
                await self._send_custom_secrets(client, api_url, settings)
                await self._initialize_conversation(client, api_url, sid, settings, initial_user_msg, replay_json)
        finally:
            self._starting_conversation_ids.discard(sid)

    async def _send_settings(self, client: httpx.AsyncClient, api_url: str, settings: Settings) -> None:
        """Send settings to nested runtime.

        Args:
            client: HTTP client
            api_url: API URL
            settings: User settings
        """
        settings_json = model_dump_with_options(settings, context={"expose_secrets": True})
        settings_json.pop("custom_secrets", None)
        settings_json.pop("git_provider_tokens", None)

        if settings_json.get("git_provider"):
            settings_json["git_provider"] = settings_json["git_provider"].value

        settings_json.pop("secrets_store", None)

        response = await client.post(f"{api_url}/api/settings", json=settings_json)
        response.raise_for_status()

    async def _send_provider_tokens(self, client: httpx.AsyncClient, api_url: str, settings: Settings) -> None:
        """Send provider tokens to nested runtime.

        Args:
            client: HTTP client
            api_url: API URL
            settings: User settings
        """
        provider_handler = self._get_provider_handler(settings)

        if not provider_handler.provider_tokens:
            return

        provider_tokens_json = {
            k.value: {"token": v.token.get_secret_value(), "user_id": v.user_id, "host": v.host}
            for k, v in provider_handler.provider_tokens.items()
            if v.token
        }

        response = await client.post(
            f"{api_url}/api/add-git-providers",
            json={"provider_tokens": provider_tokens_json},
        )
        response.raise_for_status()

    async def _send_custom_secrets(self, client: httpx.AsyncClient, api_url: str, settings: Settings) -> None:
        """Send custom secrets to nested runtime.

        Args:
            client: HTTP client
            api_url: API URL
            settings: User settings
        """
        if not settings.custom_secrets:
            return

        for key, secret in settings.custom_secrets.items():
            response = await client.post(
                f"{api_url}/api/secrets",
                json={
                    "name": key,
                    "description": secret.description,
                    "value": secret.secret.get_secret_value(),
                },
            )
            response.raise_for_status()

    async def _initialize_conversation(
        self,
        client: httpx.AsyncClient,
        api_url: str,
        sid: str,
        settings: Settings,
        initial_user_msg: MessageAction | None,
        replay_json: str | None,
    ) -> None:
        """Initialize conversation in nested runtime.

        Args:
            client: HTTP client
            api_url: API URL
            sid: Session/conversation ID
            settings: User settings
            initial_user_msg: Initial user message
            replay_json: Optional replay data
        """
        init_conversation: dict[str, Any] = {
            "initial_user_msg": initial_user_msg.content if initial_user_msg and initial_user_msg.content else None,
            "image_urls": [],
            "replay_json": replay_json,
            "conversation_id": sid,
        }

        if isinstance(settings, ConversationInitData):
            init_conversation["repository"] = settings.selected_repository
            init_conversation["selected_branch"] = settings.selected_branch
            init_conversation["git_provider"] = settings.git_provider.value if settings.git_provider else None

        response = await client.post(f"{api_url}/api/conversations", json=init_conversation)
        logger.info("_start_agent_loop:%s:%s", response.status_code, response.json())
        response.raise_for_status()

    async def send_to_event_stream(self, connection_id: str, data: dict) -> NoReturn:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def request_llm_completion(
        self,
        sid: str,
        service_id: str,
        llm_config: LLMConfig,
        messages: list[dict[str, str]],
    ) -> str:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def send_event_to_conversation(self, sid, data) -> None:
        async with httpx.AsyncClient(
            headers={"X-Session-API-Key": self._get_session_api_key_for_conversation(sid)},
        ) as client:
            nested_url = self._get_nested_url(sid)
            response = await client.post(f"{nested_url}/api/conversations/{sid}/events", json=data)
            response.raise_for_status()

    async def disconnect_from_session(self, connection_id: str) -> NoReturn:
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def close_session(self, sid: str) -> None:
        try:
            container = self.docker_client.containers.get(f"openhands-runtime-{sid}")
        except docker.errors.NotFound:
            return
        try:
            nested_url = self.get_nested_url_for_container(container)
            async with httpx.AsyncClient(
                headers={"X-Session-API-Key": self._get_session_api_key_for_conversation(sid)},
            ) as client:
                response = await client.post(f"{nested_url}/api/conversations/{sid}/stop")
                response.raise_for_status()
                for _ in range(3):
                    response = await client.get(f"{nested_url}/api/conversations/{sid}")
                    response.raise_for_status()
                    if response.json().get("status") == "STOPPED":
                        break
                    await asyncio.sleep(1)
        except Exception as e:
            logger.warning("error_stopping_container", extra={"sid": sid, "error": str(e)})
        container.stop()

    async def _get_runtime_status_from_nested_runtime(
        self,
        conversation_id: str,
        nested_url: str,
    ) -> RuntimeStatus | None:
        """Get runtime status from the nested runtime via API call.

        Args:
            conversation_id: The conversation ID to query
            nested_url: The base URL of the nested runtime

        Returns:
            The runtime status if available, None otherwise
        """
        try:
            async with httpx.AsyncClient(
                headers={"X-Session-API-Key": self._get_session_api_key_for_conversation(conversation_id)},
            ) as client:
                response = await client.get(nested_url)
                if response.status_code == 200:
                    conversation_data = response.json()
                    runtime_status_str = conversation_data.get("runtime_status")
                    if runtime_status_str:
                        return RuntimeStatus(runtime_status_str)
                else:
                    logger.debug("Failed to get conversation info for %s: %s", conversation_id, response.status_code)
        except ValueError:
            logger.debug("Invalid runtime status value: %s", runtime_status_str)
        except Exception as e:
            logger.debug("Could not get runtime status for %s: %s", conversation_id, e)
        return None

    async def get_agent_loop_info(
        self,
        user_id: str | None = None,
        filter_to_sids: set[str] | None = None,
    ) -> list[AgentLoopInfo]:
        results = []
        containers: list[Container] = self.docker_client.containers.list()
        for container in containers:
            if not container.name or not container.name.startswith("openhands-runtime-"):
                continue
            conversation_id = container.name[len("openhands-runtime-"):]
            if filter_to_sids is not None and conversation_id not in filter_to_sids:
                continue
            nested_url = self.get_nested_url_for_container(container)
            if os.getenv("NESTED_RUNTIME_BROWSER_HOST", "") != "":
                nested_url = nested_url.replace(
                    self.config.sandbox.local_runtime_url,
                    os.getenv("NESTED_RUNTIME_BROWSER_HOST", ""),
                )
            runtime_status = await self._get_runtime_status_from_nested_runtime(conversation_id, nested_url)
            agent_loop_info = AgentLoopInfo(
                conversation_id=conversation_id,
                url=nested_url,
                session_api_key=self._get_session_api_key_for_conversation(conversation_id),
                event_store=NestedEventStore(base_url=nested_url, sid=conversation_id, user_id=user_id),
                status=(
                    ConversationStatus.STARTING
                    if conversation_id in self._starting_conversation_ids
                    else ConversationStatus.RUNNING
                ),
                runtime_status=runtime_status,
            )
            results.append(agent_loop_info)
        return results

    @classmethod
    def get_instance(
        cls,
        sio: socketio.AsyncServer,
        config: OpenHandsConfig,
        file_store: FileStore,
        server_config: ServerConfig,
        monitoring_listener: MonitoringListener,
    ) -> ConversationManager:
        return DockerNestedConversationManager(
            sio=sio,
            config=config,
            server_config=server_config,
            file_store=file_store,
        )

    def get_agent_session(self, sid: str) -> NoReturn:
        """Get the agent session for a given session ID.

        Args:
            sid: The session ID.

        Returns:
            The agent session, or None if not found.
        """
        msg = "unsupported_operation"
        raise ValueError(msg)

    async def _get_conversation_store(self, user_id: str | None) -> ConversationStore:
        conversation_store_class = self._conversation_store_class
        if not conversation_store_class:
            self._conversation_store_class = conversation_store_class = get_impl(
                ConversationStore,
                self.server_config.conversation_store_class,
            )
        return await conversation_store_class.get_instance(self.config, user_id)

    def _get_nested_url(self, sid: str) -> str:
        container = self.docker_client.containers.get(f"openhands-runtime-{sid}")
        return self.get_nested_url_for_container(container)

    def get_nested_url_for_container(self, container: Container) -> str:
        env = container.attrs["Config"]["Env"]
        container_port = int(next(e[5:] for e in env if e.startswith("port=")))
        container_name = container.name or ""
        conversation_id = container_name[len("openhands-runtime-"):]
        return f"{self.config.sandbox.local_runtime_url}:{container_port}/api/conversations/{conversation_id}"

    def _get_session_api_key_for_conversation(self, conversation_id: str) -> str:
        jwt_secret = self.config.jwt_secret.get_secret_value()
        conversation_key = f"{jwt_secret}:{conversation_id}".encode()
        return urlsafe_b64encode(hashlib.sha256(conversation_key).digest()).decode().replace("=", "")

    async def ensure_num_conversations_below_limit(self, sid: str, user_id: str | None) -> None:
        response_ids = await self.get_running_agent_loops(user_id)
        if len(response_ids) >= self.config.max_concurrent_conversations:
            logger.info("too_many_sessions_for:%s", user_id or "", extra={"session_id": sid, "user_id": user_id})
            conversation_store = await self._get_conversation_store(user_id)
            conversations = await conversation_store.get_all_metadata(response_ids)
            conversations.sort(key=_last_updated_at_key, reverse=True)
            while len(conversations) >= self.config.max_concurrent_conversations:
                oldest_conversation_id = conversations.pop().conversation_id
                logger.debug(
                    "closing_from_too_many_sessions:%s:%s",
                    user_id or "",
                    oldest_conversation_id,
                    extra={"session_id": oldest_conversation_id, "user_id": user_id},
                )
                status_update_dict = {
                    "status_update": True,
                    "type": "error",
                    "id": "AGENT_ERROR$TOO_MANY_CONVERSATIONS",
                    "message": "Too many conversations at once. If you are still using this one, try reactivating it by prompting the agent to continue",
                }
                await self.sio.emit("oh_event", status_update_dict, to=ROOM_KEY.format(sid=oldest_conversation_id))
                await self.close_session(oldest_conversation_id)

    def _get_provider_handler(self, settings: Settings) -> ProviderHandler:
        provider_tokens = None
        if isinstance(settings, ConversationInitData):
            provider_tokens = settings.git_provider_tokens
        return ProviderHandler(provider_tokens=provider_tokens or cast("PROVIDER_TOKEN_TYPE", MappingProxyType({})))

    async def _create_runtime(self, sid: str, user_id: str | None, settings: Settings) -> DockerRuntime:
        config: OpenHandsConfig = ExperimentManagerImpl.run_config_variant_test(user_id, sid, self.config)
        llm_registry, conversation_stats, config = create_registry_and_conversation_stats(
            config,
            sid,
            user_id,
            settings,
        )
        session = Session(
            sid=sid,
            llm_registry=llm_registry,
            conversation_stats=conversation_stats,
            file_store=self.file_store,
            config=config,
            sio=self.sio,
            user_id=user_id,
        )
        llm_registry.retry_listner = session._notify_on_llm_retry
        agent_cls = settings.agent or config.default_agent
        agent_config = config.get_agent_config(agent_cls)
        agent = Agent.get_cls(agent_cls)(agent_config, llm_registry)
        config = config.model_copy(deep=True)
        env_vars = config.sandbox.runtime_startup_env_vars
        env_vars["CONVERSATION_MANAGER_CLASS"] = (
            "openhands.server.conversation_manager.standalone_conversation_manager.StandaloneConversationManager"
        )
        env_vars["SERVE_FRONTEND"] = "0"
        env_vars["RUNTIME"] = "local"
        env_vars["USER"] = "root"
        env_vars["SESSION_API_KEY"] = self._get_session_api_key_for_conversation(sid)
        env_vars["ALLOW_SET_CONVERSATION_ID"] = "1"
        env_vars["WORKSPACE_BASE"] = "/workspace"
        env_vars["SANDBOX_CLOSE_DELAY"] = "0"
        env_vars["SKIP_DEPENDENCY_CHECK"] = "1"
        env_vars["INITIAL_NUM_WARM_SERVERS"] = "1"
        volumes: list[str | None]
        if not config.sandbox.volumes:
            volumes = []
        else:
            volumes = [v.strip() for v in config.sandbox.volumes.split(",")]
        conversation_dir = get_conversation_dir(sid, user_id)
        if config.file_store == "local":
            file_store_path = os.path.realpath(os.path.expanduser(config.file_store_path))
            volumes.append(f"{file_store_path}/{conversation_dir}:/root/.openhands/{conversation_dir}:rw")
        config.sandbox.volumes = ",".join([v for v in volumes if v is not None])
        if not config.sandbox.runtime_container_image:
            config.sandbox.runtime_container_image = self._runtime_container_image
        event_stream = EventStream(sid, self.file_store, user_id)
        runtime = DockerRuntime(
            config=config,
            event_stream=event_stream,
            sid=sid,
            plugins=agent.sandbox_plugins,
            headless_mode=False,
            attach_to_existing=False,
            main_module="openhands.server",
            llm_registry=llm_registry,
        )
        runtime.setup_initial_env = lambda: None
        return runtime

    async def _monitor_runtime_health(self, sid: str) -> None:
        """Background task to monitor runtime health and auto-restart if needed.
        
        Args:
            sid: Conversation ID to monitor
        """
        monitor_interval = 15  # Check every 15 seconds
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while True:
            try:
                await asyncio.sleep(monitor_interval)
                
                # Check if conversation still exists
                if sid not in self._starting_conversation_ids and not await self.is_agent_loop_running(sid):
                    logger.info(f"Conversation {sid} no longer active, stopping health monitor")
                    break
                
                container_name = f"forge-runtime-{sid}"
                
                try:
                    container = self.docker_client.containers.get(container_name)
                    status = container.status
                    
                    # Container is healthy
                    if status == "running":
                        consecutive_failures = 0
                        continue
                    
                    # Container crashed
                    if status in ["exited", "dead"]:
                        logger.error(f"🔴 Runtime container {container_name} crashed (status={status})!")
                        logger.info(f"Auto-restart will be triggered on next request")
                        # Don't restart here - let _start_existing_container handle it on next request
                        consecutive_failures = 0
                        
                except docker.errors.NotFound:
                    consecutive_failures += 1
                    logger.warning(f"Runtime container {container_name} not found (attempt {consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"Runtime container {container_name} missing after {consecutive_failures} checks, stopping monitor")
                        break
                        
            except Exception as e:
                logger.error(f"Error in health monitor for {sid}: {e}", exc_info=True)
                # Continue monitoring despite errors
                await asyncio.sleep(monitor_interval)
        
        # Cleanup
        if sid in self._health_monitors:
            del self._health_monitors[sid]
            logger.debug(f"Health monitor for {sid} stopped")

    async def _start_existing_container(self, runtime: DockerRuntime) -> bool:
        try:
            if container := self.docker_client.containers.get(runtime.container_name):
                status = container.status
                
                # Reuse if running
                if status == "running":
                    return True
                
                # AUTO-RESTART crashed containers
                if status in ["exited", "dead"]:
                    logger.warning(f"Runtime container {runtime.container_name} crashed (status={status}), removing for auto-restart...")
                    await call_sync_from_async(container.remove, force=True)
                    # Return False to trigger recreation in the calling code
                    return False
                
                # Paused containers can be resumed
                if status == "paused":
                    logger.info(f"Resuming paused container {runtime.container_name}")
                    await call_sync_from_async(container.unpause)
                    return True
                
                # Unknown status - remove and recreate
                logger.warning(f"Container {runtime.container_name} in unknown status '{status}', removing...")
                await call_sync_from_async(container.remove, force=True)
                return False
            return False
        except docker.errors.NotFound:
            return False


def _last_updated_at_key(conversation: ConversationMetadata) -> float:
    last_updated_at = conversation.last_updated_at
    return 0.0 if last_updated_at is None else last_updated_at.timestamp()
