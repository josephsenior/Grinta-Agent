"""Browsing-related tests for the DockerRuntime, which connects to the ActionExecutor running in the sandbox."""

import os
import re
import pytest
from conftest import _close_test_runtime, _load_runtime
from forge.core.logger import forge_logger as logger
from forge.events.action import BrowseInteractiveAction, BrowseURLAction, CmdRunAction
from forge.events.observation import (
    BrowserOutputObservation,
    CmdOutputObservation,
    ErrorObservation,
    FileDownloadObservation,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not support browsing actions",
)


def parse_axtree_content(content: str) -> dict[str, str]:
    """Parse the accessibility tree content to extract bid -> element description mapping."""
    elements = {}
    current_bid = None
    description_lines = []
    lines = content.split("\n")
    in_axtree = False
    for line in lines:
        line = line.strip()
        if "BEGIN accessibility tree" in line:
            in_axtree = True
            continue
        elif "END accessibility tree" in line:
            break
        if not in_axtree or not line:
            continue
        if bid_match := re.match("\\[([a-zA-Z0-9]+)\\]\\s*(.*)", line):
            if current_bid and description_lines:
                elements[current_bid] = " ".join(description_lines)
            current_bid = bid_match[1]
            description_lines = [bid_match[2].strip()]
        elif current_bid:
            description_lines.append(line)
    if current_bid and description_lines:
        elements[current_bid] = " ".join(description_lines)
    return elements


def find_element_by_text(axtree_elements: dict[str, str], text: str) -> str | None:
    """Find an element bid by searching for text in the element description."""
    text = text.lower().strip()
    return next(
        (
            bid
            for bid, description in axtree_elements.items()
            if text in description.lower()
        ),
        None,
    )


def find_element_by_id(axtree_elements: dict[str, str], element_id: str) -> str | None:
    """Find an element bid by searching for HTML id attribute."""
    return next(
        (
            bid
            for bid, description in axtree_elements.items()
            if f'id="{element_id}"' in description
            or f"id='{element_id}'" in description
        ),
        None,
    )


def find_element_by_tag_and_attributes(
    axtree_elements: dict[str, str], tag: str, **attributes
) -> str | None:
    """Find an element bid by tag name and attributes."""
    tag = tag.lower()
    for bid, description in axtree_elements.items():
        description_lower = description.lower()
        if not description_lower.startswith(tag):
            continue
        match = True
        for attr_name, attr_value in attributes.items():
            attr_pattern = f'{attr_name}="{attr_value}"'
            if attr_pattern not in description:
                attr_pattern = f"{attr_name}='{attr_value}'"
            if attr_pattern not in description:
                match = False
                break
        if match:
            return bid
    return None


def test_browser_disabled(temp_dir, runtime_cls, run_as_Forge):
    runtime, _ = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=False
    )
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    action_browse = BrowseURLAction(url="http://localhost:8000", return_axtree=False)
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, ErrorObservation)
    assert "Browser functionality is not supported or disabled" in obs.content
    _close_test_runtime(runtime)


