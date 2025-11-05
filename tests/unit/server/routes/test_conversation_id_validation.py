"""Test cases for conversation ID validation to ensure proper error handling.

This addresses GitHub issue #10489 where long conversation IDs were returning
500 Internal Server Error instead of proper 4xx errors.
"""

import pytest
from fastapi import HTTPException, status
from openhands.server.utils import validate_conversation_id


class TestConversationIdValidation:
    """Test conversation ID validation function."""

    def test_valid_conversation_id(self):
        """Test that valid conversation IDs pass validation."""
        valid_id = "a1b2c3d4e5f6789012345678901234ab"
        result = validate_conversation_id(valid_id)
        assert result == valid_id
        valid_id = "abc123"
        result = validate_conversation_id(valid_id)
        assert result == valid_id
        valid_id = "a1b2c3d4-e5f6-7890-1234-5678901234ab"
        result = validate_conversation_id(valid_id)
        assert result == valid_id

    def test_long_conversation_id_rejected(self):
        """Test that very long conversation IDs are rejected with 400 Bad Request.

        This is the main test case for GitHub issue #10489.
        """
        long_id = "a" * 1000
        with pytest.raises(HTTPException) as exc_info:
            validate_conversation_id(long_id)
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "too long" in exc_info.value.detail

    def test_conversation_id_with_null_bytes_rejected(self):
        """Test that conversation IDs with null bytes are rejected."""
        invalid_id = "valid\x00id"
        with pytest.raises(HTTPException) as exc_info:
            validate_conversation_id(invalid_id)
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid characters" in exc_info.value.detail

    def test_conversation_id_with_path_traversal_rejected(self):
        """Test that conversation IDs with path traversal attempts are rejected."""
        invalid_ids = [
            "../../../etc/passwd",
            "id/../other",
            "id\\..\\other",
            "id/with/slashes",
            "id\\with\\backslashes",
        ]
        for invalid_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_conversation_id(invalid_id)
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "invalid path characters" in exc_info.value.detail

    def test_conversation_id_with_control_characters_rejected(self):
        """Test that conversation IDs with control characters are rejected."""
        invalid_ids = ["id\nwith\nnewlines", "id\twith\ttabs", "id\rwith\rcarriage", "id\x01with\x02control"]
        for invalid_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_conversation_id(invalid_id)
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "control characters" in exc_info.value.detail

    def test_conversation_id_boundary_length(self):
        """Test conversation ID length boundaries."""
        boundary_id = "a" * 100
        result = validate_conversation_id(boundary_id)
        assert result == boundary_id
        too_long_id = "a" * 101
        with pytest.raises(HTTPException) as exc_info:
            validate_conversation_id(too_long_id)
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "too long" in exc_info.value.detail

    def test_empty_conversation_id(self):
        """Test that empty conversation ID is handled."""
        result = validate_conversation_id("")
        assert result == ""

    def test_conversation_id_with_spaces(self):
        """Test that conversation IDs with spaces are allowed."""
        id_with_spaces = "id with spaces"
        result = validate_conversation_id(id_with_spaces)
        assert result == id_with_spaces
