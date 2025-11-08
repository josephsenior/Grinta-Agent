from unittest.mock import MagicMock, patch
from forge.core.config import LLMConfig
from forge.resolver.interfaces.github import GithubIssueHandler, GithubPRHandler
from forge.resolver.interfaces.issue import ReviewThread
from forge.resolver.interfaces.issue_definitions import ServiceContextIssue, ServiceContextPR


def test_get_converted_issues_initializes_review_comments():
    with patch("httpx.get") as mock_get:
        mock_issues_response = MagicMock()
        mock_issues_response.json.return_value = [{"number": 1, "title": "Test Issue", "body": "Test Body"}]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = []
        mock_get.side_effect = [mock_issues_response, mock_comments_response, mock_comments_response]
        llm_config = LLMConfig(model="test", api_key="test")
        handler = ServiceContextIssue(GithubIssueHandler("test-owner", "test-repo", "test-token"), llm_config)
        issues = handler.get_converted_issues(issue_numbers=[1])
        assert len(issues) == 1
        assert issues[0].review_comments is None
        assert issues[0].number == 1
        assert issues[0].title == "Test Issue"
        assert issues[0].body == "Test Body"
        assert issues[0].owner == "test-owner"
        assert issues[0].repo == "test-repo"


def test_get_converted_issues_handles_empty_body():
    with patch("httpx.get") as mock_get:
        mock_issues_response = MagicMock()
        mock_issues_response.json.return_value = [{"number": 1, "title": "Test Issue", "body": None}]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = []
        mock_get.side_effect = [mock_issues_response, mock_comments_response, mock_comments_response]
        llm_config = LLMConfig(model="test", api_key="test")
        handler = ServiceContextIssue(GithubIssueHandler("test-owner", "test-repo", "test-token"), llm_config)
        issues = handler.get_converted_issues(issue_numbers=[1])
        assert len(issues) == 1
        assert issues[0].body == ""
        assert issues[0].number == 1
        assert issues[0].title == "Test Issue"
        assert issues[0].owner == "test-owner"
        assert issues[0].repo == "test-repo"
        assert issues[0].review_comments is None


def test_pr_handler_get_converted_issues_with_comments():
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body fixes #1", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [{"body": "First comment"}, {"body": "Second comment"}]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"edges": []},
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_external_issue_response = MagicMock()
        mock_external_issue_response.json.return_value = {
            "body": "This is additional context from an externally referenced issue."
        }
        mock_get.side_effect = [
            mock_prs_response,
            mock_empty_response,
            mock_comments_response,
            mock_empty_response,
            mock_external_issue_response,
        ]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1])
            assert len(prs) == 1
            assert prs[0].thread_comments == ["First comment", "Second comment"]
            assert prs[0].number == 1
            assert prs[0].title == "Test PR"
            assert prs[0].body == "Test Body fixes #1"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"
            assert prs[0].closing_issues == ["This is additional context from an externally referenced issue."]


def test_get_issue_comments_with_specific_comment_id():
    with patch("httpx.get") as mock_get:
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"id": 123, "body": "First comment"},
            {"id": 456, "body": "Second comment"},
        ]
        mock_get.return_value = mock_comments_response
        llm_config = LLMConfig(model="test", api_key="test")
        handler = ServiceContextIssue(GithubIssueHandler("test-owner", "test-repo", "test-token"), llm_config)
        specific_comment = handler.get_issue_comments(issue_number=1, comment_id=123)
        assert specific_comment == ["First comment"]


def test_pr_handler_get_converted_issues_with_specific_thread_comment():
    specific_comment_id = 123
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"body": "First comment", "id": 123},
            {"body": "Second comment", "id": 124},
        ]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "review-thread-1",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [
                                                {
                                                    "fullDatabaseId": 121,
                                                    "body": "Specific review comment",
                                                    "path": "file1.txt",
                                                },
                                                {
                                                    "fullDatabaseId": 456,
                                                    "body": "Another review comment",
                                                    "path": "file2.txt",
                                                },
                                            ]
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_get.side_effect = [mock_prs_response, mock_empty_response, mock_comments_response, mock_empty_response]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1], comment_id=specific_comment_id)
            assert len(prs) == 1
            assert prs[0].thread_comments == ["First comment"]
            assert prs[0].review_comments == []
            assert prs[0].review_threads == []
            assert prs[0].number == 1
            assert prs[0].title == "Test PR"
            assert prs[0].body == "Test Body"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"


def test_pr_handler_get_converted_issues_with_specific_review_thread_comment():
    specific_comment_id = 123
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"body": "First comment", "id": 120},
            {"body": "Second comment", "id": 124},
        ]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "review-thread-1",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [
                                                {
                                                    "fullDatabaseId": specific_comment_id,
                                                    "body": "Specific review comment",
                                                    "path": "file1.txt",
                                                },
                                                {
                                                    "fullDatabaseId": 456,
                                                    "body": "Another review comment",
                                                    "path": "file1.txt",
                                                },
                                            ]
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_get.side_effect = [mock_prs_response, mock_empty_response, mock_comments_response, mock_empty_response]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1], comment_id=specific_comment_id)
            assert len(prs) == 1
            assert prs[0].thread_comments is None
            assert prs[0].review_comments == []
            assert len(prs[0].review_threads) == 1
            assert isinstance(prs[0].review_threads[0], ReviewThread)
            assert (
                prs[0].review_threads[0].comment
                == "Specific review comment\n---\nlatest feedback:\nAnother review comment\n"
            )
            assert prs[0].review_threads[0].files == ["file1.txt"]
            assert prs[0].number == 1
            assert prs[0].title == "Test PR"
            assert prs[0].body == "Test Body"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"


