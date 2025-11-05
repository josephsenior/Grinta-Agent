from __future__ import annotations

import os
from typing import TYPE_CHECKING

from google.api_core.exceptions import NotFound
from google.cloud import storage

from openhands.storage.files import FileStore

if TYPE_CHECKING:
    from google.cloud.storage.blob import Blob
    from google.cloud.storage.bucket import Bucket
    from google.cloud.storage.client import Client


class GoogleCloudFileStore(FileStore):

    def __init__(self, bucket_name: str | None = None) -> None:
        """Create a new FileStore.

        If GOOGLE_APPLICATION_CREDENTIALS is defined in the environment it will be used
        for authentication. Otherwise access will be anonymous.
        """
        if bucket_name is None:
            bucket_name = os.environ["GOOGLE_CLOUD_BUCKET_NAME"]
        self.storage_client: Client = storage.Client()
        self.bucket: Bucket = self.storage_client.bucket(bucket_name)

    def write(self, path: str, contents: str | bytes) -> None:
        blob: Blob = self.bucket.blob(path)
        mode = "wb" if isinstance(contents, bytes) else "w"
        with blob.open(mode) as f:
            f.write(contents)

    def read(self, path: str) -> str:
        blob: Blob = self.bucket.blob(path)
        try:
            with blob.open("r") as f:
                return str(f.read())
        except NotFound as err:
            raise FileNotFoundError(err) from err

    def list(self, path: str) -> list[str]:
        if not path or path == "/":
            path = ""
        elif not path.endswith("/"):
            path += "/"
        blobs: set[str] = set()
        prefix_len = len(path)
        for blob in self.bucket.list_blobs(prefix=path):
            name: str = blob.name
            if name == path:
                continue
            try:
                index = name.index("/", prefix_len + 1)
                if index != prefix_len:
                    blobs.add(name[: index + 1])
            except ValueError:
                blobs.add(name)
        return list(blobs)

    def delete(self, path: str) -> None:
        if not path or path == "/":
            path = ""
        path = path.removesuffix("/")
        for blob in self.bucket.list_blobs(prefix=f"{path}/"):
            blob.delete()
        try:
            file_blob: Blob = self.bucket.blob(path)
            file_blob.delete()
        except NotFound:
            pass
