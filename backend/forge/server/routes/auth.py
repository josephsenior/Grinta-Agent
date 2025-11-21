"""Authentication routes for user registration, login, and session management."""

from __future__ import annotations

import os
import secrets
import httpx
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

from forge.core.logger import forge_logger as logger
from forge.server.middleware.auth import AuthMiddleware, UserRole, get_current_user_id, require_auth
from forge.server.utils.responses import success, error
from forge.server.utils.password import hash_password, verify_password, is_password_strong
from forge.server.services.email_service import get_email_service
from forge.storage.data_models.user import User
from forge.storage.user import get_user_store

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

# OAuth state tokens (in-memory, use Redis in production)
_oauth_states: dict[str, tuple[str, datetime]] = {}  # state -> (provider, expiry)


# OAuth Helper Functions
def _create_error_redirect(redirect_uri: Optional[str], error_code: str) -> RedirectResponse:
    """Create a redirect response with error code."""
    redirect_url = redirect_uri or f"/auth/register?error={error_code}"
    return RedirectResponse(url=redirect_url)


def _validate_oauth_state(
    state: Optional[str], expected_provider: str, redirect_uri: Optional[str] = None
) -> tuple[bool, Optional[RedirectResponse]]:
    """Validate OAuth state parameter.
    
    Returns:
        Tuple of (is_valid, error_redirect_if_invalid)
    """
    if not state:
        return False, _create_error_redirect(redirect_uri, "missing_parameters")
    
    if state not in _oauth_states:
        return False, _create_error_redirect(redirect_uri, "invalid_state")
    
    provider, expiry = _oauth_states[state]
    if datetime.utcnow() > expiry:
        del _oauth_states[state]
        return False, _create_error_redirect(redirect_uri, "expired_state")
    
    if provider != expected_provider:
        return False, _create_error_redirect(redirect_uri, "invalid_provider")
    
    # Delete used state
    del _oauth_states[state]
    return True, None


async def _exchange_github_token(
    client: httpx.AsyncClient, client_id: str, client_secret: str, code: str, redirect_uri: Optional[str] = None
) -> tuple[Optional[str], Optional[RedirectResponse]]:
    """Exchange GitHub authorization code for access token.
    
    Returns:
        Tuple of (access_token, error_redirect_if_failed)
    """
    try:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
        
        if "error" in token_data:
            logger.error(f"GitHub token exchange error: {token_data}")
            return None, _create_error_redirect(redirect_uri, "token_exchange_failed")
        
        access_token = token_data.get("access_token")
        if not access_token:
            return None, _create_error_redirect(redirect_uri, "no_access_token")
        
        return access_token, None
    except Exception as e:
        logger.error(f"GitHub token exchange exception: {e}")
        return None, _create_error_redirect(redirect_uri, "token_exchange_failed")


async def _exchange_google_token(
    client: httpx.AsyncClient, client_id: str, client_secret: str, code: str, callback_uri: str, redirect_uri: Optional[str] = None
) -> tuple[Optional[str], Optional[RedirectResponse]]:
    """Exchange Google authorization code for access token.
    
    Returns:
        Tuple of (access_token, error_redirect_if_failed)
    """
    try:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_uri,
            },
        )
        token_data = token_response.json()
        
        if "error" in token_data:
            logger.error(f"Google token exchange error: {token_data}")
            return None, _create_error_redirect(redirect_uri, "token_exchange_failed")
        
        access_token = token_data.get("access_token")
        if not access_token:
            return None, _create_error_redirect(redirect_uri, "no_access_token")
        
        return access_token, None
    except Exception as e:
        logger.error(f"Google token exchange exception: {e}")
        return None, _create_error_redirect(redirect_uri, "token_exchange_failed")


async def _get_github_user_data(client: httpx.AsyncClient, access_token: Optional[str]) -> Optional[dict]:
    """Get user data from GitHub API."""
    try:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return user_response.json()
    except Exception as e:
        logger.error(f"Error fetching GitHub user data: {e}")
        return None


async def _get_github_user_email(client: httpx.AsyncClient, access_token: Optional[str]) -> Optional[str]:
    """Get user email from GitHub API."""
    user_data = await _get_github_user_data(client, access_token)
    if not user_data:
        return None
    
    email = user_data.get("email")
    if email:
        return email
    
    # Try emails endpoint
    try:
        emails_response = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        emails = emails_response.json()
        primary_email = next((e for e in emails if e.get("primary")), None)
        email = primary_email.get("email") if primary_email else (emails[0].get("email") if emails else None)
        return email
    except Exception as e:
        logger.error(f"Error fetching GitHub user emails: {e}")
        return None


