from __future__ import annotations

from typing import TYPE_CHECKING

from openhands.core.logger import openhands_logger as logger

if TYPE_CHECKING:
    from openhands.core.config import OpenHandsConfig
    from openhands.runtime.plugins import PluginRequirement

DEFAULT_PYTHON_PREFIX = ["/openhands/micromamba/bin/micromamba", "run", "-n", "openhands", "poetry", "run"]
DEFAULT_MAIN_MODULE = "openhands.runtime.action_execution_server"


def get_action_execution_server_startup_command(
    server_port: int,
    plugins: list[PluginRequirement],
    app_config: OpenHandsConfig,
    python_prefix: list[str] = DEFAULT_PYTHON_PREFIX,
    override_user_id: int | None = None,
    override_username: str | None = None,
    main_module: str = DEFAULT_MAIN_MODULE,
    python_executable: str = "python",
) -> list[str]:
    """Generate the startup command for the action execution server.

    Args:
        server_port: The port number for the server.
        plugins: List of plugin requirements.
        app_config: OpenHands configuration object.
        python_prefix: Python command prefix (default: micromamba with poetry).
        override_user_id: Override user ID for the server process.
        override_username: Override username for the server process.
        main_module: Main module to execute (default: action_execution_server).
        python_executable: Python executable to use.

    Returns:
        list[str]: Command arguments for starting the action execution server.
    """
    sandbox_config = app_config.sandbox
    logger.debug("app_config %s", vars(app_config))
    logger.debug("sandbox_config %s", vars(sandbox_config))
    logger.debug("override_user_id %s", override_user_id)
    plugin_args = []
    if plugins is not None and plugins:
        plugin_args = ["--plugins"] + [plugin.name for plugin in plugins]
    browsergym_args = []
    if sandbox_config.browsergym_eval_env is not None:
        # Split and validate environment string to prevent command injection
        env_parts = sandbox_config.browsergym_eval_env.split(" ")
        # Filter out empty strings and validate non-shell metacharacters
        validated_parts = []
        for part in env_parts:
            part = part.strip()
            if part and not any(char in part for char in [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", '\\']):
                validated_parts.append(part)
        if validated_parts:
            browsergym_args = ["--browsergym-eval-env"] + validated_parts
    username = override_username or ("openhands" if app_config.run_as_openhands else "root")
    # Validate username to prevent command injection
    if username and any(char in username for char in [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", '\\', ' ', '\n', '\t']):
        logger.warning("Invalid characters in username, using default")
        username = "openhands" if app_config.run_as_openhands else "root"
    
    user_id = override_user_id or (1000 if app_config.run_as_openhands else 0)
    base_cmd = [
        *python_prefix,
        python_executable,
        "-u",
        "-m",
        main_module,
        str(server_port),
        "--working-dir",
        app_config.workspace_mount_path_in_sandbox,
        *plugin_args,
        "--username",
        username,
        "--user-id",
        str(user_id),
        *browsergym_args,
    ]
    if not app_config.enable_browser:
        base_cmd.append("--no-enable-browser")
    logger.debug("get_action_execution_server_startup_command: %s", base_cmd)
    return base_cmd