def test_simple_browse(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0
    assert "[1]" in obs.content
    action_cmd = CmdRunAction(command="sleep 3 && cat server.log")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    action_browse = BrowseURLAction(url="http://localhost:8000", return_axtree=False)
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert "http://localhost:8000" in obs.url
    assert not obs.error
    assert obs.open_pages_urls == ["http://localhost:8000/"]
    assert obs.active_page_index == 0
    assert obs.last_browser_action == 'goto("http://localhost:8000")'
    assert obs.last_browser_action_error == ""
    assert "Directory listing for /" in obs.content
    assert "server.log" in obs.content
    action = CmdRunAction(command="rm -rf server.log")
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0
    _close_test_runtime(runtime)


def _create_navigation_test_pages(temp_dir):
    """Create test pages for navigation testing."""
    page1_content = '\n        <!DOCTYPE html>\n        <html>\n        <head><title>Page 1</title></head>\n        <body>\n            <h1>Page 1</h1>\n            <a href="page2.html" id="link-to-page2">Go to Page 2</a>\n        </body>\n        </html>\n        '
    page2_content = '\n        <!DOCTYPE html>\n        <html>\n        <head><title>Page 2</title></head>\n        <body>\n            <h1>Page 2</h1>\n            <a href="page1.html" id="link-to-page1">Go to Page 1</a>\n        </body>\n        </html>\n        '

    page1_path = os.path.join(temp_dir, "page1.html")
    page2_path = os.path.join(temp_dir, "page2.html")

    with open(page1_path, "w", encoding="utf-8") as f:
        f.write(page1_content)
    with open(page2_path, "w", encoding="utf-8") as f:
        f.write(page2_content)

    return page1_path, page2_path


def _setup_navigation_test_environment(runtime, config, page1_path, page2_path):
    """Setup the navigation test environment."""
    sandbox_dir = config.workspace_mount_path_in_sandbox
    runtime.copy_to(page1_path, sandbox_dir)
    runtime.copy_to(page2_path, sandbox_dir)

    # Start HTTP server
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0

    # Wait for server to start
    action_cmd = CmdRunAction(command="sleep 3")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})


def _test_goto_page1(runtime):
    """Test navigation to page 1."""
    action_browse = BrowseInteractiveAction(
        browser_actions='goto("http://localhost:8000/page1.html")', return_axtree=False
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Page 1" in obs.content
    assert "http://localhost:8000/page1.html" in obs.url
    return obs


def _test_noop_action(runtime):
    """Test noop action."""
    action_browse = BrowseInteractiveAction(
        browser_actions="noop(500)", return_axtree=False
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Page 1" in obs.content
    assert "http://localhost:8000/page1.html" in obs.url
    return obs


def _test_goto_page2(runtime):
    """Test navigation to page 2."""
    action_browse = BrowseInteractiveAction(
        browser_actions='goto("http://localhost:8000/page2.html")', return_axtree=False
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Page 2" in obs.content
    assert "http://localhost:8000/page2.html" in obs.url
    return obs


def _test_go_back(runtime):
    """Test go back action."""
    action_browse = BrowseInteractiveAction(
        browser_actions="go_back()", return_axtree=False
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Page 1" in obs.content
    assert "http://localhost:8000/page1.html" in obs.url
    return obs


def _test_go_forward(runtime):
    """Test go forward action."""
    action_browse = BrowseInteractiveAction(
        browser_actions="go_forward()", return_axtree=False
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Page 2" in obs.content
    assert "http://localhost:8000/page2.html" in obs.url
    return obs


def test_browser_navigation_actions(temp_dir, runtime_cls, run_as_Forge):
    """Test browser navigation actions: goto, go_back, go_forward, noop."""
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        # Create test pages
        page1_path, page2_path = _create_navigation_test_pages(temp_dir)

        # Setup test environment
        _setup_navigation_test_environment(runtime, config, page1_path, page2_path)

        # Test navigation actions
        _test_goto_page1(runtime)
        _test_noop_action(runtime)
        _test_goto_page2(runtime)
        _test_go_back(runtime)
        _test_go_forward(runtime)

        # Cleanup
        _cleanup_test_server(runtime)
    finally:
        _close_test_runtime(runtime)


def _create_test_form_file(temp_dir):
    """Create HTML test form file."""
    form_content = '\n        <!DOCTYPE html>\n        <html>\n        <head><title>Test Form</title></head>\n        <body>\n            <h1>Test Form</h1>\n            <form id="test-form">\n                <input type="text" id="text-input" name="text" placeholder="Enter text">\n                <textarea id="textarea-input" name="message" placeholder="Enter message"></textarea>\n                <select id="select-input" name="option">\n                    <option value="">Select an option</option>\n                    <option value="option1">Option 1</option>\n                    <option value="option2">Option 2</option>\n                    <option value="option3">Option 3</option>\n                </select>\n                <button type="button" id="test-button">Test Button</button>\n                <input type="submit" id="submit-button" value="Submit">\n            </form>\n            <div id="result"></div>\n            <script>\n                document.getElementById(\'test-button\').onclick = function() {\n                    document.getElementById(\'result\').innerHTML = \'Button clicked!\';\n                };\n            </script>\n        </body>\n        </html>\n        '
    form_path = os.path.join(temp_dir, "form.html")
    with open(form_path, "w", encoding="utf-8") as f:
        f.write(form_content)
    return form_path


def _start_test_server(runtime):
    """Start HTTP server for testing."""
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "ACTION"})
    assert obs.exit_code == 0
    action_cmd = CmdRunAction(command="sleep 3")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    return obs


def _navigate_to_form(runtime):
    """Navigate to the test form page."""
    action_browse = BrowseInteractiveAction(
        browser_actions='goto("http://localhost:8000/form.html")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Test Form" in obs.content
    return obs


def _find_form_elements(obs):
    """Find form elements in the axtree."""
    axtree_elements = parse_axtree_content(obs.content)
    text_input_bid = find_element_by_text(axtree_elements, "Enter text")
    textarea_bid = find_element_by_text(axtree_elements, "Enter message")
    select_bid = find_element_by_text(axtree_elements, "combobox")
    button_bid = find_element_by_text(axtree_elements, "Test Button")

    assert (
        text_input_bid is not None
    ), f"Could not find text input element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    assert (
        textarea_bid is not None
    ), f"Could not find textarea element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    assert (
        button_bid is not None
    ), f"Could not find button element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    assert (
        select_bid is not None
    ), f"Could not find select element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    assert text_input_bid != button_bid, (
        "Text input bid should be different from button bid"
    )

    return text_input_bid, textarea_bid, select_bid, button_bid


