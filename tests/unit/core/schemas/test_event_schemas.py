"""Tests for Forge event schemas with versioning and serialization."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from forge.core.schemas import (
    ActionSchemaUnion,
    CmdOutputObservationSchema,
    CmdRunActionSchema,
    ErrorObservationSchema,
    EventVersion,
    FileEditActionSchema,
    FileReadActionSchema,
    FileReadObservationSchema,
    MessageActionSchema,
    ObservationSchemaUnion,
    deserialize_event,
    migrate_schema_version,
    serialize_event,
    validate_event_schema,
)
from forge.core.schemas.base import EventMetadata, EventSource


class TestEventSchemas:
    """Test suite for event schema validation and serialization."""

    def test_file_read_action_schema_validation(self):
        """Test FileReadActionSchema validation."""
        schema = FileReadActionSchema(
            action_type="read",
            path="/tmp/test.py",
            start=0,
            end=10,
            thought="Reading file",
        )
        assert schema.action_type == "read"
        assert schema.path == "/tmp/test.py"
        assert schema.start == 0
        assert schema.end == 10
        assert schema.thought == "Reading file"
        assert schema.runnable is True

    def test_cmd_run_action_schema_validation(self):
        """Test CmdRunActionSchema validation."""
        schema = CmdRunActionSchema(
            action_type="run",
            command="ls -la",
            thought="Listing files",
            blocking=True,
        )
        assert schema.action_type == "run"
        assert schema.command == "ls -la"
        assert schema.thought == "Listing files"
        assert schema.blocking is True
        assert schema.runnable is True

    def test_file_edit_action_schema_validation(self):
        """Test FileEditActionSchema validation."""
        schema = FileEditActionSchema(
            action_type="edit",
            path="/tmp/test.py",
            command="str_replace",
            old_str="old",
            new_str="new",
            thought="Editing file",
        )
        assert schema.action_type == "edit"
        assert schema.path == "/tmp/test.py"
        assert schema.command == "str_replace"
        assert schema.old_str == "old"
        assert schema.new_str == "new"

    def test_cmd_output_observation_schema_validation(self):
        """Test CmdOutputObservationSchema validation."""
        schema = CmdOutputObservationSchema(
            observation_type="run",
            command="ls -la",
            content="file1.txt file2.txt",
            cmd_metadata={
                "exit_code": 0,
                "pid": 12345,
                "working_dir": "/tmp",
            },
        )
        assert schema.observation_type == "run"
        assert schema.command == "ls -la"
        assert schema.content == "file1.txt file2.txt"
        assert schema.cmd_metadata["exit_code"] == 0
        assert schema.cmd_metadata["pid"] == 12345

    def test_error_observation_schema_validation(self):
        """Test ErrorObservationSchema validation."""
        schema = ErrorObservationSchema(
            observation_type="error",
            content="Command failed",
            error_id="CMD_ERROR",
        )
        assert schema.observation_type == "error"
        assert schema.content == "Command failed"
        assert schema.error_id == "CMD_ERROR"

    def test_event_metadata(self):
        """Test EventMetadata serialization."""
        metadata = EventMetadata(
            event_id=1,
            sequence=2,
            timestamp=datetime.now(),
            source=EventSource.AGENT,
            cause=3,
            hidden=False,
            timeout=10.0,
            response_id="resp-123",
            trace_id="trace-456",
        )
        assert metadata.event_id == 1
        assert metadata.sequence == 2
        assert metadata.source == EventSource.AGENT
        assert metadata.cause == 3
        assert metadata.hidden is False
        assert metadata.timeout == 10.0
        assert metadata.response_id == "resp-123"
        assert metadata.trace_id == "trace-456"

    def test_serialize_event(self):
        """Test event serialization to JSON."""
        schema = FileReadActionSchema(
            action_type="read",
            path="/tmp/test.py",
            metadata=EventMetadata(event_id=1, trace_id="trace-123"),
        )
        json_str = serialize_event(schema)
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["action_type"] == "read"
        assert data["path"] == "/tmp/test.py"
        assert data["metadata"]["event_id"] == 1
        assert data["metadata"]["trace_id"] == "trace-123"

    def test_deserialize_event(self):
        """Test event deserialization from JSON."""
        data = {
            "schema_version": "1.0.0",
            "action_type": "read",
            "path": "/tmp/test.py",
            "start": 0,
            "end": 10,
            "runnable": True,
            "metadata": {"event_id": 1},
        }
        schema = deserialize_event(data)
        assert isinstance(schema, FileReadActionSchema)
        assert schema.action_type == "read"
        assert schema.path == "/tmp/test.py"
        assert schema.start == 0
        assert schema.end == 10

    def test_deserialize_observation(self):
        """Test observation deserialization from JSON."""
        data = {
            "schema_version": "1.0.0",
            "observation_type": "run",
            "command": "ls -la",
            "content": "file1.txt file2.txt",
            "cmd_metadata": {"exit_code": 0, "pid": 12345},
            "metadata": {"event_id": 1},
        }
        schema = deserialize_event(data)
        assert isinstance(schema, CmdOutputObservationSchema)
        assert schema.observation_type == "run"
        assert schema.command == "ls -la"
        assert schema.content == "file1.txt file2.txt"
        assert schema.cmd_metadata["exit_code"] == 0
        assert schema.metadata.event_id == 1

    def test_validate_event_schema(self):
        """Test event schema validation."""
        schema = FileReadActionSchema(
            action_type="read",
            path="/tmp/test.py",
            metadata=EventMetadata(event_id=1),
        )
        assert validate_event_schema(schema) is True

    def test_migrate_schema_version_same_version(self):
        """Test schema migration when versions are the same."""
        data = {
            "schema_version": "1.0.0",
            "action_type": "read",
            "path": "/tmp/test.py",
        }
        migrated = migrate_schema_version(data, EventVersion.V1, EventVersion.V1)
        assert migrated == data

    def test_migrate_schema_version_unsupported(self):
        """Test schema migration with unsupported versions."""
        data = {
            "schema_version": "1.0.0",
            "action_type": "read",
            "path": "/tmp/test.py",
        }
        with pytest.raises(ValueError, match="Migration from .* to .* is not"):
            migrate_schema_version(data, EventVersion.V1, EventVersion.V2)

    def test_action_schema_with_metadata(self):
        """Test action schema with metadata."""
        schema = CmdRunActionSchema(
            action_type="run",
            command="ls -la",
            metadata=EventMetadata(
                event_id=1,
                sequence=2,
                timestamp=datetime.now(),
                source=EventSource.AGENT,
                trace_id="trace-123",
            ),
        )
        assert schema.metadata.event_id == 1
        assert schema.metadata.sequence == 2
        assert schema.metadata.source == EventSource.AGENT
        assert schema.metadata.trace_id == "trace-123"

    def test_observation_schema_with_metadata(self):
        """Test observation schema with metadata."""
        schema = FileReadObservationSchema(
            observation_type="read",
            path="/tmp/test.py",
            content="file content",
            metadata=EventMetadata(
                event_id=1,
                sequence=2,
                timestamp=datetime.now(),
                source=EventSource.ENVIRONMENT,
                trace_id="trace-123",
            ),
        )
        assert schema.metadata.event_id == 1
        assert schema.metadata.sequence == 2
        assert schema.metadata.source == EventSource.ENVIRONMENT
        assert schema.metadata.trace_id == "trace-123"

    def test_serialize_deserialize_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = FileReadActionSchema(
            action_type="read",
            path="/tmp/test.py",
            start=0,
            end=10,
            thought="Reading file",
            metadata=EventMetadata(event_id=1, trace_id="trace-123"),
        )
        json_str = serialize_event(original)
        deserialized = deserialize_event(json_str)
        assert isinstance(deserialized, FileReadActionSchema)
        assert deserialized.action_type == original.action_type
        assert deserialized.path == original.path
        assert deserialized.start == original.start
        assert deserialized.end == original.end
        assert deserialized.thought == original.thought
        assert deserialized.metadata.event_id == original.metadata.event_id
        assert deserialized.metadata.trace_id == original.metadata.trace_id
