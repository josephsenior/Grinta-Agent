from __future__ import annotations

import base64
import re
import zlib
from collections import namedtuple
from typing import TYPE_CHECKING

from . import exceptions
from .snippets import findall_regex, split_by_regex

if TYPE_CHECKING:
    from collections.abc import Iterable

header = namedtuple("header", "index_path old_path old_version new_path new_version")
diffobj = namedtuple("diffobj", "header changes text")
Change = namedtuple("Change", "old new line hunk")
file_timestamp_str = "(.+?)(?:\t|:|  +)(.*)"
diffcmd_header = re.compile("^diff.* (.+) (.+)$")
unified_header_index = re.compile("^Index: (.+)$")
unified_header_old_line = re.compile(f"^--- {file_timestamp_str}$")
unified_header_new_line = re.compile("^\\+\\+\\+ " + file_timestamp_str + "$")
unified_hunk_start = re.compile("^@@ -(\\d+),?(\\d*) \\+(\\d+),?(\\d*) @@(.*)$")
unified_change = re.compile("^([-+ ])(.*)$", re.MULTILINE)
context_header_old_line = re.compile("^\\*\\*\\* " + file_timestamp_str + "$")
context_header_new_line = re.compile(f"^--- {file_timestamp_str}$")
context_hunk_start = re.compile("^\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*\\*$")
context_hunk_old = re.compile("^\\*\\*\\* (\\d+),?(\\d*) \\*\\*\\*\\*$")
context_hunk_new = re.compile("^--- (\\d+),?(\\d*) ----$")
context_change = re.compile("^([-+ !]) (.*)$")
ed_hunk_start = re.compile("^(\\d+),?(\\d*)([acd])$")
ed_hunk_end = re.compile("^.$")
rcs_ed_hunk_start = re.compile("^([ad])(\\d+) ?(\\d*)$")
default_hunk_start = re.compile("^(\\d+),?(\\d*)([acd])(\\d+),?(\\d*)$")
default_hunk_mid = re.compile("^---$")
default_change = re.compile("^([><]) (.*)$")
git_diffcmd_header = re.compile("^diff --git a/(.+) b/(.+)$")
git_header_index = re.compile("^index ([a-f0-9]+)..([a-f0-9]+) ?(\\d*)$")
git_header_old_line = re.compile("^--- (.+)$")
git_header_new_line = re.compile("^\\+\\+\\+ (.+)$")
git_header_file_mode = re.compile("^(new|deleted) file mode \\d{6}$")
git_header_binary_file = re.compile("^Binary files (.+) and (.+) differ")
git_binary_patch_start = re.compile("^GIT binary patch$")
git_binary_literal_start = re.compile("^literal (\\d+)$")
git_binary_delta_start = re.compile("^delta (\\d+)$")
base85string = re.compile("^[0-9A-Za-z!#$%&()*+;<=>?@^_`{|}~-]+$")
bzr_header_index = re.compile("=== (.+)")
bzr_header_old_line = unified_header_old_line
bzr_header_new_line = unified_header_new_line
svn_header_index = unified_header_index
svn_header_timestamp_version = re.compile("\\((?:working copy|revision (\\d+))\\)")
svn_header_timestamp = re.compile(".*(\\(.*\\))$")
cvs_header_index = unified_header_index
cvs_header_rcs = re.compile("^RCS file: (.+)(?:,\\w{1}$|$)")
cvs_header_timestamp = re.compile("(.+)\\t([\\d.]+)")
cvs_header_timestamp_colon = re.compile(":([\\d.]+)\\t(.+)")
old_cvs_diffcmd_header = re.compile("^diff.* (.+):(.*) (.+):(.*)$")


def parse_patch(text: str | list[str]) -> Iterable[diffobj]:
    lines = text.splitlines() if isinstance(text, str) else text
    lines = [x if len(x) == 0 else x.splitlines()[0] for x in lines]
    check = [
        unified_header_index,
        diffcmd_header,
        cvs_header_rcs,
        git_header_index,
        context_header_old_line,
        unified_header_old_line,
    ]
    diffs = []
    for c in check:
        diffs = split_by_regex(lines, c)
        if len(diffs) > 1:
            break
    for diff in diffs:
        difftext = "\n".join(diff) + "\n"
        h = parse_header(diff)
        d = parse_diff(diff)
        if h or d:
            yield diffobj(header=h, changes=d, text=difftext)


def parse_header(text: str | list[str]) -> header | None:
    h = parse_scm_header(text)
    if h is None:
        h = parse_diff_header(text)
    return h


def parse_scm_header(text: str | list[str]) -> header | None:
    lines = text.splitlines() if isinstance(text, str) else text
    check = [
        (git_header_index, parse_git_header),
        (old_cvs_diffcmd_header, parse_cvs_header),
        (cvs_header_rcs, parse_cvs_header),
        (svn_header_index, parse_svn_header),
    ]
    for regex, parser in check:
        diffs = findall_regex(lines, regex)
        if len(diffs) > 0:
            git_opt = findall_regex(lines, git_diffcmd_header)
            if len(git_opt) > 0:
                res = parser(lines)
                if res:
                    old_path = res.old_path
                    new_path = res.new_path
                    old_path = old_path.removeprefix("a/")
                    new_path = new_path.removeprefix("b/")
                    return header(
                        index_path=res.index_path,
                        old_path=old_path,
                        old_version=res.old_version,
                        new_path=new_path,
                        new_version=res.new_version,
                    )
            else:
                res = parser(lines)
            return res
    return None


def parse_diff_header(text: str | list[str]) -> header | None:
    lines = text.splitlines() if isinstance(text, str) else text
    check = [
        (unified_header_new_line, parse_unified_header),
        (context_header_old_line, parse_context_header),
        (diffcmd_header, parse_diffcmd_header),
        (git_header_new_line, parse_git_header),
    ]
    for regex, parser in check:
        diffs = findall_regex(lines, regex)
        if len(diffs) > 0:
            return parser(lines)
    return None


