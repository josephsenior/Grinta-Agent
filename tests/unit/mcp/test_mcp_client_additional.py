import importlib
import json
from types import SimpleNamespace

import pytest


def reload_cache(monkeypatch, env_value=None):
    module = importlib.import_module("forge.mcp_client.cache")
    if env_value is not None:
        monkeypatch.setenv("FORGE_MCP_CACHE_MAX_ENTRY_BYTES", env_value)
    else:
        monkeypatch.delenv("FORGE_MCP_CACHE_MAX_ENTRY_BYTES", raising=False)
    reloaded = importlib.reload(module)
    return reloaded


def test_cache_env_value_error(monkeypatch):
    cache_module = reload_cache(monkeypatch, env_value="not-an-int")
    assert cache_module.MAX_CACHE_ENTRY_BYTES == 5 * 1024 * 1024
    # restore default module state for other tests
    reload_cache(monkeypatch)


def test_cache_lifecycle(monkeypatch):
    cache = importlib.reload(importlib.import_module("forge.mcp_client.cache"))
    monkeypatch.setattr(cache, "_tool_cache", {})

    args = {"name": "component"}
    assert cache.get_cached("list_components", args) is None

    cache.set_cache("list_components", args, {"content": []})
    assert cache.get_cached("list_components", args) == {"content": []}

    # Respect refresh flag
    assert cache.get_cached("list_components", {"refresh": True}) is None

    # TTL expiry
    monkeypatch.setattr(cache.time, "time", lambda: 1000.0)
    cache.set_cache("list_components", args, {"content": [1]}, ttl=5)
    monkeypatch.setattr(cache.time, "time", lambda: 1006.0)
    assert cache.get_cached("list_components", args) is None

    # Clear cache
    cache.set_cache("list_components", args, {"content": []})
    removed = cache.clear_cache(prefix="list_components")
    assert removed == 1


def test_cache_size_guard(monkeypatch):
    cache = importlib.reload(importlib.import_module("forge.mcp_client.cache"))
    monkeypatch.setattr(cache, "_tool_cache", {})
    monkeypatch.setattr(cache, "MAX_CACHE_ENTRY_BYTES", 10)

    cache.set_cache("list_components", {"name": "x"}, {"content": ["A" * 20]})
    assert cache.get_cached("list_components", {"name": "x"}) is None


@pytest.mark.asyncio
async def test_wrapper_simple_passthrough(monkeypatch):
    from forge.mcp_client import wrappers

    async def fake_call(tool_name, args):
        return {"called": tool_name, "args": args}

    passthrough = wrappers._wrap_simple_passthrough("get_component")
    result = await passthrough([], {"foo": "bar"}, fake_call)
    assert result == {"called": "get_component", "args": {"foo": "bar"}}


@pytest.mark.asyncio
async def test_search_components_uses_cache(monkeypatch):
    from forge.mcp_client import wrappers

    monkeypatch.setattr("forge.mcp_client.wrappers.get_cached", lambda *args, **_: {"content": []})

    async def fake_call(tool_name, args):
        raise AssertionError("call_tool_func should not be invoked when cache hit happens")

    result = await wrappers.search_components([], {"query": "widget"}, fake_call)
    payload = json.loads(result["content"][0]["text"])
    assert payload == {"query": "widget", "results": [], "total_matches": 0}


@pytest.mark.asyncio
async def test_get_components_list_handles_invalid_json(monkeypatch):
    from forge.mcp_client import wrappers

    monkeypatch.setattr(
        "forge.mcp_client.wrappers.get_cached",
        lambda *_, **__: {"content": [{"type": "text", "text": "{not-json"}]},
    )

    async def fake_call(name, args):
        raise AssertionError("should not be called when cache is populated")

    result = await wrappers._get_components_list(fake_call)
    assert result == []


