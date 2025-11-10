import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from forge.mcp_client import utils as mcp_utils
from forge.core.config.mcp_config import MCPSSEServerConfig, MCPStdioServerConfig
from forge.events.action.mcp import MCPAction
from forge.events.observation.mcp import MCPObservation


@pytest.mark.asyncio
async def test_create_mcp_clients_empty():
    """Test creating MCP clients with empty server list."""
    with patch("sys.platform", "linux"):
        clients = await mcp_utils.create_mcp_clients([], [])
    assert clients == []


@pytest.mark.asyncio
@patch("forge.mcp_client.utils.MCPClient")
async def test_create_mcp_clients_success(mock_mcp_client):
    """Test successful creation of MCP clients."""
    mock_client_instance = AsyncMock()
    mock_mcp_client.return_value = mock_client_instance
    mock_client_instance.connect_http = AsyncMock()
    server_configs = [
        MCPSSEServerConfig(url="http://server1:8080"),
        MCPSSEServerConfig(url="http://server2:8080", api_key="test-key"),
    ]
    with patch("sys.platform", "linux"):
        clients = await mcp_utils.create_mcp_clients(server_configs, [])
    assert len(clients) == 2
    assert mock_mcp_client.call_count == 2
    mock_client_instance.connect_http.assert_any_call(server_configs[0], conversation_id=None)
    mock_client_instance.connect_http.assert_any_call(server_configs[1], conversation_id=None)


@pytest.mark.asyncio
@patch("forge.mcp_client.utils.MCPClient")
async def test_create_mcp_clients_connection_failure(mock_mcp_client):
    """Test handling of connection failures when creating MCP clients."""
    mock_client_instance = AsyncMock()
    mock_mcp_client.return_value = mock_client_instance
    mock_client_instance.connect_http.side_effect = [None, Exception("Connection failed")]
    server_configs = [MCPSSEServerConfig(url="http://server1:8080"), MCPSSEServerConfig(url="http://server2:8080")]
    with patch("sys.platform", "linux"):
        clients = await mcp_utils.create_mcp_clients(server_configs, [])
    assert len(clients) == 1


def test_convert_mcp_clients_to_tools_empty():
    """Test converting empty MCP clients list to tools."""
    tools = mcp_utils.convert_mcp_clients_to_tools(None)
    assert tools == []
    tools = mcp_utils.convert_mcp_clients_to_tools([])
    assert tools == []


def test_convert_mcp_clients_to_tools():
    """Test converting MCP clients to tools."""
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()
    mock_tool1 = MagicMock()
    mock_tool1.to_param.return_value = {"function": {"name": "tool1"}}
    mock_tool2 = MagicMock()
    mock_tool2.to_param.return_value = {"function": {"name": "tool2"}}
    mock_tool3 = MagicMock()
    mock_tool3.to_param.return_value = {"function": {"name": "tool3"}}
    mock_client1.tools = [mock_tool1, mock_tool2]
    mock_client2.tools = [mock_tool3]
    tools = mcp_utils.convert_mcp_clients_to_tools([mock_client1, mock_client2])
    assert len(tools) == 3
    assert tools[0] == {"function": {"name": "tool1"}}
    assert tools[1] == {"function": {"name": "tool2"}}
    assert tools[2] == {"function": {"name": "tool3"}}


@pytest.mark.asyncio
async def test_call_tool_mcp_no_clients():
    """Test calling MCP tool with no clients."""
    action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
    with patch("sys.platform", "linux"):
        with pytest.raises(ValueError, match="No MCP clients found"):
            await mcp_utils.call_tool_mcp([], action)


@pytest.mark.asyncio
async def test_call_tool_mcp_no_matching_client():
    """Test calling MCP tool with no matching client."""
    mock_client = MagicMock()
    mock_client.tools = [MagicMock(name="other_tool")]
    action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
    with patch("sys.platform", "linux"):
        with pytest.raises(ValueError, match="No matching MCP agent found for tool name"):
            await mcp_utils.call_tool_mcp([mock_client], action)


@pytest.mark.asyncio
async def test_call_tool_mcp_success():
    """Test successful MCP tool call."""
    mock_client = MagicMock()
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_client.tools = [mock_tool]
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {"result": "success"}
    mock_client.call_tool = AsyncMock(return_value=mock_response)
    action = MCPAction(name="test_tool", arguments={"arg1": "value1"})
    with patch("sys.platform", "linux"):
        observation = await mcp_utils.call_tool_mcp([mock_client], action)
    assert isinstance(observation, MCPObservation)
    assert json.loads(observation.content) == {"result": "success"}
    mock_client.call_tool.assert_called_once_with("test_tool", {"arg1": "value1"})


