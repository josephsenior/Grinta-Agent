"""Tests for pagination utilities."""
import pytest
from forge.server.utils.pagination import (
    PaginationParams,
    PaginatedResponse,
    parse_pagination_params,
    OffsetPaginationParams,
    CursorPaginationParams,
)


class TestPaginationParams:
    """Test PaginationParams."""

    def test_pagination_params_defaults(self):
        """Test default pagination parameters."""
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 20
        assert params.cursor is None

    def test_pagination_params_custom(self):
        """Test custom pagination parameters."""
        params = PaginationParams(page=2, limit=50, cursor="abc123")
        assert params.page == 2
        assert params.limit == 50
        assert params.cursor == "abc123"

    def test_pagination_params_offset(self):
        """Test offset calculation."""
        params = PaginationParams(page=3, limit=10)
        assert params.offset == 20  # (3-1) * 10

    def test_pagination_params_validation(self):
        """Test pagination parameter validation."""
        # Page < 1 should be set to 1
        params = PaginationParams(page=0, limit=10)
        assert params.page == 1

        # Limit < 1 should be set to 20
        params = PaginationParams(page=1, limit=0)
        assert params.limit == 20

        # Limit > max_limit should be capped
        params = PaginationParams(page=1, limit=200, max_limit=100)
        assert params.limit == 100


class TestPaginatedResponse:
    """Test PaginatedResponse."""

    def test_paginated_response_create(self):
        """Test creating paginated response."""
        items = list(range(10))
        response = PaginatedResponse.create(
            items=items,
            page=1,
            limit=10,
            total=100,
        )
        assert len(response.data) == 10
        assert response.pagination["page"] == 1
        assert response.pagination["limit"] == 10
        assert response.pagination["total"] == 100
        assert response.pagination["total_pages"] == 10
        assert response.pagination["has_more"] is True

    def test_paginated_response_last_page(self):
        """Test paginated response on last page."""
        items = list(range(5))
        response = PaginatedResponse.create(
            items=items,
            page=10,
            limit=10,
            total=95,
        )
        assert len(response.data) == 5
        assert response.pagination["has_more"] is False
        assert response.pagination["total_pages"] == 10

    def test_paginated_response_with_cursor(self):
        """Test paginated response with cursor."""
        items = list(range(10))
        response = PaginatedResponse.create(
            items=items,
            page=1,
            limit=10,
            next_cursor="next_page_token",
        )
        assert response.pagination["next_cursor"] == "next_page_token"

    def test_paginated_response_empty(self):
        """Test paginated response with empty items."""
        response = PaginatedResponse.create(
            items=[],
            page=1,
            limit=10,
            total=0,
        )
        assert len(response.data) == 0
        assert response.pagination["total"] == 0
        assert response.pagination["has_more"] is False


class TestParsePaginationParams:
    """Test parse_pagination_params."""

    def test_parse_defaults(self):
        """Test parsing with defaults."""
        params = parse_pagination_params()
        assert params.page == 1
        assert params.limit == 20
        assert params.cursor is None

    def test_parse_custom(self):
        """Test parsing with custom values."""
        params = parse_pagination_params(page=3, limit=50, cursor="token123")
        assert params.page == 3
        assert params.limit == 50
        assert params.cursor == "token123"


class TestOffsetPaginationParams:
    """Test OffsetPaginationParams."""

    def test_offset_calculation(self):
        """Test offset calculation."""
        params = OffsetPaginationParams(page=5, limit=20)
        assert params.offset == 80  # (5-1) * 20

    def test_offset_first_page(self):
        """Test offset on first page."""
        params = OffsetPaginationParams(page=1, limit=10)
        assert params.offset == 0

