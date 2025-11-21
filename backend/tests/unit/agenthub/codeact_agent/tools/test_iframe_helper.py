"""Tests for the iframe helper utilities."""

from __future__ import annotations

import pytest

from forge.agenthub.codeact_agent.tools import iframe_helper


def test_add_iframe_headers_updates_existing_dict() -> None:
    headers = {"X-Frame-Options": "DENY"}
    updated = iframe_helper.add_iframe_headers(headers)
    assert updated is headers  # modified in place
    assert updated["Content-Security-Policy"].startswith("frame-ancestors")
    # Header ends up removed to avoid conflicts
    assert "X-Frame-Options" not in updated


def test_add_iframe_headers_creates_new_dict() -> None:
    headers = iframe_helper.add_iframe_headers()
    assert "X-Frame-Options" not in headers


def test_config_helpers_return_expected_values() -> None:
    flask_cfg = iframe_helper.get_flask_iframe_config()
    assert flask_cfg["TEMPLATES_AUTO_RELOAD"] is True

    fastapi_cfg = iframe_helper.get_fastapi_iframe_config()
    assert fastapi_cfg["docs_url"] == "/docs"


def test_create_iframe_friendly_app_flask() -> None:
    content = iframe_helper.create_iframe_friendly_app("flask", port=5000)
    assert "Flask" in content
    assert "iframe-friendly headers" in content
    assert "Port: 5000" in content


def test_create_iframe_friendly_app_fastapi() -> None:
    content = iframe_helper.create_iframe_friendly_app("fastapi", port=9000)
    assert "FastAPI(**" in content
    assert "uvicorn.run" in content
    assert "Port: 9000" in content


def test_create_iframe_friendly_app_invalid_type() -> None:
    with pytest.raises(ValueError):
        iframe_helper.create_iframe_friendly_app("django")


def test_get_iframe_tips_contains_guidance() -> None:
    tips = iframe_helper.get_iframe_tips()
    assert "iframe-friendly" in tips
    assert "Testing" in tips