def parse_diff(text: str | list[str]) -> list[Change] | None:
    lines = text.splitlines() if isinstance(text, str) else text
    check = [
        (unified_hunk_start, parse_unified_diff),
        (context_hunk_start, parse_context_diff),
        (default_hunk_start, parse_default_diff),
        (ed_hunk_start, parse_ed_diff),
        (rcs_ed_hunk_start, parse_rcs_ed_diff),
        (git_binary_patch_start, parse_git_binary_diff),
    ]
    for hunk, parser in check:
        diffs = findall_regex(lines, hunk)
        if len(diffs) > 0:
            return parser(lines)
    return None


def _normalize_git_path(path: str) -> str:
    """Normalize git path by removing a/ or b/ prefix."""
    return path[2:] if path.startswith(("a/", "b/")) else path


def _process_git_diffcmd_header(line: str) -> tuple[str | None, str | None]:
    """Process git diff command header line."""
    if hm := git_diffcmd_header.match(line):
        return hm.group(1), hm.group(2)
    return None, None


def _process_git_header_index(line: str) -> tuple[str | None, str | None]:
    """Process git header index line."""
    if g := git_header_index.match(line):
        return g.group(1), g.group(2)
    return None, None


def _process_git_path_lines(line: str) -> tuple[str | None, str | None]:
    """Process git old/new path lines."""
    old_path = None
    new_path = None

    if o := git_header_old_line.match(line):
        old_path = o.group(1)
    if n := git_header_new_line.match(line):
        new_path = n.group(1)
    if binary := git_header_binary_file.match(line):
        old_path = binary.group(1)
        new_path = binary.group(2)

    return old_path, new_path


def _create_header_from_paths(old_path: str, new_path: str, old_version: str | None, new_version: str | None) -> header:
    """Create header from normalized paths and versions."""
    old_path = _normalize_git_path(old_path)
    new_path = _normalize_git_path(new_path)
    return header(
        index_path=None,
        old_path=old_path,
        old_version=old_version,
        new_path=new_path,
        new_version=new_version,
    )


def _create_header_from_cmd_paths(cmd_old_path: str, cmd_new_path: str, old_version: str, new_version: str) -> header:
    """Create header from command paths and versions."""
    cmd_old_path = _normalize_git_path(cmd_old_path)
    cmd_new_path = _normalize_git_path(cmd_new_path)

    old_path = "/dev/null" if old_version == "0000000" else cmd_old_path
    new_path = "/dev/null" if new_version == "0000000" else cmd_new_path

    return header(
        index_path=None,
        old_path=old_path,
        old_version=old_version,
        new_path=new_path,
        new_version=new_version,
    )


def parse_git_header(text: str | list[str]) -> header | None:
    """Parse git header from text or list of lines.

    Extracts file paths and version information from git diff header.
    Processes diff command headers, index lines, and path lines.

    Args:
        text: Git diff header text as string or list of lines

    Returns:
        header object with old/new paths and versions, or None if invalid
    """
    lines = text.splitlines() if isinstance(text, str) else text
    state = _GitHeaderParsingState()

    # Process all lines
    for line in lines:
        if header := _try_process_git_header_line(line, state):
            return header

    # Try to build from command paths
    return _try_build_header_from_state(state)


def _try_process_git_header_line(line: str, state: _GitHeaderParsingState) -> header | None:
    """Try to process a git header line and return header if complete.

    Args:
        line: Line to process
        state: Parsing state

    Returns:
        Header if complete, None otherwise
    """
    # Try each processor
    if _process_git_diffcmd_header_line(line, state):
        return None

    if _process_git_header_index_line(line, state):
        return None

    # Check if path line completes the header
    if _process_git_path_lines_line(line, state) and state.old_path and state.new_path:
        return _create_header_from_paths(
            state.old_path,
            state.new_path,
            state.old_version,
            state.new_version,
        )

    return None


def _try_build_header_from_state(state: _GitHeaderParsingState) -> header | None:
    """Try to build header from parsing state.

    Args:
        state: Parsing state

    Returns:
        Header if state is complete, None otherwise
    """
    if state.cmd_old_path and state.cmd_new_path and state.old_version and state.new_version:
        return _create_header_from_cmd_paths(
            state.cmd_old_path,
            state.cmd_new_path,
            state.old_version,
            state.new_version,
        )
    return None


class _GitHeaderParsingState:
    """State for parsing git header information."""

    def __init__(self) -> None:
        self.old_version = None
        self.new_version = None
        self.old_path = None
        self.new_path = None
        self.cmd_old_path = None
        self.cmd_new_path = None


def _process_git_diffcmd_header_line(line: str, state: _GitHeaderParsingState) -> bool:
    """Process git diff command header line. Returns True if processed."""
    cmd_old, cmd_new = _process_git_diffcmd_header(line)
    if cmd_old and cmd_new:
        state.cmd_old_path = cmd_old
        state.cmd_new_path = cmd_new
        return True
    return False


def _process_git_header_index_line(line: str, state: _GitHeaderParsingState) -> bool:
    """Process git header index line. Returns True if processed."""
    old_ver, new_ver = _process_git_header_index(line)
    if old_ver and new_ver:
        state.old_version = old_ver
        state.new_version = new_ver
        return True
    return False


def _process_git_path_lines_line(line: str, state: _GitHeaderParsingState) -> bool:
    """Process git path lines. Returns True if paths were found."""
    old_p, new_p = _process_git_path_lines(line)
    if old_p:
        state.old_path = old_p
    if new_p:
        state.new_path = new_p
    return old_p is not None or new_p is not None