def test_score_and_filter_components_paths():
    from forge.mcp_client import wrappers

    components = ["Exact", 123, "partial-match", "miss"]

    fuzzy_results = wrappers._score_and_filter_components(components, "ex", fuzzy=True)
    assert [name for _, name in fuzzy_results] == ["Exact"]

    exact_results = wrappers._score_and_filter_components(components, "partial", fuzzy=False)
    assert [name for _, name in exact_results] == ["partial-match"]

    assert wrappers._score_and_filter_components(["zzzz"], "a", fuzzy=True) == []
    assert wrappers._score_and_filter_components(["alpha"], "beta", fuzzy=False) == []


@pytest.mark.asyncio
async def test_search_components_requires_query():
    from forge.mcp_client import wrappers

    async def unexpected_call(name, args):
        raise AssertionError("call_tool_func should not be invoked when query missing")

    response = await wrappers.search_components([], {}, unexpected_call)
    payload = json.loads(response["content"][0]["text"])
    assert payload == {"error": "query parameter required"}


def test_wrapper_tool_params_generation():
    from forge.mcp_client.wrappers import wrapper_tool_params

    params = wrapper_tool_params(["list_components", "get_component"])
    names = {param["function"]["name"] for param in params}
    assert names == {"search_components", "get_component_cached"}


@pytest.mark.asyncio
async def test_execute_wrapper_tool_error(monkeypatch):
    from forge.events.action.mcp import MCPAction
    from forge.mcp_client.utils import _execute_wrapper_tool
    from forge.mcp_client.wrappers import WRAPPER_TOOL_REGISTRY

    async def raising_wrapper(clients, args, call_tool):
        raise RuntimeError("boom")

    monkeypatch.setitem(WRAPPER_TOOL_REGISTRY, "explode", raising_wrapper)

    observation = await _execute_wrapper_tool(
        MCPAction(name="explode", arguments={"a": 1}),
        [],
    )
    content = json.loads(observation.content)
    assert content["isError"] is True


@pytest.mark.asyncio
async def test_execute_wrapper_tool_success(monkeypatch):
    from forge.events.action.mcp import MCPAction
    from forge.mcp_client.utils import _execute_wrapper_tool, WRAPPER_TOOL_REGISTRY

    async def sample_wrapper(clients, args, call_tool):
        record = await call_tool("underlying", {"value": 1})
        return {"wrapped": args, "record": record}

    dummy_tool = SimpleNamespace(name="underlying")
    async def underlying_call(name, args):
        return SimpleNamespace(model_dump=lambda mode="json": {"name": name, "args": args})

    dummy_client = SimpleNamespace(
        tools=[dummy_tool],
        call_tool=underlying_call,
    )
    monkeypatch.setitem(WRAPPER_TOOL_REGISTRY, "sample_wrapper", sample_wrapper)
    observation = await _execute_wrapper_tool(
        MCPAction(name="sample_wrapper", arguments={"foo": "bar"}),
        [dummy_client],
    )
    payload = json.loads(observation.content)
    assert payload["wrapped"] == {"foo": "bar"}
    assert payload["record"]["name"] == "underlying"


@pytest.mark.asyncio
async def test_execute_direct_tool_uses_cache(monkeypatch):
    from forge.events.action.mcp import MCPAction
    from forge.events.observation.mcp import MCPObservation
    from forge.mcp_client import utils as mcp_utils

    dummy_tool = SimpleNamespace(name="list_components")
    dummy_client = SimpleNamespace(tools=[dummy_tool])
    monkeypatch.setattr("forge.mcp_client.utils.get_cached", lambda *args, **kwargs: {"content": ["cached"]})
    monkeypatch.setattr("sys.platform", "linux")

    observation = await mcp_utils.call_tool_mcp([dummy_client], MCPAction(name="list_components", arguments={}))
    assert isinstance(observation, MCPObservation)
    assert json.loads(observation.content) == {"content": ["cached"]}


