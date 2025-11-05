from __future__ import annotations

import os
from shutil import rmtree
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import re


def remove(path: str) -> None:
    if os.path.exists(path):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.remove(path)


def findall_regex(items: list[str], regex: re.Pattern[str]) -> list[int]:
    return [i for i in range(len(items)) if regex.match(items[i])]


def split_by_regex(items: list[str], regex: re.Pattern[str]) -> list[list[str]]:
    splits = []
    indices = findall_regex(items, regex)
    if not indices:
        splits.append(items)
        return splits
    splits.append(items[: indices[0]])
    splits.extend(items[indices[i]: indices[i + 1]] for i in range(len(indices) - 1))
    splits.append(items[indices[-1]:])
    return splits


def which(program: str) -> str | None:

    def is_exe(fpath: str) -> bool:
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None