def _extract_version_from_string(version_str: str) -> int | None:
    """Extract version number from version string."""
    match = svn_header_timestamp_version.match(version_str)
    return int(match.group(1)) if match and match.group(1) else None


def _extract_version_from_path(path: str) -> tuple[str, int | None]:
    """Extract version from path by removing timestamp and parsing version."""
    if ts_match := svn_header_timestamp.match(path):
        path_without_timestamp = path[: -len(ts_match.group(1))]
        version = _extract_version_from_string(ts_match.group(1))
        return path_without_timestamp, version
    return path, None


def _process_old_path_and_version(diff_header) -> tuple[str | None, int | None]:
    """Process old path and version from diff header."""
    opath = diff_header.old_path
    over = diff_header.old_version

    if over:
        over = _extract_version_from_string(over)
    elif opath:
        opath, over = _extract_version_from_path(opath)

    return opath, over


def _process_new_path_and_version(diff_header) -> tuple[str | None, int | None]:
    """Process new path and version from diff header."""
    npath = diff_header.new_path
    nver = diff_header.new_version

    if nver:
        nver = _extract_version_from_string(nver)
    elif npath:
        npath, nver = _extract_version_from_path(npath)

    return npath, nver


def _create_default_header(index_path: str) -> header:
    """Create a default header when diff header is not available."""
    return header(index_path=index_path, old_path=index_path, old_version=None, new_path=index_path, new_version=None)


def _process_svn_header_line(lines: list[str]) -> header | None:
    """Process a single SVN header line."""
    if not lines:
        return None

    i = svn_header_index.match(lines[0])
    del lines[0]

    if not i:
        return None

    diff_header = parse_diff_header(lines)
    if not diff_header:
        return _create_default_header(i.group(1))

    # Process old path and version
    opath, over = _process_old_path_and_version(diff_header)

    # Process new path and version
    npath, nver = _process_new_path_and_version(diff_header)

    # Ensure versions are integers or None
    if not isinstance(over, int):
        over = None
    if not isinstance(nver, int):
        nver = None

    return header(index_path=i.group(1), old_path=opath, old_version=over, new_path=npath, new_version=nver)


def parse_svn_header(text: str | list[str]) -> header | None:
    """Parse SVN header from text."""
    lines = text.splitlines() if isinstance(text, str) else text
    headers = findall_regex(lines, svn_header_index)

    if len(headers) == 0:
        return None

    while len(lines) > 0:
        if result := _process_svn_header_line(lines):
            return result

    return None


def parse_cvs_header(text: str | list[str]) -> header | None:
    """Parse CVS header from text."""
    lines = text.splitlines() if isinstance(text, str) else text
    headers = findall_regex(lines, cvs_header_rcs)
    headers_old = findall_regex(lines, old_cvs_diffcmd_header)

    if headers:
        return _parse_cvs_header_rcs(lines)
    if headers_old:
        return _parse_old_cvs_header(lines)

    return None


def _parse_cvs_header_rcs(lines: list[str]) -> header | None:
    """Parse CVS header with RCS format."""
    while lines:
        i = cvs_header_index.match(lines[0])
        del lines[0]
        if not i:
            continue

        if diff_header := parse_diff_header(lines):
            old_version = _extract_version_from_timestamp(diff_header.old_version)
            new_version = _extract_version_from_timestamp(diff_header.new_version)

            return header(
                index_path=i.group(1),
                old_path=diff_header.old_path,
                old_version=old_version,
                new_path=diff_header.new_path,
                new_version=new_version,
            )

        return header(
            index_path=i.group(1),
            old_path=i.group(1),
            old_version=None,
            new_path=i.group(1),
            new_version=None,
        )

    return None


def _parse_old_cvs_header(lines: list[str]) -> header | None:
    """Parse old CVS header format."""
    while lines:
        i = cvs_header_index.match(lines[0])
        del lines[0]
        if not i:
            continue

        d = old_cvs_diffcmd_header.match(lines[0])
        if not d:
            return header(
                index_path=i.group(1),
                old_path=i.group(1),
                old_version=None,
                new_path=i.group(1),
                new_version=None,
            )

        parse_diff_header(lines)
        over = d.group(2) or None
        nver = d.group(4) or None

        return header(
            index_path=i.group(1),
            old_path=d.group(1),
            old_version=over,
            new_path=d.group(3),
            new_version=nver,
        )

    return None


def _extract_version_from_timestamp(version: str | None) -> str | None:
    """Extract version from timestamp string."""
    if not version:
        return None

    if oend := cvs_header_timestamp.match(version):
        return oend.group(2)

    if oend_c := cvs_header_timestamp_colon.match(version):
        return oend_c.group(1)

    return version


def parse_diffcmd_header(text: str | list[str]) -> header | None:
    lines = text.splitlines() if isinstance(text, str) else text
    headers = findall_regex(lines, diffcmd_header)
    if len(headers) == 0:
        return None
    while len(lines) > 0:
        d = diffcmd_header.match(lines[0])
        del lines[0]
        if d:
            return header(index_path=None, old_path=d.group(1), old_version=None, new_path=d.group(2), new_version=None)
    return None


def parse_unified_header(text: str | list[str]) -> header | None:
    lines = text.splitlines() if isinstance(text, str) else text
    headers = findall_regex(lines, unified_header_new_line)
    if len(headers) == 0:
        return None
    while len(lines) > 1:
        o = unified_header_old_line.match(lines[0])
        del lines[0]
        if o:
            n = unified_header_new_line.match(lines[0])
            del lines[0]
            if n:
                over = o.group(2)
                if len(over) == 0:
                    over = None
                nver = n.group(2)
                if len(nver) == 0:
                    nver = None
                return header(
                    index_path=None,
                    old_path=o.group(1),
                    old_version=over,
                    new_path=n.group(1),
                    new_version=nver,
                )
    return None


