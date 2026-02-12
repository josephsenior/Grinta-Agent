"""Command-line interface for forge.

This module now primarily serves as a placeholder as the TUI has been removed.
The main entry point is now the GUI server.
"""

from __future__ import annotations

import logging

from backend.core.logger import forge_logger as logger

def run_cli_command(args) -> None:
    """Legacy entry point for CLI command.
    
    This is now deprecated and should not be used as the TUI has been removed.
    """
    logger.warning("The CLI TUI has been removed. Please use 'forge serve' to launch the GUI.")
    print("The CLI TUI has been removed. Please use 'forge serve' to launch the GUI.")
