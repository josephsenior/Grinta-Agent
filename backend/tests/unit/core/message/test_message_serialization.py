import importlib
import sys
from types import SimpleNamespace
from typing import ClassVar

import pytest
from forge.core.message import Content, ImageContent, Message, TextContent, ToolCall


def test_content_serialize_not_implemented():
    base_content = Content(type="custom")
    with pytest.raises(NotImplementedError):
        base_content.serialize_model()


def test_text_content_cache_prompt_adds_cache_control():
    content = TextContent(text="hello", cache_prompt=True)
    serialized = content.serialize_model()
    assert serialized["cache_control"]["type"] == "ephemeral"


def test_image_content_cache_prompt_marks_last_image():
    content = ImageContent(
        image_urls=["http://example.com/a.png", "http://example.com/b.png"],
        cache_prompt=True,
    )
    serialized = content.serialize_model()
    assert "cache_control" not in serialized[0]
    assert serialized[-1]["cache_control"]["type"] == "ephemeral"


def test_tool_message_cache_handling_with_text_and_image(monkeypatch):
    tool_call = ToolCall(
        id="call", type="function", function={"name": "fn", "arguments": "{}"}
    )
    message = Message(
        role="tool",
        content=[
            TextContent(text="result", cache_prompt=True),
            ImageContent(image_urls=["http://img"], cache_prompt=True),
        ],
        cache_enabled=True,
        vision_enabled=True,
        tool_calls=[tool_call],
    )
    serialized = message.serialize_model()
    assert serialized["cache_control"]["type"] == "ephemeral"
    first_item, second_item = serialized["content"]
    assert "cache_control" not in first_item
    assert "cache_control" not in second_item


def test_message_subclass_triggers_model_rebuild():
    class TrackingMessage(Message):
        rebuild_called: ClassVar[bool] = False

        @classmethod
        def model_rebuild(cls, *args, **kwargs):
            cls.rebuild_called = True
            return super().model_rebuild(*args, **kwargs)

    TrackingMessage(content=[TextContent(text="data")], role="user")
    assert TrackingMessage.rebuild_called is True


def test_message_with_vision_enabled():
    text_content1 = TextContent(text="This is a text message")
    image_content1 = ImageContent(
        image_urls=["http://example.com/image1.png", "http://example.com/image2.png"]
    )
    text_content2 = TextContent(text="This is another text message")
    image_content2 = ImageContent(
        image_urls=["http://example.com/image3.png", "http://example.com/image4.png"]
    )
    message: Message = Message(
        role="user",
        content=[text_content1, image_content1, text_content2, image_content2],
        vision_enabled=True,
    )
    serialized_message: dict = message.serialize_model()
    expected_serialized_message = {
        "role": "user",
        "content": [
            {"type": "text", "text": "This is a text message"},
            {
                "type": "image_url",
                "image_url": {"url": "http://example.com/image1.png"},
            },
            {
                "type": "image_url",
                "image_url": {"url": "http://example.com/image2.png"},
            },
            {"type": "text", "text": "This is another text message"},
            {
                "type": "image_url",
                "image_url": {"url": "http://example.com/image3.png"},
            },
            {
                "type": "image_url",
                "image_url": {"url": "http://example.com/image4.png"},
            },
        ],
    }
    assert serialized_message == expected_serialized_message
    assert message.contains_image is True


def test_message_with_only_text_content_and_vision_enabled():
    text_content1 = TextContent(text="This is a text message")
    text_content2 = TextContent(text="This is another text message")
    message: Message = Message(
        role="user", content=[text_content1, text_content2], vision_enabled=True
    )
    serialized_message: dict = message.serialize_model()
    expected_serialized_message = {
        "role": "user",
        "content": [
            {"type": "text", "text": "This is a text message"},
            {"type": "text", "text": "This is another text message"},
        ],
    }
    assert serialized_message == expected_serialized_message
    assert message.contains_image is False


def test_message_with_only_text_content_and_vision_disabled():
    text_content1 = TextContent(text="This is a text message")
    text_content2 = TextContent(text="This is another text message")
    message: Message = Message(
        role="user", content=[text_content1, text_content2], vision_enabled=False
    )
    serialized_message: dict = message.serialize_model()
    expected_serialized_message = {
        "role": "user",
        "content": "This is a text message\nThis is another text message",
    }
    assert serialized_message == expected_serialized_message
    assert message.contains_image is False


def test_message_with_mixed_content_and_vision_disabled():
    text_content1 = TextContent(text="This is a text message")
    image_content1 = ImageContent(
        image_urls=["http://example.com/image1.png", "http://example.com/image2.png"]
    )
    text_content2 = TextContent(text="This is another text message")
    image_content2 = ImageContent(
        image_urls=["http://example.com/image3.png", "http://example.com/image4.png"]
    )
    message: Message = Message(
        role="user",
        content=[text_content1, image_content1, text_content2, image_content2],
        vision_enabled=False,
    )
    serialized_message: dict = message.serialize_model()
    expected_serialized_message = {
        "role": "user",
        "content": "This is a text message\nThis is another text message",
    }
    assert serialized_message == expected_serialized_message
    assert message.contains_image


def test_message_tool_call_serialization():
    """Test that tool calls are properly serialized into dicts for token counting."""
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function={"name": "test_function", "arguments": '{"arg1": "value1"}'},
    )
    message = Message(
        role="assistant",
        content=[TextContent(text="Test message")],
        tool_calls=[tool_call],
    )
    serialized = message.model_dump()
    assert "tool_calls" in serialized
    assert isinstance(serialized["tool_calls"], list)
    assert len(serialized["tool_calls"]) == 1
    tool_call_dict = serialized["tool_calls"][0]
    assert isinstance(tool_call_dict, dict)
    assert tool_call_dict["id"] == "call_123"
    assert tool_call_dict["type"] == "function"
    assert tool_call_dict["function"]["name"] == "test_function"
    assert tool_call_dict["function"]["arguments"] == '{"arg1": "value1"}'


def test_message_tool_response_serialization():
    """Test that tool responses are properly serialized."""
    message = Message(
        role="tool",
        content=[TextContent(text="Function result")],
        tool_call_id="call_123",
        name="test_function",
    )
    serialized = message.model_dump()
    assert "tool_call_id" in serialized
    assert serialized["tool_call_id"] == "call_123"
    assert "name" in serialized
    assert serialized["name"] == "test_function"