def parse_context_header(text: str | list[str]) -> header | None:
    lines = text.splitlines() if isinstance(text, str) else text
    headers = findall_regex(lines, context_header_old_line)
    if len(headers) == 0:
        return None
    while len(lines) > 1:
        o = context_header_old_line.match(lines[0])
        del lines[0]
        if o:
            n = context_header_new_line.match(lines[0])
            del lines[0]
            if n:
                over = o.group(2)
                if len(over) == 0:
                    over = None
                nver = n.group(2)
                if len(nver) == 0:
                    nver = None
                return header(
                    index_path=None,
                    old_path=o.group(1),
                    old_version=over,
                    new_path=n.group(1),
                    new_version=nver,
                )
    return None


def _parse_default_hunk_header(match) -> tuple[int, int, int, int]:
    """Parse hunk header to extract old/new line numbers and lengths."""
    old = int(match.group(1))
    old_len = int(match.group(2)) - old + 1 if len(match.group(2)) > 0 else 0
    new = int(match.group(4))
    new_len = int(match.group(5)) - new + 1 if len(match.group(5)) > 0 else 0
    return old, old_len, new, new_len


def _process_default_change_line(
    kind: str, line: str, old: int, new: int, r: int, i: int, old_len: int, new_len: int, hunk_n: int,
) -> tuple[Change | None, int, int]:
    """Process a change line and return change object with updated counters."""
    if kind == "<" and (r != old_len or r == 0):
        return Change(old + r, None, line, hunk_n), r + 1, i
    if kind == ">" and (i != new_len or i == 0):
        return Change(None, new + i, line, hunk_n), r, i + 1
    return None, r, i


def parse_default_diff(text: str | list[str]) -> list[Change] | None:
    lines = text.splitlines() if isinstance(text, str) else text
    changes = []
    hunks = split_by_regex(lines, default_hunk_start)

    old, new, old_len, new_len = 0, 0, 0, 0

    for hunk_n, hunk in enumerate(hunks):
        if not len(hunk):
            continue

        r, i = 0, 0
        while len(hunk) > 0:
            h = default_hunk_start.match(hunk[0])
            c = default_change.match(hunk[0])
            del hunk[0]

            if h:
                old, old_len, new, new_len = _parse_default_hunk_header(h)
            elif c:
                kind = c.group(1)
                line = c.group(2)
                change, r, i = _process_default_change_line(kind, line, old, new, r, i, old_len, new_len, hunk_n)
                if change:
                    changes.append(change)

    return changes or None


def parse_unified_diff(text: str | list[str]) -> list[Change] | None:
    """Parse a unified diff into a list of changes."""
    lines = text.splitlines() if isinstance(text, str) else text
    changes = []
    hunks = split_by_regex(lines, unified_hunk_start)

    for hunk_n, hunk in enumerate(hunks):
        hunk_changes = _parse_single_hunk(hunk, hunk_n)
        changes.extend(hunk_changes)

    return changes or None


def _parse_single_hunk(hunk: list[str], hunk_n: int) -> list[Change]:
    """Parse a single hunk from the unified diff."""
    # Parse hunk header
    old, old_len, new, new_len = _parse_hunk_header(hunk)

    # Parse hunk lines
    return _parse_hunk_lines(hunk, old, old_len, new, new_len, hunk_n)


def _parse_hunk_header(hunk: list[str]) -> tuple[int, int, int, int]:
    """Parse the hunk header to extract line numbers and lengths."""
    old = 0
    old_len = 0
    new = 0
    new_len = 0

    while hunk:
        h = unified_hunk_start.match(hunk[0])
        del hunk[0]
        if h:
            old = int(h.group(1))
            old_len = int(h.group(2)) if len(h.group(2)) > 0 else 1
            new = int(h.group(3))
            new_len = int(h.group(4)) if len(h.group(4)) > 0 else 1
            break

    return old, old_len, new, new_len


def _parse_hunk_lines(hunk: list[str], old: int, old_len: int, new: int, new_len: int, hunk_n: int) -> list[Change]:
    """Parse the lines within a unified diff hunk.

    Processes additions (+), deletions (-), and context lines ( ) to build
    a list of Change objects representing the modifications.

    Args:
        hunk: List of hunk lines to parse
        old: Starting line number in old file
        old_len: Number of lines in old file section
        new: Starting line number in new file
        new_len: Number of lines in new file section
        hunk_n: Hunk number for tracking

    Returns:
        List of Change objects
    """
    changes = []
    r = 0  # old line counter
    i = 0  # new line counter

    for n in hunk:
        kind, line = _extract_line_kind_and_content(n)
        change, r_delta, i_delta = _process_hunk_line(kind, line, old, new, r, i, old_len, new_len, hunk_n)

        if change:
            changes.append(change)
        r += r_delta
        i += i_delta

    return changes


def _extract_line_kind_and_content(n: str) -> tuple[str, str]:
    """Extract line kind and content from hunk line.

    Args:
        n: Hunk line

    Returns:
        Tuple of (kind, line_content)
    """
    kind = n[0] if len(n) > 0 else " "
    line = n[1:] if len(n) > 1 else ""
    return kind, line


def _process_hunk_line(
    kind: str,
    line: str,
    old: int,
    new: int,
    r: int,
    i: int,
    old_len: int,
    new_len: int,
    hunk_n: int,
) -> tuple[Change | None, int, int]:
    """Process a single hunk line and return change with deltas.

    Args:
        kind: Line kind (+, -, or space)
        line: Line content
        old: Old file starting line
        new: New file starting line
        r: Current old line counter
        i: Current new line counter
        old_len: Old file length
        new_len: New file length
        hunk_n: Hunk number

    Returns:
        Tuple of (change, r_delta, i_delta)
    """
    if kind == "-" and (r != old_len or r == 0):
        return Change(old + r, None, line, hunk_n), 1, 0
    if kind == "+" and (i != new_len or i == 0):
        return Change(None, new + i, line, hunk_n), 0, 1
    if kind == " ":
        return Change(old + r, new + i, line, hunk_n), 1, 1

    return None, 0, 0


