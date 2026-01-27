from typing import List, cast

import pytest
from forge.llm.direct_clients import LLMResponse
from pydantic import SecretStr

from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent
from forge.core.config import AgentConfig, LLMConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.message import TextContent
from forge.events.action import MessageAction, SystemMessageAction
from forge.events.event import Event
from forge.llm.llm_registry import LLMRegistry


@pytest.fixture
def llm_config():
    return LLMConfig(
        model="claude-3-5-sonnet-20241022",
        api_key=SecretStr("fake"),
        caching_prompt=True,
    )


@pytest.fixture
def llm_registry():
    return LLMRegistry(config=ForgeConfig())


@pytest.fixture
def codeact_agent(llm_registry):
    config = AgentConfig()
    return CodeActAgent(config, llm_registry)


def response_mock(content: str, tool_call_id: str):
    return LLMResponse(
        content=content,
        model="claude-3-5-sonnet-20241022",
        usage={"prompt_tokens": 100, "completion_tokens": 50},
        tool_calls=[
            {
                "function": {
                    "id": tool_call_id,
                    "name": "execute_bash",
                    "arguments": "{}",
                }
            }
        ],
    )


def test_get_messages(codeact_agent: CodeActAgent):
    system_message_action = codeact_agent.get_system_message()
    assert system_message_action is not None
    history: list[MessageAction | SystemMessageAction] = [system_message_action]
    message_action_1 = MessageAction("Initial user message")
    message_action_1._source = "user"
    history.append(message_action_1)
    message_action_2 = MessageAction("Sure!")
    message_action_2._source = "agent"
    history.append(message_action_2)
    message_action_3 = MessageAction("Hello, agent!")
    message_action_3._source = "user"
    history.append(message_action_3)
    message_action_4 = MessageAction("Hello, user!")
    message_action_4._source = "agent"
    history.append(message_action_4)
    message_action_5 = MessageAction("Laaaaaaaast!")
    message_action_5._source = "user"
    history.append(message_action_5)
    codeact_agent.reset()
    messages = codeact_agent._get_messages(cast(list[Event], history), message_action_1)
    assert len(messages) == 6
    assert messages[0].role == "system"
    assert messages[0].content[0].cache_prompt
    assert messages[1].role == "user"
    first_user_content = messages[1].content[0]
    assert isinstance(first_user_content, TextContent)
    assert first_user_content.text.endswith("Initial user message")
    assert not first_user_content.cache_prompt
    assert messages[3].role == "user"
    third_user_content = messages[3].content[0]
    assert isinstance(third_user_content, TextContent)
    assert third_user_content.text == "Hello, agent!"
    assert not third_user_content.cache_prompt
    assert messages[4].role == "assistant"
    assistant_content = messages[4].content[0]
    assert isinstance(assistant_content, TextContent)
    assert assistant_content.text == "Hello, user!"
    assert not assistant_content.cache_prompt
    assert messages[5].role == "user"
    final_user_content = messages[5].content[0]
    assert isinstance(final_user_content, TextContent)
    assert final_user_content.text.startswith("Laaaaaaaast!")
    assert final_user_content.cache_prompt


def test_get_messages_prompt_caching(codeact_agent: CodeActAgent):
    system_message_action = codeact_agent.get_system_message()
    assert system_message_action is not None
    history: list[MessageAction | SystemMessageAction] = [system_message_action]
    initial_user_message: MessageAction | None = None
    for i in range(15):
        message_action_user = MessageAction(f"User message {i}")
        message_action_user._source = "user"
        if initial_user_message is None:
            initial_user_message = message_action_user
        history.append(message_action_user)
        message_action_agent = MessageAction(f"Agent message {i}")
        message_action_agent._source = "agent"
        history.append(message_action_agent)
    codeact_agent.reset()
    assert initial_user_message is not None
    messages = codeact_agent._get_messages(
        cast(list[Event], history), initial_user_message
    )
    cached_user_messages = [
        msg
        for msg in messages
        if msg.role in ("user", "system")
        and isinstance(msg.content[0], TextContent)
        and msg.content[0].cache_prompt
    ]
    assert len(cached_user_messages) == 2
    assert cast(TextContent, cached_user_messages[0].content[0]).text.startswith(
        "You are Forge agent"
    )
    assert cast(TextContent, cached_user_messages[1].content[0]).text.startswith(
        "User message 14"
    )
