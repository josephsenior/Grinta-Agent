"""Main entry point for Forge CLI with subcommand support."""

import sys

from backend.interface.gui_launcher import launch_gui_server
from backend.core.config import get_cli_parser
from backend.core.config.arg_utils import get_subparser


def _handle_help_request(parser) -> None:
    """Handle help request and display comprehensive help information."""
    get_subparser(parser, "cli")
    sys.exit(0)


def _normalize_arguments() -> None:
    """Normalize command line arguments for backward compatibility."""
    if len(sys.argv) == 1 or (
        len(sys.argv) > 1 and sys.argv[1] not in ["cli", "serve"]
    ):
        sys.argv.insert(1, "serve")


def _handle_version_request(args) -> None:
    """Handle version request and exit."""
    if hasattr(args, "version") and args.version:
        sys.exit(0)


def _execute_command(args, parser) -> None:
    """Execute the appropriate command based on parsed arguments."""
    if args.command == "serve":
        launch_gui_server(mount_cwd=args.mount_cwd, gpu=args.gpu)
    elif args.command == "cli":
        print("The 'cli' command is deprecated and the TUI has been removed.")
        print("Launching the GUI server instead...")
        launch_gui_server(mount_cwd=args.mount_cwd, gpu=args.gpu)
    else:
        parser.print_help()
        sys.exit(1)


def main() -> None:
    """Launch the CLI entry point with subcommand support and backward compatibility."""
    parser = get_cli_parser()

    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        _handle_help_request(parser)

    _normalize_arguments()
    args = parser.parse_args()

    _handle_version_request(args)
    _execute_command(args, parser)


if __name__ == "__main__":
    main()
