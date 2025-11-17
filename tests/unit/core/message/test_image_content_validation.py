"""Test for ImageContent serialization behavior.

Note: Image URL filtering now happens at the conversation memory level,
not at the ImageContent serialization level. These tests verify that
ImageContent correctly serializes whatever URLs it's given.
"""

from forge.core.message import ImageContent


def test_image_content_serializes_all_urls():
    """Test that ImageContent serializes all URLs it's given, including empty ones."""
    image_content = ImageContent(
        image_urls=[
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "",
            "   ",
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA==",
        ]
    )
    serialized = image_content.model_dump()
    assert len(serialized) == 4, (
        f"Expected 4 URLs (including empty), got {len(serialized)}"
    )
    expected_urls = [
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "",
        "   ",
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA==",
    ]
    for i, item in enumerate(serialized):
        assert item["type"] == "image_url"
        assert "image_url" in item
        assert "url" in item["image_url"]
        assert item["image_url"]["url"] == expected_urls[i]


def test_image_content_serializes_empty_urls():
    """Test that ImageContent serializes empty URLs (filtering happens upstream)."""
    image_content = ImageContent(image_urls=["", "   "])
    serialized = image_content.model_dump()
    assert len(serialized) == 2, f"Expected 2 URLs, got {serialized}"
    assert serialized[0]["image_url"]["url"] == ""
    assert serialized[1]["image_url"]["url"] == "   "


def test_image_content_all_valid_urls():
    """Test that ImageContent preserves all valid URLs."""
    valid_urls = [
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA==",
    ]
    image_content = ImageContent(image_urls=valid_urls)
    serialized = image_content.model_dump()
    assert len(serialized) == len(valid_urls), (
        f"Expected {len(valid_urls)} URLs, got {len(serialized)}"
    )
    for i, item in enumerate(serialized):
        assert item["type"] == "image_url"
        assert item["image_url"]["url"] == valid_urls[i]