@pytest.mark.asyncio
@patch("forge.mcp_client.utils.MCPClient")
async def test_create_mcp_clients_stdio_success(mock_mcp_client):
    """Test successful creation of MCP clients with stdio servers."""
    mock_client_instance = AsyncMock()
    mock_mcp_client.return_value = mock_client_instance
    mock_client_instance.connect_stdio = AsyncMock()
    stdio_server_configs = [
        MCPStdioServerConfig(name="test-server-1", command="python", args=["-m", "server1"], env={"DEBUG": "true"}),
        MCPStdioServerConfig(
            name="test-server-2", command="node", args=["server2.js"], env={"NODE_ENV": "development"}
        ),
    ]
    with patch("sys.platform", "linux"):
        with patch("forge.mcp_client.utils.shutil.which", return_value="C:\\Python\\python.exe"):
            clients = await mcp_utils.create_mcp_clients([], [], stdio_servers=stdio_server_configs)
    assert len(clients) == 2
    assert mock_mcp_client.call_count == 2
    mock_client_instance.connect_stdio.assert_any_call(stdio_server_configs[0])
    mock_client_instance.connect_stdio.assert_any_call(stdio_server_configs[1])


@pytest.mark.asyncio
@patch("forge.mcp_client.utils.MCPClient")
async def test_create_mcp_clients_stdio_connection_failure(mock_mcp_client):
    """Test handling of stdio connection failures when creating MCP clients."""
    mock_client_instance = AsyncMock()
    mock_mcp_client.return_value = mock_client_instance
    mock_client_instance.connect_stdio.side_effect = [None, Exception("Stdio connection failed")]
    stdio_server_configs = [
        MCPStdioServerConfig(name="server1", command="python"),
        MCPStdioServerConfig(name="server2", command="node"),
    ]
    with patch("sys.platform", "linux"):
        with patch(
            "forge.mcp_client.utils.shutil.which",
            side_effect=lambda cmd: "C:\\Path\\to\\exec.exe",
        ):
            clients = await mcp_utils.create_mcp_clients([], [], stdio_servers=stdio_server_configs)
    assert len(clients) == 1


@pytest.mark.asyncio
@patch("forge.mcp_client.utils.create_mcp_clients")
async def test_fetch_mcp_tools_from_config_with_stdio(mock_create_clients):
    """Test fetching MCP tools with stdio servers enabled."""
    from forge.core.config.mcp_config import MCPConfig

    mock_client = MagicMock()
    mock_tool = MagicMock()
    mock_tool.to_param.return_value = {"function": {"name": "stdio_tool"}}
    mock_client.tools = [mock_tool]
    mock_create_clients.return_value = [mock_client]
    mcp_config = MCPConfig(stdio_servers=[MCPStdioServerConfig(name="test-server", command="python")])
    with patch("sys.platform", "linux"):
        tools = await mcp_utils.fetch_mcp_tools_from_config(
            mcp_config, conversation_id="test-conv", use_stdio=True
        )
    assert len(tools) == 1
    assert tools[0] == {"function": {"name": "stdio_tool"}}
    mock_create_clients.assert_called_once_with([], [], "test-conv", mcp_config.stdio_servers)


@pytest.mark.asyncio
async def test_call_tool_mcp_stdio_client():
    """Test calling MCP tool on a stdio client."""
    mock_client = MagicMock()
    mock_tool = MagicMock()
    mock_tool.name = "stdio_test_tool"
    mock_client.tools = [mock_tool]
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {"result": "stdio_success", "data": "test_data"}
    mock_client.call_tool = AsyncMock(return_value=mock_response)
    action = MCPAction(name="stdio_test_tool", arguments={"input": "test_input"})
    with patch("sys.platform", "linux"):
        observation = await mcp_utils.call_tool_mcp([mock_client], action)
    assert isinstance(observation, MCPObservation)
    assert json.loads(observation.content) == {"result": "stdio_success", "data": "test_data"}
    mock_client.call_tool.assert_called_once_with("stdio_test_tool", {"input": "test_input"})


@pytest.mark.asyncio
async def test_fetch_mcp_tools_windows_disabled(monkeypatch):
    """Ensure Windows guard short-circuits tool fetching."""
    from forge.core.config.mcp_config import MCPConfig

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    with patch("sys.platform", "win32"):
        tools = await mcp_utils.fetch_mcp_tools_from_config(MCPConfig())
    assert tools == []


