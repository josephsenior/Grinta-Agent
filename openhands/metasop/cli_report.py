from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LOGS_DIR = Path("logs")
LAST_RUN_FILE = LOGS_DIR / "metasop_last_run.json"
RUNS_NDJSON = LOGS_DIR / "metasop_runs.ndjson"


def load_last() -> dict[str, Any]:
    """Load the last MetaSOP run data from the JSON file.

    Returns:
        dict[str, Any]: The last run data as a dictionary.

    Raises:
        SystemExit: If no last run file is found.
    """
    if not LAST_RUN_FILE.exists():
        msg = "No last run file found"
        raise SystemExit(msg)
    return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))


def load_runs(limit: int | None = None) -> list[dict[str, Any]]:
    """Load historical MetaSOP run data from the NDJSON file.

    Args:
        limit: Optional limit on the number of recent runs to load.

    Returns:
        list[dict[str, Any]]: List of run data dictionaries, optionally limited to recent runs.
    """
    if not RUNS_NDJSON.exists():
        return []
    lines = RUNS_NDJSON.read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    if limit:
        records = records[-limit:]
    return records


def fmt_table(rows: list[list[str]]) -> str:
    """Format a list of rows into a table string with proper column alignment.

    Args:
        rows: List of rows, where each row is a list of strings representing columns.

    Returns:
        str: Formatted table string with aligned columns and header separator.
    """
    widths = [max(len(col) for col in colset) for colset in zip(*rows)]
    out_lines = []
    for r_i, row in enumerate(rows):
        line = "  ".join((c.ljust(widths[i]) for i, c in enumerate(row)))
        out_lines.append(line)
        if r_i == 0:
            out_lines.append("  ".join("-" * w for w in widths))
    return "\n".join(out_lines)


def report_last(args) -> None:
    """Generate a report for the last MetaSOP run.

    Args:
        args: Command line arguments (unused but required by argparse).
    """
    data = load_last()
    report = data.get("report", {})
    events = report.get("events", [])
    table_rows = [["STEP", "ROLE", "STATUS", "RETRIES", "MS", "TOKENS", "MODEL", "FAILURE_TYPE"]]
    table_rows.extend(
        [
            str(evt.get("step_id")),
            str(evt.get("role")),
            str(evt.get("status")),
            str(evt.get("retries", "")),
            str(evt.get("duration_ms", "")),
            str(evt.get("total_tokens", "")),
            str(evt.get("model", "")),
            str(evt.get("failure_type", "") or (evt.get("meta") or {}).get("failure_type", "")),
        ]
        for evt in events
        if evt.get("status") in {"executed", "executed_shaped", "failed", "skipped"}
    )
    if skipped := [e for e in events if e.get("status") == "skipped"]:
        for _s in skipped:
            pass


def _calculate_aggregate_stats(recs: list[dict[str, Any]]) -> tuple[int, int, float, float, float]:
    """Calculate aggregate statistics from run records."""
    total = len(recs)
    ok_count = sum(bool(r.get("ok")) for r in recs)
    avg_tokens = sum(r.get("tokens", 0) for r in recs) / max(total, 1)
    avg_duration = sum(r.get("duration_ms", 0) for r in recs) / max(total, 1)
    avg_retries = sum(r.get("retries", 0) for r in recs) / max(total, 1)
    return total, ok_count, avg_tokens, avg_duration, avg_retries


def _collect_failure_types(recs: list[dict[str, Any]]) -> dict[str, int]:
    """Collect and count failure types from run records."""
    failure_counter = {}
    for r in recs:
        se = r.get("step_events", [])
        for ev in se:
            if ev.get("status") == "failed":
                meta = ev.get("meta") or {}
                ftype = None
                if isinstance(meta, dict):
                    ftype = meta.get("failure_type") or meta.get("type") or ev.get("reason")
                if ftype:
                    failure_counter[ftype] = failure_counter.get(ftype, 0) + 1
    return failure_counter


def report_aggregate(args) -> None:
    """Generate an aggregate report across multiple MetaSOP runs.

    Args:
        args: Command line arguments containing limit and other options.
    """
    recs = load_runs(args.limit)
    if not recs:
        return

    # Calculate statistics
    _total, _ok_count, _avg_tokens, _avg_duration, _avg_retries = _calculate_aggregate_stats(recs)

    # Print aggregate stats

    if failure_counter := _collect_failure_types(recs):
        for _k, _v in sorted(failure_counter.items(), key=lambda x: x[1], reverse=True)[:10]:
            pass


def main() -> None:
    """Main entry point for the MetaSOP reporting CLI.

    Sets up command line argument parsing and executes the appropriate
    reporting function based on user input.
    """
    ap = argparse.ArgumentParser(description="MetaSOP reporting CLI")
    sub = ap.add_subparsers(required=True)
    sp_last = sub.add_parser("last", help="Show last run detailed table")
    sp_last.set_defaults(func=report_last)
    sp_hist = sub.add_parser("hist", help="Show aggregate stats from NDJSON history")
    sp_hist.add_argument("--limit", type=int, help="Limit to last N records")
    sp_hist.set_defaults(func=report_aggregate)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
