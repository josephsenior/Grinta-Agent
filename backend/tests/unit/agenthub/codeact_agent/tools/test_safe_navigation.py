from __future__ import annotations

from forge.agenthub.codeact_agent.tools.safe_navigation import (
    create_safe_navigation_browser_code,
    safe_goto_localhost,
)


def test_safe_goto_localhost_includes_wait_code():
    code = safe_goto_localhost("http://localhost:8080", max_wait=5, check_interval=0.5)
    assert "wait_for_server_ready" in code
    assert 'goto("http://localhost:8080")' in code
    assert "max_wait = 5" in code
    assert "check_interval = 0.5" in code


def test_safe_goto_localhost_non_local():
    code = safe_goto_localhost("https://example.com")
    assert code == "goto('https://example.com')"


def test_create_safe_navigation_browser_code_localhost_with_actions():
    code = create_safe_navigation_browser_code(
        "http://localhost:3000", additional_actions="noop(1000)"
    )
    assert "wait_for_server_ready" in code
    assert code.rstrip().endswith("noop(1000)")


def test_create_safe_navigation_browser_code_remote():
    code = create_safe_navigation_browser_code(
        "https://openai.com", additional_actions="click(selector)"
    )
    assert code.startswith("goto('https://openai.com')")
    assert "wait_for_server_ready" not in code
    assert "click(selector)" in code


def test_create_safe_navigation_without_extra_actions():
    code = create_safe_navigation_browser_code("https://example.org")
    assert code.strip() == "goto('https://example.org')"
