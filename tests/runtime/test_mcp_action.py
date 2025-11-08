"""Bash-related tests for the DockerRuntime, which connects to the ActionExecutor running in the sandbox."""

import json
import os
import socket
import time
import docker
import pytest
import forge
from conftest import _load_runtime
from forge.core.config import MCPConfig
from forge.core.config.mcp_config import MCPSSEServerConfig, MCPStdioServerConfig
from forge.core.logger import forge_logger as logger
from forge.events.action import CmdRunAction, MCPAction
from forge.events.observation import CmdOutputObservation, MCPObservation

pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_RUNTIME") == "cli", reason="CLIRuntime does not support MCP actions"
)


@pytest.fixture
def sse_mcp_docker_server():
    """Manages the lifecycle of the SSE MCP Docker container for tests, using a random available port."""
    image_name = "supercorp/supergateway"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        host_port = s.getsockname()[1]
    container_internal_port = 8000
    container_command_args = [
        "--stdio",
        "npx -y @modelcontextprotocol/server-filesystem@2025.8.18 /",
        "--port",
        str(container_internal_port),
        "--baseUrl",
        f"http://localhost:{host_port}",
    ]
    client = docker.from_env()
    container = None
    log_streamer = None
    from forge.runtime.utils.log_streamer import LogStreamer

    try:
        logger.info(
            "Starting Docker container %s with command: %s and mapping internal port %s to host port %s",
            image_name,
            " ".join(container_command_args),
            container_internal_port,
            host_port,
            extra={"msg_type": "ACTION"},
        )
        container = client.containers.run(
            image_name,
            command=container_command_args,
            ports={f"{container_internal_port}/tcp": host_port},
            detach=True,
            auto_remove=True,
            stdin_open=True,
        )
        logger.info("Container %s started, listening on host port %s.", container.short_id, host_port)
        log_streamer = LogStreamer(
            container,
            lambda level, msg: getattr(logger, level.lower())(
                f"[MCP server {
                    container.short_id}] {msg}"
            ),
        )
        time.sleep(10)
        yield {"url": f"http://localhost:{host_port}/sse"}
    finally:
        if container:
            logger.info("Stopping container %s...", container.short_id)
            try:
                container.stop(timeout=5)
                logger.info("Container %s stopped (and should be auto-removed).", container.short_id)
            except docker.errors.NotFound:
                logger.info("Container %s not found, likely already stopped and removed.", container.short_id)
            except Exception as e:
                logger.error("Error stopping container %s: %s", container.short_id, e)
        if log_streamer:
            log_streamer.close()


def test_default_activated_tools():
    project_root = os.path.dirname(forge.__file__)
    mcp_config_path = os.path.join(project_root, "runtime", "mcp", "config.json")
    assert os.path.exists(mcp_config_path), f"MCP config file not found at {mcp_config_path}"
    with open(mcp_config_path, "r", encoding='utf-8') as f:
        mcp_config = json.load(f)
    assert "mcpServers" in mcp_config
    assert "default" in mcp_config["mcpServers"]
    assert "tools" in mcp_config
    assert len(mcp_config["tools"]) == 0


@pytest.mark.asyncio
async def test_fetch_mcp_via_stdio(temp_dir, runtime_cls, run_as_Forge):
    mcp_stdio_server_config = MCPStdioServerConfig(name="fetch", command="uvx", args=["mcp-server-fetch"])
    override_mcp_config = MCPConfig(stdio_servers=[mcp_stdio_server_config])
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, override_mcp_config=override_mcp_config, enable_browser=True
    )
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0
    assert "[1]" in obs.content
    action_cmd = CmdRunAction(command="sleep 3 && cat server.log")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    mcp_action = MCPAction(name="fetch", arguments={"url": "http://localhost:8000"})
    obs = await runtime.call_tool_mcp(mcp_action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, MCPObservation), "The observation should be a MCPObservation."
    result_json = json.loads(obs.content)
    assert not result_json["isError"]
    assert len(result_json["content"]) == 1
    assert result_json["content"][0]["type"] == "text"
    assert (
        result_json["content"][0]["text"]
        == "Contents of http://localhost:8000/:\n---\n\n* <.downloads/>\n* <server.log>\n\n---"
    )
    runtime.close()


@pytest.mark.asyncio
async def test_filesystem_mcp_via_sse(temp_dir, runtime_cls, run_as_Forge, sse_mcp_docker_server):
    sse_server_info = sse_mcp_docker_server
    sse_url = sse_server_info["url"]
    runtime = None
    try:
        mcp_sse_server_config = MCPSSEServerConfig(url=sse_url)
        override_mcp_config = MCPConfig(sse_servers=[mcp_sse_server_config])
        runtime, config = _load_runtime(
            temp_dir, runtime_cls, run_as_Forge, override_mcp_config=override_mcp_config
        )
        mcp_action = MCPAction(name="list_directory", arguments={"path": "."})
        obs = await runtime.call_tool_mcp(mcp_action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, MCPObservation), "The observation should be a MCPObservation."
        assert "[FILE] .dockerenv" in obs.content
    finally:
        if runtime:
            runtime.close()


