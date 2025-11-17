"""Tests for telemetry integration with event schemas."""

from __future__ import annotations

import pytest

from forge.controller.tool_telemetry import ToolTelemetry
from forge.events.action import CmdRunAction, FileReadAction, MessageAction
from forge.events.observation import CmdOutputObservation, ErrorObservation
from forge.events.observation.commands import CmdOutputMetadata


class TestTelemetrySchemaIntegration:
    """Test suite for telemetry integration with event schemas."""

    def test_telemetry_converts_action_to_schema(self):
        """Test that telemetry converts actions to typed schemas."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        action = CmdRunAction(
            command="ls -la",
            thought="Listing files",
            blocking=True,
        )
        action.id = 1
        action.sequence = 2
        action.source = "agent"

        schema = telemetry._action_to_schema(action)
        assert schema is not None
        assert schema.action_type == "run"
        assert schema.command == "ls -la"
        assert schema.thought == "Listing files"
        assert schema.blocking is True
        assert schema.metadata.event_id == 1
        assert schema.metadata.sequence == 2

    def test_telemetry_converts_file_read_action_to_schema(self):
        """Test that telemetry converts FileReadAction to typed schema."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        action = FileReadAction(
            path="/tmp/test.py",
            start=0,
            end=10,
            thought="Reading file",
        )
        action.id = 1

        schema = telemetry._action_to_schema(action)
        assert schema is not None
        assert schema.action_type == "read"
        assert schema.path == "/tmp/test.py"
        assert schema.start == 0
        assert schema.end == 10
        assert schema.thought == "Reading file"

    def test_telemetry_converts_observation_to_schema(self):
        """Test that telemetry converts observations to typed schemas."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        metadata = CmdOutputMetadata(
            exit_code=0,
            pid=12345,
            working_dir="/tmp",
        )
        observation = CmdOutputObservation(
            content="file1.txt file2.txt",
            command="ls -la",
            metadata=metadata,
        )
        observation.id = 1
        observation.sequence = 2
        observation.source = "environment"

        schema = telemetry._observation_to_schema(observation)
        assert schema is not None
        assert schema.observation_type == "run"
        assert schema.command == "ls -la"
        assert schema.content == "file1.txt file2.txt"
        assert schema.cmd_metadata["exit_code"] == 0
        assert schema.cmd_metadata["pid"] == 12345
        assert schema.metadata.event_id == 1
        assert schema.metadata.sequence == 2

    def test_telemetry_converts_error_observation_to_schema(self):
        """Test that telemetry converts ErrorObservation to typed schema."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        observation = ErrorObservation(
            content="Command failed",
            error_id="CMD_ERROR",
        )
        observation.id = 1

        schema = telemetry._observation_to_schema(observation)
        assert schema is not None
        assert schema.observation_type == "error"
        assert schema.content == "Command failed"
        assert schema.error_id == "CMD_ERROR"

    def test_telemetry_records_schema_in_events(self):
        """Test that telemetry records schema data in event entries."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        action = CmdRunAction(command="ls -la")
        action.id = 1

        # Simulate telemetry lifecycle
        from forge.controller.tool_pipeline import ToolInvocationContext
        from forge.controller.state.state import State

        ctx = ToolInvocationContext(
            controller=None,  # type: ignore
            action=action,
            state=State(),  # type: ignore
        )

        telemetry.on_plan(ctx)
        assert "action_schema" in ctx.metadata.get("telemetry", {})
        action_schema = ctx.metadata["telemetry"]["action_schema"]
        assert action_schema["action_type"] == "run"
        assert action_schema["command"] == "ls -la"

    def test_telemetry_records_observation_schema(self):
        """Test that telemetry records observation schema in event entries."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        action = CmdRunAction(command="ls -la")
        action.id = 1

        metadata = CmdOutputMetadata(exit_code=0, pid=12345)
        observation = CmdOutputObservation(
            content="file1.txt",
            command="ls -la",
            metadata=metadata,
        )
        observation.id = 2

        from forge.controller.tool_pipeline import ToolInvocationContext
        from forge.controller.state.state import State

        ctx = ToolInvocationContext(
            controller=None,  # type: ignore
            action=action,
            state=State(),  # type: ignore
        )

        telemetry.on_plan(ctx)
        telemetry.on_observe(ctx, observation)

        telemetry_data = ctx.metadata.get("telemetry", {})
        assert "observation_schema" in telemetry_data
        obs_schema = telemetry_data["observation_schema"]
        assert obs_schema["observation_type"] == "run"
        assert obs_schema["command"] == "ls -la"
        assert obs_schema["cmd_metadata"]["exit_code"] == 0

    def test_telemetry_handles_unknown_action_type(self):
        """Test that telemetry handles unknown action types gracefully."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        # Create an action with an unknown type
        action = MessageAction(content="test")
        action.action = "unknown_type"  # type: ignore

        schema = telemetry._action_to_schema(action)
        # Should return None for unknown types
        assert schema is None

    def test_telemetry_handles_unknown_observation_type(self):
        """Test that telemetry handles unknown observation types gracefully."""
        telemetry = ToolTelemetry.get_instance()
        telemetry.reset_for_test()

        # Create an observation with an unknown type
        observation = ErrorObservation(content="test")
        observation.observation = "unknown_type"  # type: ignore

        schema = telemetry._observation_to_schema(observation)
        # Should return None for unknown types
        assert schema is None
