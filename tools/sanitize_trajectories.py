"""Idempotent script to sanitize persisted conversation event files.

This script scans the conversation events directory (default root `sessions/`)
and also can target repository example trajectories. It will:
 - detect JSON files that contain top-level objects with `observation: "null"` or
   `action: "null"` and either remove those keys or drop the whole event from
   list-based trajectory files (like `trajectory` arrays).
 - be safe and idempotent: running it multiple times won't change already-cleaned files.

Usage:
    # Dry-run (report files that would be modified):
    python -m forge.tools.sanitize_trajectories --dry-run --paths tests/runtime/trajs

    # Apply changes to sessions directory (use carefully):
    python -m forge.tools.sanitize_trajectories --apply --paths sessions

By default it treats any file ending with `.json` or `.jsonl` under the provided
paths as candidates.
"""

from __future__ import annotations
import argparse
import json
import os
from typing import Any, Iterable, cast


def find_candidate_files(paths: Iterable[str]) -> list[str]:
    files: list[str] = []
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                files.extend(
                    (
                        os.path.join(root, fn)
                        for fn in filenames
                        if fn.lower().endswith((".json", ".jsonl"))
                    )
                )
    return files


def sanitize_json_content(obj: object) -> object | None:
    """Return sanitized object or None if the object should be dropped.

    Rules:
    - If obj is a dict representing a single event and contains `observation: 'null'`
      or `action: 'null'`, return None to indicate the event should be removed.
    - If obj is a container (list/dict), walk recursively and remove/drop offending items.
    - Otherwise, return the (possibly updated) obj.
    """
    if isinstance(obj, dict):
        return _sanitize_dict(obj)
    elif isinstance(obj, list):
        return _sanitize_list(obj)
    else:
        return _sanitize_primitive(obj)


def _sanitize_dict(obj: dict) -> object | None:
    """Sanitize a dictionary object."""
    # Check if this is a null event that should be dropped
    return None if _is_null_event(obj) else _process_dict_contents(obj)


def _is_null_event(obj: dict) -> bool:
    """Check if this is a null event that should be dropped."""
    return obj.get("observation") == "null" or obj.get("action") == "null"


def _process_dict_contents(obj: dict) -> dict:
    """Process dictionary contents recursively."""
    changed = False
    new = {}

    for k, v in obj.items():
        cleaned = sanitize_json_content(v)

        # Handle cases where cleaned value should be dropped
        if _should_drop_cleaned_value(cleaned, v, k):
            changed = True
            continue

        # Add cleaned value if it exists
        if cleaned is not None:
            if cleaned is not v:
                changed = True
            new[k] = cleaned

    return new if changed else obj


def _should_drop_cleaned_value(cleaned: object, original: object, key: str) -> bool:
    """Determine if a cleaned value should be dropped."""
    if cleaned is None:
        # Drop if it's a container type or a special key
        return isinstance(original, (dict, list)) or key in {"observation", "action"}
    return False


def _sanitize_list(obj: list) -> list:
    """Sanitize a list object."""
    new_list = []
    changed = False

    for item in obj:
        cleaned = sanitize_json_content(item)

        if cleaned is None:
            changed = True
            continue

        if cleaned is not item:
            changed = True

        new_list.append(cleaned)

    return new_list if changed else obj


def _sanitize_primitive(obj: object) -> object | None:
    """Sanitize a primitive object."""
    return None if obj == "null" else obj


