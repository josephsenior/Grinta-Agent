import pytest


@pytest.mark.asyncio
async def test_legacy_create_mcp_clients_proxy(monkeypatch):
    async def fake_create(*args, **kwargs):
        fake_create.called = True
        fake_create.args = args
        fake_create.kwargs = kwargs
        return ["ok"]

    fake_create.called = False
    monkeypatch.setattr("forge.mcp_client.utils.create_mcp_clients", fake_create)

    from forge.mcp import utils as legacy_utils

    result = await legacy_utils.create_mcp_clients(1, two=2)
    assert result == ["ok"]
    assert fake_create.called
    assert fake_create.args == (1,)
    assert fake_create.kwargs == {"two": 2}


@pytest.mark.asyncio
async def test_legacy_call_tool_mcp_proxy(monkeypatch):
    async def fake_call(*args, **kwargs):
        fake_call.called = True
        fake_call.args = args
        fake_call.kwargs = kwargs
        return "result"

    fake_call.called = False
    monkeypatch.setattr("forge.mcp_client.utils.call_tool_mcp", fake_call)

    from forge.mcp import utils as legacy_utils

    observation = await legacy_utils.call_tool_mcp("clients", action="action")
    assert observation == "result"
    assert fake_call.called
    assert fake_call.args == ("clients",)
    assert fake_call.kwargs == {"action": "action"}