def _parse_removal_hunk(old_hunk: list[str], old: int, old_len: int, hunk_n: int, changes: list[Change]) -> None:
    """Parse a hunk with only removals."""
    msg = "Got unexpected change in removal hunk: "
    j = 0
    while old_hunk:
        c = context_change.match(old_hunk[0])
        del old_hunk[0]
        if not c:
            continue
        kind = c.group(1)
        line = c.group(2)
        if kind == "-" and (j != old_len or j == 0):
            changes.append(Change(old + j, None, line, hunk_n))
            j += 1
        elif kind == " " and (j != old_len != 0 or j == 0):
            changes.append(Change(old + j, old + j, line, hunk_n))
            j += 1
        elif kind in ["+", "!"]:
            raise exceptions.ParseException(msg + kind, hunk_n)


def _parse_insertion_hunk(new_hunk: list[str], new: int, new_len: int, hunk_n: int, changes: list[Change]) -> None:
    """Parse a context diff hunk containing only insertions.

    Args:
        new_hunk: Lines from the new file section
        new: Starting line number in new file
        new_len: Expected number of lines
        hunk_n: Hunk number for tracking
        changes: List to append Change objects to (modified in place)

    Raises:
        ParseException: If unexpected change markers found
    """
    k = 0

    while new_hunk:
        kind, line, _consumed = _parse_insertion_line(new_hunk)

        if kind == "+" and (k != new_len or k == 0):
            changes.append(Change(None, new + k, line, hunk_n))
            k += 1
        elif kind == " " and (new_len not in (0, k) or k == 0):
            changes.append(Change(new + k, new + k, line, hunk_n))
            k += 1
        elif kind in ["-", "!"]:
            msg = f"Got unexpected change in insertion hunk: {kind}"
            raise exceptions.ParseException(msg, hunk_n)


def _parse_insertion_line(new_hunk: list[str]) -> tuple[str | None, str | None, bool]:
    """Parse a single line from insertion hunk.

    Args:
        new_hunk: Lines list (modified in place)

    Returns:
        Tuple of (kind, line, consumed)
    """
    c = context_change.match(new_hunk[0])
    del new_hunk[0]

    if not c:
        return None, None, False

    return c.group(1), c.group(2), True


def _get_change_kinds(
    old_hunk: list[str], new_hunk: list[str],
) -> tuple[str | None, str | None, str | None, str | None]:
    """Get change kinds and lines from old and new hunks."""
    c_old = context_change.match(old_hunk[0]) if old_hunk else None
    c_new = context_change.match(new_hunk[0]) if new_hunk else None

    if c_old and c_new:
        return c_old.group(1), c_old.group(2), c_new.group(1), c_new.group(2)
    return None, None, None, None


def _process_mixed_change_pair(
    kind_old: str,
    line_old: str,
    kind_new: str,
    line_new: str,
    old: int,
    new: int,
    j: int,
    k: int,
    hunk_n: int,
    changes: list[Change],
) -> tuple[int, int, int, int]:
    """Process a pair of change lines and return updated counters."""
    old_hunk_consumed = 0
    new_hunk_consumed = 0

    if kind_old == "-" and kind_new == "+":
        changes.append(Change(old + j, new + k, line_new, hunk_n))
        old_hunk_consumed, new_hunk_consumed = 1, 1
        j += 1
        k += 1
    elif kind_old == "-" and kind_new == " ":
        changes.append(Change(old + j, None, line_old, hunk_n))
        old_hunk_consumed, new_hunk_consumed = 1, 1
        j += 1
        k += 1
    elif kind_old == " " and kind_new == "+":
        changes.append(Change(None, new + k, line_new, hunk_n))
        old_hunk_consumed, new_hunk_consumed = 1, 1
        j += 1
        k += 1
    elif kind_old == " " and kind_new == " ":
        changes.append(Change(old + j, new + k, line_old, hunk_n))
        old_hunk_consumed, new_hunk_consumed = 1, 1
        j += 1
        k += 1

    return j, k, old_hunk_consumed, new_hunk_consumed


def _parse_mixed_hunk(
    old_hunk: list[str],
    new_hunk: list[str],
    old: int,
    new: int,
    old_len: int,
    new_len: int,
    hunk_n: int,
    changes: list[Change],
) -> None:
    """Parse a context diff hunk with both additions and deletions.

    Processes hunks that contain changes to both old and new files,
    synchronizing line counters between the two sections.

    Args:
        old_hunk: Lines from the old file section
        new_hunk: Lines from the new file section
        old: Starting line number in old file
        new: Starting line number in new file
        old_len: Expected number of lines in old section
        new_len: Expected number of lines in new section
        hunk_n: Hunk number for tracking
        changes: List to append Change objects to (modified in place)

    Raises:
        ParseException: If hunk format is invalid
    """
    j = 0
    k = 0

    while j < old_len and k < new_len:
        if not _skip_invalid_lines(old_hunk, new_hunk, j, k):
            kind_old, line_old, kind_new, line_new = _get_change_kinds(old_hunk, new_hunk)

            if kind_old and kind_new:
                j, k = _process_and_consume_mixed_line(
                    old_hunk,
                    new_hunk,
                    kind_old,
                    line_old,
                    kind_new,
                    line_new,
                    old,
                    new,
                    j,
                    k,
                    hunk_n,
                    changes,
                )


