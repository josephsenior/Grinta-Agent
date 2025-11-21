from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from forge.integrations.provider import ProviderHandler, ProviderToken
from forge.integrations.service_types import ProviderType
from forge.server.data_models.conversation_info import ConversationInfo
from forge.server.data_models.conversation_info_result_set import (
    ConversationInfoResultSet,
)
from forge.server.routes.manage_conversations import (
    get_microagent_management_conversations,
)
from forge.storage.conversation.conversation_store import ConversationStore
from forge.storage.data_models.conversation_metadata import (
    ConversationMetadata,
    ConversationTrigger,
)


def _provider_tokens(
    token_value: str = "token_123",
) -> MappingProxyType[ProviderType, ProviderToken]:
    return MappingProxyType(
        {
            ProviderType.GITHUB: ProviderToken(
                token=SecretStr(token_value), host="github.com"
            ),
        }
    )


def _make_metadata(
    conversation_id: str,
    *,
    selected_repository: str | None,
    pr_numbers: list[int],
    trigger: ConversationTrigger = ConversationTrigger.MICROAGENT_MANAGEMENT,
    git_provider: ProviderType = ProviderType.GITHUB,
    user_id: str = "user",
    title: str = "Conversation",
    created_at: datetime | None = None,
    last_updated_at: datetime | None = None,
) -> ConversationMetadata:
    now = datetime.now(timezone.utc)
    return ConversationMetadata(
        conversation_id=conversation_id,
        user_id=user_id,
        title=title,
        selected_repository=selected_repository,
        git_provider=git_provider,
        pr_number=pr_numbers,
        trigger=trigger,
        created_at=created_at or now,
        last_updated_at=last_updated_at or created_at or now,
    )


