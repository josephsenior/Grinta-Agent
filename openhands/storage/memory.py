from __future__ import annotations

from openhands.core.logger import openhands_logger as logger
from openhands.storage.files import FileStore


class InMemoryFileStore(FileStore):
    files: dict[str, str]

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = {}
        if files is not None:
            self.files = files

    def write(self, path: str, contents: str | bytes) -> None:
        if isinstance(contents, bytes):
            contents = contents.decode("utf-8")
        self.files[path] = contents

    def read(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def list(self, path: str) -> list[str]:
        files: list[str] = []
        for file in self.files:
            norm_file = file.replace("\\", "/")
            if not norm_file.startswith(path):
                continue
            suffix = norm_file.removeprefix(path)
            parts = suffix.split("/")
            if parts[0] == "":
                parts.pop(0)
            if len(parts) == 1:
                if not path:
                    files.append(norm_file.lstrip("/"))
                else:
                    files.append(norm_file)
            else:
                dir_path = f"{path.rstrip('/')}/{parts[0]}/" if path else f"{parts[0]}/"
                if dir_path not in files:
                    files.append(dir_path)
        return files

    def delete(self, path: str) -> None:
        try:
            keys_to_delete = [key for key in self.files if key.startswith(path)]
            for key in keys_to_delete:
                del self.files[key]
            logger.debug("Cleared in-memory file store: %s", path)
        except Exception as e:
            logger.error("Error clearing in-memory file store: %s", str(e))
