"""E2E: Settings configuration test (GitHub token).

This test navigates to Forge, configures the LLM API key if prompted,
then ensures the GitHub token is set in Settings → Integrations and that the
home screen shows the repository selector.
"""

import os
from playwright.sync_api import Page, expect


def _setup_test_environment(base_url: str) -> str:
    """Setup test environment and return base URL."""
    os.makedirs("test-results", exist_ok=True)
    if not base_url:
        base_url = "http://localhost:12000"
    return base_url


def _navigate_to_application(page: Page, base_url: str) -> None:
    """Navigate to the Forge application."""
    print(f"Step 1: Navigating to Forge application at {base_url}...")
    page.goto(base_url)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.screenshot(path="test-results/token_01_initial_load.png")
    print("Screenshot saved: token_01_initial_load.png")


def _handle_llm_configuration_modal(page: Page) -> None:
    """Handle LLM API key configuration modal."""
    config_modal = page.locator("text=AI Provider Configuration")
    if config_modal.is_visible(timeout=5000):
        print("AI Provider Configuration modal detected")
        llm_api_key_input = page.locator('[data-testid="llm-api-key-input"]')
        if llm_api_key_input.is_visible(timeout=3000):
            llm_api_key = os.getenv("LLM_API_KEY", "test-key")
            llm_api_key_input.fill(llm_api_key)
            print(f"Filled LLM API key (length: {len(llm_api_key)})")
        save_button = page.locator('button:has-text("Save")')
        if save_button.is_visible(timeout=3000):
            save_button.click()
            page.wait_for_timeout(2000)
            print("Saved LLM API key configuration")


def _handle_privacy_modal(page: Page) -> None:
    """Handle privacy preferences modal."""
    privacy_modal = page.locator("text=Your Privacy Preferences")
    if privacy_modal.is_visible(timeout=5000):
        print("Privacy Preferences modal detected")
        confirm_button = page.locator('button:has-text("Confirm Preferences")')
        if confirm_button.is_visible(timeout=3000):
            confirm_button.click()
            page.wait_for_timeout(2000)
            print("Confirmed privacy preferences")


def _handle_initial_modals(page: Page) -> None:
    """Handle initial modals that may appear."""
    try:
        _handle_llm_configuration_modal(page)
        _handle_privacy_modal(page)
    except Exception as e:
        print(f"Error handling initial modals: {e}")
        page.screenshot(path="test-results/token_01_5_modal_error.png")
        print("Screenshot saved: token_01_5_modal_error.png")


def _navigate_to_integrations_tab(page: Page) -> None:
    """Navigate to the integrations tab in settings."""
    integrations_tab = page.locator("text=Integrations")
    if integrations_tab.is_visible(timeout=3000) and (not page.url.endswith("/settings/integrations")):
        print("Clicking Integrations tab...")
        integrations_tab.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)


def _configure_github_token(page: Page, base_url: str) -> None:
    """Configure GitHub token in settings."""
    github_token_input = page.locator('[data-testid="github-token-input"]')
    if github_token_input.is_visible(timeout=5000):
        print("Found GitHub token input field")
        if github_token := os.getenv("GITHUB_TOKEN", ""):
            github_token_input.clear()
            github_token_input.fill(github_token)
            print(f"Filled GitHub token from environment variable (length: {len(github_token)})")
            if filled_value := github_token_input.input_value():
                print(f"Token field now contains value of length: {len(filled_value)}")
            else:
                print("WARNING: Token field appears to be empty after filling")
            _save_github_token_configuration(page, base_url)
        else:
            print("No GitHub token found in environment variables")
    else:
        print("GitHub token input field not found on settings page")
        page.screenshot(path="test-results/token_02_settings_debug.png")
        print("Debug screenshot saved: token_02_settings_debug.png")