def _info_from_metadata(metadata: ConversationMetadata) -> ConversationInfo:
    return ConversationInfo(
        conversation_id=metadata.conversation_id,
        title=metadata.title,
        last_updated_at=metadata.last_updated_at,
        selected_repository=metadata.selected_repository,
        git_provider=metadata.git_provider,
        trigger=metadata.trigger,
        pr_number=list(metadata.pr_number),
        created_at=metadata.created_at,
    )


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_success():
    """Test successful retrieval of microagent management conversations."""
    page_id = "test_page_123"
    limit = 10
    selected_repository = "owner/repo"
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository="owner/repo",
            pr_numbers=[123],
            user_id="user_1",
            title="Test Conversation 1",
        ),
        _make_metadata(
            "conv_2",
            selected_repository="owner/repo",
            pr_numbers=[456],
            user_id="user_2",
            title="Test Conversation 2",
        ),
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id="next_page_456")
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    mock_provider_handler.is_pr_open = AsyncMock(return_value=True)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[], next_page_id="next_page_456"
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository=selected_repository,
            page_id=page_id,
            limit=limit,
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert isinstance(result, ConversationInfoResultSet)
        assert result.next_page_id == "next_page_456"
        mock_conversation_store.search.assert_called_once_with(page_id, limit)
        mock_provider_handler.is_pr_open.assert_called()


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_no_results():
    """Test when no conversations match the criteria."""
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=[], next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    with (
        patch("forge.server.routes.manage_conversations.ProviderHandler"),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert isinstance(result, ConversationInfoResultSet)
        assert result.next_page_id is None
        assert len(result.results) == 0


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_filter_by_repository():
    """Test filtering conversations by selected repository."""
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository="owner/repo1",
            pr_numbers=[123],
            user_id="user_1",
            title="Test Conversation 1",
        ),
        _make_metadata(
            "conv_2",
            selected_repository="owner/repo2",
            pr_numbers=[456],
            user_id="user_2",
            title="Test Conversation 2",
        ),
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    mock_provider_handler.is_pr_open = AsyncMock(return_value=True)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[_info_from_metadata(mock_conversations[0])], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo1",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 1
        assert result.results[0].conversation_id == "conv_1"
        assert result.results[0].selected_repository == "owner/repo1"


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_filter_by_trigger():
    """Test that only microagent_management conversations are returned."""
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository="owner/repo",
            pr_numbers=[123],
            user_id="user_1",
            title="Test Conversation 1",
        ),
        _make_metadata(
            "conv_2",
            selected_repository="owner/repo",
            pr_numbers=[456],
            user_id="user_2",
            title="Test Conversation 2",
            trigger=ConversationTrigger.GUI,
        ),
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    mock_provider_handler.is_pr_open = AsyncMock(return_value=True)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[_info_from_metadata(mock_conversations[0])], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 1
        assert result.results[0].conversation_id == "conv_1"
        assert result.results[0].trigger == ConversationTrigger.MICROAGENT_MANAGEMENT


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_filter_inactive_pr():
    """Test filtering out conversations with inactive PRs."""
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository="owner/repo",
            pr_numbers=[123],
            user_id="user_1",
            title="Test Conversation 1",
        ),
        _make_metadata(
            "conv_2",
            selected_repository="owner/repo",
            pr_numbers=[456],
            user_id="user_2",
            title="Test Conversation 2",
        ),
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    mock_provider_handler.is_pr_open = AsyncMock(side_effect=[True, False])
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[_info_from_metadata(mock_conversations[0])], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 1
        assert result.results[0].conversation_id == "conv_1"
        assert mock_provider_handler.is_pr_open.call_count == 2


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_no_pr_number():
    """Test conversations without PR numbers are included."""
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository="owner/repo",
            pr_numbers=[],
            user_id="user_1",
            title="Test Conversation 1",
        )
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[_info_from_metadata(mock_conversations[0])], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 1
        assert result.results[0].conversation_id == "conv_1"
        mock_provider_handler.is_pr_open.assert_not_called()


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_no_repository():
    """Test conversations without selected repository are filtered out for PR checks."""
    mock_conversations = [
        _make_metadata(
            "conv_1",
            selected_repository=None,
            pr_numbers=[123],
            user_id="user_1",
            title="Test Conversation 1",
        )
    ]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 0
        mock_provider_handler.is_pr_open.assert_not_called()


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_age_filter():
    """Test that conversations are filtered by age."""
    now = datetime.now(timezone.utc)
    old_conversation = _make_metadata(
        "conv_old",
        selected_repository="owner/repo",
        pr_numbers=[123],
        user_id="user_1",
        title="Old Conversation",
        created_at=now.replace(year=now.year - 1),
        last_updated_at=now.replace(year=now.year - 1),
    )
    recent_conversation = _make_metadata(
        "conv_recent",
        selected_repository="owner/repo",
        pr_numbers=[456],
        user_id="user_2",
        title="Recent Conversation",
        created_at=now,
        last_updated_at=now,
    )
    mock_conversations = [old_conversation, recent_conversation]
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=mock_conversations, next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    mock_provider_handler = MagicMock(spec=ProviderHandler)
    mock_provider_handler.is_pr_open = AsyncMock(return_value=True)
    with (
        patch(
            "forge.server.routes.manage_conversations.ProviderHandler",
            return_value=mock_provider_handler,
        ),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[_info_from_metadata(recent_conversation)], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 3600
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        assert len(result.results) == 1
        assert result.results[0].conversation_id == "conv_recent"


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_pagination():
    """Test pagination functionality."""
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=[], next_page_id="next_page_789")
    )
    mock_provider_tokens = _provider_tokens()
    with (
        patch("forge.server.routes.manage_conversations.ProviderHandler"),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[], next_page_id="next_page_789"
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            page_id="test_page",
            limit=5,
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        mock_conversation_store.search.assert_called_once_with("test_page", 5)
        assert result.next_page_id == "next_page_789"


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_default_parameters():
    """Test default parameter values."""
    mock_conversation_store = MagicMock(spec=ConversationStore)
    mock_conversation_store.search = AsyncMock(
        return_value=MagicMock(results=[], next_page_id=None)
    )
    mock_provider_tokens = _provider_tokens()
    with (
        patch("forge.server.routes.manage_conversations.ProviderHandler"),
        patch(
            "forge.server.routes.manage_conversations._build_conversation_result_set"
        ) as mock_build_result,
        patch("forge.server.routes.manage_conversations.config") as mock_config,
    ):
        mock_build_result.return_value = ConversationInfoResultSet(
            results=[], next_page_id=None
        )
        mock_config.conversation_max_age_seconds = 86400
        result = await get_microagent_management_conversations(
            selected_repository="owner/repo",
            conversation_store=mock_conversation_store,
            provider_tokens=mock_provider_tokens,
        )
        mock_conversation_store.search.assert_called_once_with(None, 20)
        assert isinstance(result, ConversationInfoResultSet)
