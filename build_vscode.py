import logging
import os
import pathlib
import subprocess
import shutil

logger = logging.getLogger(__name__)
EXTENSION_NAME = "Forge-vscode"
EXTENSION_VERSION = "0.0.1"
VSIX_FILENAME = f"{EXTENSION_NAME}-{EXTENSION_VERSION}.vsix"
ROOT_DIR = pathlib.Path(__file__).parent.resolve()
VSCODE_EXTENSION_DIR = ROOT_DIR / "forge" / "integrations" / "vscode"


def check_node_version():
    """Check if Node.js version is sufficient for building the extension."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
        version_str = result.stdout.strip()
        major_version = int(version_str.lstrip("v").split(".")[0])
        return major_version >= 18
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return False


def _handle_skip_build(vsix_path):
    """Handle case when VS Code build is skipped."""
    logger.info("--- Skipping VS Code extension build (SKIP_VSCODE_BUILD is set) ---")
    if vsix_path.exists():
        logger.info("--- Using existing VS Code extension: %s", vsix_path)
    else:
        logger.info("--- No pre-built VS Code extension found ---")


def _handle_node_version_check(vsix_path):
    """Handle case when Node.js version is insufficient."""
    logger.warning("--- Warning: Node.js version < 18 detected or Node.js not found ---")
    logger.info("--- Skipping VS Code extension build (requires Node.js >= 18) ---")
    logger.info("--- Using pre-built extension if available ---")
    if not vsix_path.exists():
        logger.warning("--- Warning: No pre-built VS Code extension found ---")
        logger.warning("--- VS Code extension will not be available ---")
    else:
        logger.info("--- Using pre-built VS Code extension: %s", vsix_path)


def _build_extension_package(vsix_path):
    """Build the VS Code extension package."""
    logger.info("--- Building VS Code extension in %s ---", VSCODE_EXTENSION_DIR)

    try:
        _install_npm_dependencies()
        _package_extension()
        _verify_package_built(vsix_path)
        logger.info("--- VS Code extension built successfully: %s", vsix_path)
    except subprocess.CalledProcessError as e:
        _handle_build_failure(e, vsix_path)


def _install_npm_dependencies():
    """Install npm dependencies for VS Code extension."""
    logger.info("--- Running npm install for VS Code extension ---")
    # On Windows the npm executable is often `npm.cmd`; use shutil.which to
    # find the correct program in PATH (this avoids FileNotFoundError when
    # Poetry runs the build in a temporary environment that may use a
    # different shell resolution strategy).
    npm_exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_exe:
        logger.warning("npm not found in PATH; skipping npm install for VS Code extension")
        return
    subprocess.run([npm_exe, "install"], cwd=VSCODE_EXTENSION_DIR, check=True, shell=False)


def _package_extension():
    """Package the VS Code extension."""
    logger.info("--- Packaging VS Code extension (%s) ---", VSIX_FILENAME)
    npm_exe = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_exe:
        logger.warning("npm not found in PATH; skipping VS Code packaging step")
        return
    subprocess.run([npm_exe, "run", "package-vsix"], cwd=VSCODE_EXTENSION_DIR, check=True, shell=False)


def _verify_package_built(vsix_path):
    """Verify that the extension package was built successfully."""
    if not vsix_path.exists():
        raise FileNotFoundError(f"VS Code extension package not found after build: {vsix_path}")


def _handle_build_failure(error: subprocess.CalledProcessError, vsix_path):
    """Handle build failure gracefully."""
    logger.warning("--- Warning: Failed to build VS Code extension: %s ---", error)
    logger.info("--- Continuing without building extension ---")

    if not vsix_path.exists():
        logger.warning("--- Warning: No pre-built VS Code extension found ---")
        logger.warning("--- VS Code extension will not be available ---")


def build_vscode_extension():
    """Builds the VS Code extension."""
    vsix_path = VSCODE_EXTENSION_DIR / VSIX_FILENAME

    if os.environ.get("SKIP_VSCODE_BUILD", "").lower() in ("1", "true", "yes"):
        _handle_skip_build(vsix_path)
        return

    if not check_node_version():
        _handle_node_version_check(vsix_path)
        return

    _build_extension_package(vsix_path)


def build(setup_kwargs):
    """This function is called by Poetry during the build process.

    `setup_kwargs` is a dictionary that will be passed to `setuptools.setup()`.
    """
    logger.info("--- Running custom Poetry build script (build_vscode.py) ---")
    build_vscode_extension()
    logger.info("--- Custom Poetry build script (build_vscode.py) finished ---")


if __name__ == "__main__":
    logger.info("Running build_vscode.py directly for testing VS Code extension packaging...")
    build_vscode_extension()
    logger.info("Direct execution of build_vscode.py finished.")