@pytest.mark.asyncio
async def test_execute_direct_tool_sets_cache(monkeypatch):
    from forge.events.action.mcp import MCPAction
    from forge.events.observation.mcp import MCPObservation
    from forge.mcp_client import utils as mcp_utils

    stored = {}

    async def fake_call(tool_name, arguments):
        return SimpleNamespace()

    dummy_tool = SimpleNamespace(name="foo")
    dummy_client = SimpleNamespace(
        tools=[dummy_tool],
        call_tool=fake_call,
    )

    monkeypatch.setattr("forge.mcp_client.utils.get_cached", lambda *args, **kwargs: None)

    def fake_set_cache(name, args, result):
        stored["result"] = result
        raise RuntimeError("fail after storing")

    monkeypatch.setattr("forge.mcp_client.utils.set_cache", fake_set_cache)
    monkeypatch.setattr("forge.mcp_client.utils.model_dump_with_options", lambda *args, **kwargs: {"result": "fresh"})
    monkeypatch.setattr("sys.platform", "linux")

    observation = await mcp_utils.call_tool_mcp([dummy_client], MCPAction(name="foo", arguments={"a": 1}))
    assert isinstance(observation, MCPObservation)
    assert stored["result"] == {"result": "fresh"}


@pytest.mark.asyncio
async def test_call_tool_mcp_windows_branch(monkeypatch):
    from forge.events.action.mcp import MCPAction
    from forge.mcp_client.utils import call_tool_mcp
    from forge.events.observation import ErrorObservation

    with monkeypatch.context() as m:
        m.setattr("sys.platform", "win32")
        result = await call_tool_mcp([], MCPAction(name="anything", arguments={}))
    assert isinstance(result, ErrorObservation)


def test_serialize_result_to_json_fallback():
    from forge.mcp_client.utils import _serialize_result_to_json

    class BadRepr:
        def __str__(self):
            raise RuntimeError("no str")

        def __repr__(self):
            raise RuntimeError("no repr")

    class BadDict(dict):
        def __iter__(self):
            raise TypeError("no iterate")

    result = _serialize_result_to_json({"key": BadDict(), "other": BadRepr()})
    assert result == '{"error":"unserializable_result"}'


def test_build_http_headers_and_transport(monkeypatch):
    from forge.core.config.mcp_config import MCPSHTTPServerConfig, MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient

    client = MCPClient()
    headers = client._build_http_headers("abc", "cid")
    assert headers["Authorization"] == "Bearer abc"
    assert headers["X-Forge-ServerConversation-ID"] == "cid"

    http_server = MCPSHTTPServerConfig(url="https://example.com", api_key="abc")
    sse_server = MCPSSEServerConfig(url="https://example.com")

    transport_http = client._create_http_transport(http_server, http_server.url, headers)
    transport_sse = client._create_http_transport(sse_server, sse_server.url, headers)
    from fastmcp.client.transports import StreamableHttpTransport, SSETransport

    assert isinstance(transport_http, StreamableHttpTransport)
    assert isinstance(transport_sse, SSETransport)


@pytest.mark.asyncio
async def test_mcp_client_call_tool_errors(monkeypatch):
    from forge.mcp_client.client import MCPClient

    client = MCPClient()
    with pytest.raises(ValueError):
        await client.call_tool("missing", {})

    client.tool_map["tool"] = SimpleNamespace()
    with pytest.raises(RuntimeError):
        await client.call_tool("tool", {})


def test_mcp_client_handle_connection_error(monkeypatch):
    from forge.core.config.mcp_config import MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient
    from forge.mcp_client.error_collector import mcp_error_collector

    client = MCPClient()
    server = MCPSSEServerConfig(url="https://server")
    mcp_error_collector.clear_errors()
    client._handle_connection_error("https://server", server, ValueError("bad"), is_mcp_error=False)
    errors = mcp_error_collector.get_errors()
    assert errors and errors[0].server_type == "sse"


@pytest.mark.asyncio
async def test_mcp_client_connect_http_success(monkeypatch):
    from forge.core.config.mcp_config import MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.list_tools_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def list_tools(self):
            self.list_tools_calls += 1
            return [
                SimpleNamespace(name="one", description="d", inputSchema={"type": "object"}),
            ]

    monkeypatch.setattr("forge.mcp_client.client.Client", lambda *args, **kwargs: DummyClient())

    client = MCPClient()
    await client.connect_http(MCPSSEServerConfig(url="https://server"))
    assert client.tools[0].name == "one"