def _skip_invalid_lines(old_hunk: list[str], new_hunk: list[str], j: int, k: int) -> bool:
    """Skip invalid lines in hunks and increment counters.

    Args:
        old_hunk: Old hunk lines
        new_hunk: New hunk lines
        j: Old line counter
        k: New line counter

    Returns:
        True if line was skipped
    """
    c_old = context_change.match(old_hunk[0]) if old_hunk else None
    c_new = context_change.match(new_hunk[0]) if new_hunk else None

    if not c_old:
        del old_hunk[0]
        return True
    if not c_new:
        del new_hunk[0]
        return True

    return False


def _process_and_consume_mixed_line(
    old_hunk: list[str],
    new_hunk: list[str],
    kind_old: str,
    line_old: str,
    kind_new: str,
    line_new: str,
    old: int,
    new: int,
    j: int,
    k: int,
    hunk_n: int,
    changes: list[Change],
) -> tuple[int, int]:
    """Process and consume lines from mixed hunk.

    Args:
        old_hunk: Old hunk lines
        new_hunk: New hunk lines
        kind_old: Old line kind
        line_old: Old line content
        kind_new: New line kind
        line_new: New line content
        old: Old file start line
        new: New file start line
        j: Old line counter
        k: New line counter
        hunk_n: Hunk number
        changes: Changes list

    Returns:
        Updated (j, k) counters

    Raises:
        ParseException: If invalid format
    """
    j, k, old_consumed, new_consumed = _process_mixed_change_pair(
        kind_old,
        line_old,
        kind_new,
        line_new,
        old,
        new,
        j,
        k,
        hunk_n,
        changes,
    )

    if old_consumed:
        del old_hunk[0]
    if not new_consumed:
        msg = f"Unexpected pair: old={kind_old}, new={kind_new}"
        raise exceptions.ParseException(msg, hunk_n)
    del new_hunk[0]

    return j + 1, k + 1


def parse_context_diff(text: str | list[str]) -> list[Change] | None:
    """Parse context diff format and return list of changes.

    Context diff format shows changes with surrounding context lines.
    This function parses the diff and extracts individual changes.

    Args:
        text: Diff text as string or list of lines

    Returns:
        List of Change objects, or None if no changes

    Raises:
        ParseException: If diff format is invalid
    """
    lines = text.splitlines() if isinstance(text, str) else text
    changes = []
    hunks = split_by_regex(lines, context_hunk_start)

    for hunk_n, hunk in enumerate(hunks):
        if hunk:
            _process_context_hunk(hunk, hunk_n, changes)

    return changes or None


def _process_context_hunk(hunk: list[str], hunk_n: int, changes: list[Change]) -> None:
    """Process a single context diff hunk.

    Args:
        hunk: Hunk lines
        hunk_n: Hunk number
        changes: Changes list to append to

    Raises:
        ParseException: If hunk format invalid
    """
    parts = split_by_regex(hunk, context_hunk_new)
    if len(parts) != 2:
        msg = "Context diff invalid"
        raise exceptions.ParseException(msg, hunk_n)

    old_hunk, new_hunk = parts
    old, old_len = _extract_context_old_range(old_hunk)
    new, new_len = _extract_context_new_range(new_hunk)

    _dispatch_context_hunk_type(old_hunk, new_hunk, old, new, old_len, new_len, hunk_n, changes)


def _extract_context_old_range(old_hunk: list[str]) -> tuple[int, int]:
    """Extract old file range from context hunk.

    Args:
        old_hunk: Old hunk lines (modified in place)

    Returns:
        Tuple of (old_start, old_len)
    """
    while old_hunk:
        o = context_hunk_old.match(old_hunk[0])
        del old_hunk[0]
        if o:
            old = int(o.group(1))
            old_len = int(o.group(2)) + 1 - old
            return old, old_len
    return 0, 0


def _extract_context_new_range(new_hunk: list[str]) -> tuple[int, int]:
    """Extract new file range from context hunk.

    Args:
        new_hunk: New hunk lines (modified in place)

    Returns:
        Tuple of (new_start, new_len)
    """
    while new_hunk:
        n = context_hunk_new.match(new_hunk[0])
        del new_hunk[0]
        if n:
            new = int(n.group(1))
            new_len = int(n.group(2)) + 1 - new
            return new, new_len
    return 0, 0


def _dispatch_context_hunk_type(
    old_hunk: list[str],
    new_hunk: list[str],
    old: int,
    new: int,
    old_len: int,
    new_len: int,
    hunk_n: int,
    changes: list[Change],
) -> None:
    """Dispatch to appropriate hunk parser based on hunk type.

    Args:
        old_hunk: Old hunk lines
        new_hunk: New hunk lines
        old: Old start line
        new: New start line
        old_len: Old length
        new_len: New length
        hunk_n: Hunk number
        changes: Changes list
    """
    if old_hunk and not new_hunk:
        _parse_removal_hunk(old_hunk, old, old_len, hunk_n, changes)
    elif not old_hunk and new_hunk:
        _parse_insertion_hunk(new_hunk, new, new_len, hunk_n, changes)
    else:
        _parse_mixed_hunk(old_hunk, new_hunk, old, new, old_len, new_len, hunk_n, changes)


def _process_ed_deletion(old: int, old_end: int, hunk_n: int, changes: list, r: int) -> tuple[int, int]:
    """Process ed deletion hunk."""
    k = 0
    while old_end >= old:
        changes.append(Change(old + k, None, None, hunk_n))
        r += 1
        k += 1
        old_end -= 1
    return r, k


def _process_ed_change_removal(old: int, old_end: int, hunk_n: int, changes: list, r: int) -> tuple[int, int]:
    """Process removal part of ed change hunk."""
    k = 0
    while old_end >= old:
        changes.append(Change(old + k, None, None, hunk_n))
        r += 1
        k += 1
        old_end -= 1
    return r, k


