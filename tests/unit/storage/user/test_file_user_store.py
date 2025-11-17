"""Tests for file-based user store."""
import pytest
import tempfile
import shutil
import os
from forge.storage.user.file_user_store import FileUserStore
from forge.storage.data_models.user import User
from forge.server.utils.password import hash_password
from forge.server.middleware.auth import UserRole


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for user storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def user_store(temp_storage_dir):
    """Create a FileUserStore instance with temporary storage."""
    return FileUserStore(storage_path=temp_storage_dir)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("test_password_123"),
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )


class TestFileUserStore:
    """Test FileUserStore operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_store, sample_user_data):
        """Test creating a new user."""
        user = await user_store.create_user(sample_user_data)
        assert user.id is not None
        assert user.email == sample_user_data.email
        assert user.username == sample_user_data.username
        assert user.role == sample_user_data.role
        assert user.is_active == sample_user_data.is_active
        assert user.email_verified == sample_user_data.email_verified
        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_store, sample_user_data):
        """Test retrieving a user by ID."""
        created_user = await user_store.create_user(sample_user_data)
        retrieved_user = await user_store.get_user_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_store):
        """Test retrieving a non-existent user."""
        user = await user_store.get_user_by_id("nonexistent_id")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_store, sample_user_data):
        """Test retrieving a user by email."""
        created_user = await user_store.create_user(sample_user_data)
        retrieved_user = await user_store.get_user_by_email(sample_user_data.email)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == sample_user_data.email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_store):
        """Test retrieving a user by non-existent email."""
        user = await user_store.get_user_by_email("nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_store, sample_user_data):
        """Test retrieving a user by username."""
        created_user = await user_store.create_user(sample_user_data)
        retrieved_user = await user_store.get_user_by_username(sample_user_data.username)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == sample_user_data.username

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, user_store):
        """Test retrieving a user by non-existent username."""
        user = await user_store.get_user_by_username("nonexistent_user")
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user(self, user_store, sample_user_data):
        """Test updating a user."""
        created_user = await user_store.create_user(sample_user_data)
        created_user.username = "updated_username"
        created_user.is_active = False
        created_user.email_verified = True
        updated_user = await user_store.update_user(created_user)
        assert updated_user.username == "updated_username"
        assert updated_user.is_active is False
        assert updated_user.email_verified is True
        assert updated_user.id == created_user.id
        assert updated_user.email == created_user.email  # Email should not change

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_store):
        """Test updating a non-existent user."""
        fake_user = User(
            id="nonexistent_id",
            email="fake@example.com",
            username="fake",
            password_hash="hash",
        )
        with pytest.raises(ValueError, match="not found"):
            await user_store.update_user(fake_user)

    @pytest.mark.asyncio
    async def test_delete_user(self, user_store, sample_user_data):
        """Test deleting a user."""
        created_user = await user_store.create_user(sample_user_data)
        result = await user_store.delete_user(created_user.id)
        assert result is True
        deleted_user = await user_store.get_user_by_id(created_user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_store):
        """Test deleting a non-existent user."""
        result = await user_store.delete_user("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_users(self, user_store):
        """Test listing all users."""
        # Create multiple users
        users = []
        for i in range(5):
            user_data = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password_hash=hash_password(f"password{i}"),
                role=UserRole.USER,
                is_active=True,
                email_verified=False,
            )
            created = await user_store.create_user(user_data)
            users.append(created)

        all_users = await user_store.list_users()
        assert len(all_users) == 5
        user_ids = {user.id for user in all_users}
        assert user_ids == {user.id for user in users}

    @pytest.mark.asyncio
    async def test_list_users_empty(self, user_store):
        """Test listing users when store is empty."""
        users = await user_store.list_users()
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_duplicate_email(self, user_store, sample_user_data):
        """Test that duplicate emails are not allowed."""
        await user_store.create_user(sample_user_data)
        duplicate_user = User(
            email=sample_user_data.email,
            username="different_user",
            password_hash=hash_password("password"),
            role=UserRole.USER,
        )
        with pytest.raises(ValueError, match="email.*already exists"):
            await user_store.create_user(duplicate_user)

    @pytest.mark.asyncio
    async def test_duplicate_username(self, user_store, sample_user_data):
        """Test that duplicate usernames are not allowed."""
        await user_store.create_user(sample_user_data)
        duplicate_user = User(
            email="different@example.com",
            username=sample_user_data.username,
            password_hash=hash_password("password"),
            role=UserRole.USER,
        )
        with pytest.raises(ValueError, match="username.*already exists"):
            await user_store.create_user(duplicate_user)

    @pytest.mark.asyncio
    async def test_persistence(self, temp_storage_dir, sample_user_data):
        """Test that users persist across store instances."""
        # Create user with first store instance
        store1 = FileUserStore(storage_path=temp_storage_dir)
        created_user = await store1.create_user(sample_user_data)

        # Create new store instance with same storage path
        store2 = FileUserStore(storage_path=temp_storage_dir)
        retrieved_user = await store2.get_user_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    @pytest.mark.asyncio
    async def test_user_roles(self, user_store):
        """Test different user roles."""
        roles = [UserRole.USER, UserRole.ADMIN, UserRole.SERVICE]
        for role in roles:
            user_data = User(
                email=f"{role.value}@example.com",
                username=role.value,
                password_hash=hash_password("password"),
                role=role,
                is_active=True,
                email_verified=False,
            )
            user = await user_store.create_user(user_data)
            assert user.role == role

    @pytest.mark.asyncio
    async def test_user_inactive(self, user_store):
        """Test inactive user."""
        user_data = User(
            email="inactive@example.com",
            username="inactive",
            password_hash=hash_password("password"),
            role=UserRole.USER,
            is_active=False,
        )
        user = await user_store.create_user(user_data)
        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_update_password_hash(self, user_store, sample_user_data):
        """Test updating password hash."""
        created_user = await user_store.create_user(sample_user_data)
        created_user.password_hash = hash_password("new_password_123")
        updated_user = await user_store.update_user(created_user)
        assert updated_user.password_hash == created_user.password_hash