async def _get_github_username(client: httpx.AsyncClient, access_token: str, email: Optional[str] = None) -> str:
    """Get username from GitHub user data."""
    user_data = await _get_github_user_data(client, access_token)
    if user_data:
        login = user_data.get("login")
        if login:
            return login
    # Fallback to email username or default
    if email:
        return email.split("@")[0]
    return "user"


async def _get_google_user_email(client: httpx.AsyncClient, access_token: Optional[str]) -> Optional[str]:
    """Get user email from Google API."""
    try:
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_response.json()
        return user_data.get("email")
    except Exception as e:
        logger.error(f"Error fetching Google user email: {e}")
        return None


async def _get_or_create_oauth_user(
    email: str, username_base: str, provider: str
) -> tuple[Optional[User], Optional[RedirectResponse]]:
    """Get existing user or create new user from OAuth.
    
    Returns:
        Tuple of (user, error_redirect_if_failed)
    """
    if not email:
        return None, _create_error_redirect(None, "no_email")
    
    user_store = get_user_store()
    user = await user_store.get_user_by_email(email.lower())
    
    if not user:
        # Create new user with unique username
        username = username_base.lower()
        base_username = username
        counter = 1
        while await user_store.get_user_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=email.lower(),
            username=username,
            password_hash="",  # OAuth users don't have passwords
            role=UserRole.USER,
            email_verified=True,  # OAuth emails are verified
            is_active=True,
        )
        user = await user_store.create_user(user)
        logger.info(f"User created via {provider} OAuth: {user.email} ({user.id})")
    else:
        logger.info(f"User logged in via {provider} OAuth: {user.email} ({user.id})")
    
    return user, None


def _create_success_redirect(redirect_uri: Optional[str], token: str) -> RedirectResponse:
    """Create redirect response with authentication token."""
    redirect_url = redirect_uri or "/dashboard"
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(url=f"{redirect_url}{separator}token={token}")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: Request, register_data: RegisterRequest) -> JSONResponse:
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
async def login(request: Request, login_data: LoginRequest) -> JSONResponse:
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
async def logout(request: Request) -> JSONResponse:
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
async def get_current_user(request: Request) -> JSONResponse:
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
) -> JSONResponse:
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
) -> JSONResponse:
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
    if user:
        reset_token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        _reset_tokens[reset_data.email.lower()] = (reset_token, expiry)

        logger.info(f"Password reset requested for: {reset_data.email}")
        
        # Send password reset email
        email_service = get_email_service()
        email_sent = email_service.send_password_reset_email(
            to_email=user.email,
            reset_token=reset_token,
        )
        
        if not email_sent:
            logger.warning(
                f"Failed to send password reset email to {user.email}. "
                "Check SMTP configuration. Token: {reset_token}"
            )

    return success(
        message="If the email exists, a password reset link has been sent",
        request=request,
    )


@router.post("/reset-password")
async def reset_password(
    request: Request, reset_data: ResetPasswordConfirmRequest
) -> JSONResponse:
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
async def refresh_token(request: Request) -> JSONResponse:
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