def _test_fill_actions(runtime, text_input_bid, textarea_bid):
    """Test filling form fields."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'\nfill("{text_input_bid}", "Hello World")\nfill("{textarea_bid}", "This is a test message")\n'.strip(),
        return_axtree=True,
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, (
        f"Browser action failed with error: {obs.last_browser_action_error}"
    )

    updated_axtree_elements = parse_axtree_content(obs.content)
    assert text_input_bid in updated_axtree_elements, f"Text input element {
        text_input_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"
    text_input_desc = updated_axtree_elements[text_input_bid]
    assert "Hello World" in text_input_desc or "'Hello World'" in text_input_desc, (
        f"Text input should contain 'Hello World' but description is: {text_input_desc}"
    )
    assert textarea_bid in updated_axtree_elements, f"Textarea element {
        textarea_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"
    textarea_desc = updated_axtree_elements[textarea_bid]
    assert (
        "This is a test message" in textarea_desc
        or "'This is a test message'" in textarea_desc
    ), f"Textarea should contain test message but description is: {textarea_desc}"
    return obs


def _test_select_option(runtime, select_bid):
    """Test selecting an option from dropdown."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'select_option("{select_bid}", "option2")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, (
        f"Select option action failed: {obs.last_browser_action_error}"
    )

    updated_axtree_elements = parse_axtree_content(obs.content)
    assert select_bid in updated_axtree_elements, f"Select element {
        select_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"
    select_desc = updated_axtree_elements[select_bid]
    assert "option2" in select_desc or "Option 2" in select_desc, (
        f"Select element should show 'option2' as selected but description is: {select_desc}"
    )
    return obs


def _test_button_click(runtime, button_bid):
    """Test clicking a button."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'click("{button_bid}")', return_axtree=True
    )
    obs = runtime.run_action(action_browse)
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Click action failed: {obs.last_browser_action_error}"

    updated_axtree_elements = parse_axtree_content(obs.content)
    result_found = any(
        ("Button clicked!" in desc for desc in updated_axtree_elements.values())
    )
    assert result_found, f"Button click should have triggered JavaScript to show 'Button clicked!' but not found in: {
        dict(list(updated_axtree_elements.items())[:10])
    }"
    return obs


def _test_clear_action(runtime, text_input_bid):
    """Test clearing form field."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'clear("{text_input_bid}")', return_axtree=True
    )
    obs = runtime.run_action(action_browse)
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Clear action failed: {obs.last_browser_action_error}"

    updated_axtree_elements = parse_axtree_content(obs.content)
    assert text_input_bid in updated_axtree_elements
    text_input_desc = updated_axtree_elements[text_input_bid]
    assert "Hello World" not in text_input_desc, (
        f"Text input should be cleared but still contains text: {text_input_desc}"
    )
    assert (
        "Enter text" in text_input_desc
        or "textbox" in text_input_desc.lower()
        or text_input_desc.strip() == ""
    ), (
        f"Cleared text input should show placeholder or be empty but description is: {text_input_desc}"
    )
    return obs


