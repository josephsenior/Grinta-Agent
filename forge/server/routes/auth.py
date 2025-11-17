"""Authentication routes for user registration, login, and session management."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field, field_validator

from forge.core.logger import forge_logger as logger
from forge.server.middleware.auth import AuthMiddleware, UserRole, get_current_user_id, require_auth
from forge.server.utils.responses import success, error
from forge.server.utils.password import hash_password, verify_password, is_password_strong
from forge.storage.data_models.user import User
from forge.storage.user.file_user_store import get_user_store

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v.lower()


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response."""

    token: str = Field(..., description="JWT authentication token")
    user: dict = Field(..., description="User information")
    expires_in: int = Field(..., description="Token expiration in seconds")


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class ResetPasswordRequest(BaseModel):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email address")


class ResetPasswordConfirmRequest(BaseModel):
    """Password reset confirmation request."""

    email: EmailStr = Field(..., description="User email address")
    reset_token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


# Password reset tokens (in-memory, use Redis in production)
_reset_tokens: dict[str, tuple[str, datetime]] = {}  # email -> (token, expiry)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: Request, register_data: RegisterRequest) -> dict:
    """Register a new user account.

    Args:
        request: FastAPI request
        register_data: Registration data

    Returns:
        User information and authentication token
    """
    user_store = get_user_store()

    # Validate password strength
    is_strong, error_msg = is_password_strong(register_data.password)
    if not is_strong:
        return error(
            message=error_msg or "Password does not meet strength requirements",
            error_code="WEAK_PASSWORD",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Check if user already exists (normalize email to lowercase)
    existing = await user_store.get_user_by_email(register_data.email.lower())
    if existing:
        return error(
            message="User with this email already exists",
            error_code="EMAIL_ALREADY_EXISTS",
            request=request,
            status_code=status.HTTP_409_CONFLICT,
        )

    existing = await user_store.get_user_by_username(register_data.username.lower())
    if existing:
        return error(
            message="Username already taken",
            error_code="USERNAME_ALREADY_EXISTS",
            request=request,
            status_code=status.HTTP_409_CONFLICT,
        )

    # Hash password
    try:
        password_hash = hash_password(register_data.password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        return error(
            message="Failed to process password",
            error_code="PASSWORD_HASH_ERROR",
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Create user
    user = User(
        email=register_data.email.lower(),
        username=register_data.username,
        password_hash=password_hash,
        role=UserRole.USER,
        email_verified=False,
        is_active=True,
    )

    try:
        user = await user_store.create_user(user)
    except ValueError as e:
        return error(
            message=str(e),
            error_code="USER_CREATION_ERROR",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Generate JWT token
    token = AuthMiddleware.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    logger.info(f"User registered: {user.email} ({user.id})")

    return success(
        data={
            "token": token,
            "user": user.to_dict(),
            "expires_in": int(os.getenv("JWT_EXPIRATION_HOURS", "24")) * 3600,
        },
        message="User registered successfully",
        request=request,
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login")
async def login(request: Request, login_data: LoginRequest) -> dict:
    """Authenticate user and return JWT token.

    Args:
        request: FastAPI request
        login_data: Login credentials

    Returns:
        Authentication token and user information
    """
    user_store = get_user_store()

    # Get user by email
    user = await user_store.get_user_by_email(login_data.email.lower())
    if not user:
        # Don't reveal if email exists (security best practice)
        return error(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
            request=request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if account is locked
    if user.is_locked():
        return error(
            message="Account is temporarily locked due to too many failed login attempts",
            error_code="ACCOUNT_LOCKED",
            request=request,
            status_code=status.HTTP_423_LOCKED,
        )

    # Check if account is active
    if not user.is_active:
        return error(
            message="Account is deactivated",
            error_code="ACCOUNT_DEACTIVATED",
            request=request,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        max_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        lockout_duration = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "30"))

        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=lockout_duration)
            logger.warning(f"Account locked: {user.email} after {user.failed_login_attempts} failed attempts")

        await user_store.update_user(user)

        return error(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
            request=request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    await user_store.update_user(user)

    # Generate JWT token
    token = AuthMiddleware.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    logger.info(f"User logged in: {user.email} ({user.id})")

    return success(
        data={
            "token": token,
            "user": user.to_dict(),
            "expires_in": int(os.getenv("JWT_EXPIRATION_HOURS", "24")) * 3600,
        },
        message="Login successful",
        request=request,
    )


@router.post("/logout")
async def logout(request: Request) -> dict:
    """Logout user (client should discard token).

    Args:
        request: FastAPI request

    Returns:
        Success message
    """
    # In a stateless JWT system, logout is handled client-side by discarding the token
    # Server-side: Could implement token blacklisting here if needed
    return success(
        message="Logged out successfully",
        request=request,
    )


@router.get("/me")
async def get_current_user(request: Request) -> dict:
    """Get current authenticated user information.

    Args:
        request: FastAPI request

    Returns:
        Current user information
    """
    user_id = require_auth(request)
    user_store = get_user_store()

    user = await user_store.get_user_by_id(user_id)
    if not user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return success(
        data={"user": user.to_dict()},
        request=request,
    )


@router.post("/change-password")
async def change_password(
    request: Request, password_data: ChangePasswordRequest
) -> dict:
    """Change user password.

    Args:
        request: FastAPI request
        password_data: Password change data

    Returns:
        Success message
    """
    user_id = get_current_user_id(request)
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    user_store = get_user_store()

    user = await user_store.get_user_by_id(user_id)
    if not user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Verify current password
    if not verify_password(password_data.current_password, user.password_hash):
        return error(
            message="Current password is incorrect",
            error_code="INVALID_PASSWORD",
            request=request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Validate new password strength
    is_strong, error_msg = is_password_strong(password_data.new_password)
    if not is_strong:
        return error(
            message=error_msg or "New password does not meet strength requirements",
            error_code="WEAK_PASSWORD",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Hash and update password
    user.password_hash = hash_password(password_data.new_password)
    await user_store.update_user(user)

    logger.info(f"Password changed for user: {user.email} ({user_id})")

    return success(
        message="Password changed successfully",
        request=request,
    )


@router.post("/forgot-password")
async def forgot_password(
    request: Request, reset_data: ResetPasswordRequest
) -> dict:
    """Request password reset (sends reset token).

    Args:
        request: FastAPI request
        reset_data: Password reset request data

    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    user_store = get_user_store()
    user = await user_store.get_user_by_email(reset_data.email.lower())

    # Always return success to prevent email enumeration
    # In production, send email with reset token
    if user:
        import secrets

        reset_token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        _reset_tokens[reset_data.email.lower()] = (reset_token, expiry)

        logger.info(f"Password reset requested for: {reset_data.email}")
        # TODO: Send email with reset token
        # await send_password_reset_email(user.email, reset_token)

    return success(
        message="If the email exists, a password reset link has been sent",
        request=request,
    )


@router.post("/reset-password")
async def reset_password(
    request: Request, reset_data: ResetPasswordConfirmRequest
) -> dict:
    """Reset password using reset token.

    Args:
        request: FastAPI request
        reset_data: Password reset confirmation data

    Returns:
        Success message
    """
    user_store = get_user_store()

    # Verify reset token
    email_key = reset_data.email.lower()
    if email_key not in _reset_tokens:
        return error(
            message="Invalid or expired reset token",
            error_code="INVALID_RESET_TOKEN",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token, expiry = _reset_tokens[email_key]
    if datetime.utcnow() > expiry:
        del _reset_tokens[email_key]
        return error(
            message="Reset token has expired",
            error_code="RESET_TOKEN_EXPIRED",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if token != reset_data.reset_token:
        return error(
            message="Invalid reset token",
            error_code="INVALID_RESET_TOKEN",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Get user
    user = await user_store.get_user_by_email(reset_data.email.lower())
    if not user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Validate new password strength
    is_strong, error_msg = is_password_strong(reset_data.new_password)
    if not is_strong:
        return error(
            message=error_msg or "New password does not meet strength requirements",
            error_code="WEAK_PASSWORD",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Update password
    user.password_hash = hash_password(reset_data.new_password)
    user.failed_login_attempts = 0  # Reset failed attempts
    user.locked_until = None
    await user_store.update_user(user)

    # Remove used token
    del _reset_tokens[email_key]

    logger.info(f"Password reset for user: {user.email} ({user.id})")

    return success(
        message="Password reset successfully",
        request=request,
    )


@router.post("/refresh")
async def refresh_token(request: Request) -> dict:
    """Refresh authentication token.

    Args:
        request: FastAPI request

    Returns:
        New authentication token
    """
    user_id = get_current_user_id(request)
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    user_store = get_user_store()

    user = await user_store.get_user_by_id(user_id)
    if not user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Generate new token
    token = AuthMiddleware.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return success(
        data={
            "token": token,
            "expires_in": int(os.getenv("JWT_EXPIRATION_HOURS", "24")) * 3600,
        },
        request=request,
    )

