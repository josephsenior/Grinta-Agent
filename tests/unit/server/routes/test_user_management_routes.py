"""Tests for user management routes (admin only)."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch
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
    with patch.dict(os.environ, {
        "USER_STORAGE_PATH": temp_storage_dir,
        "AUTH_ENABLED": "true",
        "JWT_SECRET": "test_secret_key_for_testing_only",
        "JWT_ALGORITHM": "HS256",
        "AUTH_VERIFY_USER_ACTIVE": "false"  # Disable user verification in tests for performance
    }):
        # Reset the global user store instance to use the temp directory
        import forge.storage.user.file_user_store as user_store_module
        user_store_module._user_store_instance = None
        yield app
        # Cleanup
        user_store_module._user_store_instance = None


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def user_store(temp_storage_dir):
    """Create a FileUserStore instance using get_user_store to ensure consistency."""
    # Set environment variable for user store
    with patch.dict(os.environ, {"USER_STORAGE_PATH": temp_storage_dir}):
        # Reset the global instance to ensure we get a fresh one
        from forge.storage.user.file_user_store import _user_store_instance
        import forge.storage.user.file_user_store as user_store_module
        user_store_module._user_store_instance = None
        store = get_user_store()
        yield store
        # Cleanup - reset instance but keep environment variable set
        user_store_module._user_store_instance = None


@pytest.fixture
def admin_user(user_store):
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin_password_123"),
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    return asyncio.run(user_store.create_user(user))


@pytest.fixture
def regular_user(user_store):
    """Create a regular user."""
    user = User(
        email="user@example.com",
        username="user",
        password_hash=hash_password("user_password_123"),
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )
    return asyncio.run(user_store.create_user(user))


@pytest.fixture
def admin_token(client, admin_user):
    """Get admin authentication token."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": admin_user.email,
            "password": "admin_password_123",
        },
    )
    assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
    login_data = response.json()
    assert login_data["status"] == "ok", f"Login response status not ok: {login_data}"
    assert "data" in login_data, f"Login response missing data: {login_data}"
    assert "token" in login_data["data"], f"Login response missing token: {login_data}"
    return login_data["data"]["token"]


@pytest.fixture
def user_token(client, regular_user):
    """Get regular user authentication token."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": regular_user.email,
            "password": "user_password_123",
        },
    )
    assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
    login_data = response.json()
    assert login_data["status"] == "ok", f"Login response status not ok: {login_data}"
    assert "data" in login_data, f"Login response missing data: {login_data}"
    assert "token" in login_data["data"], f"Login response missing token: {login_data}"
    return login_data["data"]["token"]


class TestListUsersRoute:
    """Test list users endpoint."""

    def test_list_users_admin(self, client, admin_token, regular_user, admin_user):
        """Test listing users as admin."""
        response = client.get(
            "/api/users/",  # Use trailing slash to match route definition
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"page": 1, "limit": 20},
            follow_redirects=True,  # Follow redirects if any
        )
        assert response.status_code == 200
        data = response.json()
        # PaginatedResponse returns data and pagination keys directly
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 2  # At least admin and regular user
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 20

    def test_list_users_non_admin(self, client, user_token):
        """Test listing users as non-admin."""
        response = client.get(
            "/api/users/",  # Use trailing slash to match route definition
            headers={"Authorization": f"Bearer {user_token}"},
            follow_redirects=True,
        )
        assert response.status_code == 403  # Forbidden

    def test_list_users_no_auth(self, client):
        """Test listing users without authentication."""
        response = client.get("/api/users/", follow_redirects=True)
        assert response.status_code == 401

    def test_list_users_pagination(self, client, admin_token, user_store):
        """Test pagination in list users."""
        # Create multiple users
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash=hash_password(f"password{i}"),
                role=UserRole.USER,
                is_active=True,
                email_verified=False,
            )
            asyncio.run(user_store.create_user(user))

        # First page
        response = client.get(
            "/api/users/",  # Use trailing slash to match route definition
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"page": 1, "limit": 3},
            follow_redirects=True,
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 3
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 3


class TestGetUserByIdRoute:
    """Test get user by ID endpoint."""

    def test_get_user_by_id_admin(self, client, admin_token, regular_user):
        """Test getting user by ID as admin."""
        response = client.get(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["user"]["id"] == regular_user.id
        assert data["data"]["user"]["email"] == regular_user.email

    def test_get_user_by_id_non_admin(self, client, user_token, regular_user):
        """Test getting user by ID as non-admin."""
        response = client.get(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403  # Forbidden

    def test_get_user_by_id_not_found(self, client, admin_token):
        """Test getting non-existent user."""
        response = client.get(
            "/api/users/nonexistent_id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_get_user_by_id_no_auth(self, client, regular_user):
        """Test getting user without authentication."""
        response = client.get(f"/api/users/{regular_user.id}")
        assert response.status_code == 401


class TestUpdateUserRoute:
    """Test update user endpoint."""

    def test_update_user_admin(self, client, admin_token, regular_user):
        """Test updating user as admin."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "updated_username",
                "is_active": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["user"]["username"] == "updated_username"
        assert data["data"]["user"]["is_active"] is False

    def test_update_user_role(self, client, admin_token, regular_user):
        """Test updating user role as admin."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "role": "admin",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["user"]["role"] == "admin"

    def test_update_user_non_admin(self, client, user_token, regular_user):
        """Test updating user as non-admin."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "username": "updated_username",
            },
        )
        assert response.status_code == 403  # Forbidden

    def test_update_user_not_found(self, client, admin_token):
        """Test updating non-existent user."""
        response = client.patch(
            "/api/users/nonexistent_id",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "updated_username",
            },
        )
        assert response.status_code == 404

    def test_update_user_no_auth(self, client, regular_user):
        """Test updating user without authentication."""
        response = client.patch(
            f"/api/users/{regular_user.id}",
            json={
                "username": "updated_username",
            },
        )
        assert response.status_code == 401


class TestDeleteUserRoute:
    """Test delete user endpoint."""

    def test_delete_user_admin(self, client, admin_token, user_store):
        """Test deleting user as admin."""
        # Create a user to delete
        user_to_delete = User(
            email="todelete@example.com",
            username="todelete",
            password_hash=hash_password("password123"),
            role=UserRole.USER,
            is_active=True,
            email_verified=False,
        )
        created_user = asyncio.run(user_store.create_user(user_to_delete))

        response = client.delete(
            f"/api/users/{created_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Verify user is deleted
        response = client.get(
            f"/api/users/{created_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_user_non_admin(self, client, user_token, regular_user):
        """Test deleting user as non-admin."""
        response = client.delete(
            f"/api/users/{regular_user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403  # Forbidden

    def test_delete_user_not_found(self, client, admin_token):
        """Test deleting non-existent user."""
        response = client.delete(
            "/api/users/nonexistent_id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_user_no_auth(self, client, regular_user):
        """Test deleting user without authentication."""
        response = client.delete(f"/api/users/{regular_user.id}")
        assert response.status_code == 401

    def test_delete_own_account(self, client, admin_token, admin_user):
        """Test admin cannot delete their own account."""
        response = client.delete(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Should either prevent deletion or return error
        assert response.status_code in [400, 403, 422]