def _cleanup_test_server(runtime):
    """Clean up the test server."""
    action_cmd = CmdRunAction(command='pkill -f "python3 -m http.server" || true')
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    return obs


def test_browser_form_interactions(temp_dir, runtime_cls, run_as_Forge):
    """Test browser form interaction actions: fill, click, select_option, clear."""
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        # Create test form file
        form_path = _create_test_form_file(temp_dir)
        sandbox_dir = config.workspace_mount_path_in_sandbox
        runtime.copy_to(form_path, sandbox_dir)

        # Start test server
        _start_test_server(runtime)

        # Navigate to form
        obs = _navigate_to_form(runtime)

        # Find form elements
        text_input_bid, textarea_bid, select_bid, button_bid = _find_form_elements(obs)

        # Test form interactions
        _test_fill_actions(runtime, text_input_bid, textarea_bid)
        _test_select_option(runtime, select_bid)
        _test_button_click(runtime, button_bid)
        _test_clear_action(runtime, text_input_bid)

        # Cleanup
        _cleanup_test_server(runtime)
    finally:
        _close_test_runtime(runtime)


def _create_scroll_test_page(temp_dir):
    """Create HTML page for scroll testing."""
    scroll_content = '\n        <!DOCTYPE html>\n        <html>\n        <head>\n            <title>Scroll Test</title>\n            <style>\n                body { margin: 0; padding: 20px; }\n                .content { height: 2000px; background: linear-gradient(to bottom, #ff0000, #0000ff); }\n                .hover-target {\n                    width: 200px; height: 100px; background: #ccc; margin: 20px;\n                    border: 2px solid #000; cursor: pointer;\n                }\n                .hover-target:hover { background: #ffff00; }\n                #focus-input { margin: 20px; padding: 10px; font-size: 16px; }\n            </style>\n        </head>\n        <body>\n            <h1>Interactive Test Page</h1>\n            <div class="hover-target" id="hover-div">Hover over me</div>\n            <input type="text" id="focus-input" placeholder="Focus me and type">\n            <div class="content">\n                <p>This is a long scrollable page...</p>\n                <p style="margin-top: 500px;">Middle content</p>\n                <p style="margin-top: 500px;" id="bottom-content">Bottom content</p>\n            </div>\n        </body>\n        </html>\n        '
    scroll_path = os.path.join(temp_dir, "scroll.html")
    with open(scroll_path, "w", encoding="utf-8") as f:
        f.write(scroll_content)
    return scroll_path


def _navigate_to_scroll_page(runtime):
    """Navigate to the scroll test page."""
    action_browse = BrowseInteractiveAction(
        browser_actions='goto("http://localhost:8000/scroll.html")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "Interactive Test Page" in obs.content
    return obs


def _test_scroll_action(runtime):
    """Test scroll action."""
    action_browse = BrowseInteractiveAction(
        browser_actions="scroll(0, 300)", return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Scroll action failed: {obs.last_browser_action_error}"
    assert (
        "scroll(0, 300)" in obs.last_browser_action
    ), f"Expected scroll action in browser history but got: {obs.last_browser_action}"
    return obs


def _find_interactive_elements(obs):
    """Find interactive elements in the page."""
    axtree_elements = parse_axtree_content(obs.content)
    hover_div_bid = find_element_by_text(axtree_elements, "Hover over me")
    focus_input_bid = find_element_by_text(axtree_elements, "Focus me and type")
    assert (
        hover_div_bid is not None
    ), f"Could not find hover div element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    assert (
        focus_input_bid is not None
    ), f"Could not find focus input element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:5])
    }"
    return hover_div_bid, focus_input_bid


