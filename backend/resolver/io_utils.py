"""Utility helpers for loading resolver outputs from JSONL archives."""

import json
from collections.abc import Iterable

from backend.resolver.interfaces.issue import Issue
from backend.resolver.resolver_output import ResolverOutput


def _deserialize_resolver_output(data: dict) -> ResolverOutput:
    """Convert a JSON dictionary into a ResolverOutput instance."""
    issue_payload = data.get("issue") or {}
    issue = Issue(**issue_payload)

    return ResolverOutput(
        issue=issue,
        issue_type=data.get("issue_type", ""),
        instruction=data.get("instruction", ""),
        base_commit=data.get("base_commit") or "",
        git_patch=data.get("git_patch") or "",
        history=data.get("history", []),
        metrics=data.get("metrics"),
        success=bool(data.get("success", False)),
        comment_success=data.get("comment_success"),
        result_explanation=data.get("result_explanation", ""),
        error=data.get("error"),
    )


def load_all_resolver_outputs(output_jsonl: str) -> Iterable[ResolverOutput]:
    """Load all resolver outputs from a JSONL file.

    Args:
        output_jsonl: Path to the JSONL file containing resolver outputs.

    Yields:
        ResolverOutput: Each resolver output from the file.

    """
    with open(output_jsonl, encoding="utf-8") as f:
        for line in f:
            yield _deserialize_resolver_output(json.loads(line))


def load_single_resolver_output(output_jsonl: str, issue_number: int) -> ResolverOutput:
    """Load a single resolver output by issue number from a JSONL file.

    Args:
        output_jsonl: Path to the JSONL file containing resolver outputs.
        issue_number: The issue number to search for.

    Returns:
        ResolverOutput: The resolver output for the specified issue number.

    Raises:
        ValueError: If the issue number is not found in the file.

    """
    for resolver_output in load_all_resolver_outputs(output_jsonl):
        if resolver_output.issue.number == issue_number:
            return resolver_output
    msg = f"Issue number {issue_number} not found in {output_jsonl}"
    raise ValueError(msg)
