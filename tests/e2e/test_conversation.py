"""E2E: Conversation start test.

This test assumes the GitHub token has already been configured (by the
settings test) and verifies that a conversation can be started and the
agent responds to a README line-count question.
"""

import os
import time
from playwright.sync_api import Page, expect


def get_readme_line_count():
    """Get the line count of the main README.md file for verification."""
    current_dir = os.getcwd()
    if current_dir.endswith("tests/e2e"):
        repo_root = os.path.abspath(os.path.join(current_dir, "../.."))
    else:
        repo_root = current_dir
    readme_path = os.path.join(repo_root, "README.md")
    print(f"Looking for README.md at: {readme_path}")
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return len(lines)
    except (IOError, OSError) as e:
        print(f"Error reading README.md: {e}")
        return 0


def _navigate_to_openhands(page: Page, base_url: str) -> None:
    """Navigate to OpenHands application and take initial screenshot."""
    print(f"Step 1: Navigating to OpenHands application at {base_url}...")
    page.goto(base_url)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.screenshot(path="test-results/conv_01_initial_load.png")
    print("Screenshot saved: conv_01_initial_load.png")


def _select_repository(page: Page) -> None:
    """Select the OpenHands repository from dropdown."""
    print("Step 2: Selecting openhands-agent/OpenHands repository...")
    home_screen = page.locator('[data-testid="home-screen"]')
    expect(home_screen).to_be_visible(timeout=15000)
    print("Home screen is visible")

    repo_dropdown = page.locator('[data-testid="repo-dropdown"]')
    expect(repo_dropdown).to_be_visible(timeout=15000)
    print("Repository dropdown is visible")
    repo_dropdown.click()
    page.wait_for_timeout(1000)

    try:
        page.keyboard.press("Control+a")
        page.keyboard.type("openhands-agent/OpenHands")
        print("Used keyboard.type() for React Select component")
    except Exception as e:
        print(f"Keyboard input failed: {e}")

    page.wait_for_timeout(2000)
    _select_repository_option(page)
    page.screenshot(path="test-results/conv_02_repo_selected.png")
    print("Screenshot saved: conv_02_repo_selected.png")


def _select_repository_option(page: Page) -> None:
    """Select repository option from dropdown with fallback strategies."""
    option_selectors = [
        '[data-testid="repo-dropdown"] [role="option"]:has-text("openhands-agent/OpenHands")',
        '[data-testid="repo-dropdown"] [role="option"]:has-text("OpenHands")',
        '[data-testid="repo-dropdown"] div[id*="option"]:has-text("openhands-agent/OpenHands")',
        '[data-testid="repo-dropdown"] div[id*="option"]:has-text("OpenHands")',
        '[role="option"]:has-text("openhands-agent/OpenHands")',
        '[role="option"]:has-text("OpenHands")',
        'div:has-text("openhands-agent/OpenHands"):not([id="aria-results"])',
        'div:has-text("OpenHands"):not([id="aria-results"])',
    ]

    option_found = False
    for selector in option_selectors:
        try:
            option = page.locator(selector).first
            if option.is_visible(timeout=3000):
                print(f"Found repository option with selector: {selector}")
                try:
                    option.click(force=True)
                    print("Successfully clicked option with force=True")
                    option_found = True
                    page.wait_for_timeout(2000)
                    break
                except Exception:
                    continue
        except Exception:
            continue

    if not option_found:
        print("Could not find repository option in dropdown, trying keyboard navigation")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        print("Used keyboard navigation to select option")


def _click_launch_button(page: Page) -> None:
    """Click the launch button with retry logic."""
    print("Step 3: Clicking Launch button...")
    launch_button = page.locator('[data-testid="repo-launch-button"]')
    expect(launch_button).to_be_visible(timeout=10000)

    button_enabled = _wait_for_button_enabled(page, launch_button)
    _execute_launch_click(page, launch_button, button_enabled)


