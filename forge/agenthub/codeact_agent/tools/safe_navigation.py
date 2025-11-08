"""Safe navigation tool for preventing chrome-error://chromewebdata/ issues.

This tool provides a safe way to navigate to localhost URLs by ensuring server readiness.
"""

from forge.core.logger import forge_logger as logger


def safe_goto_localhost(url: str, max_wait: int = 30, check_interval: float = 1.0) -> str:
    """Safely navigate to a localhost URL by waiting for server readiness.

    Args:
        url: The localhost URL to navigate to
        max_wait: Maximum time to wait for server readiness (seconds)
        check_interval: Time between readiness checks (seconds)

    Returns:
        Browser code that safely navigates to the URL

    """
    if not url.startswith(("http://localhost:", "https://localhost:")):
        return f"goto('{url}')"

    logger.info(f"Creating safe navigation code for {url}")

    return f"""
import time
import requests

def wait_for_server_ready():
    \"\"\"Wait for a server to become ready before proceeding.

    This function checks if a server is responding to requests within
    the specified timeout period and check interval.

    Returns:
        bool: True if the server becomes ready, False if timeout is reached.
    \"\"\"
    url = "{url}"
    max_wait = {max_wait}
    check_interval = {check_interval}

    print(f"🔍 Checking if server at {{url}} is ready...")
    start_time = time.time()

    for i in range(max_wait):
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code < 500:
                print(f"✅ Server is ready! Status: {{response.status_code}}")
                return True
        except Exception as e:
            print(f"⏳ Server not ready yet ({{i+1}}/{{max_wait}}): {{e}}")
        time.sleep(check_interval)

    print(f"⚠️ Server not ready after {{max_wait}} seconds, proceeding anyway...")
    return False

# Wait for server to be ready
server_ready = wait_for_server_ready()

# Navigate to the URL
goto("{url}")

# Wait a moment for page to load
noop(2000)
"""


def create_safe_navigation_browser_code(url: str, additional_actions: str = "") -> str:
    """Create complete browser code that safely navigates to a URL.

    Args:
        url: The URL to navigate to
        additional_actions: Additional browser actions to perform after navigation

    Returns:
        Complete browser code with safety checks

    """
    if url.startswith(("http://localhost:", "https://localhost:")):
        base_code = safe_goto_localhost(url)
    else:
        base_code = f"goto('{url}')"

    if additional_actions:
        base_code += f"\n{additional_actions}"

    return base_code
