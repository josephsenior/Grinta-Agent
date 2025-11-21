"""Tests for authentication routes."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from forge.server.app import app
from forge.storage.user.file_user_store import FileUserStore, get_user_store
from forge.storage.data_models.user import User
from forge.server.utils.password import hash_password
from forge.server.middleware.auth import UserRole
import tempfile
import shutil
import os


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for user storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_app(temp_storage_dir):
    """Get FastAPI app with temporary user storage."""
    with patch.dict(os.environ, {"USER_STORAGE_PATH": temp_storage_dir, "AUTH_ENABLED": "true", "JWT_SECRET": "test_secret_key_for_testing_only", "JWT_ALGORITHM": "HS256"}):
        # Reset the global user store instance to use the temp directory
        from forge.storage.user.file_user_store import _user_store_instance
        global _user_store_instance
        _user_store_instance = None
        yield app
        # Cleanup
        _user_store_instance = None


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def user_store(temp_storage_dir):
    """Create a FileUserStore instance."""
    return FileUserStore(storage_path=temp_storage_dir)


@pytest.fixture
def test_user(user_store):
    """Create a test user synchronously."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("test_password_123"),
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )
    # Use asyncio.run() to execute async code in sync fixture
    return asyncio.run(user_store.create_user(user))


@pytest.fixture
def admin_user(user_store):
    """Create an admin test user synchronously."""
    user = User(
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin_password_123"),
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    # Use asyncio.run() to execute async code in sync fixture
    return asyncio.run(user_store.create_user(user))


class TestRegisterRoute:
    """Test user registration endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert "token" in data["data"]
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == "newuser@example.com"
        assert data["data"]["user"]["username"] == "newuser"
        assert "password" not in data["data"]["user"]  # Password should not be in response

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "username": "different_user",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data["status"] == "error"
        assert "email" in data["message"].lower() or "already exists" in data["message"].lower()

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert data["status"] == "error"
        assert "username" in data["message"].lower() or "already taken" in data["message"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid_email",
                "username": "newuser",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "weak",
            },
        )
        # FastAPI validation or our route handler should reject weak password
        assert response.status_code in [400, 422]  # Accept both validation errors

    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                # Missing username and password
            },
        )
        assert response.status_code == 422  # Validation error


class TestLoginRoute:
    """Test user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "test_password_123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "token" in data["data"]
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == test_user.email

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "wrong_password",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"

    def test_login_inactive_user(self, client, user_store):
        """Test login with inactive user."""
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            password_hash=hash_password("password123"),
            role=UserRole.USER,
            is_active=False,
            email_verified=False,
        )
        created_user = asyncio.run(user_store.create_user(inactive_user))
        response = client.post(
            "/api/auth/login",
            json={
                "email": created_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                # Missing password
            },
        )
        assert response.status_code == 422  # Validation error


class TestGetCurrentUserRoute:
    """Test get current user endpoint."""

    def test_get_current_user_success(self, client, test_user):
        """Test getting current user with valid token."""
        # First login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "test_password_123",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["status"] == "ok"
        token = login_data["data"]["token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["user"]["email"] == test_user.email
        assert data["data"]["user"]["id"] == test_user.id

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestLogoutRoute:
    """Test logout endpoint."""

    def test_logout_success(self, client, test_user):
        """Test successful logout."""
        # First login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "test_password_123",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["status"] == "ok"
        token = login_data["data"]["token"]

        # Logout
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_logout_no_token(self, client):
        """Test logout without token."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 401


class TestChangePasswordRoute:
    """Test change password endpoint."""

    def test_change_password_success(self, client, test_user):
        """Test successful password change."""
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "test_password_123",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["status"] == "ok"
        token = login_data["data"]["token"]

        # Change password
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "test_password_123",
                "new_password": "NewSecurePassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Verify new password works
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "NewSecurePassword123!",
            },
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client, test_user):
        """Test password change with wrong current password."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_user.email,
                "password": "test_password_123",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["status"] == "ok"
        token = login_data["data"]["token"]

        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrong_password",
                "new_password": "NewSecurePassword123!",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"

    def test_change_password_no_token(self, client):
        """Test password change without token."""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "old",
                "new_password": "new",
            },
        )
        assert response.status_code == 401


class TestForgotPasswordRoute:
    """Test forgot password endpoint."""

    def test_forgot_password_success(self, client, test_user):
        """Test successful forgot password request."""
        response = client.post(
            "/api/auth/forgot-password",
            json={
                "email": test_user.email,
            },
        )
        # Should return success even if email doesn't exist (security)
        assert response.status_code in [200, 202]
        data = response.json()
        assert data["status"] == "ok"

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/api/auth/forgot-password",
            json={
                "email": "nonexistent@example.com",
            },
        )
        # Should return success for security (don't reveal if email exists)
        assert response.status_code in [200, 202]


class TestResetPasswordRoute:
    """Test reset password endpoint."""

    def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "test@example.com",
                "reset_token": "invalid_token",
                "new_password": "NewPassword123!",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"