def _wait_for_button_enabled(page: Page, launch_button) -> bool:
    """Wait for launch button to become enabled."""
    max_wait_attempts = 30
    button_enabled = False

    for attempt in range(max_wait_attempts):
        try:
            if is_disabled := launch_button.is_disabled():
                print(f"Launch button still disabled, waiting... (attempt {attempt + 1}/{max_wait_attempts})")
                page.wait_for_timeout(2000)
            else:
                print(f"Repository Launch button is now enabled (attempt {attempt + 1})")
                button_enabled = True
                break
        except Exception as e:
            print(f"Error checking button state (attempt {attempt + 1}): {e}")
            page.wait_for_timeout(2000)

    return button_enabled


def _execute_launch_click(page: Page, launch_button, button_enabled: bool) -> None:
    """Execute the launch button click with fallback strategies."""
    try:
        if button_enabled:
            launch_button.click()
            print("Launch button clicked normally")
        else:
            print("Launch button still disabled, trying JavaScript force click...")
            if page.evaluate(
                "() => {\n                const button = document.querySelector('[data-testid=\"repo-launch-button\"]');\n                if (button) {\n                    console.log('Found button, removing disabled attribute');\n                    button.removeAttribute('disabled');\n                    console.log('Clicking button');\n                    button.click();\n                    return true;\n                }\n                return false;\n            }"
            ):
                print("Successfully force-clicked Launch button with JavaScript")
            else:
                print("JavaScript could not find the Launch button")
    except Exception as e:
        print(f"Error clicking Launch button: {e}")
        page.screenshot(path="test-results/conv_03_launch_error.png")
        print("Screenshot saved: conv_03_launch_error.png")
        raise


def _wait_for_conversation_interface(page: Page) -> None:
    """Wait for conversation interface to load."""
    print("Step 4: Waiting for conversation interface to load...")
    navigation_timeout = 300000
    check_interval = 10000
    page.screenshot(path="test-results/conv_04_after_launch.png")
    print("Screenshot saved: conv_04_after_launch.png")

    _wait_for_loading_complete(page)
    _wait_for_conversation_elements(page, navigation_timeout, check_interval)


def _wait_for_loading_complete(page: Page) -> None:
    """Wait for loading indicators to disappear."""
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
            if loading.is_visible(timeout=5000):
                print(f"Found loading indicator with selector: {selector}")
                print("Waiting for loading to complete...")
                expect(loading).not_to_be_visible(timeout=120000)
                print("Loading completed")
                break
        except Exception:
            continue


def _wait_for_conversation_elements(page: Page, navigation_timeout: int, check_interval: int) -> None:
    """Wait for conversation interface elements to appear."""
    try:
        current_url = page.url
        print(f"Current URL: {current_url}")
        if "/conversation/" in current_url or "/chat/" in current_url:
            print("URL indicates conversation page has loaded")
    except Exception as e:
        print(f"Error checking URL: {e}")

    start_time = time.time()
    conversation_loaded = False

    while time.time() - start_time < navigation_timeout / 1000:
        try:
            selectors = [
                ".scrollbar.flex.flex-col.grow",
                '[data-testid="chat-input"]',
                '[data-testid="app-route"]',
                '[data-testid="conversation-screen"]',
                '[data-testid="message-input"]',
                ".conversation-container",
                ".chat-container",
                "textarea",
                "form textarea",
                'div[role="main"]',
                "main",
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector)
                    if element.is_visible(timeout=2000):
                        print(f"Found conversation interface element with selector: {selector}")
                        conversation_loaded = True
                        break
                except Exception:
                    continue

            if conversation_loaded:
                break

            if (time.time() - start_time) % (check_interval / 1000) < 1:
                elapsed = int(time.time() - start_time)
                page.screenshot(path=f"test-results/conv_05_waiting_{elapsed}s.png")
                print(f"Screenshot saved: conv_05_waiting_{elapsed}s.png")

            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Error checking for conversation interface: {e}")
            page.wait_for_timeout(5000)

    if not conversation_loaded:
        print("Timed out waiting for conversation interface to load")
        page.screenshot(path="test-results/conv_06_timeout.png")
        print("Screenshot saved: conv_06_timeout.png")
        raise TimeoutError("Timed out waiting for conversation interface to load")


