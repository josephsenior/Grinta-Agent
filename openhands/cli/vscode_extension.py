from __future__ import annotations

import importlib.resources
import json
import os
import pathlib
import subprocess
import tempfile
import urllib.request
from urllib.error import URLError

from openhands.core.logger import openhands_logger as logger


def download_latest_vsix_from_github() -> str | None:
    """Download latest .vsix from GitHub releases.

    Returns:
        Path to downloaded .vsix file, or None if failed
    """
    api_url = "https://api.github.com/repos/All-Hands-AI/OpenHands/releases"
    try:
        with urllib.request.urlopen(
            api_url,
            timeout=10,
        ) as response:  # nosec B310 - Safe: accessing GitHub API with validated URL
            if response.status != 200:
                logger.debug("GitHub API request failed with status: %s", response.status)
                return None
            releases = json.loads(response.read().decode())
            for release in releases:
                if release.get("tag_name", "").startswith("ext-v"):
                    for asset in release.get("assets", []):
                        if asset.get("name", "").endswith(".vsix"):
                            download_url = asset.get("browser_download_url")
                            if not download_url:
                                continue
                            with urllib.request.urlopen(
                                download_url,
                                timeout=30,
                            ) as download_response:  # nosec B310 - Safe: downloading from verified GitHub release URL
                                if download_response.status != 200:
                                    logger.debug("Failed to download .vsix with status: %s", download_response.status)
                                    continue
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".vsix") as tmp_file:
                                    tmp_file.write(download_response.read())
                                    return tmp_file.name
                    return None
    except (URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.debug("Failed to download from GitHub releases: %s", e)
        return None
    return None


def _detect_supported_editor() -> tuple[bool, bool]:
    """Detect if running in a supported editor (VS Code or Windsurf)."""
    is_vscode_like = os.environ.get("TERM_PROGRAM") == "vscode"
    is_windsurf = (
        os.environ.get("__CFBundleIdentifier") == "com.exafunction.windsurf"
        or "windsurf" in os.environ.get("PATH", "").lower()
        or any("windsurf" in val.lower() for val in os.environ.values() if isinstance(val, str))
    )
    return is_vscode_like, is_windsurf


def _get_editor_config(is_windsurf: bool) -> tuple[str, str, str]:
    """Get editor configuration based on detected editor type."""
    if is_windsurf:
        return ("surf", "Windsurf", "windsurf")
    return ("code", "VS Code", "vscode")


def _setup_extension_flag_file(editor_name: str, flag_suffix: str) -> tuple[pathlib.Path, bool]:
    """Set up extension flag file and return (flag_file, should_continue)."""
    flag_dir = pathlib.Path.home() / ".openhands"
    flag_file = flag_dir / f".{flag_suffix}_extension_installed"

    try:
        flag_dir.mkdir(parents=True, exist_ok=True)
        if flag_file.exists():
            return flag_file, False
    except OSError as e:
        logger.debug("Could not create or check %s extension flag directory: %s", editor_name, e)
        return flag_file, False

    return flag_file, True


def _handle_already_installed_extension(
    editor_command: str,
    editor_name: str,
    extension_id: str,
    flag_file: pathlib.Path,
) -> bool:
    """Handle case where extension is already installed."""
    if _is_extension_installed(editor_command, extension_id):
        _mark_installation_successful(flag_file, editor_name)
        return True
    return False


def _attempt_extension_installation(editor_command: str, editor_name: str, flag_file: pathlib.Path) -> None:
    """Attempt to install the extension using various methods."""
    if _attempt_bundled_install(editor_command, editor_name):
        _mark_installation_successful(flag_file, editor_name)
        return

    if _attempt_github_install(editor_command, editor_name):
        _mark_installation_successful(flag_file, editor_name)
        return


def attempt_vscode_extension_install() -> None:
    """Checks if running in a supported editor and attempts to install the OpenHands companion extension.

    This is a best-effort, one-time attempt.
    """
    is_vscode_like, is_windsurf = _detect_supported_editor()
    if not (is_vscode_like or is_windsurf):
        return

    editor_command, editor_name, flag_suffix = _get_editor_config(is_windsurf)
    flag_file, should_continue = _setup_extension_flag_file(editor_name, flag_suffix)

    if not should_continue:
        return

    extension_id = "openhands.openhands-vscode"

    if _handle_already_installed_extension(editor_command, editor_name, extension_id, flag_file):
        return

    _attempt_extension_installation(editor_command, editor_name, flag_file)


def _mark_installation_successful(flag_file: pathlib.Path, editor_name: str) -> None:
    """Mark the extension installation as successful by creating the flag file.

    Args:
        flag_file: Path to the flag file to create
        editor_name: Human-readable name of the editor for logging
    """
    try:
        flag_file.touch()
        logger.debug("%s extension installation marked as successful.", editor_name)
    except OSError as e:
        logger.debug("Could not create %s extension success flag file: %s", editor_name, e)


def _is_extension_installed(editor_command: str, extension_id: str) -> bool:
    """Check if the OpenHands extension is already installed.

    Args:
        editor_command: The command to run the editor (e.g., 'code', 'windsurf')
        extension_id: The extension ID to check for

    Returns:
        bool: True if extension is already installed, False otherwise
    """
    try:
        process = subprocess.run([editor_command, "--list-extensions"], capture_output=True, text=True, check=False)
        if process.returncode == 0:
            installed_extensions = process.stdout.strip().split("\n")
            return extension_id in installed_extensions
    except Exception as e:
        logger.debug("Could not check installed extensions: %s", e)
    return False


def _attempt_github_install(editor_command: str, editor_name: str) -> bool:
    """Attempt to install the extension from GitHub Releases.

    Downloads the latest VSIX file from GitHub releases and attempts to install it.
    Ensures proper cleanup of temporary files.

    Args:
        editor_command: The command to run the editor (e.g., 'code', 'windsurf')
        editor_name: Human-readable name of the editor (e.g., 'VS Code', 'Windsurf')

    Returns:
        bool: True if installation succeeded, False otherwise
    """
    vsix_path_from_github = download_latest_vsix_from_github()
    if not vsix_path_from_github:
        return False
    github_success = False
    try:
        process = subprocess.run(
            [editor_command, "--install-extension", vsix_path_from_github, "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            github_success = True
        else:
            logger.debug("Failed to install .vsix from GitHub: %s", process.stderr.strip())
    finally:
        if os.path.exists(vsix_path_from_github):
            try:
                os.remove(vsix_path_from_github)
            except OSError as e:
                logger.debug("Failed to delete temporary file %s: %s", vsix_path_from_github, e)
    return github_success


def _attempt_bundled_install(editor_command: str, editor_name: str) -> bool:
    """Attempt to install the extension from the bundled VSIX file.

    Uses the VSIX file packaged with the OpenHands installation.

    Args:
        editor_command: The command to run the editor (e.g., 'code', 'windsurf')
        editor_name: Human-readable name of the editor (e.g., 'VS Code', 'Windsurf')

    Returns:
        bool: True if installation succeeded, False otherwise
    """
    try:
        vsix_filename = "openhands-vscode-0.0.1.vsix"
        with importlib.resources.as_file(
            importlib.resources.files("openhands").joinpath("integrations", "vscode", vsix_filename),
        ) as vsix_path:
            if vsix_path.exists():
                process = subprocess.run(
                    [editor_command, "--install-extension", str(vsix_path), "--force"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if process.returncode == 0:
                    return True
                logger.debug("Bundled .vsix installation failed: %s", process.stderr.strip())
            else:
                logger.debug("Bundled .vsix not found at %s.", vsix_path)
    except Exception as e:
        logger.warning('Could not auto-install extension. Please make sure "code" command is in PATH. Error: %s', e)
    return False


def _attempt_marketplace_install(editor_command: str, editor_name: str, extension_id: str) -> bool:
    """Attempt to install the extension from the marketplace.

    This method is currently unused as the OpenHands extension is not yet published
    to the VS Code/Windsurf marketplace. It's kept here for future use when the
    extension becomes available.

    Args:
        editor_command: The command to use ('code' or 'surf')
        editor_name: Human-readable editor name ('VS Code' or 'Windsurf')
        extension_id: The extension ID to install

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        process = subprocess.run(
            [editor_command, "--install-extension", extension_id, "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            return True
        logger.debug("Marketplace installation failed: %s", process.stderr.strip())
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.debug("An unexpected error occurred trying to install from the Marketplace: %s", e)
        return False