@pytest.mark.asyncio
async def test_fetch_mcp_tools_returns_empty_when_no_clients(monkeypatch):
    """fetch_mcp_tools_from_config returns empty list when connections fail."""
    from forge.core.config.mcp_config import MCPConfig

    async def fake_create(*args, **kwargs):
        return []

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    monkeypatch.setattr(mcp_utils, "create_mcp_clients", fake_create)
    with patch("sys.platform", "linux"):
        tools = await mcp_utils.fetch_mcp_tools_from_config(MCPConfig())
    assert tools == []


@pytest.mark.asyncio
async def test_fetch_mcp_tools_error_path(monkeypatch):
    """Errors during fetch are captured and reported."""
    from forge.core.config.mcp_config import MCPConfig

    async def raising_create(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    monkeypatch.setattr(mcp_utils, "create_mcp_clients", raising_create)
    with patch("sys.platform", "linux"):
        tools = await mcp_utils.fetch_mcp_tools_from_config(MCPConfig())
    assert tools == []


def test_serialize_result_to_json_repr_fallback():
    """_serialize_result_to_json falls back to repr when json encoding fails."""
    result = mcp_utils._serialize_result_to_json({"value": object()})
    assert "object at" in result


def test_serialize_result_to_json_final_fallback():
    """_serialize_result_to_json returns sentinel when repr also fails."""

    class BadRepr:
        def __repr__(self):
            raise RuntimeError("no repr")

    payload = {"value": BadRepr()}
    text = mcp_utils._serialize_result_to_json(payload)
    assert text == '{"error":"unserializable_result"}'


@pytest.mark.asyncio
async def test_call_tool_mcp_windows_disabled(monkeypatch):
    """call_tool_mcp returns ErrorObservation on Windows when disabled."""
    from forge.events.action.mcp import MCPAction
    from forge.events.observation import ErrorObservation

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    with patch("sys.platform", "win32"):
        observation = await mcp_utils.call_tool_mcp([MagicMock()], MCPAction(name="tool", arguments={}))
    assert isinstance(observation, ErrorObservation)


@pytest.mark.asyncio
async def test_add_mcp_tools_windows_disabled(monkeypatch):
    """add_mcp_tools_to_agent clears tools when Windows guard is active."""
    agent = MagicMock()
    runtime = MagicMock()
    runtime.runtime_initialized = True
    memory = MagicMock()
    memory.get_microagent_mcp_tools.return_value = []

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    with patch("sys.platform", "win32"):
        result = await mcp_utils.add_mcp_tools_to_agent(agent, runtime, memory)

    agent.set_mcp_tools.assert_called_once_with([])
    assert result is None


@pytest.mark.asyncio
async def test_add_mcp_tools_merges_stdio(monkeypatch):
    """add_mcp_tools_to_agent merges microagent stdio servers and sets tools."""
    extra_server = MCPStdioServerConfig(name="extra", command="python")
    duplicate_server = MCPStdioServerConfig(name="extra", command="python")

    class FakeRuntime:
        runtime_initialized = True

        def __init__(self):
            self.received_stdio = None

        def get_mcp_config(self, extra_stdio):
            self.received_stdio = list(extra_stdio)
            return SimpleNamespace(
                sse_servers=[], shttp_servers=[], stdio_servers=list(extra_stdio)
            )

    async def fake_fetch(config, conversation_id=None, use_stdio=False):
        assert use_stdio is True
        return [{"function": {"name": "stdio_tool"}}]

    agent = MagicMock()
    memory = MagicMock()
    memory.get_microagent_mcp_tools.return_value = [
        SimpleNamespace(sse_servers=[], stdio_servers=[extra_server]),
        SimpleNamespace(sse_servers=[], stdio_servers=[duplicate_server]),
    ]

    monkeypatch.delenv("FORGE_ENABLE_WINDOWS_MCP", raising=False)
    monkeypatch.setattr(mcp_utils, "fetch_mcp_tools_from_config", fake_fetch)
    monkeypatch.setattr(mcp_utils, "CLIRuntime", FakeRuntime)

    with patch("sys.platform", "linux"):
        runtime = FakeRuntime()
        result = await mcp_utils.add_mcp_tools_to_agent(agent, runtime, memory)

    assert runtime.received_stdio == [extra_server]
    agent.set_mcp_tools.assert_called_once_with([{"function": {"name": "stdio_tool"}}])
    assert result.stdio_servers == [extra_server]
