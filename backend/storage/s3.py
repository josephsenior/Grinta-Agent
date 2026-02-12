"""AWS S3 (or compatible) FileStore implementation with utility TypedDicts."""

from __future__ import annotations

import os
from typing import Any, TypedDict

import boto3
import botocore

from backend.storage.files import FileStore


class S3ObjectDict(TypedDict):
    """TypedDict representing minimal S3 object metadata returned by list APIs."""

    Key: str


class GetObjectOutputDict(TypedDict):
    """TypedDict representing response body of S3 get_object call."""

    Body: Any


class ListObjectsV2OutputDict(TypedDict):
    """TypedDict representing response payload of list_objects_v2."""

    Contents: list[S3ObjectDict] | None




class S3FileStore(FileStore):
    """FileStore implementation backed by AWS S3-compatible object storage."""

    def __init__(self, bucket_name: str | None) -> None:
        """Initialize S3 client using environment configuration or provided bucket."""
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        secure = os.getenv("AWS_S3_SECURE", "true").lower() == "true"
        endpoint = self._ensure_url_scheme(secure, os.getenv("AWS_S3_ENDPOINT"))
        if bucket_name is None:
            bucket_name = os.environ["AWS_S3_BUCKET"]
        self.bucket: str = bucket_name
        self.client: Any = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint,
            use_ssl=secure,
        )

    def write(self, path: str, contents: str | bytes) -> None:
        """Write to S3 bucket.

        Args:
            path: Object key path
            contents: Content to write

        Raises:
            FileNotFoundError: On access denied or bucket not found

        """
        try:
            as_bytes = (
                contents.encode("utf-8") if isinstance(contents, str) else contents
            )
            self.client.put_object(Bucket=self.bucket, Key=path, Body=as_bytes)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                msg = f"Error: Access denied to bucket '{self.bucket}'."
                raise FileNotFoundError(msg) from e
            if e.response["Error"]["Code"] == "NoSuchBucket":
                msg = f"Error: The bucket '{self.bucket}' does not exist."
                raise FileNotFoundError(msg) from e
            msg = (
                f"Error: Failed to write to bucket '{self.bucket}' at path {path}: {e}"
            )
            raise FileNotFoundError(msg) from e

    def read(self, path: str) -> str:
        """Read from S3 bucket.

        Args:
            path: Object key path

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If object not found

        """
        try:
            response: GetObjectOutputDict = self.client.get_object(
                Bucket=self.bucket, Key=path
            )
            with response["Body"] as stream:
                return str(stream.read().decode("utf-8"))
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchBucket":
                msg = f"Error: The bucket '{self.bucket}' does not exist."
                raise FileNotFoundError(msg) from e
            if e.response["Error"]["Code"] == "NoSuchKey":
                msg = f"Error: The object key '{path}' does not exist in bucket '{
                    self.bucket
                }'."
                raise FileNotFoundError(
                    msg,
                ) from e
            msg = (
                f"Error: Failed to read from bucket '{self.bucket}' at path {path}: {e}"
            )
            raise FileNotFoundError(msg) from e
        except Exception as e:
            msg = (
                f"Error: Failed to read from bucket '{self.bucket}' at path {path}: {e}"
            )
            raise FileNotFoundError(msg) from e

    def list(self, path: str) -> list[str]:
        """List objects in S3 bucket at given prefix.

        Args:
            path: Directory prefix

        Returns:
            List of object keys

        """
        if not path or path == "/":
            path = ""
        elif not path.endswith("/"):
            path += "/"
        results: set[str] = set()
        prefix_len = len(path)
        response: ListObjectsV2OutputDict = self.client.list_objects_v2(
            Bucket=self.bucket, Prefix=path
        )
        contents = response.get("Contents")
        if not contents:
            return []
        paths = [obj["Key"] for obj in contents]
        for sub_path in paths:
            if sub_path == path:
                continue
            try:
                index = sub_path.index("/", prefix_len + 1)
                if index != prefix_len:
                    results.add(sub_path[: index + 1])
            except ValueError:
                results.add(sub_path)
        return list(results)

    def delete(self, path: str) -> None:
        """Delete objects from S3 bucket.

        Args:
            path: Object key or prefix to delete

        """
        try:
            if not path or path == "/":
                path = ""
            path = path.removesuffix("/")
            response = self.client.list_objects_v2(
                Bucket=self.bucket, Prefix=f"{path}/"
            )
            for content in response.get("Contents") or []:
                self.client.delete_object(Bucket=self.bucket, Key=content["Key"])
            self.client.delete_object(Bucket=self.bucket, Key=path)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchBucket":
                msg = f"Error: The bucket '{self.bucket}' does not exist."
                raise FileNotFoundError(msg) from e
            if e.response["Error"]["Code"] == "AccessDenied":
                msg = f"Error: Access denied to bucket '{self.bucket}'."
                raise FileNotFoundError(msg) from e
            if e.response["Error"]["Code"] == "NoSuchKey":
                msg = f"Error: The object key '{path}' does not exist in bucket '{
                    self.bucket
                }'."
                raise FileNotFoundError(
                    msg,
                ) from e
            msg = (
                f"Error: Failed to delete key '{path}' from bucket '{self.bucket}': {e}"
            )
            raise FileNotFoundError(msg) from e
        except Exception as e:
            msg = (
                f"Error: Failed to delete key '{path}' from bucket '{self.bucket}: {e}"
            )
            raise FileNotFoundError(msg) from e

    def _ensure_url_scheme(self, secure: bool, url: str | None) -> str | None:
        """Ensure URL has correct scheme (http or https) based on security setting.

        Converts URLs to use https:// if secure=True, http:// if secure=False.
        Strips conflicting schemes before adding the correct one.

        Args:
            secure: Whether to use https (True) or http (False)
            url: URL to process, or None

        Returns:
            str | None: URL with correct scheme, or None if input was None

        Example:
            >>> storage._ensure_url_scheme(True, "http://example.com")
            "https://example.com"
            >>> storage._ensure_url_scheme(False, "https://example.com")
            "http://example.com"

        """
        if not url:
            return None
        if secure:
            if not url.startswith("https://"):
                url = "https://" + url.removeprefix("http://")
        elif not url.startswith("http://"):
            url = "http://" + url.removeprefix("https://")
        return url