def _test_hover_action(runtime, hover_div_bid):
    """Test hover action."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'hover("{hover_div_bid}")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Hover action failed: {obs.last_browser_action_error}"
    return obs


def _test_focus_action(runtime, focus_input_bid):
    """Test focus action."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'focus("{focus_input_bid}")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Focus action failed: {obs.last_browser_action_error}"
    assert (
        obs.focused_element_bid == focus_input_bid
    ), f"Expected focused element to be {focus_input_bid}, but got {
        obs.focused_element_bid
    }"
    return obs


def _test_fill_action(runtime, focus_input_bid):
    """Test fill action."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'fill("{focus_input_bid}", "TestValue123")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Fill action failed: {obs.last_browser_action_error}"

    updated_axtree_elements = parse_axtree_content(obs.content)
    assert focus_input_bid in updated_axtree_elements, f"Focus input element {
        focus_input_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"
    input_desc = updated_axtree_elements[focus_input_bid]
    assert "TestValue123" in input_desc or "'TestValue123'" in input_desc, (
        f"Input should contain 'TestValue123' but description is: {input_desc}"
    )
    return obs


def _test_press_action(runtime, focus_input_bid):
    """Test press action."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'press("{focus_input_bid}", "Backspace")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Press action failed: {obs.last_browser_action_error}"

    updated_axtree_elements = parse_axtree_content(obs.content)
    assert focus_input_bid in updated_axtree_elements, f"Focus input element {
        focus_input_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"
    input_desc = updated_axtree_elements[focus_input_bid]
    assert "TestValue12" in input_desc or "'TestValue12'" in input_desc, (
        f"Input should contain 'TestValue12' after backspace but description is: {input_desc}"
    )
    return obs


def _test_multiple_actions_sequence(runtime):
    """Test multiple actions in sequence."""
    action_browse = BrowseInteractiveAction(
        browser_actions="\nscroll(0, -200)\nnoop(1000)\nscroll(0, 400)\n".strip(),
        return_axtree=False,
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, (
        f"Multiple actions sequence failed: {obs.last_browser_action_error}"
    )
    assert (
        "scroll(0, 400)" in obs.last_browser_action
        or "noop(1000)" in obs.last_browser_action
    ), f"Expected final action from sequence but got: {obs.last_browser_action}"
    return obs


def test_browser_interactive_actions(temp_dir, runtime_cls, run_as_Forge):
    """Test browser interactive actions: scroll, hover, fill, press, focus."""
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        # Create scroll test page
        scroll_path = _create_scroll_test_page(temp_dir)
        sandbox_dir = config.workspace_mount_path_in_sandbox
        runtime.copy_to(scroll_path, sandbox_dir)

        # Start server and navigate
        _start_test_server(runtime)
        obs = _navigate_to_scroll_page(runtime)

        # Test scroll action
        obs = _test_scroll_action(runtime)

        # Find interactive elements
        hover_div_bid, focus_input_bid = _find_interactive_elements(obs)

        # Test interactive actions
        _test_hover_action(runtime, hover_div_bid)
        _test_focus_action(runtime, focus_input_bid)
        _test_fill_action(runtime, focus_input_bid)
        _test_press_action(runtime, focus_input_bid)
        _test_multiple_actions_sequence(runtime)

        # Cleanup
        _cleanup_test_server(runtime)
    finally:
        _close_test_runtime(runtime)


def _create_test_files(temp_dir):
    """Create test files for upload testing."""
    test_file_content = "This is a test file for upload testing."
    test_file_path = os.path.join(temp_dir, "upload_test.txt")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_file_content)

    upload_content = """<!DOCTYPE html>
<html>
<head><title>File Upload Test</title></head>
<body>
    <h1>File Upload Test</h1>
    <form enctype="multipart/form-data">
        <input type="file" id="file-input" name="file" accept=".txt,.pdf,.png">
        <button type="button" onclick="handleUpload()">Upload File</button>
    </form>
    <div id="upload-result"></div>
    <script>
        function handleUpload() {
            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length > 0) {
                document.getElementById('upload-result').innerHTML =
                    'File selected: ' + fileInput.files[0].name;
            } else {
                document.getElementById('upload-result').innerHTML = 'No file selected';
            }
        }
    </script>
</body>
</html>"""

    upload_path = os.path.join(temp_dir, "upload.html")
    with open(upload_path, "w", encoding="utf-8") as f:
        f.write(upload_content)

    return test_file_path, upload_path