# OAuth Models
class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="OAuth state parameter")


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    request: Request,
    provider: str,
    redirect_uri: Optional[str] = Query(None, description="Redirect URI after OAuth"),
) -> JSONResponse:
    """Initiate OAuth flow for GitHub or Google.

    Args:
        request: FastAPI request
        provider: OAuth provider (github or google)
        redirect_uri: Optional redirect URI after authentication

    Returns:
        OAuth authorization URL
    """
    if provider not in ["github", "google"]:
        return error(
            message="Unsupported OAuth provider",
            error_code="UNSUPPORTED_PROVIDER",
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Generate state token
    state = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
    _oauth_states[state] = (provider, expiry)

    # Get OAuth configuration
    if provider == "github":
        client_id = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GITHUB_APP_CLIENT_ID")
        if not client_id:
            return error(
                message="GitHub OAuth not configured",
                error_code="OAUTH_NOT_CONFIGURED",
                request=request,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Build redirect URI
        base_url = str(request.base_url).rstrip("/")
        callback_uri = f"{base_url}/api/auth/oauth/github/callback"
        if redirect_uri:
            callback_uri += f"?redirect_uri={redirect_uri}"

        # GitHub OAuth URL
        params = {
            "client_id": client_id,
            "redirect_uri": callback_uri,
            "scope": "user:email",
            "state": state,
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    else:  # google
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            return error(
                message="Google OAuth not configured",
                error_code="OAUTH_NOT_CONFIGURED",
                request=request,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Build redirect URI
        base_url = str(request.base_url).rstrip("/")
        callback_uri = f"{base_url}/api/auth/oauth/google/callback"
        if redirect_uri:
            callback_uri += f"?redirect_uri={redirect_uri}"

        # Google OAuth URL
        params = {
            "client_id": client_id,
            "redirect_uri": callback_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return success(
        data={"auth_url": auth_url, "state": state},
        request=request,
    )


@router.get("/oauth/github/callback")
async def _process_github_oauth_flow(
    client: httpx.AsyncClient, client_id: str, client_secret: str, code: str, redirect_uri: Optional[str]
) -> tuple[Optional[User], Optional[RedirectResponse]]:
    """Process GitHub OAuth flow after token exchange.
    
    Returns:
        Tuple of (user, error_redirect_if_failed)
    """
    # Exchange code for access token
    access_token, error_redirect = await _exchange_github_token(client, client_id, client_secret, code, redirect_uri)
    if error_redirect or not access_token:
        return None, error_redirect or _create_error_redirect(redirect_uri, "no_access_token")

    # Get user email from GitHub
    email = await _get_github_user_email(client, access_token)
    if not email:
        return None, _create_error_redirect(redirect_uri, "no_email")

    # Get username from GitHub user data
    username_base = await _get_github_username(client, access_token, email)

    # Get or create user
    user, error_redirect = await _get_or_create_oauth_user(email, username_base, "GitHub")
    return user, error_redirect


async def oauth_github_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
) -> RedirectResponse:
    """Handle GitHub OAuth callback.

    Args:
        request: FastAPI request
        code: OAuth authorization code
        state: OAuth state parameter
        error: OAuth error if any
        redirect_uri: Redirect URI after authentication

    Returns:
        Redirect response
    """
    if error:
        logger.error(f"GitHub OAuth error: {error}")
        return _create_error_redirect(redirect_uri, "oauth_failed")

    if not code:
        return _create_error_redirect(redirect_uri, "missing_parameters")

    # Validate state
    is_valid, error_redirect = _validate_oauth_state(state, "github", redirect_uri)
    if not is_valid:
        return error_redirect or _create_error_redirect(redirect_uri, "invalid_state")

    # Get OAuth credentials
    client_id = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GITHUB_APP_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        return _create_error_redirect(redirect_uri, "oauth_not_configured")

    try:
        async with httpx.AsyncClient() as client:
            user, error_redirect = await _process_github_oauth_flow(
                client, client_id, client_secret, code, redirect_uri
            )
            if error_redirect:
                return error_redirect
            if not user:
                return _create_error_redirect(redirect_uri, "user_creation_failed")

            # Generate JWT token and redirect
            token = AuthMiddleware.create_token(
                user_id=user.id,
                email=user.email,
                role=user.role,
            )
            return _create_success_redirect(redirect_uri, token)

    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return _create_error_redirect(redirect_uri, "oauth_callback_failed")


@router.get("/oauth/google/callback")
async def oauth_google_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None),
) -> RedirectResponse:
    """Handle Google OAuth callback.

    Args:
        request: FastAPI request
        code: OAuth authorization code
        state: OAuth state parameter
        error: OAuth error if any
        redirect_uri: Redirect URI after authentication

    Returns:
        Redirect response
    """
    if error:
        logger.error(f"Google OAuth error: {error}")
        return _create_error_redirect(redirect_uri, "oauth_failed")

    if not code:
        return _create_error_redirect(redirect_uri, "missing_parameters")

    # Validate state
    is_valid, error_redirect = _validate_oauth_state(state, "google", redirect_uri)
    if not is_valid:
        return error_redirect or _create_error_redirect(redirect_uri, "invalid_state")

    # Get OAuth credentials
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return _create_error_redirect(redirect_uri, "oauth_not_configured")

    try:
        base_url = str(request.base_url).rstrip("/")
        callback_uri = f"{base_url}/api/auth/oauth/google/callback"

        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            access_token, error_redirect = await _exchange_google_token(
                client, client_id, client_secret, code, callback_uri, redirect_uri
            )
            if error_redirect or not access_token:
                return error_redirect or _create_error_redirect(redirect_uri, "no_access_token")

            # Get user email from Google
            email = await _get_google_user_email(client, access_token)
            if not email:
                return _create_error_redirect(redirect_uri, "no_email")

            # Get username from Google user data
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_data = user_response.json()
            username_base = user_data.get("given_name", email.split("@")[0])

            # Get or create user
            user, error_redirect = await _get_or_create_oauth_user(email, username_base, "Google")
            if error_redirect:
                return error_redirect
            if not user:
                return _create_error_redirect(redirect_uri, "user_creation_failed")

            # Generate JWT token and redirect
            token = AuthMiddleware.create_token(
                user_id=user.id,
                email=user.email,
                role=user.role,
            )
            return _create_success_redirect(redirect_uri, token)

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return _create_error_redirect(redirect_uri, "oauth_callback_failed")

