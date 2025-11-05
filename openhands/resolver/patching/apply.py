from __future__ import annotations

import os.path
import subprocess
import tempfile
from typing import TYPE_CHECKING

from .exceptions import HunkApplyException, SubprocessException
from .snippets import remove, which

if TYPE_CHECKING:
    from .patch import Change, diffobj


def _apply_diff_with_subprocess(
    diff: diffobj,
    lines: list[str],
    reverse: bool = False,
) -> tuple[list[str], list[str] | None]:
    patchexec = which("patch")
    if not patchexec:
        msg = "cannot find patch program"
        raise SubprocessException(msg, code=-1)
    tempdir = tempfile.gettempdir()
    filepath = os.path.join(tempdir, f"wtp-{hash(diff.header)}")
    oldfilepath = f"{filepath}.old"
    newfilepath = f"{filepath}.new"
    rejfilepath = f"{filepath}.rej"
    patchfilepath = f"{filepath}.patch"
    with open(oldfilepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(patchfilepath, "w", encoding="utf-8") as f:
        f.write(diff.text)
    args = [
        patchexec,
        "--reverse" if reverse else "--forward",
        "--quiet",
        "--no-backup-if-mismatch",
        "-o",
        newfilepath,
        "-i",
        patchfilepath,
        "-r",
        rejfilepath,
        oldfilepath,
    ]
    ret = subprocess.call(args)
    with open(newfilepath, encoding="utf-8") as f:
        lines = f.read().splitlines()
    try:
        with open(rejfilepath, encoding="utf-8") as f:
            rejlines = f.read().splitlines()
    except OSError:
        rejlines = None
    remove(oldfilepath)
    remove(newfilepath)
    remove(rejfilepath)
    remove(patchfilepath)
    if ret != 0:
        msg = "patch program failed"
        raise SubprocessException(msg, code=ret)
    return (lines, rejlines)


def _reverse(changes: list[Change]) -> list[Change]:

    def _reverse_change(c: Change) -> Change:
        return c._replace(old=c.new, new=c.old)

    return [_reverse_change(c) for c in changes]


def _validate_context_line(old: int, line: str, lines: list[str], n_lines: int, hunk) -> None:
    """Validate that a context line matches the source."""
    if old > n_lines:
        msg = f'context line {old}, "{line}" does not exist in source'
        raise HunkApplyException(
            msg,
            hunk=hunk,
        )

    if lines[old - 1] != line:
        normalized_line = " ".join(line.split())
        normalized_source = " ".join(lines[old - 1].split())
        if normalized_line != normalized_source:
            msg = f'context line {old}, "{line}" does not match "{lines[old - 1]}"'
            raise HunkApplyException(
                msg,
                hunk=hunk,
            )


def _validate_all_context_lines(changes, lines: list[str], n_lines: int) -> None:
    """Validate all context lines before applying changes."""
    for old, _new, line, hunk in changes:
        if old is not None and line is not None:
            _validate_context_line(old, line, lines, n_lines, hunk)


def _apply_changes_to_lines(changes, lines: list[str]) -> list[str]:
    """Apply changes to lines (deletions and insertions)."""
    r = 0  # Deletions counter
    i = 0  # Insertions counter

    for old, new, line, _hunk in changes:
        if old is not None and new is None:
            # Deletion
            del lines[old - 1 - r + i]
            r += 1
        elif old is None and new is not None:
            # Insertion
            lines.insert(new - 1, line)
            i += 1

    return lines


def apply_diff(diff: diffobj, text: str | list[str], reverse: bool = False, use_patch: bool = False) -> list[str]:
    lines = text.splitlines() if isinstance(text, str) else list(text)

    if use_patch:
        lines, _ = _apply_diff_with_subprocess(diff, lines, reverse)
        return lines

    n_lines = len(lines)
    changes = _reverse(diff.changes) if reverse else diff.changes

    # Validate all context lines first
    _validate_all_context_lines(changes, lines, n_lines)

    # Apply changes
    return _apply_changes_to_lines(changes, lines)
