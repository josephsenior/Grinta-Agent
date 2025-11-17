"""Runtime environment and execution infrastructure.

Classes:
    Runtime

Functions:
    runtime_initialized
    setup_initial_env
    close
    log
    set_runtime_status
"""

from __future__ import annotations

import asyncio
import atexit
import copy
import json
import os
import platform
import random
import shutil
import stat
import string
import tempfile
import time
from abc import abstractmethod
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Mapping, cast
from zipfile import ZipFile

import httpx
from typing_extensions import Self

from forge.core.exceptions import AgentRuntimeDisconnectedError
from forge.core.logger import forge_logger as logger
from forge.events import EventSource, EventStream, EventStreamSubscriber
from forge.events.action import (
    Action,
    ActionConfirmationStatus,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
    TaskTrackingAction,
)
from forge.events.action.mcp import MCPAction
from forge.events.action.files import FileEditAction
from forge.events.observation import (
    AgentThinkObservation,
    CmdOutputObservation,
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    NullObservation,
    Observation,
    TaskTrackingObservation,
    UserRejectObservation,
)
from forge.events.serialization.action import ACTION_TYPE_TO_CLASS
from pydantic import SecretStr

from forge.integrations.provider import (
    PROVIDER_TOKEN_TYPE,
    ProviderHandler,
    ProviderToken,
    ProviderType,
)
from forge.integrations.service_types import AuthenticationError
from forge.microagent import BaseMicroagent, load_microagents_from_dir
from forge.runtime.plugins import (
    JupyterRequirement,
    PluginRequirement,
    VSCodeRequirement,
)
from forge.runtime.runtime_status import RuntimeStatus
from forge.runtime.utils.edit import FileEditRuntimeMixin
from forge.runtime.utils.git_handler import CommandResult, GitHandler
from forge.security import SecurityAnalyzer, options
from forge.storage.locations import get_conversation_dir
from forge.utils.async_utils import (
    GENERAL_TIMEOUT,
    call_async_from_sync,
    call_sync_from_async,
)

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig, SandboxConfig
    from forge.core.config.mcp_config import MCPConfig, MCPStdioServerConfig
    from forge.events.event import Event
    from forge.llm.llm_registry import LLMRegistry


def _default_env_vars(sandbox_config: SandboxConfig) -> dict[str, str]:
    """Build default environment variables for sandbox from host environment.

    Copies environment variables prefixed with SANDBOX_ENV_ into the runtime,
    removing the prefix. Also sets auto-lint flag if enabled.

    Args:
        sandbox_config: Sandbox configuration settings

    Returns:
        Dictionary of environment variables for the sandbox

    """
    ret = {}
    for key in os.environ:
        if key.startswith("SANDBOX_ENV_"):
            sandbox_key = key.removeprefix("SANDBOX_ENV_")
            ret[sandbox_key] = os.environ[key]
    if sandbox_config.enable_auto_lint:
        ret["ENABLE_AUTO_LINT"] = "true"
    return ret


def _normalize_provider_tokens(
    tokens: PROVIDER_TOKEN_TYPE | None,
) -> MappingProxyType[ProviderType, ProviderToken]:
    """Ensure provider tokens are stored as an immutable mapping."""
    if isinstance(tokens, MappingProxyType):
        return tokens
    if tokens is None:
        return MappingProxyType({})
    return MappingProxyType(dict(tokens))