@pytest.mark.asyncio
async def test_both_stdio_and_sse_mcp(temp_dir, runtime_cls, run_as_Forge, sse_mcp_docker_server):
    sse_server_info = sse_mcp_docker_server
    sse_url = sse_server_info["url"]
    runtime = None
    try:
        mcp_sse_server_config = MCPSSEServerConfig(url=sse_url)
        mcp_stdio_server_config = MCPStdioServerConfig(name="fetch", command="uvx", args=["mcp-server-fetch"])
        override_mcp_config = MCPConfig(sse_servers=[mcp_sse_server_config], stdio_servers=[mcp_stdio_server_config])
        runtime, config = _load_runtime(
            temp_dir, runtime_cls, run_as_Forge, override_mcp_config=override_mcp_config, enable_browser=True
        )
        mcp_action_sse = MCPAction(name="list_directory", arguments={"path": "."})
        obs_sse = await runtime.call_tool_mcp(mcp_action_sse)
        logger.info(obs_sse, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_sse, MCPObservation), "The observation should be a MCPObservation."
        assert "[FILE] .dockerenv" in obs_sse.content
        action_cmd_http = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
        logger.info(action_cmd_http, extra={"msg_type": "ACTION"})
        obs_http = runtime.run_action(action_cmd_http)
        logger.info(obs_http, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_http, CmdOutputObservation)
        assert obs_http.exit_code == 0
        assert "[1]" in obs_http.content
        action_cmd_cat = CmdRunAction(command="sleep 3 && cat server.log")
        logger.info(action_cmd_cat, extra={"msg_type": "ACTION"})
        obs_cat = runtime.run_action(action_cmd_cat)
        logger.info(obs_cat, extra={"msg_type": "OBSERVATION"})
        assert obs_cat.exit_code == 0
        mcp_action_fetch = MCPAction(name="fetch", arguments={"url": "http://localhost:8000"})
        obs_fetch = await runtime.call_tool_mcp(mcp_action_fetch)
        logger.info(obs_fetch, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_fetch, MCPObservation), "The observation should be a MCPObservation."
        result_json = json.loads(obs_fetch.content)
        assert not result_json["isError"]
        assert len(result_json["content"]) == 1
        assert result_json["content"][0]["type"] == "text"
        assert (
            result_json["content"][0]["text"]
            == "Contents of http://localhost:8000/:\n---\n\n* <.downloads/>\n* <server.log>\n\n---"
        )
    finally:
        if runtime:
            runtime.close()


@pytest.mark.asyncio
async def test_microagent_and_one_stdio_mcp_in_config(temp_dir, runtime_cls, run_as_Forge):
    runtime = None
    try:
        filesystem_config = MCPStdioServerConfig(
            name="filesystem", command="npx", args=["@modelcontextprotocol/server-filesystem@2025.8.18", "/"]
        )
        override_mcp_config = MCPConfig(stdio_servers=[filesystem_config])
        runtime, config = _load_runtime(
            temp_dir, runtime_cls, run_as_Forge, override_mcp_config=override_mcp_config, enable_browser=True
        )
        fetch_config = MCPStdioServerConfig(name="fetch", command="uvx", args=["mcp-server-fetch"])
        updated_config = runtime.get_mcp_config([fetch_config])
        logger.info("updated_config: %s", updated_config)
        mcp_action_sse = MCPAction(name="filesystem_list_directory", arguments={"path": "/"})
        obs_sse = await runtime.call_tool_mcp(mcp_action_sse)
        logger.info(obs_sse, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_sse, MCPObservation), "The observation should be a MCPObservation."
        assert "[FILE] .dockerenv" in obs_sse.content
        action_cmd_http = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
        logger.info(action_cmd_http, extra={"msg_type": "ACTION"})
        obs_http = runtime.run_action(action_cmd_http)
        logger.info(obs_http, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_http, CmdOutputObservation)
        assert obs_http.exit_code == 0
        assert "[1]" in obs_http.content
        action_cmd_cat = CmdRunAction(command="sleep 3 && cat server.log")
        logger.info(action_cmd_cat, extra={"msg_type": "ACTION"})
        obs_cat = runtime.run_action(action_cmd_cat)
        logger.info(obs_cat, extra={"msg_type": "OBSERVATION"})
        assert obs_cat.exit_code == 0
        mcp_action_fetch = MCPAction(name="fetch_fetch", arguments={"url": "http://localhost:8000"})
        obs_fetch = await runtime.call_tool_mcp(mcp_action_fetch)
        logger.info(obs_fetch, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs_fetch, MCPObservation), "The observation should be a MCPObservation."
        result_json = json.loads(obs_fetch.content)
        assert not result_json["isError"]
        assert len(result_json["content"]) == 1
        assert result_json["content"][0]["type"] == "text"
        assert (
            result_json["content"][0]["text"]
            == "Contents of http://localhost:8000/:\n---\n\n* <.downloads/>\n* <server.log>\n\n---"
        )
    finally:
        if runtime:
            runtime.close()