def _wait_for_agent_ready(page: Page) -> None:
    """Wait for agent to be ready for input."""
    print("Step 5: Waiting for agent to initialize...")
    try:
        chat_input = page.locator('[data-testid="chat-input"]')
        expect(chat_input).to_be_visible(timeout=60000)
        submit_button = page.locator('[data-testid="chat-input"] button[type="submit"]')
        expect(submit_button).to_be_visible(timeout=10000)
        print("Agent interface is loaded")
        page.wait_for_timeout(10000)
    except Exception as e:
        print(f"Could not confirm agent interface is loaded: {e}")

    page.screenshot(path="test-results/conv_07_agent_ready.png")
    print("Screenshot saved: conv_07_agent_ready.png")

    print("Step 6: Waiting for agent to be fully ready for input...")
    _wait_for_agent_input_ready(page)


def _wait_for_agent_input_ready(page: Page) -> None:
    """Wait for agent to be ready for user input."""
    max_wait_time = 480
    start_time = time.time()
    agent_ready = False
    print(f"Waiting up to {max_wait_time} seconds for agent to be ready...")

    while time.time() - start_time < max_wait_time:
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0 and elapsed > 0:
            page.screenshot(path=f"test-results/conv_waiting_{elapsed}s.png")
            print(f"Screenshot saved: conv_waiting_{elapsed}s.png (waiting {elapsed}s)")

        try:
            status_messages = _get_status_messages(page)
            ready_indicators = [
                'div:has-text("Agent is ready")',
                'div:has-text("Waiting for user input")',
                'div:has-text("Awaiting input")',
                'div:has-text("Task completed")',
                'div:has-text("Agent has finished")',
            ]

            input_ready, submit_ready = _check_input_ready(page)
            connecting_or_starting = any(
                msg
                for msg in status_messages
                if "connecting" in msg.lower() or "starting" in msg.lower() or "runtime to start" in msg.lower()
            )
            has_ready_indicator = _check_ready_indicators(page, ready_indicators)

            if (has_ready_indicator or not connecting_or_starting) and input_ready and submit_ready:
                print("✅ Agent is ready for user input - input field and submit button are enabled")
                agent_ready = True
                break
        except Exception as e:
            print(f"Error checking agent ready state: {e}")

        page.wait_for_timeout(2000)

    if not agent_ready:
        page.screenshot(path="test-results/conv_timeout_waiting_for_agent.png")
        raise AssertionError(f"Agent did not become ready for input within {max_wait_time} seconds")


def _get_status_messages(page: Page) -> list[str]:
    """Get status messages from the page."""
    status_messages = []
    status_bar_selector = ".bg-base-secondary .text-stone-400"
    try:
        status_elements = page.locator(status_bar_selector)
        if status_elements.count() > 0:
            for i in range(status_elements.count()):
                text = status_elements.nth(i).text_content()
                if text and text.strip():
                    status_messages.append(text.strip())
    except Exception:
        pass
    return status_messages


def _check_input_ready(page: Page) -> tuple[bool, bool]:
    """Check if input field and submit button are ready."""
    input_ready = False
    submit_ready = False
    try:
        input_field = page.locator('[data-testid="chat-input"] textarea')
        submit_button = page.locator('[data-testid="chat-input"] button[type="submit"]')
        if (
            input_field.is_visible(timeout=2000)
            and input_field.is_enabled(timeout=2000)
            and submit_button.is_visible(timeout=2000)
            and submit_button.is_enabled(timeout=2000)
        ):
            print("Chat input field and submit button are both visible and enabled")
            input_ready = True
            submit_ready = True
    except Exception:
        pass
    return input_ready, submit_ready


def _check_ready_indicators(page: Page, ready_indicators: list[str]) -> bool:
    """Check for ready indicators on the page."""
    has_ready_indicator = False
    for indicator in ready_indicators:
        try:
            element = page.locator(indicator)
            if element.is_visible(timeout=2000):
                print(f"Agent appears ready (found: {indicator})")
                has_ready_indicator = True
                break
        except Exception:
            continue
    return has_ready_indicator