def parse_ed_diff(text: str | list[str]) -> list[Change] | None:
    """Parse ed diff format and return list of changes.

    Ed diff format is a line-oriented format used by the ed editor.
    Hunks are processed in reverse order to maintain line number accuracy.

    Args:
        text: Diff text as string or list of lines

    Returns:
        List of Change objects, or None if no changes

    Raises:
        ParseException: If diff format is invalid
    """
    lines = text.splitlines() if isinstance(text, str) else text
    changes = []
    hunks = split_by_regex(lines, ed_hunk_start)
    hunks.reverse()

    state = _EdDiffState()

    for hunk_number, hunk in enumerate(hunks):
        if hunk:
            _process_ed_hunk(hunk, hunk_number, changes, state)

    return changes or None


class _EdDiffState:
    """State for parsing ed diff format."""

    def __init__(self) -> None:
        self.line_offset = 0
        self.change_offset = 0
        self.deletion_offset = 0
        self.addition_offset = 0


def _process_ed_hunk(hunk: list[str], hunk_number: int, changes: list[Change], state: _EdDiffState) -> None:
    """Process a single ed diff hunk.

    Args:
        hunk: Hunk lines
        hunk_number: Hunk number
        changes: Changes list
        state: Parsing state
    """
    state.change_offset = 0

    while hunk:
        hunk_match = ed_hunk_start.match(hunk[0])
        hunk.pop(0)

        if not hunk_match:
            continue

        old_start = int(hunk_match.group(1))
        old_end = int(hunk_match.group(2)) if hunk_match.group(2) else old_start
        operation = hunk_match.group(3)

        if operation == "d":
            state.deletion_offset, state.change_offset = _process_ed_deletion(
                old_start,
                old_end,
                hunk_number,
                changes,
                state.deletion_offset,
            )
        else:
            _process_ed_addition_or_change(hunk, old_start, old_end, operation, hunk_number, changes, state)


def _process_ed_addition_or_change(
    hunk: list[str],
    old_start: int,
    old_end: int,
    operation: str,
    hunk_number: int,
    changes: list[Change],
    state: _EdDiffState,
) -> None:
    """Process ed addition or change operation.

    Args:
        hunk: Hunk lines
        old_start: Old start line
        old_end: Old end line
        operation: Operation type (a or c)
        hunk_number: Hunk number
        changes: Changes list
        state: Parsing state
    """
    while hunk:
        if ed_hunk_end.match(hunk[0]):
            break

        if operation == "c":
            state.deletion_offset, state.change_offset = _process_ed_change_removal(
                old_start,
                old_end,
                hunk_number,
                changes,
                state.deletion_offset,
            )
            line_number = (
                old_start - state.deletion_offset + state.line_offset + state.change_offset + state.addition_offset
            )
            changes.append(Change(None, line_number, hunk[0], hunk_number))
            state.line_offset += 1
            state.addition_offset += 1
        elif operation == "a":
            line_number = old_start - state.deletion_offset + state.line_offset + 1
            changes.append(Change(None, line_number, hunk[0], hunk_number))
            state.line_offset += 1

        hunk.pop(0)


def parse_rcs_ed_diff(text: str | list[str]) -> list[Change] | None:
    """Parse RCS ed diff format and return list of changes.

    RCS ed diff is a variant of ed format that tracks line number changes
    as hunks are applied. Total change size is accumulated to adjust
    subsequent line numbers.

    Args:
        text: Diff text as string or list of lines

    Returns:
        List of Change objects, or None if no changes

    Raises:
        ParseException: If diff format is invalid
    """
    lines = text.splitlines() if isinstance(text, str) else text
    changes = []
    hunks = split_by_regex(lines, rcs_ed_hunk_start)

    state = _RcsEdDiffState()

    for hunk_n, hunk in enumerate(hunks):
        if hunk:
            _process_rcs_ed_hunk(hunk, hunk_n, changes, state)

    return changes or None


class _RcsEdDiffState:
    """State for parsing RCS ed diff format."""

    def __init__(self) -> None:
        self.total_change_size = 0


def _process_rcs_ed_hunk(hunk: list[str], hunk_n: int, changes: list[Change], state: _RcsEdDiffState) -> None:
    """Process a single RCS ed diff hunk.

    Args:
        hunk: Hunk lines
        hunk_n: Hunk number
        changes: Changes list
        state: Parsing state
    """
    j = 0

    while hunk:
        o = rcs_ed_hunk_start.match(hunk[0])
        del hunk[0]

        if not o:
            continue

        hunk_kind = o.group(1)
        old = int(o.group(2))
        size = int(o.group(3)) if o.group(3) else 0

        if hunk_kind == "a":
            j = _process_rcs_addition(hunk, old, size, state, hunk_n, changes, j)
        elif hunk_kind == "d":
            j = _process_rcs_deletion(old, size, state, hunk_n, changes, j)


def _process_rcs_addition(
    hunk: list[str],
    old: int,
    size: int,
    state: _RcsEdDiffState,
    hunk_n: int,
    changes: list[Change],
    j: int,
) -> int:
    """Process RCS addition operation.

    Args:
        hunk: Hunk lines
        old: Old line number
        size: Number of lines to add
        state: Parsing state
        hunk_n: Hunk number
        changes: Changes list
        j: Line counter

    Returns:
        Updated line counter
    """
    old += state.total_change_size + 1
    state.total_change_size += size

    while size > 0 and hunk:
        changes.append(Change(None, old + j, hunk[0], hunk_n))
        j += 1
        size -= 1
        del hunk[0]

    return j


def _process_rcs_deletion(
    old: int,
    size: int,
    state: _RcsEdDiffState,
    hunk_n: int,
    changes: list[Change],
    j: int,
) -> int:
    """Process RCS deletion operation.

    Args:
        old: Old line number
        size: Number of lines to delete
        state: Parsing state
        hunk_n: Hunk number
        changes: Changes list
        j: Line counter

    Returns:
        Updated line counter
    """
    state.total_change_size -= size

    while size > 0:
        changes.append(Change(old + j, None, None, hunk_n))
        j += 1
        size -= 1

    return j


