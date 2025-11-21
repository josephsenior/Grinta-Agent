"""Password hashing and verification utilities.

Uses bcrypt for secure password hashing.
"""

from __future__ import annotations

import bcrypt
from typing import Optional

from forge.core.logger import forge_logger as logger


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password
        rounds: Number of bcrypt rounds (default: 12, higher = more secure but slower)

    Returns:
        Bcrypt hashed password string
    """
    if not password:
        raise ValueError("Password cannot be empty")

    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=rounds)
    password_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash.

    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    if not password or not password_hash:
        return False

    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def is_password_strong(password: str) -> tuple[bool, Optional[str]]:
    """Check if password meets strength requirements.

    Args:
        password: Password to check

    Returns:
        Tuple of (is_strong, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must be less than 128 characters"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower):
        return False, "Password must contain both uppercase and lowercase letters"

    if not has_digit:
        return False, "Password must contain at least one digit"

    # Special characters are recommended but not required
    # if not has_special:
    #     return False, "Password must contain at least one special character"

    return True, None