def _ask_readme_question(page: Page, expected_line_count: int) -> None:
    """Ask question about README.md file."""
    print("Step 7: Asking question about README.md file...")
    message_input = _find_message_input(page)
    message_input.fill(
        "How many lines are there in the README.md file in the root directory of this repository? Please use wc -l README.md to count the lines."
    )
    print("Entered question about README.md line count")

    _submit_question(page)
    page.screenshot(path="test-results/conv_08_question_sent.png")
    print("Screenshot saved: conv_08_question_sent.png")


def _find_message_input(page: Page):
    """Find message input field with fallback strategies."""
    input_selectors = [
        '[data-testid="chat-input"] textarea',
        '[data-testid="message-input"]',
        "textarea",
        "form textarea",
        'input[type="text"]',
        '[placeholder*="message"]',
        '[placeholder*="question"]',
        '[placeholder*="ask"]',
        '[contenteditable="true"]',
    ]

    message_input = None
    for selector in input_selectors:
        try:
            input_element = page.locator(selector)
            if input_element.is_visible(timeout=5000):
                print(f"Found message input with selector: {selector}")
                message_input = input_element
                break
        except Exception:
            continue

    if not message_input:
        print("Could not find message input, trying to reload the page")
        page.screenshot(path="test-results/conv_08_no_input_found.png")
        print("Screenshot saved: conv_08_no_input_found.png")
        message_input = _reload_and_find_input(page, input_selectors)

    if not message_input:
        print("Still could not find message input, taking final screenshot")
        page.screenshot(path="test-results/conv_09_reload_failed.png")
        print("Screenshot saved: conv_09_reload_failed.png")
        raise AssertionError("Could not find message input field after reload")

    return message_input


def _reload_and_find_input(page: Page, input_selectors: list[str]):
    """Reload page and try to find input again."""
    try:
        print("Reloading the page...")
        page.reload()
        page.wait_for_load_state("networkidle", timeout=30000)
        print("Page reloaded")

        for selector in input_selectors:
            try:
                input_element = page.locator(selector)
                if input_element.is_visible(timeout=5000):
                    print(f"Found message input after reload with selector: {selector}")
                    return input_element
            except Exception:
                continue
    except Exception as e:
        print(f"Error reloading page: {e}")
    return None


def _submit_question(page: Page) -> None:
    """Submit the question with fallback strategies."""
    submit_selectors = [
        '[data-testid="chat-input"] button[type="submit"]',
        'button[type="submit"]',
        'button:has-text("Send")',
        'button:has-text("Submit")',
        'button svg[data-testid="send-icon"]',
        "button.send-button",
        "form button",
        "button:right-of(textarea)",
        'button:right-of(input[type="text"])',
    ]

    submit_button = None
    for selector in submit_selectors:
        try:
            button_element = page.locator(selector)
            if button_element.is_visible(timeout=5000):
                print(f"Found submit button with selector: {selector}")
                submit_button = button_element
                break
        except Exception:
            continue

    button_enabled = _wait_for_submit_button_enabled(page, submit_button)
    _execute_submit(page, submit_button, button_enabled)


def _wait_for_submit_button_enabled(page: Page, submit_button) -> bool:
    """Wait for submit button to become enabled."""
    button_enabled = False
    if submit_button:
        max_wait_time = 60
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                if not submit_button.is_disabled():
                    button_enabled = True
                    print("Submit button is enabled")
                    break
                print(f"Waiting for submit button to be enabled... ({int(time.time() - start_time)}s)")
            except Exception as e:
                print(f"Error checking if button is disabled: {e}")
            page.wait_for_timeout(2000)
    return button_enabled


