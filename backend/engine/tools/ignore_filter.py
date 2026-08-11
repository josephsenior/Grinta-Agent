"""Robust file exclusion filtering using pathspec."""

import os

import pathspec
from shadowgit import DEFAULT_IGNORE_PATTERNS, build_pathspec


def get_ignore_spec(root: str) -> pathspec.PathSpec:
    """Build a pathspec from default ignores and project .gitignore."""
    return build_pathspec(
        root,
        default_patterns=(*DEFAULT_IGNORE_PATTERNS, '.tmp_cli_manual/'),
    )


def prune_ignored_dirs(
    root: str, current_root: str, dirs: list[str], spec: pathspec.PathSpec
) -> None:
    """Modify dirs list in-place to remove ignored directories."""
    rel_root = os.path.relpath(current_root, root)
    if rel_root == '.':
        rel_root = ''

    kept_dirs = []
    for d in dirs:
        # pathspec expects paths relative to git root, with trailing slash for dirs
        rel_path = os.path.join(rel_root, d) if rel_root else d
        rel_path = rel_path.replace(os.sep, '/') + '/'

        if not spec.match_file(rel_path):
            kept_dirs.append(d)

    dirs[:] = kept_dirs


def is_ignored_file(
    root: str, current_root: str, filename: str, spec: pathspec.PathSpec
) -> bool:
    """Check if a file matches the ignore spec."""
    rel_root = os.path.relpath(current_root, root)
    if rel_root == '.':
        rel_root = ''

    rel_path = os.path.join(rel_root, filename) if rel_root else filename
    rel_path = rel_path.replace(os.sep, '/')

    return spec.match_file(rel_path)
