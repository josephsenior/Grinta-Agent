"""Get git diff in a single git file for the closest git repo in the file system.

NOTE: Since this is run as a script, there should be no imports from project files!
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

MAX_FILE_SIZE_FOR_GIT_DIFF = 1024 * 1024


def get_closest_git_repo(path: Path) -> Path | None:
    """Find the closest git repository directory by walking up the directory tree.

    Args:
        path: The starting path to search from.

    Returns:
        Path | None: The path to the git repository, or None if not found.

    """
    while True:
        path = path.parent
        git_path = Path(path, ".git")
        if git_path.is_dir():
            return path
        if path.parent == path:
            return None


def run(cmd: str, cwd: str) -> str:
    """Run a shell command and return its output.

    Args:
        cmd: The command to run.
        cwd: The working directory to run the command in.

    Returns:
        str: The command output.

    Raises:
        RuntimeError: If the command fails to execute.

    """
    # Use shlex.split() to safely parse the command and avoid shell=True
    result = subprocess.run(
        check=False,
        args=shlex.split(cmd),
        shell=False,
        capture_output=True,
        cwd=cwd,
    )
    byte_content = result.stderr or result.stdout or b""
    if result.returncode != 0:
        msg = f"error_running_cmd:{result.returncode}:{byte_content.decode()}"
        raise RuntimeError(
            msg,
        )
    return byte_content.decode().strip()


def get_valid_ref(repo_dir: str) -> str | None:
    """Get a valid git reference for comparison.

    Tries multiple git references in order of preference:
    1. Current branch origin
    2. Default branch references
    3. Empty tree reference

    Args:
        repo_dir: The repository directory.

    Returns:
        str | None: A valid git reference hash, or None if none found.

    """
    refs = []
    try:
        current_branch = run("git --no-pager rev-parse --abbrev-ref HEAD", repo_dir)
        refs.append(f"origin/{current_branch}")
    except RuntimeError:
        pass
    try:
        default_branch = (
            run('git --no-pager remote show origin | grep "HEAD branch"', repo_dir)
            .split()[-1]
            .strip()
        )
        ref_non_default_branch = f'$(git --no-pager merge-base HEAD "$(git --no-pager rev-parse --abbrev-ref origin/{default_branch})")'
        ref_default_branch = f"origin/{default_branch}"
        refs.extend((ref_non_default_branch, ref_default_branch))
    except RuntimeError:
        pass
    ref_new_repo = (
        "$(git --no-pager rev-parse --verify 4b825dc642cb6eb9a060e54bf8d69288fbee4904)"
    )
    refs.append(ref_new_repo)
    for ref in refs:
        try:
            return run(f"git --no-pager rev-parse --verify {ref}", repo_dir)
        except RuntimeError:
            continue
    return None


def get_git_diff(relative_file_path: str) -> dict[str, str]:
    """Get git diff for a specific file.

    Args:
        relative_file_path: The relative path to the file to get diff for.

    Returns:
        dict[str, str]: Dictionary with 'modified' and 'original' file contents.

    Raises:
        ValueError: If file is too large or no repository is found.

    """
    path = Path(os.getcwd(), relative_file_path).resolve()
    if os.path.getsize(path) > MAX_FILE_SIZE_FOR_GIT_DIFF:
        msg = "file_to_large"
        raise ValueError(msg)
    closest_git_repo = get_closest_git_repo(path)
    if not closest_git_repo:
        msg = "no_repository"
        raise ValueError(msg)
    current_rev = get_valid_ref(str(closest_git_repo))
    try:
        original = run(
            f'git show "{current_rev}:{path.relative_to(closest_git_repo)}"',
            str(closest_git_repo),
        )
    except RuntimeError:
        original = ""
    try:
        with open(path, encoding="utf-8") as f:
            modified = "\n".join(f.read().splitlines())
    except FileNotFoundError:
        modified = ""
    return {"modified": modified, "original": original}


def _fallback_print(
    obj,
) -> None:  # pragma: no cover - exercised via tests with patched stdout
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    except Exception:  # pragma: no cover
        try:
            sys.stdout.write(repr(obj) + "\n")
        except Exception:
            sys.stdout.write('{"error":"unserializable"}\n')
    sys.stdout.flush()


def _main() -> None:
    diff = get_git_diff(sys.argv[-1])
    try:
        from forge.core.io import print_json_stdout
    except Exception:  # pragma: no cover - fallback is tested separately
        _fallback_print(diff)
    else:
        print_json_stdout(diff)


if __name__ == "__main__":  # pragma: no cover
    _main()
