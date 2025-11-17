"""Tests for authenticated user auth implementation."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from forge.server.user_auth.authenticated_user_auth import AuthenticatedUserAuth
from forge.storage.user.file_user_store import FileUserStore, get_user_store
from forge.server.utils.password import hash_password
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
def user_store(temp_storage_dir):
    """Create a FileUserStore instance."""
    return FileUserStore(storage_path=temp_storage_dir)


@pytest.fixture
def auth_impl():
    """Create AuthenticatedUserAuth instance."""
    return AuthenticatedUserAuth(user_id=None)


@pytest.fixture
def test_user(user_store):
    """Create a test user."""
    return user_store.create_user(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("test_password_123"),
        role="user",
        is_active=True,
        email_verified=False,
    )


class TestAuthenticatedUserAuth:
    """Test AuthenticatedUserAuth implementation."""

    @pytest.mark.asyncio
    async def test_get_user_id(self, auth_impl):
        """Test getting user ID."""
        auth_impl.user_id = "test_user_id"
        user_id = await auth_impl.get_user_id()
        assert user_id == "test_user_id"

    @pytest.mark.asyncio
    async def test_get_user_id_none(self, auth_impl):
        """Test getting user ID when not set."""
        auth_impl.user_id = None
        user_id = await auth_impl.get_user_id()
        assert user_id is None

    @pytest.mark.asyncio
    async def test_get_user_email(self, auth_impl, test_user, temp_storage_dir):
        """Test getting user email."""
        with patch.dict(os.environ, {"USER_STORAGE_PATH": temp_storage_dir}):
            auth_impl.user_id = test_user.id
            email = await auth_impl.get_user_email()
            assert email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_email_no_user_id(self, auth_impl):
        """Test getting user email when user_id is None."""
        auth_impl.user_id = None
        email = await auth_impl.get_user_email()
        assert email is None

    @pytest.mark.asyncio
    async def test_get_user_email_nonexistent_user(self, auth_impl, temp_storage_dir):
        """Test getting user email for non-existent user."""
        with patch.dict(os.environ, {"USER_STORAGE_PATH": temp_storage_dir}):
            auth_impl.user_id = "nonexistent_id"
            email = await auth_impl.get_user_email()
            assert email is None

    @pytest.mark.asyncio
    async def test_get_access_token(self, auth_impl):
        """Test getting access token."""
        token = await auth_impl.get_access_token()
        assert token is None  # Token is handled by middleware

    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test creating instance from request."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user_id"
        
        instance = await AuthenticatedUserAuth.get_instance(mock_request)
        assert isinstance(instance, AuthenticatedUserAuth)
        assert instance.user_id == "test_user_id"

    @pytest.mark.asyncio
    async def test_get_instance_no_user_id(self):
        """Test creating instance when user_id is not in request state."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        # Use hasattr to check if attribute exists
        if hasattr(mock_request.state, 'user_id'):
            delattr(mock_request.state, 'user_id')
        
        instance = await AuthenticatedUserAuth.get_instance(mock_request)
        assert isinstance(instance, AuthenticatedUserAuth)
        assert instance.user_id is None
