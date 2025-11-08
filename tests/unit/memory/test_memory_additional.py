import asyncio
from types import SimpleNamespace

import pytest


class DummyEventStream:
    def __init__(self):
        self.subscriptions = []
        self.events = []

    def subscribe(self, subscriber, callback, sid):
        self.subscriptions.append((subscriber, sid))

    def add_event(self, event, source):
        self.events.append((event, source))


@pytest.fixture
def memory_instance(monkeypatch):
    from forge.memory.memory import Memory

    monkeypatch.setattr(
        "forge.memory.memory.load_microagents_from_dir",
        lambda path: ({}, {}),
    )

    stream = DummyEventStream()
    mem = Memory(stream, sid="test")
    return mem, stream


def test_workspace_context_recall(memory_instance):
    from forge.events.action.agent import RecallAction
    from forge.events.event import EventSource, RecallType

    mem, stream = memory_instance

    mem.repo_microagents["repo"] = SimpleNamespace(content="Repo instructions", metadata=SimpleNamespace(mcp_tools=None))
    mem.knowledge_microagents["agent"] = SimpleNamespace(
        name="agent",
        match_trigger=lambda query: "keyword" if "keyword" in query else None,
        content="Knowledge",
    )
    mem.set_repository_info("repo", "/repo", "main")
    mem.set_runtime_info(
        runtime=SimpleNamespace(runtime_initialized=True, web_hosts=["localhost"], additional_agent_instructions=None),
        custom_secrets_descriptions={"SECRET": "desc"},
        working_dir="/work",
    )
    mem.set_conversation_instructions("Be helpful")

    action = RecallAction(query="keyword", recall_type=RecallType.WORKSPACE_CONTEXT)
    action._source = EventSource.USER
    memory_observation = mem._on_workspace_context_recall(action)
    assert memory_observation is not None
    assert "Repo instructions" in memory_observation.repo_instructions


def test_microagent_recall(memory_instance):
    from forge.events.action.agent import RecallAction
    from forge.events.event import EventSource, RecallType

    mem, _ = memory_instance

    mem.knowledge_microagents["agent"] = SimpleNamespace(
        name="agent",
        match_trigger=lambda query: "trigger" if "important" in query else None,
        content="Knowledge base",
    )

    action = RecallAction(query="important topic", recall_type=RecallType.KNOWLEDGE)
    action._source = EventSource.AGENT
    obs = mem._on_microagent_recall(action)
    assert obs is not None
    assert obs.microagent_knowledge


def test_get_microagent_mcp_tools(memory_instance):
    mem, _ = memory_instance
    mock_config = SimpleNamespace()
    mem.repo_microagents["agent"] = SimpleNamespace(
        name="agent",
        metadata=SimpleNamespace(mcp_tools=mock_config),
    )
    tools = mem.get_microagent_mcp_tools()
    assert tools == [mock_config]


@pytest.mark.asyncio
async def test_set_runtime_status(memory_instance, monkeypatch):
    mem, _ = memory_instance
    received = {}
    event = asyncio.Event()

    def status_callback(msg_type, status, message):
        received["values"] = (msg_type, status, message)
        event.set()

    loop = asyncio.get_running_loop()
    mem.loop = loop
    mem.status_callback = status_callback
    monkeypatch.setattr("asyncio.get_running_loop", lambda: loop)

    mem.set_runtime_status(SimpleNamespace(name="ERROR"), "failure")
    await event.wait()
    assert received["values"][2] == "failure"

