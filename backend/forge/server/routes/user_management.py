"""User management routes for admin operations."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from forge.core.logger import forge_logger as logger
from forge.server.middleware.auth import UserRole, get_current_user_id
from forge.server.utils.responses import success, error
from forge.server.utils.pagination import PaginatedResponse, parse_pagination_params
from forge.storage.user import get_user_store
from forge.storage.data_models.user import User
from forge.server.middleware.auth import AuthMiddleware

router = APIRouter(prefix="/api/users", tags=["user-management"])


# Helper Functions
def _validate_user_update_permissions(
    current_user: Optional[User], current_user_id: str, target_user_id: str, update_data: "UpdateUserRequest"
) -> tuple[bool, Optional[str], Optional[str]]:
    """Validate permissions for user update.
    
    Returns:
        Tuple of (is_allowed, error_message_if_not_allowed, error_code_if_not_allowed)
    """
    is_admin = current_user and current_user.role == UserRole.ADMIN
    is_own_account = current_user_id == target_user_id
    
    if not (is_admin or is_own_account):
        return False, "Access denied", "FORBIDDEN"
    
    # Non-admins can only update limited fields
    if not is_admin:
        if update_data.role is not None or update_data.is_active is not None:
            return False, "Insufficient permissions", "FORBIDDEN"
    
    return True, None, None


async def _validate_username_uniqueness(
    user_store, username: str, user_id: str, request: Request
) -> tuple[bool, Optional[JSONResponse]]:
    """Validate username uniqueness.
    
    Returns:
        Tuple of (is_unique, error_response_if_not_unique)
    """
    existing = await user_store.get_user_by_username(username)
    if existing and existing.id != user_id:
        return False, error(
            message="Username already taken",
            error_code="USERNAME_ALREADY_EXISTS",
            request=request,
            status_code=409,
        )
    return True, None


async def _validate_email_uniqueness(
    user_store, email: str, user_id: str, request: Request
) -> tuple[bool, Optional[JSONResponse]]:
    """Validate email uniqueness.
    
    Returns:
        Tuple of (is_unique, error_response_if_not_unique)
    """
    existing = await user_store.get_user_by_email(email)
    if existing and existing.id != user_id:
        return False, error(
            message="Email already taken",
            error_code="EMAIL_ALREADY_EXISTS",
            request=request,
            status_code=409,
        )
    return True, None


async def _update_username_field(
    user_store, target_user: User, username: str, request: Request
) -> tuple[bool, Optional[JSONResponse]]:
    """Update username field with validation.
    
    Returns:
        Tuple of (success, error_response_if_failed)
    """
    is_unique, error_response = await _validate_username_uniqueness(
        user_store, username, target_user.id, request
    )
    if not is_unique:
        return False, error_response
    target_user.username = username
    return True, None


async def _update_email_field(
    user_store, target_user: User, email: str, request: Request
) -> tuple[bool, Optional[JSONResponse]]:
    """Update email field with validation.
    
    Returns:
        Tuple of (success, error_response_if_failed)
    """
    is_unique, error_response = await _validate_email_uniqueness(
        user_store, email, target_user.id, request
    )
    if not is_unique:
        return False, error_response
    target_user.email = email.lower()
    return True, None


def _update_admin_fields(target_user: User, update_data: "UpdateUserRequest", is_admin: bool) -> None:
    """Update admin-only fields if user is admin."""
    if not is_admin:
        return
    
    if update_data.role is not None:
        target_user.role = UserRole(update_data.role)
    
    if update_data.is_active is not None:
        target_user.is_active = update_data.is_active
    
    if update_data.email_verified is not None:
        target_user.email_verified = update_data.email_verified


async def _apply_user_updates(
    user_store, target_user: User, update_data: "UpdateUserRequest", is_admin: bool, request: Request
) -> tuple[Optional[User], Optional[JSONResponse]]:
    """Apply updates to user object.
    
    Returns:
        Tuple of (updated_user, error_response_if_validation_failed)
    """
    if update_data.username is not None:
        success, error_response = await _update_username_field(
            user_store, target_user, update_data.username, request
        )
        if not success:
            return None, error_response
    
    if update_data.email is not None:
        success, error_response = await _update_email_field(
            user_store, target_user, update_data.email, request
        )
        if not success:
            return None, error_response
    
    _update_admin_fields(target_user, update_data, is_admin)
    
    updated_user = await user_store.update_user(target_user)
    return updated_user, None


class UpdateUserRequest(BaseModel):
    """Update user request."""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None


@router.get("/", response_model=None)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> JSONResponse | PaginatedResponse[dict]:
    """List all users (admin only).

    Args:
        request: FastAPI request
        page: Page number
        limit: Items per page

    Returns:
        Paginated list of users
    """
    # Require admin role
    user_id = get_current_user_id(request)
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    user_store = get_user_store()
    current_user = await user_store.get_user_by_id(user_id)
    
    if not current_user or current_user.role != UserRole.ADMIN:
        return error(
            message="Admin access required",
            error_code="FORBIDDEN",
            request=request,
            status_code=403,
        )

    params = parse_pagination_params(page=page, limit=limit)
    users = await user_store.list_users(skip=params.offset, limit=params.limit)
    
    # Get total count (simplified - in production, use count query)
    all_users = await user_store.list_users(skip=0, limit=10000)
    total = len(all_users)

    return PaginatedResponse.create(
        items=[user.to_dict() for user in users],
        page=params.page,
        limit=params.limit,
        total=total,
    )


@router.get("/{user_id}")
async def get_user(request: Request, user_id: str) -> JSONResponse:
    """Get user by ID (admin or own account).

    Args:
        request: FastAPI request
        user_id: User ID

    Returns:
        User information
    """
    current_user_id = get_current_user_id(request)
    if not current_user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    user_store = get_user_store()
    current_user = await user_store.get_user_by_id(current_user_id)

    # Allow access to own account or admin
    if current_user_id != user_id:
        if not current_user or current_user.role != UserRole.ADMIN:
            return error(
                message="Access denied",
                error_code="FORBIDDEN",
                request=request,
                status_code=403,
            )

    user = await user_store.get_user_by_id(user_id)
    if not user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=404,
        )

    return success(
        data={"user": user.to_dict()},
        request=request,
    )


@router.patch("/{user_id}")
async def update_user(
    request: Request, user_id: str, update_data: UpdateUserRequest
) -> JSONResponse:
    """Update user (admin only, or own account for limited fields).

    Args:
        request: FastAPI request
        user_id: User ID
        update_data: Update data

    Returns:
        Updated user information
    """
    current_user_id = get_current_user_id(request)
    if not current_user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    
    user_store = get_user_store()
    current_user = await user_store.get_user_by_id(current_user_id)
    target_user = await user_store.get_user_by_id(user_id)

    if not target_user:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=404,
        )

    # Validate permissions
    is_allowed, error_message, error_code = _validate_user_update_permissions(
        current_user, current_user_id, user_id, update_data
    )
    if not is_allowed:
        return error(
            message=error_message or "Access denied",
            error_code=error_code or "FORBIDDEN",
            request=request,
            status_code=403,
        )

    # Apply updates
    is_admin = bool(current_user and current_user.role == UserRole.ADMIN)
    updated_user, error_response = await _apply_user_updates(
        user_store, target_user, update_data, is_admin, request
    )
    if error_response:
        return error_response

    if not updated_user:
        return error(
            message="Failed to update user",
            error_code="UPDATE_FAILED",
            request=request,
            status_code=500,
        )

    logger.info(f"User updated: {user_id} by {current_user_id}")

    return success(
        data={"user": updated_user.to_dict()},
        message="User updated successfully",
        request=request,
    )


@router.delete("/{user_id}")
async def delete_user(request: Request, user_id: str) -> JSONResponse:
    """Delete user (admin only).

    Args:
        request: FastAPI request
        user_id: User ID to delete

    Returns:
        Success message
    """
    current_user_id = get_current_user_id(request)
    if not current_user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    user_store = get_user_store()
    current_user = await user_store.get_user_by_id(current_user_id)

    if not current_user or current_user.role != UserRole.ADMIN:
        return error(
            message="Admin access required",
            error_code="FORBIDDEN",
            request=request,
            status_code=403,
        )

    # Prevent self-deletion
    if current_user_id == user_id:
        return error(
            message="Cannot delete your own account",
            error_code="INVALID_OPERATION",
            request=request,
            status_code=400,
        )

    deleted = await user_store.delete_user(user_id)
    if not deleted:
        return error(
            message="User not found",
            error_code="USER_NOT_FOUND",
            request=request,
            status_code=404,
        )

    logger.info(f"User deleted: {user_id} by {current_user_id}")

    return success(
        message="User deleted successfully",
        request=request,
    )

