"""Main entry point for Forge CLI with subcommand support."""

import sys

from backend.core.config import get_cli_parser
from backend.interface.gui_launcher import launch_gui_server


def _handle_help_request(parser) -> None:
    """Handle help request and display comprehensive help information."""
    parser.print_help()
    sys.exit(0)


def _normalize_arguments() -> None:
    """Normalize command line arguments."""
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] not in ["serve"]):
        sys.argv.insert(1, "serve")


def _handle_version_request(args) -> None:
    """Handle version request and exit."""
    if hasattr(args, "version") and args.version:
        sys.exit(0)


def _execute_command(args, parser) -> None:
    """Execute the appropriate command based on parsed arguments."""
    if args.command == "serve":
        launch_gui_server()
    elif args.command == "init":
        from backend.interface.cli.init_project import init_project

        init_project(args.project_name, args.template)
    else:
        parser.print_help()
        sys.exit(1)


def main() -> None:
    """Launch the CLI entry point with subcommand support."""
    parser = get_cli_parser()

    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        _handle_help_request(parser)

    _normalize_arguments()
    args = parser.parse_args()

    _handle_version_request(args)
    _execute_command(args, parser)


if __name__ == "__main__":
    main()
