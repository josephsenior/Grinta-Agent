"""User management routes for admin operations."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel, EmailStr

from forge.core.logger import forge_logger as logger
from forge.server.middleware.auth import UserRole, get_current_user_id
from forge.server.utils.responses import success, error
from forge.server.utils.pagination import PaginatedResponse, parse_pagination_params
from forge.storage.user.file_user_store import get_user_store
from forge.storage.data_models.user import User
from forge.server.middleware.auth import AuthMiddleware

router = APIRouter(prefix="/api/users", tags=["user-management"])


class UpdateUserRequest(BaseModel):
    """Update user request."""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None


@router.get("/")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
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
async def get_user(request: Request, user_id: str) -> dict:
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
) -> dict:
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

    # Check permissions
    is_admin = current_user and current_user.role == UserRole.ADMIN
    is_own_account = current_user_id == user_id

    if not (is_admin or is_own_account):
        return error(
            message="Access denied",
            error_code="FORBIDDEN",
            request=request,
            status_code=403,
        )

    # Non-admins can only update limited fields
    if not is_admin:
        if update_data.role is not None or update_data.is_active is not None:
            return error(
                message="Insufficient permissions",
                error_code="FORBIDDEN",
                request=request,
                status_code=403,
            )

    # Update fields
    if update_data.username is not None:
        # Check username uniqueness
        existing = await user_store.get_user_by_username(update_data.username)
        if existing and existing.id != user_id:
            return error(
                message="Username already taken",
                error_code="USERNAME_ALREADY_EXISTS",
                request=request,
                status_code=409,
            )
        target_user.username = update_data.username

    if update_data.email is not None:
        # Check email uniqueness
        existing = await user_store.get_user_by_email(update_data.email)
        if existing and existing.id != user_id:
            return error(
                message="Email already taken",
                error_code="EMAIL_ALREADY_EXISTS",
                request=request,
                status_code=409,
            )
        target_user.email = update_data.email.lower()

    if update_data.role is not None and is_admin:
        target_user.role = UserRole(update_data.role)

    if update_data.is_active is not None and is_admin:
        target_user.is_active = update_data.is_active

    if update_data.email_verified is not None and is_admin:
        target_user.email_verified = update_data.email_verified

    updated_user = await user_store.update_user(target_user)

    logger.info(f"User updated: {user_id} by {current_user_id}")

    return success(
        data={"user": updated_user.to_dict()},
        message="User updated successfully",
        request=request,
    )


@router.delete("/{user_id}")
async def delete_user(request: Request, user_id: str) -> dict:
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

