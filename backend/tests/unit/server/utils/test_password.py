"""Tests for password utilities."""
import pytest
from forge.server.utils.password import (
    hash_password,
    verify_password,
    is_password_strong,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_for_same_password(self):
        """Test that hashing the same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test that verify_password handles empty password."""
        # Empty password should raise ValueError when hashing
        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password("")
        
        # verify_password should return False for empty inputs
        assert verify_password("", "some_hash") is False
        assert verify_password("password", "") is False

    def test_verify_password_special_characters(self):
        """Test password with special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("P@ssw0rd!#$%^&*()", hashed) is True

    def test_verify_password_unicode(self):
        """Test password with unicode characters."""
        password = "密码123🔒"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestPasswordStrength:
    """Test password strength validation."""

    def test_is_password_strong_weak(self):
        """Test weak password detection."""
        weak_passwords = [
            ("short", "Password must be at least 8 characters long"),  # Too short
            ("12345678", "Password must contain both uppercase and lowercase letters"),  # Only numbers
            ("abcdefgh", "Password must contain both uppercase and lowercase letters"),  # Only lowercase
            ("ABCDEFGH", "Password must contain both uppercase and lowercase letters"),  # Only uppercase (checks case first)
        ]
        for password, expected_error in weak_passwords:
            is_strong, error = is_password_strong(password)
            assert is_strong is False
            assert expected_error in error

    def test_is_password_strong_valid(self):
        """Test valid password detection."""
        valid_passwords = [
            "Password1",  # Has uppercase, lowercase, number
            "Test1234",  # Has uppercase, lowercase, number
            "MyPass123",  # Has uppercase, lowercase, number
            "StrongP@ssw0rd123!",  # Has special characters too
            "MyVerySecureP@ssw0rd!2024",  # Complex password
        ]
        for password in valid_passwords:
            is_strong, error = is_password_strong(password)
            assert is_strong is True
            assert error is None

    def test_is_password_strong_minimum_length(self):
        """Test that passwords must meet minimum length."""
        short_password = "Pass1"  # Less than 8 characters
        is_strong, error = is_password_strong(short_password)
        assert is_strong is False
        assert "at least 8 characters" in error

    def test_is_password_strong_maximum_length(self):
        """Test that passwords must not exceed maximum length."""
        long_password = "A" * 129 + "1"  # More than 128 characters
        is_strong, error = is_password_strong(long_password)
        assert is_strong is False
        assert "less than 128 characters" in error

    def test_is_password_strong_empty(self):
        """Test empty password."""
        is_strong, error = is_password_strong("")
        assert is_strong is False
        assert "at least 8 characters" in error

    def test_is_password_strong_whitespace(self):
        """Test password with whitespace."""
        password = "  Password123  "
        is_strong, error = is_password_strong(password)
        # Should validate (whitespace is allowed)
        assert is_strong is True
        assert error is None

