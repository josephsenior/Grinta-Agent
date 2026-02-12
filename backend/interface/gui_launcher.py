"""GUI launcher for Forge CLI."""

import os
import subprocess
import sys
from pathlib import Path

from backend import __version__


def ensure_config_dir_exists() -> Path:
    """Ensure the Forge configuration directory exists and return its path."""
    config_dir = Path.home() / ".Forge"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def launch_gui_server(mount_cwd: bool = False, gpu: bool = False) -> None:
    """Launch the Forge GUI server locally.

    Args:
        mount_cwd: (Deprecated) Kept for backward compatibility.
        gpu: (Deprecated) Kept for backward compatibility.

    """
    print(f"🚀 Launching Forge v{__version__} GUI server...")
    print("")

    ensure_config_dir_exists()

    print("✅ Starting local Forge server...")
    print("The server will be available at: http://localhost:3000")
    print("Press Ctrl+C to stop the server.")
    print("")

    # Set environment variables for local execution
    env = os.environ.copy()
    env["FORGE_RUNTIME"] = "local"
    env["SERVE_FRONTEND"] = "true"

    try:
        # Start the server using uvicorn
        # We use the listen module which mounts the frontend and Socket.IO
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "forge.server.listen:app",
            "--host",
            "0.0.0.0",
            "--port",
            "3000",
        ]
        
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print("")
        print("❌ Failed to start Forge GUI server.")
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("")
        print("✓ Forge GUI server stopped successfully.")
        sys.exit(0)
    except Exception as e:
        print("")
        print(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)
