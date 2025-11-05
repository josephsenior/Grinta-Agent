from __future__ import annotations

import os
import shutil

from openhands.core.logger import openhands_logger as logger
from openhands.storage.files import FileStore


class LocalFileStore(FileStore):
    root: str

    def __init__(self, root: str) -> None:
        if root.startswith("~"):
            root = os.path.expanduser(root)
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def get_full_path(self, path: str) -> str:
        path = path.removeprefix("/")
        return os.path.join(self.root, path)

    def write(self, path: str, contents: str | bytes) -> None:
        full_path = self.get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        mode = "w" if isinstance(contents, str) else "wb"
        if isinstance(contents, str):
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(contents)
        else:
            with open(full_path, mode) as f:
                f.write(contents)

    def read(self, path: str) -> str:
        full_path = self.get_full_path(path)
        with open(full_path, encoding="utf-8") as f:
            return f.read()

    def list(self, path: str) -> list[str]:
        full_path = self.get_full_path(path)
        files: list[str] = []
        for f in os.listdir(full_path):
            joined = os.path.join(path, f)
            norm = joined.replace("\\", "/")
            if os.path.isdir(self.get_full_path(joined)) and (not norm.endswith("/")):
                norm = f"{norm}/"
            files.append(norm)
        return files

    def delete(self, path: str) -> None:
        try:
            full_path = self.get_full_path(path)
            if not os.path.exists(full_path):
                logger.debug("Local path does not exist: %s", full_path)
                return
            if os.path.isfile(full_path):
                os.remove(full_path)
                logger.debug("Removed local file: %s", full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
                logger.debug("Removed local directory: %s", full_path)
        except Exception as e:
            logger.error("Error clearing local file store: %s", str(e))