@pytest.mark.asyncio
async def test_mcp_client_connect_http_error(monkeypatch):
    from forge.core.config.mcp_config import MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient

    class FailingClient:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("forge.mcp_client.client.Client", lambda *args, **kwargs: FailingClient())
    client = MCPClient()
    with pytest.raises(RuntimeError):
        await client.connect_http(MCPSSEServerConfig(url="https://server"))


@pytest.mark.asyncio
async def test_mcp_client_connect_stdio_failure(monkeypatch):
    from forge.core.config.mcp_config import MCPStdioServerConfig
    from forge.mcp_client.client import MCPClient

    class FailingClient:
        async def __aenter__(self):
            raise RuntimeError("stdio boom")

        async def __aexit__(self, *exc):
            return False

        async def list_tools(self):
            return []

    monkeypatch.setattr("forge.mcp_client.client.Client", lambda *args, **kwargs: FailingClient())
    monkeypatch.setattr("forge.mcp_client.client.StdioTransport", lambda *args, **kwargs: SimpleNamespace())

    client = MCPClient()

    with pytest.raises(RuntimeError):
        await client.connect_stdio(MCPStdioServerConfig(name="stdio", command="missing"))


@pytest.mark.asyncio
async def test_call_mcp_raw(monkeypatch):
    from forge.mcp_client.utils import _call_mcp_raw

    dummy_tool = SimpleNamespace(name="foo")

    async def fake_call(tool_name, arguments):
        return SimpleNamespace(model_dump=lambda mode="json": {"value": 1})

    client = SimpleNamespace(
        tools=[dummy_tool],
        call_tool=fake_call,
    )

    monkeypatch.setattr("forge.mcp_client.utils.get_cached", lambda *args, **kwargs: None)
    monkeypatch.setattr("forge.mcp_client.utils.set_cache", lambda *args, **kwargs: None)

    action = SimpleNamespace(name="foo", arguments={})
    result = await _call_mcp_raw([client], action)
    assert result == {"value": 1}

    with pytest.raises(ValueError):
        await _call_mcp_raw([], action)