def _read_file_content(path: str) -> str | None:
    """Read file content and return it, or None if failed."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[skip] Could not read {path}: {e}")
        return None


def _is_jsonl_file(path: str) -> bool:
    """Check if file is a JSONL file."""
    return path.lower().endswith(".jsonl")


def _process_jsonl_content(raw: str) -> tuple[list, list, bool]:
    """Process JSONL content and return parsed, sanitized, and changed status."""
    lines = [line for line in raw.splitlines() if line.strip()]
    parsed = [json.loads(line) for line in lines]
    sanitized = [sanitize_json_content(item) for item in parsed]
    sanitized = [s for s in sanitized if s is not None]

    changed = len(sanitized) != len(parsed) or any(
        (
            json.dumps(p, sort_keys=True) != json.dumps(s, sort_keys=True)
            for p, s in zip(parsed, sanitized)
        )
    )

    return parsed, sanitized, changed


def _write_jsonl_file(path: str, sanitized: list) -> None:
    """Write sanitized content to JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for item in sanitized:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _process_trajectory_data(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Process data with trajectory field."""
    original = json.dumps(data, sort_keys=True)
    sanitized_traj = sanitize_json_content(data["trajectory"])
    data["trajectory"] = [] if sanitized_traj is None else sanitized_traj
    changed = json.dumps(data, sort_keys=True) != original
    return data, changed


def _write_json_file(path: str, data: dict | None) -> None:
    """Write data to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        if data is None:
            json.dump({}, f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _process_regular_json_data(
    data: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    """Process regular JSON data."""
    sanitized_obj = sanitize_json_content(data)
    sanitized_dict = (
        cast(dict[str, Any], sanitized_obj) if isinstance(sanitized_obj, dict) else None
    )
    changed = sanitized_dict is None or json.dumps(
        sanitized_dict, sort_keys=True
    ) != json.dumps(data, sort_keys=True)
    return sanitized_dict, changed


def _process_jsonl_file(raw: str, path: str, apply: bool) -> bool:
    """Process JSONL file and return changed status."""
    parsed, sanitized, changed = _process_jsonl_content(raw)
    if changed and apply:
        _write_jsonl_file(path, sanitized)
    return changed


def _process_json_file(raw: str, path: str, apply: bool) -> bool:
    """Process JSON file and return changed status."""
    data = json.loads(raw)

    if (
        isinstance(data, dict)
        and "trajectory" in data
        and isinstance(data["trajectory"], list)
    ):
        # Process trajectory data
        data, changed = _process_trajectory_data(data)
        if changed and apply:
            _write_json_file(path, data)
    else:
        # Process regular JSON data
        sanitized, changed = _process_regular_json_data(data)
        if changed and apply:
            _write_json_file(path, sanitized)

    return changed


def process_file(path: str, apply: bool = False) -> bool:
    """Process a file; return True if file was changed (or would be changed in dry-run).

    If apply=True, write changes back to disk. Otherwise just report.
    """
    # Read file content
    raw = _read_file_content(path)
    if raw is None:
        return False

    try:
        if _is_jsonl_file(path):
            return _process_jsonl_file(raw, path, apply)
        else:
            return _process_json_file(raw, path, apply)

    except json.JSONDecodeError:
        print(f"[skip] Not a JSON file or invalid JSON: {path}")
        return False
    except Exception as e:
        print(f"[error] Failed processing {path}: {e}")
        return False


def main(argv: list[str] | None = None) -> int:
    """Main function for sanitizing trajectory files."""
    # Parse command line arguments
    args = _parse_arguments(argv)

    # Find candidate files
    files = find_candidate_files(args.paths)
    if not files:
        print("No candidate files found under the provided paths")
        return 0

    # Process files
    changed_files = _process_files(files, args.apply)

    # Print summary
    _print_summary(files, changed_files)

    return 0


def _parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    """Parse command line arguments."""
    p = argparse.ArgumentParser()
    p.add_argument(
        "--paths",
        "-p",
        nargs="+",
        default=["tests/runtime/trajs"],
        help="Paths to scan",
    )
    p.add_argument("--apply", action="store_true", help="Write changes to disk")
    p.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )
    return p.parse_args(argv)


def _process_files(files: list[str], apply: bool) -> list[str]:
    """Process all candidate files."""
    changed_files: list[str] = []

    for path in files:
        rel = os.path.relpath(path)
        if changed := process_file(path, apply=apply):
            changed_files.append(rel)
            action = "changed" if apply else "would change"
            print(f"[{action}] {rel}")

    return changed_files


def _print_summary(files: list[str], changed_files: list[str]):
    """Print summary of processing results."""
    print("\nSummary:")
    print(f"  scanned: {len(files)} files")
    print(f"  affected: {len(changed_files)} files")

    if changed_files:
        for f in changed_files[:20]:
            print("   -", f)


if __name__ == "__main__":
    raise SystemExit(main())