def _save_github_token_configuration(page: Page, base_url: str) -> None:
    """Save GitHub token configuration."""
    save_button = page.locator('[data-testid="submit-button"]')
    if save_button.is_visible(timeout=3000):
        is_disabled = save_button.is_disabled()
        print(f"Save Changes button found, disabled: {is_disabled}")
        if not is_disabled:
            print("Clicking Save Changes button...")
            save_button.click()
            try:
                page.wait_for_timeout(1000)
                page.wait_for_function(
                    "document.querySelector('[data-testid=\"submit-button\"]').disabled === true", timeout=10000
                )
                print("Save operation completed - form is now clean")
            except Exception:
                print("Save operation completed (timeout waiting for form clean state)")
            print("Navigating back to home page...")
            page.goto(base_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
        else:
            print("Save Changes button is disabled - form may be invalid")
    else:
        print("Save Changes button not found")


def _handle_github_token_not_configured(page: Page, base_url: str) -> None:
    """Handle case when GitHub token is not configured."""
    print("GitHub token not configured. Need to navigate to settings...")
    navigate_to_settings_button = page.locator('[data-testid="navigate-to-settings-button"]')
    if navigate_to_settings_button.is_visible(timeout=3000):
        navigate_to_settings_button.click()
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(3000)
        print("Navigated to settings page, looking for GitHub token input...")
        settings_screen = page.locator('[data-testid="settings-screen"]')
        if settings_screen.is_visible(timeout=5000):
            print("Settings screen is visible")
            _navigate_to_integrations_tab(page)
            _configure_github_token(page, base_url)
        else:
            print("Settings screen not found")


def _handle_github_token_already_configured(page: Page, base_url: str) -> None:
    """Handle case when GitHub token is already configured."""
    print("GitHub token is already configured, repository selection is available")
    settings_button = page.locator('button:has-text("Settings")')
    if settings_button.is_visible(timeout=3000):
        print("Settings button found, clicking to navigate to settings page...")
        settings_button.click()
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(3000)
        _navigate_to_integrations_tab(page)
        _configure_github_token(page, base_url)
    else:
        print("Settings button not found, continuing with existing token")


def _check_github_token_configuration(page: Page, base_url: str) -> None:
    """Check and configure GitHub token if needed."""
    print("Step 2: Checking if GitHub token is configured...")
    try:
        connect_to_provider = page.locator("text=Connect to a Repository")
        if connect_to_provider.is_visible(timeout=3000):
            print('Found "Connect to a Repository" section')
            navigate_to_settings_button = page.locator('[data-testid="navigate-to-settings-button"]')
            if navigate_to_settings_button.is_visible(timeout=3000):
                _handle_github_token_not_configured(page, base_url)
            else:
                _handle_github_token_already_configured(page, base_url)
        else:
            print('Could not find "Connect to a Repository" section')
        page.screenshot(path="test-results/token_03_after_settings.png")
        print("Screenshot saved: token_03_after_settings.png")
    except Exception as e:
        print(f"Error checking GitHub token configuration: {e}")
        page.screenshot(path="test-results/token_04_error.png")
        print("Screenshot saved: token_04_error.png")


def _verify_repository_selection(page: Page) -> None:
    """Verify that repository selection is available."""
    print("Step 3: Verifying repository selection is available...")
    home_screen = page.locator('[data-testid="home-screen"]')
    expect(home_screen).to_be_visible(timeout=15000)
    print("Home screen is visible")
    repo_dropdown = page.locator('[data-testid="repo-dropdown"]')
    expect(repo_dropdown).to_be_visible(timeout=15000)
    print("Repository dropdown is visible")
    print("GitHub token configuration verified successfully")
    page.screenshot(path="test-results/token_05_success.png")
    print("Screenshot saved: token_05_success.png")


def test_github_token_configuration(page: Page, base_url: str):
    """Test the GitHub token configuration flow.

    1. Navigate to Forge
    2. Configure LLM API key if needed
    3. Check if GitHub token is already configured
    4. If not, navigate to settings and configure it
    5. Verify the token is saved and repository selection is available.
    """
    # Setup test environment
    base_url = _setup_test_environment(base_url)

    # Navigate to application
    _navigate_to_application(page, base_url)

    # Handle initial modals
    _handle_initial_modals(page)

    # Check and configure GitHub token
    _check_github_token_configuration(page, base_url)

    # Verify repository selection
    _verify_repository_selection(page)