def _setup_test_environment(runtime, config, test_file_path, upload_path):
    """Setup the test environment by copying files and starting server."""
    sandbox_dir = config.workspace_mount_path_in_sandbox
    runtime.copy_to(upload_path, sandbox_dir)
    runtime.copy_to(test_file_path, sandbox_dir)

    # Start HTTP server
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0

    # Wait for server to start
    action_cmd = CmdRunAction(command="sleep 3")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})


def _navigate_to_upload_page(runtime):
    """Navigate to the upload page and verify it loads."""
    action_browse = BrowseInteractiveAction(
        browser_actions='goto("http://localhost:8000/upload.html")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error
    assert "File Upload Test" in obs.content

    return obs


def _find_upload_elements(obs):
    """Find file input and upload button elements."""
    axtree_elements = parse_axtree_content(obs.content)
    file_input_bid = (
        find_element_by_text(axtree_elements, "Choose File")
        or find_element_by_text(axtree_elements, "No file chosen")
        or find_element_by_text(axtree_elements, "Browse")
        or find_element_by_text(axtree_elements, "file")
        or find_element_by_id(axtree_elements, "file-input")
    )
    upload_button_bid = find_element_by_text(axtree_elements, "Upload File")

    assert (
        file_input_bid is not None
    ), f"Could not find file input element in axtree. Available elements: {
        dict(list(axtree_elements.items())[:10])
    }"

    return file_input_bid, upload_button_bid


def _perform_file_upload(runtime, file_input_bid):
    """Perform the file upload action."""
    action_browse = BrowseInteractiveAction(
        browser_actions=f'upload_file("{file_input_bid}", "/workspace/upload_test.txt")',
        return_axtree=True,
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"File upload action failed: {obs.last_browser_action_error}"

    return obs


def _verify_upload_success(obs, file_input_bid):
    """Verify that the file upload was successful."""
    updated_axtree_elements = parse_axtree_content(obs.content)
    assert file_input_bid in updated_axtree_elements, f"File input element {
        file_input_bid
    } should be present in updated axtree. Available elements: {
        list(updated_axtree_elements.keys())[:10]
    }"

    file_input_desc = updated_axtree_elements[file_input_bid]
    assert (
        "upload_test.txt" in file_input_desc
        or "upload_test" in file_input_desc
        or "txt" in file_input_desc
    ), f"File input should show selected file but description is: {file_input_desc}"


def _test_upload_button_click(runtime, upload_button_bid):
    """Test clicking the upload button if it exists."""
    if not upload_button_bid:
        return

    action_browse = BrowseInteractiveAction(
        browser_actions=f'click("{upload_button_bid}")', return_axtree=True
    )
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, BrowserOutputObservation)
    assert not obs.error, f"Upload button click failed: {obs.last_browser_action_error}"

    final_axtree_elements = parse_axtree_content(obs.content)
    result_found = any(
        (
            "File selected:" in desc or "upload_test.txt" in desc
            for desc in final_axtree_elements.values()
        )
    )
    assert result_found, f"JavaScript upload handler should have updated the page but no result found in: {
        dict(list(final_axtree_elements.items())[:10])
    }"


def _cleanup_server(runtime):
    """Clean up the HTTP server."""
    action_cmd = CmdRunAction(command='pkill -f "python3 -m http.server" || true')
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})