@pytest.mark.asyncio
async def test_fetch_mcp_tools_error(monkeypatch):
    from forge.core.config.mcp_config import MCPConfig
    from forge.mcp_client.utils import fetch_mcp_tools_from_config

    monkeypatch.setattr("sys.platform", "linux")

    async def failing_create(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr("forge.mcp_client.utils.create_mcp_clients", failing_create)

    tools = await fetch_mcp_tools_from_config(MCPConfig())
    assert tools == []


@pytest.mark.asyncio
async def test_add_mcp_tools_to_agent(monkeypatch):
    from forge.mcp_client.utils import add_mcp_tools_to_agent

    class DummyAgent:
        def __init__(self):
            self.tools = None

        def set_mcp_tools(self, tools):
            self.tools = tools

    class DummyRuntime:
        runtime_initialized = True

        def get_mcp_config(self, extra_stdio):
            from forge.core.config.mcp_config import MCPConfig

            return MCPConfig()

    class DummyMemory:
        def get_microagent_mcp_tools(self):
            return []

    monkeypatch.setattr("sys.platform", "linux")
    async def fake_fetch(*args, **kwargs):
        return [{"function": {"name": "tool"}}]

    monkeypatch.setattr("forge.mcp_client.utils.fetch_mcp_tools_from_config", fake_fetch)

    agent = DummyAgent()
    runtime = DummyRuntime()
    memory = DummyMemory()

    config = await add_mcp_tools_to_agent(agent, runtime, memory)
    assert agent.tools == [{"function": {"name": "tool"}}]
    assert config is not None


def test_wrapper_tool_params_includes_cache_variants():
    from forge.mcp_client.wrappers import wrapper_tool_params

    params = wrapper_tool_params(["get_block", "get_component"])
    names = [p["function"]["name"] for p in params]
    assert {"get_block_cached", "get_component_cached"} <= set(names)


def test_wrappers_fuzzy_score_variations():
    from forge.mcp_client.wrappers import _fuzzy_score

    assert _fuzzy_score("abc", "abc") == 1.0
    assert _fuzzy_score("abc", "abcd") > 0.6
    assert _fuzzy_score("abc", "a_b_c") > 0.0


@pytest.mark.asyncio
async def test_get_components_list_fetches_when_uncached(monkeypatch):
    from forge.mcp_client.wrappers import _get_components_list

    monkeypatch.setattr("forge.mcp_client.wrappers.get_cached", lambda *args, **kwargs: None)

    async def fake_call(tool_name, args):
        return {"content": [{"type": "text", "text": json.dumps(["alpha", "beta"])}]}

    components = await _get_components_list(fake_call)
    assert components == ["alpha", "beta"]


def test_convert_mcp_clients_to_tools_error(monkeypatch):
    from forge.mcp_client.utils import convert_mcp_clients_to_tools

    class BadTool:
        def to_param(self):
            raise RuntimeError("fail")

    mock_client = SimpleNamespace(tools=[BadTool()])
    tools = convert_mcp_clients_to_tools([mock_client])
    assert tools == []


def test_cache_skips_error_responses(monkeypatch):
    cache = importlib.reload(importlib.import_module("forge.mcp_client.cache"))
    monkeypatch.setattr(cache, "_tool_cache", {})

    cache.set_cache("list_components", {}, {"isError": True})
    assert cache._tool_cache == {}
    cache.set_cache("list_components", {}, {"content": {"isError": True}})
    assert cache._tool_cache == {}


def test_cache_clear_all(monkeypatch):
    cache = importlib.reload(importlib.import_module("forge.mcp_client.cache"))
    monkeypatch.setattr(cache, "_tool_cache", {})
    cache.set_cache("list_components", {}, {"result": 1})
    removed = cache.clear_cache()
    assert removed == 1


def test_mcp_client_tool_to_param():
    from forge.mcp_client.tool import MCPClientTool

    tool = MCPClientTool(name="demo", description="desc", inputSchema={"type": "object"})
    params = tool.to_param()
    assert params["function"]["name"] == "demo"


@pytest.mark.asyncio
async def test_mcp_client_initialize_without_session():
    from forge.mcp_client.client import MCPClient

    client = MCPClient()
    with pytest.raises(RuntimeError):
        await client._initialize_and_list_tools()


@pytest.mark.asyncio
async def test_mcp_client_connect_http_missing_url():
    from forge.core.config.mcp_config import MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient

    client = MCPClient()
    with pytest.raises(ValueError):
        await client.connect_http(MCPSSEServerConfig(url=""))


@pytest.mark.asyncio
async def test_mcp_client_connect_http_mcp_error(monkeypatch):
    from forge.core.config.mcp_config import MCPSSEServerConfig
    from forge.mcp_client.client import MCPClient
    from mcp import McpError

    class ErrorClient:
        async def __aenter__(self):
            raise McpError(SimpleNamespace(message="boom"))

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("forge.mcp_client.client.Client", lambda *args, **kwargs: ErrorClient())

    client = MCPClient()
    with pytest.raises(McpError):
        await client.connect_http(MCPSSEServerConfig(url="https://server"))


@pytest.mark.asyncio
async def test_mcp_client_call_tool_success_path(monkeypatch):
    from forge.mcp_client.client import MCPClient

    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def list_tools(self):
            return [SimpleNamespace(name="tool", description="d", inputSchema={"type": "object"})]

        async def call_tool_mcp(self, name, arguments):
            return {"result": arguments}

    monkeypatch.setattr("forge.mcp_client.client.Client", lambda *args, **kwargs: DummySession())

    client = MCPClient()
    await client.connect_http(SimpleNamespace(url="https://server", api_key=None))
    result = await client.call_tool("tool", {"value": 1})
    assert result == {"result": {"value": 1}}