class Runtime(FileEditRuntimeMixin):
    """Abstract base class for agent runtime environments.

    This is an extension point in Forge that allows applications to customize how
    agents interact with the external environment. The runtime provides a sandbox with:
    - Bash shell access
    - Browser interaction
    - Filesystem operations
    - Git operations
    - Environment variable management

    Applications can substitute their own implementation by:
    1. Creating a class that inherits from Runtime
    2. Implementing all required methods
    3. Setting the runtime name in configuration or using get_runtime_cls()

    The class is instantiated via get_impl() in get_runtime_cls().

    Built-in implementations include:
    - DockerRuntime: Containerized environment using Docker
    - RemoteRuntime: Remote execution environment
    - LocalRuntime: Local execution for development
    - KubernetesRuntime: Kubernetes-based execution environment
    - CLIRuntime: Command-line interface runtime

    Args:
        sid: Session ID that uniquely identifies the current user session

    """

    sid: str
    config: ForgeConfig
    initial_env_vars: dict[str, str]
    attach_to_existing: bool
    status_callback: Callable[[str, RuntimeStatus, str], None] | None
    runtime_status: RuntimeStatus | None
    _runtime_initialized: bool = False
    security_analyzer: SecurityAnalyzer | None = None

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: EventStream | None,
        llm_registry: LLMRegistry,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = False,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> None:
        """Initialize runtime state, subscriptions, plugins, and provider credentials."""
        self.git_handler = GitHandler(
            execute_shell_fn=self._execute_shell_fn_git_handler,
            create_file_fn=self._create_file_fn_git_handler,
        )
        self.sid = sid
        self.event_stream = event_stream
        if event_stream:
            # Unsubscribe first if already exists (handles reconnection cases)
            try:
                event_stream.unsubscribe(EventStreamSubscriber.RUNTIME, self.sid)
            except Exception:
                pass  # Ignore if not subscribed
            event_stream.subscribe(
                EventStreamSubscriber.RUNTIME, self.on_event, self.sid
            )
        self.plugins = (
            copy.deepcopy(plugins) if plugins is not None and len(plugins) > 0 else []
        )
        if not headless_mode:
            self.plugins.append(VSCodeRequirement())
        self.status_callback = status_callback
        self.attach_to_existing = attach_to_existing
        self.config = copy.deepcopy(config)
        atexit.register(self.close)
        self.initial_env_vars = _default_env_vars(config.sandbox)
        if env_vars is not None:
            self.initial_env_vars.update(env_vars)
        provider_tokens = _normalize_provider_tokens(git_provider_tokens)
        self.provider_handler = ProviderHandler(
            provider_tokens=provider_tokens,
            external_auth_id=user_id,
            external_token_manager=True,
        )
        raw_env_vars = cast(
            dict[str, str],
            call_async_from_sync(
                self.provider_handler.get_env_vars,
                GENERAL_TIMEOUT,
                True,
                None,
                False,
            ),
        )
        self.initial_env_vars.update(raw_env_vars)
        self._vscode_enabled = any(
            isinstance(plugin, VSCodeRequirement) for plugin in self.plugins
        )
        FileEditRuntimeMixin.__init__(
            self,
            enable_llm_editor=config.get_agent_config().enable_llm_editor,
            llm_registry=llm_registry,
        )
        self.user_id = user_id
        self.git_provider_tokens = provider_tokens

        # 🧹 CRITICAL FIX: Process manager for tracking and cleaning up long-running processes
        from forge.runtime.utils.process_manager import ProcessManager

        self.process_manager = ProcessManager()
        self.runtime_status = None
        self.security_analyzer = None
        if self.config.security.security_analyzer:
            analyzer_cls = options.SecurityAnalyzers.get(
                self.config.security.security_analyzer, SecurityAnalyzer
            )
            self.security_analyzer = analyzer_cls()
            logger.debug(
                "Security analyzer %s initialized for runtime %s",
                analyzer_cls.__name__,
                self.sid,
            )

    @property
    def runtime_initialized(self) -> bool:
        """Check if runtime has completed initialization.

        Returns:
            True if runtime is initialized and ready

        """
        return self._runtime_initialized

    def setup_initial_env(self) -> None:
        """Set up initial environment variables and git configuration.

        Skipped if attaching to existing runtime. Adds initial env vars,
        runtime startup vars, and configures git user settings.
        """
        if self.attach_to_existing:
            return
        logger.debug("Adding env vars: %s", self.initial_env_vars.keys())
        self.add_env_vars(self.initial_env_vars)
        if self.config.sandbox.runtime_startup_env_vars:
            self.add_env_vars(self.config.sandbox.runtime_startup_env_vars)
        self._setup_git_config()

    def close(self) -> None:
        """This should only be called by conversation manager or closing the session.

        If called for instance by error handling, it could prevent recovery.
        """
        if not self._should_cleanup_processes():
            return
        try:
            logger.info(
                "🧹 Cleaning up %s long-running processes",
                self.process_manager.count(),
            )
            self._cleanup_processes()
        except Exception as e:
            logger.error(f"Failed to cleanup processes: {e}")

    def _should_cleanup_processes(self) -> bool:
        return hasattr(self, "process_manager") and self.process_manager.count() > 0

    def _cleanup_processes(self) -> None:
        loop, created = self._resolve_event_loop()
        if loop and loop.is_running():
            loop.create_task(self.process_manager.cleanup_all(runtime=self))
            return
        self._run_cleanup_synchronously(loop, created)

    def _resolve_event_loop(self) -> tuple[asyncio.AbstractEventLoop | None, bool]:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            return loop, False
        except RuntimeError:
            pass
        try:
            loop = asyncio.get_event_loop()
            return loop, False
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop, True

    def _run_cleanup_synchronously(
        self, loop: asyncio.AbstractEventLoop | None, created: bool
    ) -> None:
        import asyncio

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            created = True
        try:
            loop.run_until_complete(self.process_manager.cleanup_all(runtime=self))
        finally:
            self._close_loop_if_needed(loop, created)

    def _close_loop_if_needed(
        self, loop: asyncio.AbstractEventLoop, created: bool
    ) -> None:
        import asyncio

        if not created:
            return
        try:
            if loop and not loop.is_closed() and loop is not asyncio.get_running_loop():
                loop.close()
        except RuntimeError:
            pass

    @classmethod
    async def delete(cls, conversation_id: str) -> None:
        """Delete runtime resources associated with a conversation.

        Args:
            conversation_id: ID of conversation to clean up

        """
        pass

    def log(self, level: str, message: str) -> None:
        """Log message with runtime context.

        Args:
            level: Log level ('debug', 'info', 'warning', 'error')
            message: Message to log

        """
        message = f"[runtime {self.sid}] {message}"
        getattr(logger, level)(message, stacklevel=2)

    def set_runtime_status(
        self, runtime_status: RuntimeStatus, msg: str = "", level: str = "info"
    ) -> None:
        """Sends a status message if the callback function was provided."""
        self.runtime_status = runtime_status
        if self.status_callback:
            self.status_callback(level, runtime_status, msg)

    def _uses_windows_shell(self) -> bool:
        """Determine if runtime shell commands should use PowerShell syntax."""
        return False

    def _add_env_vars_to_jupyter(self, env_vars: dict[str, str]) -> None:
        """Add environment variables to Jupyter/IPython session."""
        code = "import os\n"
        for key, value in env_vars.items():
            code += f'os.environ["{key}"] = {json.dumps(value)}\n'
        code += "\n"
        self.run_ipython(IPythonRunCellAction(code))
        logger.debug("Added env vars to IPython")

    def _build_powershell_env_cmd(self, env_vars: dict[str, str]) -> str:
        """Build PowerShell command to set environment variables."""
        cmd = "".join(
            f"$env:{key} = {json.dumps(value)}; " for key, value in env_vars.items()
        )
        return cmd.strip() if cmd else ""

    def _add_env_vars_to_powershell(self, env_vars: dict[str, str]) -> None:
        """Add environment variables to PowerShell session."""
        cmd = self._build_powershell_env_cmd(env_vars)
        if not cmd:
            return
        logger.debug("Adding env vars to PowerShell")
        action = CmdRunAction(cmd, blocking=True, hidden=True)
        action.set_hard_timeout(30)
        obs = self.run(action)
        if not isinstance(obs, CmdOutputObservation) or obs.exit_code != 0:
            msg = f"Failed to add env vars [{env_vars.keys()}] to environment: {obs.content}"
            raise RuntimeError(msg)
        logger.debug("Added env vars to PowerShell session: %s", env_vars.keys())

    def _build_bash_env_commands(self, env_vars: dict[str, str]) -> tuple[str, str]:
        """Build bash commands to set environment variables."""
        cmd = ""
        bashrc_cmd = ""
        for key, value in env_vars.items():
            cmd += f"export {key}={json.dumps(value)}; "
            bashrc_cmd += f'touch ~/.bashrc; grep -q "^export {
                key
            }=" ~/.bashrc || echo "export {key}={json.dumps(value)}" >> ~/.bashrc; '
        return cmd.strip() if cmd else "", bashrc_cmd.strip() if bashrc_cmd else ""

    def _add_env_vars_to_bash(self, env_vars: dict[str, str]) -> None:
        """Add environment variables to bash session and .bashrc."""
        cmd, bashrc_cmd = self._build_bash_env_commands(env_vars)
        if not cmd:
            return

        # Add to current session
        logger.debug("Adding env vars to bash")
        action = CmdRunAction(cmd, blocking=True, hidden=True)
        action.set_hard_timeout(30)
        obs = self.run(action)
        if not isinstance(obs, CmdOutputObservation) or obs.exit_code != 0:
            msg = f"Failed to add env vars [{env_vars.keys()}] to environment: {obs.content}"
            raise RuntimeError(msg)

        # Add to .bashrc for persistence
        logger.debug("Adding env var to .bashrc: %s", env_vars.keys())
        bashrc_action = CmdRunAction(bashrc_cmd, blocking=True, hidden=True)
        bashrc_action.set_hard_timeout(30)
        obs = self.run(bashrc_action)
        if not isinstance(obs, CmdOutputObservation) or obs.exit_code != 0:
            msg = (
                f"Failed to add env vars [{env_vars.keys()}] to .bashrc: {obs.content}"
            )
            raise RuntimeError(msg)

    def add_env_vars(self, env_vars: dict[str, str]) -> None:
        """Add environment variables to runtime.

        Sets variables in Jupyter and bash environments.

        Args:
            env_vars: Dictionary of environment variables to add

        """
        env_vars = {key.upper(): value for key, value in env_vars.items()}
        os.environ.update(env_vars)

        # Add to Jupyter if available
        if any(isinstance(plugin, JupyterRequirement) for plugin in self.plugins):
            self._add_env_vars_to_jupyter(env_vars)

        # Add to shell environment
        try:
            if self._uses_windows_shell():
                self._add_env_vars_to_powershell(env_vars)
            else:
                self._add_env_vars_to_bash(env_vars)
        except RuntimeError as exc:
            logger.warning(
                "Unable to apply shell env vars %s: %s",
                list(env_vars.keys()),
                exc,
            )

    def on_event(self, event: Event) -> None:
        """Handle incoming events (primarily actions from agent).

        Args:
            event: Event to process

        """
        if isinstance(event, Action):
            self._run_or_schedule(self._handle_action(event))

    @staticmethod
    def _run_or_schedule(coro: Coroutine[Any, Any, Any]) -> None:
        """Ensure coroutine runs on an event loop, creating one if necessary."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            loop.create_task(coro)
            return

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)

    async def _export_latest_git_provider_tokens(self, event: Action) -> None:
        """Refresh runtime provider tokens when agent attemps to run action with provider token."""
        providers_called = ProviderHandler.check_cmd_action_for_provider_token_ref(
            event
        )
        if not providers_called:
            return
        provider_handler = ProviderHandler(
            provider_tokens=self.git_provider_tokens,
            external_auth_id=self.user_id,
            external_token_manager=True,
            session_api_key=self.session_api_key,
            sid=self.sid,
        )
        logger.info("Fetching latest provider tokens for runtime")
        env_vars = cast(
            dict[ProviderType, SecretStr],
            await provider_handler.get_env_vars(
                providers=providers_called,
                expose_secrets=False,
                get_latest=True,
            ),
        )
        if len(env_vars) == 0:
            return
        try:
            if self.event_stream:
                await provider_handler.set_event_stream_secrets(
                    self.event_stream, env_vars=env_vars
                )
            self.add_env_vars(provider_handler.expose_env_vars(env_vars))
        except Exception as e:
            logger.warning("Failed to export latest provider tokens to runtime")

    def _is_long_running_command(self, command: str) -> bool:
        """Detect if a command is a long-running server/process.

        Args:
            command: The bash command to check

        Returns:
            True if command should run without timeout, False otherwise

        """
        # Normalize command for checking
        cmd_lower = command.lower().strip()

        # Server commands that should run indefinitely
        server_patterns = [
            "python -m http.server",
            "python3 -m http.server",
            "npm run dev",
            "npm start",
            "yarn dev",
            "yarn start",
            "pnpm dev",
            "pnpm start",
            "node server",
            "nodemon",
            "flask run",
            "django-admin runserver",
            "python manage.py runserver",
            "uvicorn",
            "gunicorn",
            "hypercorn",
            "daphne",
            "streamlit run",
            "gradio",
            "rails server",
            "bundle exec rails",
            "php artisan serve",
            "go run",
            "./server",
            "java -jar",
            "docker run",
            "docker-compose up",
        ]

        return any(pattern in cmd_lower for pattern in server_patterns)

    def _set_action_timeout(self, event: Action) -> None:
        """Set appropriate timeout for action based on type.

        Args:
            event: Action to set timeout for

        """
        if event.timeout is not None:
            return

        # Check if this is a long-running command (server, etc.)
        if isinstance(event, CmdRunAction) and self._is_long_running_command(
            event.command
        ):
            # No timeout for servers - they should run until explicitly stopped
            logger.info(
                f"🚀 Detected long-running command, removing timeout: {event.command[:100]}"
            )
            event.set_hard_timeout(None, blocking=False)

            # Register long-running process for cleanup
            if hasattr(self, "process_manager"):
                command_id = f"{self.sid}_{event.id}_{int(time.time())}"
                self.process_manager.register_process(event.command, command_id)
        else:
            # Normal commands get standard timeout
            event.set_hard_timeout(self.config.sandbox.timeout, blocking=False)

    async def _execute_action(self, event: Action) -> Observation:
        """Execute action and return observation.

        Args:
            event: Action to execute

        Returns:
            Observation from action execution

        """
        await self._export_latest_git_provider_tokens(event)

        if isinstance(event, MCPAction):
            return await self.call_tool_mcp(event)
        else:
            return await call_sync_from_async(self.run_action, event)

    def _handle_runtime_error(
        self, event: Action, error: Exception, is_network_error: bool = False
    ) -> None:
        """Handle runtime error during action execution.

        Args:
            event: Action that caused error
            error: Exception raised
            is_network_error: Whether this is a network/disconnection error

        """
        runtime_status = (
            RuntimeStatus.ERROR_RUNTIME_DISCONNECTED
            if is_network_error
            else RuntimeStatus.ERROR
        )
        error_message = f"{type(error).__name__}: {error!s}"
        self.log("error", f"Unexpected error while running action: {error_message}")
        self.log("error", f"Problematic action: {event!s}")
        self.set_runtime_status(runtime_status, error_message, level="error")

    def _process_observation(self, observation: Observation, event: Action) -> bool:
        """Process observation result and add to event stream.

        Args:
            observation: Observation to process
            event: Source action

        Returns:
            True if observation should be added to stream, False otherwise

        """
        observation.cause = event.id
        observation.tool_call_metadata = event.tool_call_metadata

        if isinstance(observation, NullObservation):
            return False

        return True

    async def _handle_action(self, event: Action) -> None:
        """Handle action execution with timeout, error handling, and observation processing."""
        self._set_action_timeout(event)

        assert event.timeout is not None or (
            isinstance(event, CmdRunAction)
            and self._is_long_running_command(event.command)
        )

        try:
            observation = await self._execute_action(event)
        except PermissionError as e:
            observation = ErrorObservation(content=str(e))
        except (httpx.NetworkError, AgentRuntimeDisconnectedError) as e:
            self._handle_runtime_error(event, e, is_network_error=True)
            return
        except Exception as e:
            self._handle_runtime_error(event, e, is_network_error=False)
            return

        if not self._process_observation(observation, event):
            return

        source = event.source or EventSource.AGENT
        if self.event_stream:
            self.event_stream.add_event(observation, source)

    async def clone_or_init_repo(
        self,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None,
        selected_repository: str | None,
        selected_branch: str | None,
    ) -> str:
        """Clone repository or initialize workspace.

        Args:
            git_provider_tokens: Provider authentication tokens
            selected_repository: Repository to clone (None to use workspace)
            selected_branch: Branch to checkout

        Returns:
            Path to repository directory

        """
        if not selected_repository:
            if self.config.init_git_in_empty_workspace:
                logger.debug(
                    "No repository selected. Initializing a new git repository in the workspace."
                )
                action = CmdRunAction(
                    command=f"git init && git config --global --add safe.directory {self.workspace_root}",
                )
                await call_sync_from_async(self.run_action, action)
            else:
                logger.info(
                    "In workspace mount mode, not initializing a new git repository."
                )
            return ""
        remote_repo_url = await self.provider_handler.get_authenticated_git_url(
            selected_repository
        )
        if not remote_repo_url:
            msg = "Missing either Git token or valid repository"
            raise ValueError(msg)
        if self.status_callback:
            self.status_callback(
                "info", RuntimeStatus.SETTING_UP_WORKSPACE, "Setting up workspace..."
            )
        dir_name = selected_repository.split("/")[-1].lower()
        random_str = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        FORGE_workspace_branch = f"Forge-workspace-{random_str}"
        clone_command = f"git clone {remote_repo_url} {dir_name}"
        checkout_command = (
            f"git checkout {selected_branch}"
            if selected_branch
            else f"git checkout -b {FORGE_workspace_branch}"
        )
        clone_action = CmdRunAction(command=clone_command)
        await call_sync_from_async(self.run_action, clone_action)
        cd_checkout_action = CmdRunAction(
            command=f"cd {dir_name} && {checkout_command}"
        )
        action = cd_checkout_action
        self.log("info", f"Cloning repo: {selected_repository}")
        await call_sync_from_async(self.run_action, action)
        return dir_name

    def maybe_run_setup_script(self) -> None:
        """Run .Forge/setup.sh if it exists in the workspace or repository."""
        setup_script = ".Forge/setup.sh"
        read_obs = self.read(FileReadAction(path=setup_script))
        if isinstance(read_obs, ErrorObservation):
            return
        if self.status_callback:
            self.status_callback(
                "info", RuntimeStatus.SETTING_UP_WORKSPACE, "Setting up workspace..."
            )
        action = CmdRunAction(
            f"chmod +x {setup_script} && source {setup_script}",
            blocking=True,
            hidden=True,
        )
        action.set_hard_timeout(600)
        source = EventSource.ENVIRONMENT
        if self.event_stream:
            self.event_stream.add_event(action, source)
        self.run_action(action)

    @property
    def workspace_root(self) -> Path:
        """Return the workspace root path."""
        return Path(self.config.workspace_mount_path_in_sandbox)

    def _setup_git_hooks_directory(self) -> bool:
        """Create git hooks directory if needed."""
        action = CmdRunAction("mkdir -p .git/hooks")
        obs = self.run_action(action)
        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                return True
            self.log("error", f"Failed to create git hooks directory: {obs.content}")
            return False
        return False

    def _make_script_executable(self, script_path: str) -> bool:
        """Make a script file executable."""
        action = CmdRunAction(f"chmod +x {script_path}")
        obs = self.run_action(action)
        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                return True
            self.log("error", f"Failed to make {script_path} executable: {obs.content}")
            return False
        return False

    def _preserve_existing_hook(self, pre_commit_hook: str) -> bool:
        """Preserve existing pre-commit hook by moving it to .local file."""
        pre_commit_local = ".git/hooks/pre-commit.local"
        action = CmdRunAction(f"mv {pre_commit_hook} {pre_commit_local}")
        obs = self.run_action(action)
        if isinstance(obs, CmdOutputObservation):
            if obs.exit_code == 0:
                return bool(Runtime._make_script_executable(self, pre_commit_local))
            self.log(
                "error", f"Failed to preserve existing pre-commit hook: {obs.content}"
            )
            return False

        try:
            shutil.move(pre_commit_hook, pre_commit_local)
            return bool(Runtime._make_script_executable(self, pre_commit_local))
        except (OSError, shutil.Error) as exc:
            self.log("error", f"Failed to preserve existing pre-commit hook: {exc}")
            return False

    def _install_pre_commit_hook(
        self, pre_commit_script: str, pre_commit_hook: str
    ) -> bool:
        """Install the pre-commit hook file."""
        pre_commit_hook_content = f'#!/bin/bash\n# This hook was installed by Forge\n# It calls the pre-commit script in the .Forge directory\n\nif [ -x "{pre_commit_script}" ]; then\n    source "{pre_commit_script}"\n    exit $?\nelse\n    echo "Warning: {pre_commit_script} not found or not executable"\n    exit 0\nfi\n'

        write_obs = self.write(
            FileWriteAction(path=pre_commit_hook, content=pre_commit_hook_content)
        )
        if isinstance(write_obs, ErrorObservation):
            self.log("error", f"Failed to write pre-commit hook: {write_obs.content}")
            return False

        return bool(Runtime._make_script_executable(self, pre_commit_hook))

    def maybe_setup_git_hooks(self) -> None:
        """Set up git hooks if .Forge/pre-commit.sh exists in the workspace or repository."""
        pre_commit_script = ".Forge/pre-commit.sh"
        pre_commit_hook = ".git/hooks/pre-commit"

        # Check if pre-commit script exists
        read_obs = self.read(FileReadAction(path=pre_commit_script))
        if isinstance(read_obs, ErrorObservation):
            return

        if self.status_callback:
            self.status_callback(
                "info", RuntimeStatus.SETTING_UP_GIT_HOOKS, "Setting up git hooks..."
            )

        # Setup hooks directory
        if not Runtime._setup_git_hooks_directory(self):
            return

        # Make pre-commit script executable
        if not Runtime._make_script_executable(self, pre_commit_script):
            return

        # Preserve existing hook if needed
        read_obs = self.read(FileReadAction(path=pre_commit_hook))
        if (
            not isinstance(read_obs, ErrorObservation)
            and "This hook was installed by Forge" not in read_obs.content
        ):
            self.log("info", "Preserving existing pre-commit hook")
            if not Runtime._preserve_existing_hook(self, pre_commit_hook):
                return

        # Install new hook
        if Runtime._install_pre_commit_hook(self, pre_commit_script, pre_commit_hook):
            self.log("info", "Git pre-commit hook installed successfully")

    def _load_microagents_from_directory(
        self, microagents_dir: Path, source_description: str
    ) -> list[BaseMicroagent]:
        """Load microagents from a directory.

        Args:
            microagents_dir: Path to the directory containing microagents
            source_description: Description of the source for logging purposes

        Returns:
            A list of loaded microagents

        """
        loaded_microagents: list[BaseMicroagent] = []
        self.log(
            "info",
            f"Attempting to list files in {source_description} microagents directory: {microagents_dir}",
        )
        files = self.list_files(str(microagents_dir))
        if not files:
            self.log(
                "debug",
                f"No files found in {source_description} microagents directory: {microagents_dir}",
            )
            return loaded_microagents
        self.log(
            "info",
            f"Found {len(files)} files in {source_description} microagents directory",
        )
        zip_path = self.copy_from(str(microagents_dir))
        microagent_folder = tempfile.mkdtemp()
        try:
            with ZipFile(zip_path, "r") as zip_file:
                zip_file.extractall(microagent_folder)
            zip_path.unlink()
            repo_agents, knowledge_agents = load_microagents_from_dir(microagent_folder)
            self.log(
                "info",
                f"Loaded {len(repo_agents)} repo agents and {
                    len(knowledge_agents)
                } knowledge agents from {source_description}",
            )
            loaded_microagents.extend(repo_agents.values())
            loaded_microagents.extend(knowledge_agents.values())
        except Exception as e:
            self.log("error", f"Failed to load agents from {source_description}: {e}")
        finally:
            shutil.rmtree(microagent_folder)
        return loaded_microagents

    def _is_gitlab_repository(self, repo_name: str) -> bool:
        """Check if a repository is hosted on GitLab.

        Args:
            repo_name: Repository name (e.g., "gitlab.com/org/repo" or "org/repo")

        Returns:
            True if the repository is hosted on GitLab, False otherwise

        """
        try:
            provider_handler = ProviderHandler(self.git_provider_tokens)
            repository = call_async_from_sync(
                provider_handler.verify_repo_provider, GENERAL_TIMEOUT, repo_name
            )
            return repository.git_provider == ProviderType.GITLAB
        except Exception:
            return False

    def get_microagents_from_org_or_user(
        self, selected_repository: str
    ) -> list[BaseMicroagent]:
        """Load microagents from the organization or user level repository.

        For example, if the repository is github.com/acme-co/api, this will check if
        github.com/acme-co/.Forge exists. If it does, it will clone it and load
        the microagents from the ./microagents/ folder.

        For GitLab repositories, it will use Forge-config instead of .Forge
        since GitLab doesn't support repository names starting with non-alphanumeric
        characters.

        Args:
            selected_repository: The repository path (e.g., "github.com/acme-co/api")

        Returns:
            A list of loaded microagents from the org/user level repository

        """
        self.log(
            "debug",
            f"Starting org-level microagent loading for repository: {selected_repository}",
        )

        org_name = self._extract_org_name(selected_repository)
        if not org_name:
            return []

        org_FORGE_repo = self._get_org_config_repo_path(selected_repository, org_name)
        self.log("info", f"Checking for org-level microagents at {org_FORGE_repo}")

        return self._clone_and_load_org_microagents(org_name, org_FORGE_repo)

    def _extract_org_name(self, selected_repository: str) -> str | None:
        """Extract organization name from repository path.

        Args:
            selected_repository: Full repository path

        Returns:
            Organization name or None if invalid

        """
        repo_parts = selected_repository.split("/")
        if len(repo_parts) < 2:
            self.log(
                "warning",
                f"Repository path has insufficient parts ({len(repo_parts)} < 2), skipping org-level microagents",
            )
            return None

        org_name = repo_parts[-2]
        self.log("info", f"Extracted org/user name: {org_name}")
        return org_name

    def _get_org_config_repo_path(self, selected_repository: str, org_name: str) -> str:
        """Get org-level config repository path.

        Args:
            selected_repository: Full repository path
            org_name: Organization name

        Returns:
            Config repository path

        """
        is_gitlab = self._is_gitlab_repository(selected_repository)
        self.log("debug", f"Repository type detection - is_gitlab: {is_gitlab}")

        if is_gitlab:
            return f"{org_name}/Forge-config"
        return f"{org_name}/.Forge"

    def _clone_and_load_org_microagents(
        self, org_name: str, org_FORGE_repo: str
    ) -> list[BaseMicroagent]:
        """Clone org config repo and load microagents.

        Args:
            org_name: Organization name
            org_FORGE_repo: Org config repository path

        Returns:
            List of loaded microagents

        """
        org_repo_dir = self.workspace_root / f"org_FORGE_{org_name}"
        self.log("debug", f"Creating temporary directory for org repo: {org_repo_dir}")

        try:
            remote_url = call_async_from_sync(
                self.provider_handler.get_authenticated_git_url,
                GENERAL_TIMEOUT,
                org_FORGE_repo,
            )
        except AuthenticationError as e:
            self.log(
                "debug",
                f"org-level microagent directory {org_FORGE_repo} not found: {e!s}",
            )
            return []
        except Exception as e:
            self.log(
                "debug", f"Failed to get authenticated URL for {org_FORGE_repo}: {e!s}"
            )
            return []

        return self._execute_clone_and_load(org_repo_dir, remote_url, org_FORGE_repo)

    def _execute_clone_and_load(
        self, org_repo_dir, remote_url: str, org_FORGE_repo: str
    ) -> list[BaseMicroagent]:
        """Execute git clone and load microagents.

        Args:
            org_repo_dir: Directory to clone into
            remote_url: Git remote URL
            org_FORGE_repo: Org config repository name

        Returns:
            List of loaded microagents

        """
        clone_cmd = (
            f"GIT_TERMINAL_PROMPT=0 git clone --depth 1 {remote_url} {org_repo_dir}"
        )
        self.log("info", "Executing clone command for org-level repo")

        action = CmdRunAction(command=clone_cmd)
        obs = self.run_action(action)

        if isinstance(obs, CmdOutputObservation) and obs.exit_code == 0:
            return self._load_and_cleanup_org_microagents(org_repo_dir, org_FORGE_repo)
        self._log_clone_failure(obs, org_FORGE_repo)
        return []

    def _load_and_cleanup_org_microagents(
        self, org_repo_dir, org_FORGE_repo: str
    ) -> list[BaseMicroagent]:
        """Load microagents and cleanup cloned repo.

        Args:
            org_repo_dir: Cloned repository directory
            org_FORGE_repo: Org config repository name

        Returns:
            List of loaded microagents

        """
        self.log(
            "info", f"Successfully cloned org-level microagents from {org_FORGE_repo}"
        )
        org_microagents_dir = org_repo_dir / "microagents"
        self.log("info", f"Looking for microagents in directory: {org_microagents_dir}")

        loaded_microagents = self._load_microagents_from_directory(
            org_microagents_dir, "org-level"
        )
        self.log(
            "info",
            f"Loaded {len(loaded_microagents)} microagents from org-level repository {org_FORGE_repo}",
        )

        # Cleanup
        action = CmdRunAction(f"rm -rf {org_repo_dir}")
        self.run_action(action)

        return loaded_microagents

    def _log_clone_failure(self, obs, org_FORGE_repo: str) -> None:
        """Log clone failure details.

        Args:
            obs: Observation from clone command
            org_FORGE_repo: Org config repository name

        """
        clone_error_msg = (
            obs.content if isinstance(obs, CmdOutputObservation) else "Unknown error"
        )
        exit_code = obs.exit_code if isinstance(obs, CmdOutputObservation) else "N/A"
        self.log(
            "info",
            f"No org-level microagents found at {org_FORGE_repo} (exit_code: {exit_code})",
        )
        self.log("debug", f"Clone command output: {clone_error_msg}")

    def get_microagents_from_selected_repo(
        self, selected_repository: str | None
    ) -> list[BaseMicroagent]:
        """Load microagents from the selected repository.

        If selected_repository is None, load microagents from the current workspace.
        This is the main entry point for loading microagents.

        This method also checks for user/org level microagents stored in a repository.
        For example, if the repository is github.com/acme-co/api, it will also check for
        github.com/acme-co/.Forge and load microagents from there if it exists.

        For GitLab repositories, it will use Forge-config instead of .Forge
        since GitLab doesn't support repository names starting with non-alphanumeric
        characters.
        """
        microagents_dir = self.workspace_root / ".Forge" / "microagents"
        repo_root = None
        loaded_microagents: list[BaseMicroagent] = []
        if selected_repository:
            org_microagents = self.get_microagents_from_org_or_user(selected_repository)
            loaded_microagents.extend(org_microagents)
            repo_root = self.workspace_root / selected_repository.split("/")[-1]
            microagents_dir = repo_root / ".Forge" / "microagents"
        self.log(
            "info",
            f"Selected repo: {selected_repository}, loading microagents from {microagents_dir} (inside runtime)",
        )
        obs = self.read(
            FileReadAction(path=str(self.workspace_root / ".FORGE_instructions"))
        )
        if isinstance(obs, ErrorObservation) and repo_root is not None:
            self.log(
                "debug",
                f".FORGE_instructions not present, trying to load from repository microagents_dir={
                    microagents_dir!r
                }",
            )
            obs = self.read(FileReadAction(path=str(repo_root / ".FORGE_instructions")))
        if isinstance(obs, FileReadObservation):
            self.log("info", "FORGE_instructions microagent loaded.")
            loaded_microagents.append(
                BaseMicroagent.load(
                    path=".FORGE_instructions",
                    microagent_dir=None,
                    file_content=obs.content,
                ),
            )
        repo_microagents = self._load_microagents_from_directory(
            microagents_dir, "repository"
        )
        loaded_microagents.extend(repo_microagents)
        return loaded_microagents

    def run_action(self, action: Action) -> Observation:
        """Run an action and return the resulting observation.

        If the action is not runnable in any runtime, a NullObservation is returned.
        If the action is not supported by the current runtime, an ErrorObservation is returned.
        """
        # Handle special action types
        if isinstance(action, AgentThinkAction):
            return AgentThinkObservation("Your thought has been logged.")

        if isinstance(action, TaskTrackingAction):
            return self._handle_task_tracking_action(action)

        # Check confirmation state
        confirmation_result = self._check_action_confirmation(action)
        if confirmation_result is not None:
            return confirmation_result

        # Validate action type and runtime support
        validation_result = self._validate_action(action)
        if validation_result is not None:
            return validation_result

        # Check if this is an agent-level action that should not be executed by runtime
        action_type = action.action
        agent_level_actions = {
            "change_agent_state",
            "message",
            "recall",
            "think",
            "finish",
            "reject",
            "delegate",
            "condensation",
            "condensation_request",
            "task_tracking",
            "system",
        }

        if action_type in agent_level_actions:
            # These actions are handled by the agent system, not the runtime
            return NullObservation(content="")

        # Execute the action (synchronous path)
        observation = self._execute_action_sync(action)

        # Verify critical actions (Layer 3: Post-Action Verification)
        verification_obs = self._verify_action_if_needed(action, observation)
        if verification_obs:
            # Return combined observation with verification result
            return verification_obs

        return observation

    def _verify_action_if_needed(
        self, action: Action, observation: Observation
    ) -> Observation | None:
        """Verify critical actions to prevent hallucinations (Layer 3).

        Args:
            action: The action that was executed
            observation: The observation returned from execution

        Returns:
            Enhanced observation with verification, or None if no verification needed

        """
        # Only verify file operations
        if not isinstance(action, FileEditAction):
            return None

        # Skip verification if action already failed
        if isinstance(observation, ErrorObservation):
            return None

        try:
            # Verify file exists
            file_path = action.path
            verify_cmd = (
                f"test -f {file_path} && echo 'VERIFIED:EXISTS' || echo 'ERROR:MISSING'"
            )
            verify_result = self._execute_action_sync(CmdRunAction(command=verify_cmd))

            if isinstance(verify_result, CmdOutputObservation):
                if "ERROR:MISSING" in verify_result.content:
                    # CRITICAL: File was not created despite tool execution
                    logger.error(
                        f"HALLUCINATION DETECTED: File {file_path} missing after edit_file"
                    )
                    error_msg = f"""❌ CRITICAL VERIFICATION FAILURE:
File {file_path} does NOT exist despite edit_file tool execution.
This indicates a hallucination or execution failure.

Original observation: {observation.content[:200]}

Please retry the file creation."""
                    return ErrorObservation(content=error_msg)

                # File exists - get size/lines for confirmation
                size_cmd = (
                    f"wc -l {file_path} 2>/dev/null | awk '{{print $1}}' || echo '0'"
                )
                size_result = self._execute_action_sync(CmdRunAction(command=size_cmd))

                if isinstance(size_result, CmdOutputObservation):
                    try:
                        lines = int(size_result.content.strip())
                        # Enhance the original observation with verification
                        enhanced_content = f"""{observation.content}

✅ VERIFICATION: File {file_path} confirmed to exist ({lines} lines)"""
                        return FileWriteObservation(
                            content=enhanced_content, path=file_path
                        )
                    except ValueError:
                        pass

            # Return original observation if verification inconclusive
            return None

        except Exception as e:
            logger.warning(f"Verification error for {action.path}: {e}")
            # Don't fail the action due to verification errors
            return None

    def _handle_task_tracking_action(self, action: TaskTrackingAction) -> Observation:
        """Handle task tracking actions (plan/view)."""
        if self.event_stream is None:
            return ErrorObservation("Task tracking requires an event stream")
        conversation_dir = get_conversation_dir(self.sid, self.event_stream.user_id)
        task_file_path = f"{conversation_dir}TASKS.md"

        if action.command == "plan":
            return self._handle_task_plan_action(action, task_file_path)
        if action.command == "view":
            return self._handle_task_view_action(action, task_file_path)
        return NullObservation("")

    def _handle_task_plan_action(
        self, action: TaskTrackingAction, task_file_path: str
    ) -> Observation:
        """Handle task plan command - create/update task list."""
        content = self._generate_task_list_content(action.task_list)

        try:
            assert self.event_stream is not None
            self.event_stream.file_store.write(task_file_path, content)
            return TaskTrackingObservation(
                content=f"Task list has been updated with {len(action.task_list)} items. Stored in session directory: {task_file_path}",
                command=action.command,
                task_list=action.task_list,
            )
        except Exception as e:
            return ErrorObservation(
                f"Failed to write task list to session directory {task_file_path}: {e!s}"
            )

    def _handle_task_view_action(
        self, action: TaskTrackingAction, task_file_path: str
    ) -> Observation:
        """Handle task view command - read and display task list."""
        try:
            assert self.event_stream is not None
            content = self.event_stream.file_store.read(task_file_path)
            return TaskTrackingObservation(
                content=content, command=action.command, task_list=[]
            )
        except FileNotFoundError:
            return TaskTrackingObservation(
                command=action.command,
                task_list=[],
                content='No task list found. Use the "plan" command to create one.',
            )
        except Exception as e:
            return TaskTrackingObservation(
                command=action.command,
                task_list=[],
                content=f"Failed to read the task list from session directory {task_file_path}. Error: {e!s}",
            )

    def _generate_task_list_content(self, task_list: list) -> str:
        """Generate markdown content for task list."""
        content = "# Task List\n\n"
        for i, task in enumerate(task_list, 1):
            status_icon = {"todo": "⏳", "in_progress": "🔄", "done": "✅"}.get(
                task.get("status", "todo"),
                "⏳",
            )
            content += (
                f"{i}. {status_icon} {task.get('title', '')}\n{task.get('notes', '')}\n"
            )
        return content

    def _check_action_confirmation(self, action: Action) -> Observation | None:
        """Check action confirmation state and return appropriate observation."""
        if (
            hasattr(action, "confirmation_state")
            and action.confirmation_state
            == ActionConfirmationStatus.AWAITING_CONFIRMATION
        ):
            return NullObservation("")

        if (
            getattr(action, "confirmation_state", None)
            == ActionConfirmationStatus.REJECTED
        ):
            return UserRejectObservation(
                "Action has been rejected by the user! Waiting for further user input."
            )

        return None

    def _validate_action(self, action: Action) -> Observation | None:
        """Validate action type and runtime support."""
        action_type = action.action

        if action_type not in ACTION_TYPE_TO_CLASS:
            return ErrorObservation(f"Action {action_type} does not exist.")

        # Agent-level actions that should not be executed by runtime
        agent_level_actions = {
            "change_agent_state",
            "message",
            "recall",
            "think",
            "finish",
            "reject",
            "delegate",
            "condensation",
            "condensation_request",
            "task_tracking",
            "system",
        }

        if action_type in agent_level_actions:
            # These actions are handled by the agent system, not the runtime
            return None

        if not hasattr(self, action_type):
            return ErrorObservation(
                f"Action {action_type} is not supported in the current runtime."
            )

        return None

    def _execute_action_sync(self, action: Action) -> Observation:
        """Execute the validated action (synchronous internal path)."""
        action_type = action.action
        return getattr(self, action_type)(action)

    def __enter__(self) -> Self:
        """Enter runtime context manager.

        Returns:
            Self for context manager protocol

        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit runtime context manager, ensuring cleanup.

        Args:
            exc_type: Exception type if an error occurred
            exc_value: Exception value if an error occurred
            traceback: Traceback if an error occurred

        """
        self.close()

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the runtime environment.

        Must be implemented by subclasses to establish connection to
        the execution environment (local process, Docker container, etc.).
        """
        pass

    def _setup_git_config(self) -> None:
        """Configure git user settings during initial environment setup.

        This method is called automatically during setup_initial_env() to ensure
        git configuration is applied to the runtime environment.
        """
        git_user_name = self.config.git_user_name
        git_user_email = self.config.git_user_email
        is_cli_runtime = self.config.runtime == "cli"
        if is_cli_runtime:
            logger.debug(
                "Skipping git configuration for CLI runtime - using user's local git config"
            )
            return
        cmd = f'git config --global user.name "{git_user_name}" && git config --global user.email "{git_user_email}"'
        try:
            action = CmdRunAction(command=cmd)
            obs = self.run(action)
            if isinstance(obs, CmdOutputObservation) and obs.exit_code != 0:
                logger.warning(
                    "Git config command failed: %s, error: %s", cmd, obs.content
                )
            else:
                logger.info(
                    "Successfully configured git: name=%s, email=%s",
                    git_user_name,
                    git_user_email,
                )
        except Exception as e:
            logger.warning(
                "Failed to execute git config command: %s, error: %s", cmd, e
            )

    @abstractmethod
    def get_mcp_config(
        self, extra_stdio_servers: list[MCPStdioServerConfig] | None = None
    ) -> MCPConfig:
        """Get MCP (Model Context Protocol) configuration for this runtime.

        Args:
            extra_stdio_servers: Additional stdio servers to include in config

        Returns:
            MCP configuration with server definitions

        """
        pass

    @abstractmethod
    def run(self, action: CmdRunAction) -> Observation:
        """Execute a bash/shell command in the runtime environment.

        Args:
            action: Command run action containing command to execute

        Returns:
            Observation with command output and exit code

        """
        pass

    @abstractmethod
    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        """Execute Python code in IPython/Jupyter environment.

        Args:
            action: IPython action containing code to execute

        Returns:
            Observation with execution output

        """
        pass

    @abstractmethod
    def read(self, action: FileReadAction) -> Observation:
        """Read file contents from the runtime filesystem.

        Args:
            action: File read action with file path

        Returns:
            Observation with file contents

        """
        pass

    @abstractmethod
    def write(self, action: FileWriteAction) -> Observation:
        """Write content to a file in the runtime filesystem.

        Args:
            action: File write action with path and content

        Returns:
            Observation confirming write operation

        """
        pass

    @abstractmethod
    def edit(self, action: FileEditAction) -> Observation:
        """Edit file using search/replace or other edit operations.

        Args:
            action: File edit action with edit details

        Returns:
            Observation with edit results and diff

        """
        pass

    @abstractmethod
    def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        """Copy files from host into the runtime sandbox."""
        raise NotImplementedError

    @abstractmethod
    def copy_from(self, path: str) -> Path:
        """Copy files from the runtime sandbox to the host."""
        raise NotImplementedError

    @abstractmethod
    def list_files(self, path: str, recursive: bool = False) -> list[str]:
        """List files within the runtime sandbox."""
        raise NotImplementedError

    @abstractmethod
    def browse(self, action: BrowseURLAction) -> Observation:
        """Browse a URL and return page content.

        Args:
            action: Browse action with URL to visit

        Returns:
            Observation with page content

        """
        pass

    @abstractmethod
    def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        """Execute interactive browser commands using BrowserGym.

        Args:
            action: Browse interactive action with browser commands

        Returns:
            Observation with browser interaction results

        """
        pass

    @abstractmethod
    async def call_tool_mcp(self, action: MCPAction) -> Observation:
        """Call an MCP (Model Context Protocol) tool.

        Args:
            action: MCP action with tool name and arguments

        Returns:
            Observation with tool execution results

        """
        pass

    def get_git_diff(self, file_path: str, cwd: str) -> dict[str, str]:
        """Get git diff for a specific file.

        Args:
            file_path: Path to file to diff
            cwd: Working directory for git command

        Returns:
            Dictionary with diff information

        """
        self.git_handler.set_cwd(cwd)
        return self.git_handler.get_git_diff(file_path)

    def get_workspace_branch(self, primary_repo_path: str | None = None) -> str | None:
        """Get the current branch of the workspace.

        Args:
            primary_repo_path: Path to the primary repository within the workspace.
                              If None, uses the workspace root.

        Returns:
            str | None: The current branch name, or None if not a git repository or error occurs.

        """
        if primary_repo_path:
            git_cwd = str(self.workspace_root / primary_repo_path)
        else:
            git_cwd = str(self.workspace_root)
        self.git_handler.set_cwd(git_cwd)
        return self.git_handler.get_current_branch()

    @property
    def session_api_key(self) -> str | None:
        """Return a session API key if configured for the runtime (default: None)."""
        return None

    def _execute_shell_fn_git_handler(
        self, command: str, cwd: str | None
    ) -> CommandResult:
        """This function is used by the GitHandler to execute shell commands."""
        obs = self.run(
            CmdRunAction(command=command, is_static=True, hidden=True, cwd=cwd)
        )
        exit_code = 0
        if isinstance(obs, ErrorObservation):
            exit_code = -1
        else:
            exit_attr = getattr(obs, "exit_code", None)
            if isinstance(exit_attr, int):
                exit_code = exit_attr
        content = getattr(obs, "content", "")
        return CommandResult(content=content, exit_code=exit_code)

    def _create_file_fn_git_handler(self, path: str, content: str) -> int:
        """This function is used by the GitHandler to create files in the runtime."""
        obs = self.write(FileWriteAction(path=path, content=content))
        return -1 if isinstance(obs, ErrorObservation) else 0

    def additional_agent_instructions(self) -> str:
        """Provide runtime-specific instructions appended to agent prompts."""
        return ""

    def subscribe_to_shell_stream(
        self, callback: Callable[[str], None] | None = None
    ) -> bool:
        """Subscribe to shell command output stream.

        This method is meant to be overridden by runtime implementations
        that want to stream shell command output to external consumers.

        Args:
            callback: A function that will be called with each line of output from shell commands.
                     If None, any existing subscription will be removed.

        Returns False by default.

        """
        return False

    @classmethod
    def setup(cls, config: ForgeConfig, headless_mode: bool = False) -> None:
        """Set up the environment for runtimes to be created."""

    @classmethod
    def teardown(cls, config: ForgeConfig) -> None:
        """Tear down the environment in which runtimes are created."""
