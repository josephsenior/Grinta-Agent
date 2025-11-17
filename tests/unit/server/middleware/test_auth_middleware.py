"""Tests for authentication middleware."""
import pytest
import asyncio
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from forge.server.middleware.auth import AuthMiddleware, UserRole
from forge.storage.user.file_user_store import FileUserStore
from forge.storage.data_models.user import User
from forge.server.utils.password import hash_password
import tempfile
import shutil
import os
import jwt


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for user storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_app(temp_storage_dir):
    """Create FastAPI app with auth middleware."""
    with patch.dict(os.environ, {
        "USER_STORAGE_PATH": temp_storage_dir,
        "AUTH_ENABLED": "true",
        "JWT_SECRET": "test_secret_key_for_testing_only",
        "JWT_ALGORITHM": "HS256",
    }):
        # Reset the global user store instance
        from forge.storage.user.file_user_store import _user_store_instance
        global _user_store_instance
        _user_store_instance = None
        
        app = FastAPI()
        app.add_middleware(AuthMiddleware)
        
        @app.get("/protected")
        async def protected_route(request: Request):
            user_id = getattr(request.state, "user_id", None)
            return {"user_id": user_id, "message": "protected"}
        
        @app.get("/health")  # This is in PUBLIC_PATHS
        async def health_route():
            return {"status": "healthy"}
        
        @app.get("/api/auth/register")  # This is in PUBLIC_PATHS
        async def register_route():
            return {"message": "register"}
        
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
    return asyncio.run(user_store.create_user(user))


@pytest.fixture
def jwt_secret():
    """JWT secret for testing."""
    return "test_secret_key_for_testing_only"


@pytest.fixture
def valid_token(test_user, jwt_secret):
    """Create a valid JWT token using AuthMiddleware.create_token."""
    return AuthMiddleware.create_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role,
    )


class TestAuthMiddleware:
    """Test authentication middleware."""

    def test_public_route_no_auth(self, client):
        """Test that public routes don't require authentication."""
        # Test /health which is in PUBLIC_PATHS
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_public_auth_route(self, client):
        """Test that auth registration route is public."""
        response = client.get("/api/auth/register")
        assert response.status_code == 200

    def test_protected_route_no_token(self, client):
        """Test that protected routes require authentication."""
        response = client.get("/protected")
        assert response.status_code == 401

    def test_protected_route_valid_token(self, client, valid_token, test_user):
        """Test protected route with valid token."""
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["message"] == "protected"

    def test_protected_route_invalid_token(self, client):
        """Test protected route with invalid token."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_protected_route_expired_token(self, client, test_user, jwt_secret):
        """Test protected route with expired token."""
        import time
        payload = {
            "user_id": test_user.id,
            "email": test_user.email,
            "role": test_user.role.value,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        expired_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_protected_route_malformed_header(self, client):
        """Test protected route with malformed authorization header."""
        response = client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat"},
        )
        assert response.status_code == 401

    def test_protected_route_no_bearer(self, client, valid_token):
        """Test protected route without Bearer prefix."""
        response = client.get(
            "/protected",
            headers={"Authorization": valid_token},
        )
        assert response.status_code == 401

    def test_health_endpoint_public(self, client):
        """Test that health endpoint is public."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_inactive_user(self, client, user_store, jwt_secret):
        """Test that inactive users cannot access protected routes."""
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            password_hash=hash_password("password123"),
            role=UserRole.USER,
            is_active=False,
            email_verified=False,
        )
        created_user = asyncio.run(user_store.create_user(inactive_user))
        
        # Create token for inactive user
        token = AuthMiddleware.create_token(
            user_id=created_user.id,
            email=created_user.email,
            role=created_user.role,
        )
        
        with patch.dict(os.environ, {"AUTH_VERIFY_USER_ACTIVE": "true"}):
            response = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401

    def test_nonexistent_user(self, client, jwt_secret):
        """Test token with non-existent user ID."""
        token = AuthMiddleware.create_token(
            user_id="nonexistent_user_id",
            email="nonexistent@example.com",
            role=UserRole.USER,
        )
        
        with patch.dict(os.environ, {"AUTH_VERIFY_USER_ACTIVE": "true"}):
            response = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401
