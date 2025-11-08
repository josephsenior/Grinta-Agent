"""Test for fixing empty image URL issue in multimodal browsing."""

from forge.core.config.agent_config import AgentConfig
from forge.core.message import ImageContent
from forge.events.observation.browse import BrowserOutputObservation
from forge.memory.conversation_memory import ConversationMemory
from forge.utils.prompt import PromptManager


def test_empty_image_url_handling():
    """Test that empty image URLs are properly filtered out and notification text is added."""
    browser_obs = BrowserOutputObservation(
        url="https://example.com",
        trigger_by_action="browse_interactive",
        screenshot="",
        set_of_marks="",
        content="Some webpage content",
    )
    agent_config = AgentConfig(enable_som_visual_browsing=True)
    prompt_manager = PromptManager(prompt_dir="Forge/agenthub/codeact_agent/prompts")
    conv_memory = ConversationMemory(agent_config, prompt_manager)
    messages = conv_memory._process_observation(
        obs=browser_obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=[],
    )
    has_image_content = False
    has_notification_text = False
    for message in messages:
        for content in message.content:
            if isinstance(content, ImageContent):
                has_image_content = True
                for url in content.image_urls:
                    assert url != "", "Empty image URL should be filtered out"
                    assert url is not None, "None image URL should be filtered out"
                    if url:
                        assert url.startswith("data:"), f"Invalid image URL format: {url}"
            elif hasattr(content, "text"):
                if "No visual information" in content.text or "has been filtered" in content.text:
                    has_notification_text = True
    assert not has_image_content, "Should not have ImageContent for empty images"
    assert has_notification_text, "Should have notification text about missing visual information"


def test_valid_image_url_handling():
    """Test that valid image URLs are properly handled."""
    valid_base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    browser_obs = BrowserOutputObservation(
        url="https://example.com",
        trigger_by_action="browse_interactive",
        screenshot=valid_base64_image,
        set_of_marks=valid_base64_image,
        content="Some webpage content",
    )
    agent_config = AgentConfig(enable_som_visual_browsing=True)
    prompt_manager = PromptManager(prompt_dir="Forge/agenthub/codeact_agent/prompts")
    conv_memory = ConversationMemory(agent_config, prompt_manager)
    messages = conv_memory._process_observation(
        obs=browser_obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=[],
    )
    found_image_content = False
    for message in messages:
        for content in message.content:
            if isinstance(content, ImageContent):
                found_image_content = True
                assert len(content.image_urls) > 0, "Should have at least one image URL"
                for url in content.image_urls:
                    assert url != "", "Image URL should not be empty"
                    assert url.startswith("data:image/"), f"Invalid image URL format: {url}"
    assert found_image_content, "Should have found ImageContent with valid URLs"


def test_mixed_image_url_handling():
    """Test handling of mixed valid and invalid image URLs."""
    valid_base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    browser_obs = BrowserOutputObservation(
        url="https://example.com",
        trigger_by_action="browse_interactive",
        screenshot="",
        set_of_marks=valid_base64_image,
        content="Some webpage content",
    )
    agent_config = AgentConfig(enable_som_visual_browsing=True)
    prompt_manager = PromptManager(prompt_dir="Forge/agenthub/codeact_agent/prompts")
    conv_memory = ConversationMemory(agent_config, prompt_manager)
    messages = conv_memory._process_observation(
        obs=browser_obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=[],
    )
    found_image_content = False
    for message in messages:
        for content in message.content:
            if isinstance(content, ImageContent):
                found_image_content = True
                assert len(content.image_urls) == 1, f"Should have exactly one image URL, got {len(content.image_urls)}"
                url = content.image_urls[0]
                assert url == valid_base64_image, f"Should use the valid image URL: {url}"
    assert found_image_content, "Should have found ImageContent with valid URL"


def test_ipython_empty_image_url_handling():
    """Test that empty image URLs in IPython observations are properly filtered with notification text."""
    from forge.events.observation.commands import IPythonRunCellObservation

    ipython_obs = IPythonRunCellObservation(content="Some output", code='print("hello")', image_urls=["", None, ""])
    agent_config = AgentConfig(enable_som_visual_browsing=True)
    prompt_manager = PromptManager(prompt_dir="Forge/agenthub/codeact_agent/prompts")
    conv_memory = ConversationMemory(agent_config, prompt_manager)
    messages = conv_memory._process_observation(
        obs=ipython_obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=[],
    )
    has_image_content = False
    has_notification_text = False
    for message in messages:
        for content in message.content:
            if isinstance(content, ImageContent):
                has_image_content = True
            elif hasattr(content, "text"):
                if "invalid or empty and have been filtered" in content.text:
                    has_notification_text = True
    assert not has_image_content, "Should not have ImageContent for empty images"
    assert has_notification_text, "Should have notification text about filtered images"


def test_ipython_mixed_image_url_handling():
    """Test handling of mixed valid and invalid image URLs in IPython observations."""
    from forge.events.observation.commands import IPythonRunCellObservation

    valid_base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    ipython_obs = IPythonRunCellObservation(
        content="Some output", code='print("hello")', image_urls=["", valid_base64_image, None]
    )
    agent_config = AgentConfig(enable_som_visual_browsing=True)
    prompt_manager = PromptManager(prompt_dir="Forge/agenthub/codeact_agent/prompts")
    conv_memory = ConversationMemory(agent_config, prompt_manager)
    messages = conv_memory._process_observation(
        obs=ipython_obs,
        tool_call_id_to_message={},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=[],
    )
    found_image_content = False
    has_notification_text = False
    for message in messages:
        for content in message.content:
            if isinstance(content, ImageContent):
                found_image_content = True
                assert len(content.image_urls) == 1, f"Should have exactly one image URL, got {len(content.image_urls)}"
                url = content.image_urls[0]
                assert url == valid_base64_image, f"Should use the valid image URL: {url}"
            elif hasattr(content, "text"):
                if "invalid or empty image(s) were filtered" in content.text:
                    has_notification_text = True
    assert found_image_content, "Should have found ImageContent with valid URL"
    assert has_notification_text, "Should have notification text about filtered images"
