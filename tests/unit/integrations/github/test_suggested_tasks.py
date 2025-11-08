from unittest.mock import AsyncMock
import pytest
from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import TaskType, User


@pytest.mark.asyncio
def _create_mock_user():
    """Create mock user for testing."""
    return User(id="1", login="test-user", avatar_url="https://example.com/avatar.jpg", name="Test User")


def _create_mock_graphql_response():
    """Create mock GraphQL response for testing."""
    return {
        "data": {
            "user": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 1,
                            "title": "PR with conflicts",
                            "repository": {"nameWithOwner": "test-org/repo-1"},
                            "mergeable": "CONFLICTING",
                            "commits": {"nodes": [{"commit": {"statusCheckRollup": None}}]},
                            "reviews": {"nodes": []},
                        },
                        {
                            "number": 2,
                            "title": "PR with failing checks",
                            "repository": {"nameWithOwner": "test-org/repo-1"},
                            "mergeable": "MERGEABLE",
                            "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "FAILURE"}}}]},
                            "reviews": {"nodes": []},
                        },
                        {
                            "number": 4,
                            "title": "PR with comments",
                            "repository": {"nameWithOwner": "test-user/repo-2"},
                            "mergeable": "MERGEABLE",
                            "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]},
                            "reviews": {"nodes": [{"state": "CHANGES_REQUESTED"}]},
                        },
                    ]
                },
                "issues": {
                    "nodes": [
                        {"number": 3, "title": "Assigned issue 1", "repository": {"nameWithOwner": "test-org/repo-1"}},
                        {"number": 5, "title": "Assigned issue 2", "repository": {"nameWithOwner": "test-user/repo-2"}},
                    ]
                },
            }
        }
    }


def _setup_mock_service():
    """Setup mock GitHub service."""
    service = GitHubService()
    service.get_user = AsyncMock(return_value=_create_mock_user())
    service.execute_graphql_query = AsyncMock(return_value=_create_mock_graphql_response())
    return service


def _validate_task_count_and_types(tasks):
    """Validate task count and types."""
    assert len(tasks) == 5
    task_types = [task.task_type for task in tasks]
    assert TaskType.MERGE_CONFLICTS in task_types
    assert TaskType.FAILING_CHECKS in task_types
    assert TaskType.UNRESOLVED_COMMENTS in task_types
    assert TaskType.OPEN_ISSUE in task_types
    assert len([t for t in task_types if t == TaskType.OPEN_ISSUE]) == 2


def _validate_task_repositories(tasks):
    """Validate task repositories."""
    repos = {task.repo for task in tasks}
    assert "test-org/repo-1" in repos
    assert "test-user/repo-2" in repos


def _validate_specific_tasks(tasks):
    """Validate specific task details."""
    # Validate merge conflicts task
    conflict_pr = next((t for t in tasks if t.task_type == TaskType.MERGE_CONFLICTS))
    assert conflict_pr.issue_number == 1
    assert conflict_pr.title == "PR with conflicts"

    # Validate failing checks task
    failing_pr = next((t for t in tasks if t.task_type == TaskType.FAILING_CHECKS))
    assert failing_pr.issue_number == 2
    assert failing_pr.title == "PR with failing checks"

    # Validate unresolved comments task
    commented_pr = next((t for t in tasks if t.task_type == TaskType.UNRESOLVED_COMMENTS))
    assert commented_pr.issue_number == 4
    assert commented_pr.title == "PR with comments"


async def test_get_suggested_tasks():
    """Test getting suggested tasks from GitHub."""
    # Setup mock service
    service = _setup_mock_service()

    # Get suggested tasks
    tasks = await service.get_suggested_tasks()

    # Validate results
    _validate_task_count_and_types(tasks)
    _validate_task_repositories(tasks)
    _validate_specific_tasks(tasks)