def _parse_diff_command_header(line: str) -> tuple[str | None, str | None]:
    """Parse git diff command header and return old_path, new_path."""
    if hm := git_diffcmd_header.match(line):
        return hm.group(1), hm.group(2)
    return None, None


def _parse_git_header_index(line: str) -> tuple[str | None, str | None]:
    """Parse git header index and return old_version, new_version."""
    if g := git_header_index.match(line):
        return g.group(1), g.group(2)
    return None, None


def _process_new_size_literal(line: str) -> int | None:
    """Process new size literal and return size if found."""
    if literal := git_binary_literal_start.match(line):
        return int(literal.group(1))
    return None


def _process_old_size_literal(line: str) -> int | None:
    """Process old size literal and return size if found."""
    if literal := git_binary_literal_start.match(line):
        return int(literal.group(1))
    return None


def _is_delta_start(line: str) -> bool:
    """Check if line is a delta start."""
    return git_binary_delta_start.match(line) is not None


def _is_base85_string(line: str) -> bool:
    """Check if line is a base85 string."""
    return base85string.match(line) is not None


def _validate_base85_line(line: str) -> None:
    """Validate base85 line format."""
    assert len(line) >= 6
    assert (len(line) - 1) % 5 == 0


def _decode_and_decompress_data(encoded: str, expected_size: int) -> bytes:
    """Decode base85 and decompress data."""
    decoded = base64.b85decode(encoded)
    data = zlib.decompress(decoded)
    assert expected_size == len(data)
    return data


def _process_new_encoded_data(line: str, new_encoded: str, new_size: int) -> tuple[str, int]:
    """Process new encoded data line."""
    if _is_base85_string(line):
        _validate_base85_line(line)
        return new_encoded + line[1:], new_size
    if not line:
        return "", 0
    return "", 0


def _process_old_encoded_data(line: str, old_encoded: str, old_size: int) -> tuple[str, int]:
    """Process old encoded data line."""
    if _is_base85_string(line):
        _validate_base85_line(line)
        return old_encoded + line[1:], old_size
    if not line:
        return "", 0
    return "", 0


def _create_added_change(added_data: bytes) -> Change:
    """Create a change for added data."""
    return Change(None, 0, added_data, None)


def _create_removed_change(removed_data: bytes) -> Change:
    """Create a change for removed data."""
    return Change(0, None, None, removed_data)


def _parse_command_header(
    line: str,
    cmd_old_path: str | None,
    cmd_new_path: str | None,
) -> tuple[str | None, str | None]:
    """Parse command header if not already parsed."""
    if cmd_old_path is None and cmd_new_path is None:
        return _parse_diff_command_header(line)
    return cmd_old_path, cmd_new_path


def _parse_git_index(line: str, old_version: str | None, new_version: str | None) -> tuple[str | None, str | None]:
    """Parse git index if not already parsed."""
    if old_version is None and new_version is None:
        return _parse_git_header_index(line)
    return old_version, new_version


def _process_new_size_parsing(line: str, new_size: int) -> int:
    """Process new size parsing logic."""
    if new_size == 0:
        size = _process_new_size_literal(line)
        if size is not None:
            return size
        if _is_delta_start(line):
            return 0
    return new_size


def _process_old_size_parsing(line: str, old_size: int) -> int:
    """Process old size parsing logic."""
    if old_size == 0:
        size = _process_old_size_literal(line)
        if size is not None:
            return size
        if _is_delta_start(line):
            return 0
    return old_size


def _process_new_encoded_content(line: str, new_encoded: str, new_size: int, changes: list[Change]) -> tuple[str, int]:
    """Process new encoded content and update changes if needed."""
    if new_size > 0:
        new_encoded, new_size = _process_new_encoded_data(line, new_encoded, new_size)
        if new_size == 0 and new_encoded:
            added_data = _decode_and_decompress_data(new_encoded, new_size)
            changes.append(_create_added_change(added_data))
            new_encoded = ""
    return new_encoded, new_size


def _process_old_encoded_content(line: str, old_encoded: str, old_size: int, changes: list[Change]) -> tuple[str, int]:
    """Process old encoded content and update changes if needed."""
    if old_size > 0:
        old_encoded, old_size = _process_old_encoded_data(line, old_encoded, old_size)
        if old_size == 0 and old_encoded:
            removed_data = _decode_and_decompress_data(old_encoded, old_size)
            changes.append(_create_removed_change(removed_data))
            old_encoded = ""
    return old_encoded, old_size


def parse_git_binary_diff(text: str | list[str]) -> list[Change] | None:
    """Parse git binary diff and return list of changes."""
    lines = text.splitlines() if isinstance(text, str) else text
    changes: list[Change] = []
    old_version = None
    new_version = None
    cmd_old_path = None
    cmd_new_path = None
    new_size = 0
    old_size = 0
    old_encoded = ""
    new_encoded = ""

    for line in lines:
        # Parse command header
        cmd_old_path, cmd_new_path = _parse_command_header(line, cmd_old_path, cmd_new_path)
        if cmd_old_path is not None and cmd_new_path is not None:
            continue

        # Parse git header index
        old_version, new_version = _parse_git_index(line, old_version, new_version)
        if old_version is not None and new_version is not None:
            continue

        # Process new size
        new_size = _process_new_size_parsing(line, new_size)
        if new_size != 0:
            continue

        # Process old size
        old_size = _process_old_size_parsing(line, old_size)
        if old_size != 0:
            continue

        # Process encoded content
        new_encoded, new_size = _process_new_encoded_content(line, new_encoded, new_size, changes)
        old_encoded, old_size = _process_old_encoded_content(line, old_encoded, old_size, changes)

    return changes
