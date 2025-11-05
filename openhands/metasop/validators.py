from __future__ import annotations

import json
from typing import Any

from json_repair import repair_json
from jsonschema import Draft7Validator


def _extract_first_json_snippet(text: str) -> str:
    """Best-effort extraction of the first JSON object/array from a text blob.

    - Strips Markdown code fences if present.
    - Locates the first top-level {...} or [...] block via bracket counting.
    Fallback: returns original text.

    Args:
        text: Text potentially containing JSON

    Returns:
        Extracted JSON string or original text
    """
    s = _strip_markdown_fences(text.strip())

    for opener, closer in (("{", "}"), ("[", "]")):
        extracted = _extract_bracket_block(s, opener, closer)
        if extracted:
            return extracted

    return text


def _strip_markdown_fences(s: str) -> str:
    """Strip markdown code fences from text.

    Args:
        s: Text with potential markdown fences

    Returns:
        Text with fences removed
    """
    if not s.startswith("```"):
        return s

    lines = s.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _extract_bracket_block(s: str, opener: str, closer: str) -> str | None:
    """Extract balanced bracket block from text.

    Args:
        s: Text to search
        opener: Opening bracket character
        closer: Closing bracket character

    Returns:
        Extracted block or None if not found
    """
    start = s.find(opener)
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return s[start: i + 1]

    return None


def validate_json(content: str, schema: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Validate a JSON string against a schema; attempt to repair if needed.

    Returns: (ok, data, error)
    """
    candidate = _extract_first_json_snippet(content)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        try:
            repaired = repair_json(candidate)
            data = json.loads(repaired)
        except Exception as e:
            return (False, None, f"JSON parse/repair failed: {e}")
    validator = Draft7Validator(schema)
    if errors := sorted(validator.iter_errors(data), key=lambda e: e.path):
        msg = "; ".join([f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors])
        return (False, None, f"Schema validation failed: {msg}")
    return (True, data, None)


def corrective_prompt_for_validation(error_msg: str, minimal_example: dict[str, Any]) -> str:
    return f"Your previous output did not match the required JSON schema.\nErrors: {error_msg}\nRespond with JSON ONLY that conforms to the schema.\nMinimal example: {
        json.dumps(
            minimal_example,
            ensure_ascii=False)}"