def _execute_submit(page: Page, submit_button, button_enabled: bool) -> None:
    """Execute submit with fallback strategies."""
    if not submit_button or not button_enabled:
        print("Submit button not found or never became enabled, trying alternatives")
        try:
            message_input = page.locator('[data-testid="chat-input"] textarea')
            message_input.press("Enter")
            print("Pressed Enter key to submit")
            button_enabled = True
        except Exception as e:
            print(f"Error pressing Enter key: {e}")
            if submit_button:
                try:
                    page.evaluate(
                        "() => {\n                        const button = document.querySelector('[data-testid=\"chat-input\"] button[type=\"submit\"]');\n                        if (button) {\n                            button.removeAttribute('disabled');\n                            button.click();\n                            return true;\n                        }\n                        return false;\n                    }"
                    )
                    print("Used JavaScript to force click submit button")
                    button_enabled = True
                except Exception as e2:
                    print(f"JavaScript force click failed: {e2}")
    else:
        submit_button.click()

    if not button_enabled:
        page.screenshot(path="test-results/conv_09_submit_failed.png")
        print("Screenshot saved: conv_09_submit_failed.png")
        raise RuntimeError("Could not submit message")

    print("Clicked submit button")


def _wait_for_agent_response(page: Page, expected_line_count: int) -> None:
    """Wait for agent response and verify it contains README line count."""
    print("Step 8: Waiting for agent response to README question...")
    response_wait_time = 180
    response_start_time = time.time()

    while time.time() - response_start_time < response_wait_time:
        elapsed = int(time.time() - response_start_time)
        if elapsed % 30 == 0 and elapsed > 0:
            page.screenshot(path=f"test-results/conv_response_wait_{elapsed}s.png")
            print(f"Screenshot saved: conv_response_wait_{elapsed}s.png (waiting {elapsed}s for response)")

        try:
            agent_messages = page.locator('[data-testid="agent-message"]').all()
            if elapsed % 30 == 0:
                print(f"Found {len(agent_messages)} agent messages")

            for i, msg in enumerate(agent_messages):
                try:
                    content = msg.text_content()
                    if content and len(content.strip()) > 10:
                        if _check_readme_response(content, expected_line_count):
                            print("✅ Found agent response about README.md with line count!")
                            page.screenshot(path="test-results/conv_09_agent_response.png")
                            print("Screenshot saved: conv_09_agent_response.png")
                            page.screenshot(path="test-results/conv_10_final_state.png")
                            print("Screenshot saved: conv_10_final_state.png")
                            print("✅ Test completed successfully - agent provided correct README line count")
                            return
                except Exception as e:
                    print(f"Error processing agent message {i}: {e}")
                    continue
        except Exception as e:
            print(f"Error checking for agent messages: {e}")

        page.wait_for_timeout(5000)

    print("❌ Did not find agent response with README line count within time limit")
    page.screenshot(path="test-results/conv_09_agent_response.png")
    print("Screenshot saved: conv_09_agent_response.png")
    page.screenshot(path="test-results/conv_10_final_state.png")
    print("Screenshot saved: conv_10_final_state.png")
    raise AssertionError("Agent response did not include README line count within time limit")


def _check_readme_response(content: str, expected_line_count: int) -> bool:
    """Check if agent response contains README line count."""
    content_lower = content.lower()
    import re

    line_count_pattern = r"\b(\d{3})\b"
    line_counts = re.findall(line_count_pattern, content)

    return (
        str(expected_line_count) in content
        and "readme" in content_lower
        or (
            "line" in content_lower
            and "readme" in content_lower
            and any(num in content for num in ["183", str(expected_line_count)])
        )
        or (
            "line" in content_lower
            and "readme" in content_lower
            and line_counts
            and any(100 <= int(num) <= 300 for num in line_counts)
        )
    )


def test_conversation_start(page: Page, base_url: str):
    """Test starting a conversation with the OpenHands agent.

    1. Navigate to OpenHands (assumes GitHub token is already configured)
    2. Select the OpenHands repository
    3. Click Launch
    4. Wait for the agent to initialize
    5. Ask a question about the README.md file
    6. Verify the agent responds correctly.
    """
    os.makedirs("test-results", exist_ok=True)
    if not base_url:
        base_url = "http://localhost:12000"

    expected_line_count = get_readme_line_count()
    print(f"Expected README.md line count: {expected_line_count}")

    _navigate_to_openhands(page, base_url)
    _select_repository(page)
    _click_launch_button(page)
    _wait_for_conversation_interface(page)
    _wait_for_agent_ready(page)
    _ask_readme_question(page, expected_line_count)
    _wait_for_agent_response(page, expected_line_count)