def test_pr_handler_get_converted_issues_with_specific_comment_and_issue_refs():
    specific_comment_id = 123
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR fixes #3", "body": "Test Body", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"body": "First comment", "id": 120},
            {"body": "Second comment", "id": 124},
        ]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "review-thread-1",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [
                                                {
                                                    "fullDatabaseId": specific_comment_id,
                                                    "body": "Specific review comment that references #6",
                                                    "path": "file1.txt",
                                                },
                                                {
                                                    "fullDatabaseId": 456,
                                                    "body": "Another review comment referencing #7",
                                                    "path": "file2.txt",
                                                },
                                            ]
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_external_issue_response_in_body = MagicMock()
        mock_external_issue_response_in_body.json.return_value = {"body": "External context #1."}
        mock_external_issue_response_review_thread = MagicMock()
        mock_external_issue_response_review_thread.json.return_value = {"body": "External context #2."}
        mock_get.side_effect = [
            mock_prs_response,
            mock_empty_response,
            mock_comments_response,
            mock_empty_response,
            mock_external_issue_response_in_body,
            mock_external_issue_response_review_thread,
        ]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1], comment_id=specific_comment_id)
            assert len(prs) == 1
            assert prs[0].thread_comments is None
            assert prs[0].review_comments == []
            assert len(prs[0].review_threads) == 1
            assert isinstance(prs[0].review_threads[0], ReviewThread)
            assert (
                prs[0].review_threads[0].comment
                == "Specific review comment that references #6\n---\nlatest feedback:\nAnother review comment referencing #7\n"
            )
            assert prs[0].closing_issues == ["External context #1.", "External context #2."]
            assert prs[0].number == 1
            assert prs[0].title == "Test PR fixes #3"
            assert prs[0].body == "Test Body"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"


def test_pr_handler_get_converted_issues_with_duplicate_issue_refs():
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body fixes #1", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"body": "First comment addressing #1"},
            {"body": "Second comment addressing #2"},
        ]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"edges": []},
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_external_issue_response_in_body = MagicMock()
        mock_external_issue_response_in_body.json.return_value = {"body": "External context #1."}
        mock_external_issue_response_in_comment = MagicMock()
        mock_external_issue_response_in_comment.json.return_value = {"body": "External context #2."}
        mock_get.side_effect = [
            mock_prs_response,
            mock_empty_response,
            mock_comments_response,
            mock_empty_response,
            mock_external_issue_response_in_body,
            mock_external_issue_response_in_comment,
        ]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1])
            assert len(prs) == 1
            assert prs[0].thread_comments == ["First comment addressing #1", "Second comment addressing #2"]
            assert prs[0].number == 1
            assert prs[0].title == "Test PR"
            assert prs[0].body == "Test Body fixes #1"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"
            assert prs[0].closing_issues == ["External context #1.", "External context #2."]


def test_pr_handler_filters_threads_without_matching_comment_id():
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = []
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "review-thread-1",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [
                                                {
                                                    "fullDatabaseId": 999,
                                                    "body": "Unrelated review comment",
                                                    "path": "file.txt",
                                                }
                                            ]
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_get.side_effect = [mock_prs_response, mock_empty_response, mock_comments_response, mock_empty_response]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), LLMConfig(model="test"))
            prs = handler.get_converted_issues(issue_numbers=[1], comment_id=123)
            assert len(prs) == 1
            assert prs[0].review_threads == []
            assert prs[0].thread_ids == []


def test_pr_handler_get_converted_issues_no_comment_id():
    with patch("httpx.get") as mock_get:
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [
            {"number": 1, "title": "Test PR", "body": "Test Body", "head": {"ref": "test-branch"}}
        ]
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {"body": "First comment", "id": 123},
            {"body": "Second comment", "id": 124},
        ]
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "closingIssuesReferences": {"edges": []},
                        "reviews": {"nodes": []},
                        "reviewThreads": {
                            "edges": [
                                {
                                    "node": {
                                        "id": "review-thread-1",
                                        "isResolved": False,
                                        "comments": {
                                            "nodes": [
                                                {
                                                    "fullDatabaseId": 121,
                                                    "body": "Specific review comment",
                                                    "path": "file1.txt",
                                                },
                                                {
                                                    "fullDatabaseId": 456,
                                                    "body": "Another review comment",
                                                    "path": "file2.txt",
                                                },
                                            ]
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            }
        }
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        mock_get.side_effect = [mock_prs_response, mock_empty_response, mock_comments_response, mock_empty_response]
        with patch("httpx.post") as mock_post:
            mock_post.return_value = mock_graphql_response
            llm_config = LLMConfig(model="test", api_key="test")
            handler = ServiceContextPR(GithubPRHandler("test-owner", "test-repo", "test-token"), llm_config)
            prs = handler.get_converted_issues(issue_numbers=[1])
            assert len(prs) == 1
            assert prs[0].thread_comments == ["First comment", "Second comment"]
            assert prs[0].number == 1
            assert prs[0].title == "Test PR"
            assert prs[0].body == "Test Body"
            assert prs[0].owner == "test-owner"
            assert prs[0].repo == "test-repo"
            assert prs[0].head_branch == "test-branch"
