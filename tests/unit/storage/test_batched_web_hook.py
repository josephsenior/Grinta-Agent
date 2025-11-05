import time
from unittest.mock import MagicMock
import httpx
import pytest
from openhands.storage.batched_web_hook import BatchedWebHookFileStore
from openhands.storage.files import FileStore


class MockFileStore(FileStore):

    def __init__(self):
        self.files = {}

    def write(self, path: str, contents: str | bytes) -> None:
        self.files[path] = contents

    def read(self, path: str) -> str:
        return self.files.get(path, "")

    def list(self, path: str) -> list[str]:
        return [k for k in self.files.keys() if k.startswith(path)]

    def delete(self, path: str) -> None:
        if path in self.files:
            del self.files[path]


class TestBatchedWebHookFileStore:

    @pytest.fixture
    def mock_client(self):
        client = MagicMock(spec=httpx.Client)
        client.post.return_value.raise_for_status = MagicMock()
        client.delete.return_value.raise_for_status = MagicMock()
        return client

    @pytest.fixture
    def file_store(self):
        return MockFileStore()

    @pytest.fixture
    def batched_store(self, file_store, mock_client):
        return BatchedWebHookFileStore(
            file_store=file_store,
            base_url="http://example.com",
            client=mock_client,
            batch_timeout_seconds=0.1,
            batch_size_limit_bytes=1000,
        )

    def test_write_operation_batched(self, batched_store, mock_client):
        batched_store.write("/test.txt", "Hello, world!")
        mock_client.post.assert_not_called()
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "POST"
        assert batch_payload[0]["path"] == "/test.txt"
        assert batch_payload[0]["content"] == "Hello, world!"

    def test_delete_operation_batched(self, batched_store, mock_client):
        batched_store.write("/test.txt", "Hello, world!")
        batched_store.delete("/test.txt")
        mock_client.post.assert_not_called()
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "DELETE"
        assert batch_payload[0]["path"] == "/test.txt"
        assert "content" not in batch_payload[0]

    def test_batch_size_limit_triggers_send(self, batched_store, mock_client):
        large_content = "x" * 1001
        batched_store.write("/large.txt", large_content)
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "POST"
        assert batch_payload[0]["path"] == "/large.txt"
        assert batch_payload[0]["content"] == large_content

    def test_multiple_updates_same_file(self, batched_store, mock_client):
        batched_store.write("/test.txt", "Version 1")
        batched_store.write("/test.txt", "Version 2")
        batched_store.write("/test.txt", "Version 3")
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "POST"
        assert batch_payload[0]["path"] == "/test.txt"
        assert batch_payload[0]["content"] == "Version 3"

    def test_flush_sends_immediately(self, batched_store, mock_client):
        batched_store.write("/test.txt", "Hello, world!")
        mock_client.post.assert_not_called()
        batched_store.flush()
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "POST"
        assert batch_payload[0]["path"] == "/test.txt"
        assert batch_payload[0]["content"] == "Hello, world!"

    def test_multiple_operations_in_single_batch(self, batched_store, mock_client):
        batched_store.write("/file1.txt", "Content 1")
        batched_store.write("/file2.txt", "Content 2")
        batched_store.delete("/file3.txt")
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 3
        operations = {item["path"]: item for item in batch_payload}
        assert "/file1.txt" in operations
        assert operations["/file1.txt"]["method"] == "POST"
        assert operations["/file1.txt"]["content"] == "Content 1"
        assert "/file2.txt" in operations
        assert operations["/file2.txt"]["method"] == "POST"
        assert operations["/file2.txt"]["content"] == "Content 2"
        assert "/file3.txt" in operations
        assert operations["/file3.txt"]["method"] == "DELETE"
        assert "content" not in operations["/file3.txt"]

    def test_binary_content_handling(self, batched_store, mock_client):
        binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd\xfc"
        batched_store.write("/binary.bin", binary_content)
        time.sleep(0.2)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://example.com"
        assert "json" in kwargs
        batch_payload = kwargs["json"]
        assert isinstance(batch_payload, list)
        assert len(batch_payload) == 1
        assert batch_payload[0]["method"] == "POST"
        assert batch_payload[0]["path"] == "/binary.bin"
        assert "content" in batch_payload[0]
        assert "encoding" in batch_payload[0]
        assert batch_payload[0]["encoding"] == "base64"
        import base64

        decoded = base64.b64decode(batch_payload[0]["content"].encode("ascii"))
        assert decoded == binary_content
