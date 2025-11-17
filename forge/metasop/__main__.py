"""Command-line entry point for MetaSOP maintenance utilities."""

from __future__ import annotations

import argparse
import logging
from typing import NoReturn

from forge.core.io import print_json_stdout

from .discovery import list_sop_templates
from .metrics import get_metrics_registry
from .validation import validate_manifest_file, validate_template_file

logger = logging.getLogger(__name__)


def main() -> None:
    """Main function for MetaSOP utilities."""
    parser = _create_argument_parser()
    args = parser.parse_args()
    _handle_command(args)


def _create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="MetaSOP utilities")
    sub = parser.add_subparsers(dest="command")

    _add_list_parser(sub)
    _add_validate_manifest_parser(sub)
    _add_validate_template_parser(sub)
    sub.add_parser(
        "metrics-snapshot",
        help="Print in-process metrics snapshot (if process collected events)",
    )

    return parser


def _add_list_parser(sub) -> None:
    """Add list command parser."""
    ls = sub.add_parser("list", help="List available SOP templates")
    ls.add_argument("--json", action="store_true", help="Output JSON instead of text")
    ls.add_argument("--paths", action="store_true", help="Include filesystem paths")


def _add_validate_manifest_parser(sub) -> None:
    """Add validate-manifest command parser."""
    vm = sub.add_parser("validate-manifest", help="Validate a run manifest JSON file")
    vm.add_argument("path", help="Path to manifest JSON")


def _add_validate_template_parser(sub) -> None:
    """Add validate-template command parser."""
    vt = sub.add_parser("validate-template", help="Validate a SOP template file (YAML)")
    vt.add_argument("path", help="Template file path or template name")


def _handle_command(args) -> None:
    """Handle the parsed command."""
    if args.command == "list":
        _handle_list_command(args)
    elif args.command == "validate-manifest":
        _handle_validate_manifest_command(args)
    elif args.command == "validate-template":
        _handle_validate_template_command(args)
    elif args.command == "metrics-snapshot":
        _handle_metrics_snapshot_command()
    else:
        _print_help()


def _handle_list_command(args) -> None:
    """Handle the list command."""
    templates = list_sop_templates()
    if args.json:
        _output_templates_json(templates, args.paths)
    else:
        _output_templates_text(templates, args.paths)


def _output_templates_json(templates, include_paths) -> None:
    """Output templates in JSON format."""
    payload = [
        {
            "name": t.name,
            **({"description": t.description} if t.description else {}),
            **({"path": str(t.path)} if include_paths else {}),
        }
        for t in templates
    ]
    print_json_stdout(payload, pretty=True)


def _output_templates_text(templates, include_paths) -> None:
    """Output templates in text format."""
    if not templates:
        logger.info("No SOP templates found.")
        return

    width = max(len(t.name) for t in templates)
    for t in templates:
        line = t.name.ljust(width)
        if t.description:
            line += f"  - {t.description}"
        if include_paths:
            line += f"  ({t.path})"
        logger.info(line)


def _handle_validate_manifest_command(args) -> NoReturn:
    """Handle the validate-manifest command."""
    ok, errs = validate_manifest_file(args.path)
    if ok:
        logger.info("Manifest OK")
        raise SystemExit(0)
    logger.error("Manifest INVALID:")
    for e in errs:
        logger.error(" - %s", e)
    raise SystemExit(1)


def _handle_validate_template_command(args) -> NoReturn:
    """Handle the validate-template command."""
    ok, errs = validate_template_file(args.path)
    if ok:
        logger.info("Template OK")
        raise SystemExit(0)
    logger.error("Template INVALID:")
    for e in errs:
        logger.error(" - %s", e)
    raise SystemExit(1)


def _handle_metrics_snapshot_command() -> NoReturn:
    """Handle the metrics-snapshot command."""
    snap = get_metrics_registry().snapshot()
    print_json_stdout(snap, pretty=True)
    raise SystemExit(0)


def _print_help() -> None:
    """Print help message."""
    import argparse

    parser = argparse.ArgumentParser(description="MetaSOP utilities")
    parser.print_help()


if __name__ == "__main__":
    main()