def test_browser_file_upload(temp_dir, runtime_cls, run_as_Forge):
    """Test browser file upload action."""
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        # Create test files
        test_file_path, upload_path = _create_test_files(temp_dir)

        # Setup test environment
        _setup_test_environment(runtime, config, test_file_path, upload_path)

        # Navigate to upload page
        obs = _navigate_to_upload_page(runtime)

        # Find upload elements
        file_input_bid, upload_button_bid = _find_upload_elements(obs)

        # Perform file upload
        obs = _perform_file_upload(runtime, file_input_bid)

        # Verify upload success
        _verify_upload_success(obs, file_input_bid)

        # Test upload button click
        _test_upload_button_click(runtime, upload_button_bid)

    finally:
        _cleanup_server(runtime)
        _close_test_runtime(runtime)


def test_read_pdf_browse(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        pdf_path = os.path.join(temp_dir, "test_document.pdf")
        pdf_content = "This is test content for PDF reading test"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, pdf_content)
        c.drawString(100, 700, "Additional line for PDF structure")
        c.drawString(100, 650, "Third line to ensure valid PDF")
        c.setPageCompression(0)
        c.save()
        sandbox_dir = config.workspace_mount_path_in_sandbox
        runtime.copy_to(pdf_path, sandbox_dir)
        action_cmd = CmdRunAction(command="ls -alh")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        assert "test_document.pdf" in obs.content
        action_cmd = CmdRunAction(command="cat /tmp/oh-server-url")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        server_url = obs.content.strip()
        pdf_url = f"{server_url}/view?path=/workspace/test_document.pdf"
        action_browse = BrowseInteractiveAction(
            browser_actions=f'goto("{pdf_url}")', return_axtree=False
        )
        logger.info(action_browse, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_browse)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, BrowserOutputObservation)
        observation_text = str(obs)
        assert "[Action executed successfully.]" in observation_text
        assert "Canvas" in observation_text
        assert (
            "Screenshot saved to: /workspace/.browser_screenshots/screenshot_"
            in observation_text
        )
        action_cmd = CmdRunAction(command="ls /workspace/.browser_screenshots")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        assert "screenshot_" in obs.content
        assert ".png" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_read_png_browse(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )
    try:
        from PIL import Image, ImageDraw

        png_path = os.path.join(temp_dir, "test_image.png")
        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        text = "This is a test PNG image"
        d.text((20, 80), text, fill=(0, 0, 0))
        img.save(png_path)
        sandbox_dir = config.workspace_mount_path_in_sandbox
        runtime.copy_to(png_path, sandbox_dir)
        action_cmd = CmdRunAction(command="ls -alh")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        assert "test_image.png" in obs.content
        action_cmd = CmdRunAction(command="cat /tmp/oh-server-url")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        server_url = obs.content.strip()
        png_url = f"{server_url}/view?path=/workspace/test_image.png"
        action_browse = BrowseInteractiveAction(
            browser_actions=f'goto("{png_url}")', return_axtree=False
        )
        logger.info(action_browse, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_browse)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, BrowserOutputObservation)
        observation_text = str(obs)
        assert "[Action executed successfully.]" in observation_text
        assert "File Viewer - test_image.png" in observation_text
        assert (
            "Screenshot saved to: /workspace/.browser_screenshots/screenshot_"
            in observation_text
        )
        action_cmd = CmdRunAction(command="ls /workspace/.browser_screenshots")
        logger.info(action_cmd, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action_cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        assert "screenshot_" in obs.content
        assert ".png" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_download_file(temp_dir, runtime_cls, run_as_Forge):
    """Test downloading a file using the browser."""
    runtime, config = _load_runtime(
        temp_dir, runtime_cls, run_as_Forge, enable_browser=True
    )

    try:
        # Setup test files
        test_file_name = _setup_test_files(temp_dir, config, runtime)

        # Start HTTP server
        _start_http_server(runtime)

        # Test file download
        _test_file_download(runtime, test_file_name)

        # Cleanup
        _cleanup_test_environment(runtime)

    finally:
        _close_test_runtime(runtime)


def _setup_test_files(temp_dir, config, runtime):
    """Setup test files for download testing."""
    # Create PDF test file
    test_file_name = "test_download.pdf"
    test_file_path = _create_pdf_test_file(temp_dir, test_file_name)

    # Copy PDF to sandbox
    sandbox_dir = config.workspace_mount_path_in_sandbox
    runtime.copy_to(test_file_path, sandbox_dir)

    # Create HTML test page
    _create_html_test_page(temp_dir, test_file_name, sandbox_dir, runtime)

    # Verify files are in place
    _verify_test_files_created(runtime, test_file_name)

    return test_file_name


def _create_pdf_test_file(temp_dir, test_file_name):
    """Create a test PDF file."""
    pdf_content = b"%PDF-1.4\n        1 0 obj\n\n        /Type /Catalog\n        /Pages 2 0 R\n        >>\n        endobj\n        2 0 obj\n\n        /Type /Pages\n        /Kids [3 0 R]\n        /Count 1\n        >>\n        endobj\n        3 0 obj\n\n        /Type /Page\n        /Parent 2 0 R\n        /MediaBox [0 0 612 792]\n        >>\n        endobj\n        xref\n        0 4\n        0000000000 65535 f\n        0000000010 00000 n\n        0000000053 00000 n\n        0000000125 00000 n\n        trailer\n\n        /Size 4\n        /Root 1 0 R\n        >>\n        startxref\n        212\n        %%EOF"
    test_file_path = os.path.join(temp_dir, test_file_name)
    with open(test_file_path, "wb") as f:
        f.write(pdf_content)
    return test_file_path


def _create_html_test_page(temp_dir, test_file_name, sandbox_dir, runtime):
    """Create HTML test page for download testing."""
    html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Download Test</title>
        </head>
        <body>
            <h1>Download Test Page</h1>
            <p>Click the link below to download the test file:</p>
            <a href="/{test_file_name}" download="{test_file_name}" id="download-link">Download Test File</a>
        </body>
        </html>
        """
    html_file_path = os.path.join(temp_dir, "download_test.html")
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    runtime.copy_to(html_file_path, sandbox_dir)


def _verify_test_files_created(runtime, test_file_name):
    """Verify that test files were created successfully."""
    action_cmd = CmdRunAction(command="ls -alh")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0
    assert test_file_name in obs.content
    assert "download_test.html" in obs.content


def _start_http_server(runtime):
    """Start HTTP server for testing."""
    # Create downloads directory
    action_cmd = CmdRunAction(command="mkdir -p /workspace/.downloads")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert obs.exit_code == 0

    # Start HTTP server
    action_cmd = CmdRunAction(command="python3 -m http.server 8000 > server.log 2>&1 &")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0

    # Wait for server to start
    action_cmd = CmdRunAction(command="sleep 2")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})


def _test_file_download(runtime, test_file_name):
    """Test the actual file download process."""
    # Browse to download page
    action_browse = BrowseURLAction(url="http://localhost:8000/download_test.html")
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, BrowserOutputObservation)
    assert "http://localhost:8000/download_test.html" in obs.url
    assert not obs.error
    assert "Download Test Page" in obs.content

    # Navigate to file URL to trigger download
    file_url = f"http://localhost:8000/{test_file_name}"
    action_browse = BrowseInteractiveAction(browser_actions=f'goto("{file_url}")')
    logger.info(action_browse, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_browse)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    # Verify download
    downloaded_file_name = "file_1.pdf"
    assert isinstance(obs, FileDownloadObservation)
    assert "Location of downloaded file:" in str(obs)
    assert downloaded_file_name in str(obs)

    # Wait for download to complete
    action_cmd = CmdRunAction(command="sleep 3")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    # Verify file was downloaded
    action_cmd = CmdRunAction(command="ls -la /workspace")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0
    assert downloaded_file_name in obs.content


def _cleanup_test_environment(runtime):
    """Cleanup test environment."""
    # Stop HTTP server
    action_cmd = CmdRunAction(command='pkill -f "python3 -m http.server" || true')
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})

    # Remove log file
    action_cmd = CmdRunAction(command="rm -f server.log")
    logger.info(action_cmd, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action_cmd)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
