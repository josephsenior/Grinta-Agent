from openhands.resolver.utils import extract_issue_references


def test_extract_issue_references():
    assert extract_issue_references("Fixes #123") == [123]
    assert extract_issue_references("Fixes #123, #456") == [123, 456]
    assert extract_issue_references(
        "\n    Here's a code block:\n    ```python\n    # This is a comment with #123\n    def func():\n        pass  # Another #456\n    ```\n    But this #789 should be extracted\n    "
    ) == [789]
    assert extract_issue_references("This `#123` should be ignored but #456 should be extracted") == [456]
    assert extract_issue_references("This `#123` should be ignored but #456 should be extracted") == [456]
    assert extract_issue_references("Check http://example.com/#123 but #456 should be extracted") == [456]
    assert extract_issue_references("Check http://example.com/#123 but #456 should be extracted") == [456]
    assert extract_issue_references("[Link to #123](http://example.com) and #456") == [123, 456]
    assert extract_issue_references("[Link to #123](http://example.com) and #456") == [123, 456]
    assert extract_issue_references("Issue #123 is fixed and #456 is pending") == [123, 456]
    assert extract_issue_references("Issue #123 is fixed and #456 is pending") == [123, 456]
