"""E2E: Web browsing catchphrase test (Issue #10378).

Goal: In a new conversation, instruct the agent to browse to all-hands.dev and
return the page's main catchphrase. We assert that a browsing action/observation
is emitted and that the agent returns the expected catchphrase.

This follows existing patterns from tests/e2e/test_conversation.py and
uses robust waits and screenshots.
"""

import os
import re
import time
from playwright.sync_api import Page, expect

CATCHPHRASE_PATTERNS = ["\\bcode\\s*less\\W*make\\s*more\\b"]


def _screenshot(page: Page, name: str) -> None:
    os.makedirs("test-results", exist_ok=True)
    page.screenshot(path=f"test-results/browse_{name}.png")


def _wait_for_home_and_repo_selection(page: Page) -> None:
    home_screen = page.locator('[data-testid="home-screen"]')
    expect(home_screen).to_be_visible(timeout=30000)
    repo_dropdown = page.locator('[data-testid="repo-dropdown"]')
    expect(repo_dropdown).to_be_visible(timeout=30000)
    repo_dropdown.click()
    page.wait_for_timeout(1000)
    try:
        page.keyboard.press("Control+a")
        page.keyboard.type("Forge-agent/Forge")
    except Exception:
        pass
    page.wait_for_timeout(2000)
    option_selectors = [
        '[data-testid="repo-dropdown"] [role="option"]:has-text("Forge-agent/Forge")',
        '[data-testid="repo-dropdown"] [role="option"]:has-text("forge")',
        '[role="option"]:has-text("Forge-agent/Forge")',
        '[role="option"]:has-text("forge")',
        'div:has-text("Forge-agent/Forge"):not([id="aria-results"])',
        'div:has-text("forge"):not([id="aria-results"])',
    ]
    for selector in option_selectors:
        try:
            option = page.locator(selector).first
            if option.is_visible(timeout=3000):
                option.click(force=True)
                page.wait_for_timeout(1000)
                break
        except Exception:
            continue


def _launch_conversation(page: Page) -> None:
    launch_button = page.locator('[data-testid="repo-launch-button"]')
    expect(launch_button).to_be_visible(timeout=30000)
    start = time.time()
    while time.time() - start < 120:
        try:
            if not launch_button.is_disabled():
                break
        except Exception:
            pass
        page.wait_for_timeout(1000)
    try:
        if launch_button.is_disabled():
            page.evaluate(
                "\n                () => {\n                    const btn = document.querySelector('[data-testid=\"repo-launch-button\"]');\n                    if (btn) { btn.removeAttribute('disabled'); btn.click(); return true; }\n                    return false;\n                }\n                "
            )
        else:
            launch_button.click()
    except Exception:
        try:
            launch_button.focus()
            page.keyboard.press("Enter")
        except Exception:
            pass
    _screenshot(page, "after_launch_click")
    loading_selectors = [
        '[data-testid="loading-indicator"]',
        '[data-testid="loading-spinner"]',
        ".loading-spinner",
        ".spinner",
        'div:has-text("Loading...")',
        'div:has-text("Initializing...")',
        'div:has-text("Please wait...")',
    ]
    for selector in loading_selectors:
        try:
            loading = page.locator(selector)
            if loading.is_visible(timeout=3000):
                expect(loading).not_to_be_visible(timeout=120000)
                break
        except Exception:
            continue
    chat_input = page.locator('[data-testid="chat-input"]')
    expect(chat_input).to_be_visible(timeout=120000)
    page.wait_for_timeout(5000)


def _send_prompt(page: Page, prompt: str) -> None:
    selectors = ['[data-testid="chat-input"] textarea', '[data-testid="message-input"]', "textarea", "form textarea"]
    message_input = None
    for sel in selectors:
        try:
            el = page.locator(sel)
            if el.is_visible(timeout=5000):
                message_input = el
                break
        except Exception:
            continue
    if not message_input:
        raise AssertionError("Message input not found")
    message_input.fill(prompt)
    submit_selectors = [
        '[data-testid="chat-input"] button[type="submit"]',
        'button[type="submit"]',
        'button:has-text("Send")',
    ]
    submitted = False
    for sel in submit_selectors:
        try:
            btn = page.locator(sel)
            if btn.is_visible(timeout=3000):
                start = time.time()
                while time.time() - start < 60:
                    try:
                        if not btn.is_disabled():
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(1000)
                try:
                    btn.click()
                    submitted = True
                    break
                except Exception:
                    pass
        except Exception:
            continue
    if not submitted:
        message_input.press("Enter")
    _screenshot(page, "prompt_sent")


def _wait_for_browsing_event(page: Page, timeout_s: int = 240) -> None:
    start = time.time()
    browse_indicators = ["Interactive browsing in progress", "Browsing the web", "Browsing completed"]
    while time.time() - start < timeout_s:
        for text in browse_indicators:
            try:
                if page.get_by_text(text, exact=False).is_visible(timeout=2000):
                    _screenshot(page, "browsing_event_seen")
                    return
            except Exception:
                continue
        try:
            if page.get_by_text("Current URL:", exact=False).is_visible(timeout=1000):
                _screenshot(page, "browsing_url_seen")
                return
        except Exception:
            pass
        page.wait_for_timeout(2000)
    raise AssertionError("Did not observe a browsing action/observation in time")


def _wait_for_catchphrase(page: Page, timeout_s: int = 300) -> None:
    start = time.time()
    pattern = re.compile("|".join(CATCHPHRASE_PATTERNS), re.IGNORECASE)
    while time.time() - start < timeout_s:
        try:
            messages = page.locator('[data-testid="agent-message"]').all()
            for i, msg in enumerate(messages):
                try:
                    content = msg.text_content() or ""
                    if pattern.search(content):
                        _screenshot(page, f"catchphrase_found_{i}")
                        return
                except Exception:
                    continue
        except Exception:
            pass
        try:
            if page.get_by_text("Code Less, Make More", exact=False).is_visible(timeout=1000):
                _screenshot(page, "catchphrase_found_global")
                return
        except Exception:
            pass
        page.wait_for_timeout(2000)
    raise AssertionError("Agent did not return the expected catchphrase within time limit")


def test_browsing_catchphrase(page: Page):
    os.makedirs("test-results", exist_ok=True)
    page.goto("http://localhost:12000")
    page.wait_for_load_state("networkidle", timeout=30000)
    _screenshot(page, "initial_load")
    _wait_for_home_and_repo_selection(page)
    _screenshot(page, "home_ready")
    _launch_conversation(page)
    _screenshot(page, "conversation_loaded")
    prompt = "Use the web-browsing tool to navigate to https://www.all-hands.dev and tell me the main catchphrase displayed on the page. Do not answer from memory; perform the browsing action and respond with only the exact catchphrase."
    _send_prompt(page, prompt)
    _wait_for_browsing_event(page)
    _wait_for_catchphrase(page)
    _screenshot(page, "final_state")
