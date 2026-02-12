"""End-to-End tests for autonomous system with real-world app building scenarios.

Tests the full autonomous workflow including:
- Safety validation
- Task completion
- Error recovery
- Circuit breaker
- Audit logging
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from backend.core.config import ForgeConfig
from backend.core.config.llm_config import LLMConfig
from backend.core.config.agent_config import AgentConfig
from backend.security.safety_config import SafetyConfig


@pytest.fixture
def safety_enabled_config():
    """Create a config with all safety features enabled."""
    config = ForgeConfig()

    # Enable safety features
    config.agent = AgentConfig(
        # Safety configuration
        safety=SafetyConfig(
            enabled=True,
            environment="development",  # More permissive for testing
            block_critical_commands=True,
            block_high_risk_in_production=True,
            require_confirmation_for_high_risk=False,  # Auto-block, don't ask
            custom_blocked_patterns=[],
            custom_allowed_commands=[],
        ),
        # Task validation
        enable_completion_validation=True,
        allow_force_finish=False,
        min_progress_threshold=0.7,
        # Circuit breaker
        enable_circuit_breaker=True,
        max_consecutive_errors=5,
        max_high_risk_actions=10,
        max_stuck_detections=3,
    )

    # LLM config
    config.llm = LLMConfig(
        model="claude-sonnet-4-20250514",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,  # Deterministic for testing
    )

    return config


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestRealWorldAutonomousScenarios:
    """Test autonomous system with real app building scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_build_simple_todo_app(self, safety_enabled_config, temp_workspace):
        """Test building a simple TODO app from scratch."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction
        from backend.events.observation import AgentStateChangedObservation

        # Create runtime and agent
        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        # Create controller with safety enabled
        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=20,
            config=safety_enabled_config,
        )

        # Task: Build a simple TODO app
        task = """
        Build a simple TODO app with the following features:
        1. HTML file with a clean UI
        2. JavaScript for adding/removing tasks
        3. Local storage persistence
        4. No external dependencies
        
        Save it as todo.html in the workspace.
        """

        # Send task to agent
        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        # Run the agent
        try:
            state = await controller.run()

            # Verify task completed
            assert state.agent_state.value == "FINISHED", (
                "Agent should finish successfully"
            )

            # Verify file was created
            todo_file = temp_workspace / "todo.html"
            assert todo_file.exists(), "todo.html should be created"

            # Verify file contains expected content
            content = todo_file.read_text()
            assert "TODO" in content.upper(), "Should contain TODO functionality"
            assert "<html" in content.lower(), "Should be valid HTML"
            assert "localStorage" in content or "sessionStorage" in content, (
                "Should use storage"
            )

            # Verify no safety violations
            audit_logs = (
                controller.telemetry_logger.get_recent_entries(limit=100)
                if hasattr(controller, "telemetry_logger")
                else []
            )
            blocked_actions = [
                log for log in audit_logs if not log.get("allowed", True)
            ]

            # Should have no critical commands blocked (building HTML/JS is safe)
            critical_blocked = [
                log for log in blocked_actions if log.get("risk_level") == "CRITICAL"
            ]
            assert len(critical_blocked) == 0, (
                f"No critical commands should be blocked: {critical_blocked}"
            )

            print(f"✅ Successfully built TODO app in {state.iteration} iterations")
            print(f"📝 File size: {todo_file.stat().st_size} bytes")

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_dangerous_command_blocked(
        self, safety_enabled_config, temp_workspace
    ):
        """Test that dangerous commands are blocked by safety validator."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction, CmdRunAction
        from backend.events.observation import ErrorObservation

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=5,
            config=safety_enabled_config,
        )

        try:
            # Try to execute a dangerous command
            dangerous_cmd = CmdRunAction(command="rm -rf /")
            controller.state.history.append(dangerous_cmd)

            # This should trigger safety validation
            await controller._handle_runnable_action(dangerous_cmd)

            # Check that an error observation was created
            error_obs = [
                obs
                for obs in controller.state.history
                if isinstance(obs, ErrorObservation) and "SAFETY" in obs.content
            ]

            assert len(error_obs) > 0, "Safety validator should block dangerous command"
            assert "BLOCKED" in error_obs[0].content, (
                "Should explicitly state command was blocked"
            )

            print("✅ Dangerous command successfully blocked by safety validator")

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_recovery_and_retry(
        self, safety_enabled_config, temp_workspace
    ):
        """Test that agent recovers from errors and retries intelligently."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=15,
            config=safety_enabled_config,
        )

        # Task that will initially fail but can be recovered
        task = """
        1. Try to read a file that doesn't exist (nonexistent.txt)
        2. When it fails, create the file with some content
        3. Read it again to verify it worked
        """

        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        try:
            state = await controller.run()

            # Should complete despite initial failure
            assert state.agent_state.value == "FINISHED", (
                "Should recover from error and complete"
            )

            # Verify file was created after recovery
            test_file = temp_workspace / "nonexistent.txt"
            assert test_file.exists(), "File should be created after recovery"

            # Check error recovery metrics
            error_count = sum(
                1
                for event in controller.state.history
                if "error" in str(type(event)).lower()
            )
            assert error_count > 0, "Should have encountered at least one error"
            assert error_count < 5, "Should not have excessive errors"

            print(f"✅ Successfully recovered from {error_count} error(s)")

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_circuit_breaker_trips_on_repeated_errors(
        self, safety_enabled_config, temp_workspace
    ):
        """Test that circuit breaker stops execution after too many errors."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction

        # Lower error threshold for testing
        safety_enabled_config.agent.max_consecutive_errors = 3

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=20,
            config=safety_enabled_config,
        )

        # Task designed to fail repeatedly
        task = """
        Run the command 'invalid_command_that_does_not_exist' 10 times.
        Keep trying even if it fails.
        """

        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        try:
            state = await controller.run()

            # Circuit breaker should trip before completing all iterations
            assert state.iteration < 10, "Circuit breaker should stop execution early"

            # Check circuit breaker status
            if hasattr(controller, "circuit_breaker"):
                assert controller.circuit_breaker.is_tripped(), (
                    "Circuit breaker should be tripped"
                )

            print(f"✅ Circuit breaker tripped after {state.iteration} iterations")

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_build_calculator_with_tests(
        self, safety_enabled_config, temp_workspace
    ):
        """Test building a calculator with automated tests."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=25,
            config=safety_enabled_config,
        )

        task = """
        Build a calculator application with the following:
        1. calculator.py with basic operations (add, subtract, multiply, divide)
        2. test_calculator.py with pytest tests for all operations
        3. Run the tests to verify everything works
        4. Create a requirements.txt if needed
        
        Make sure all tests pass before finishing.
        """

        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        try:
            state = await controller.run()

            # Verify files were created
            calc_file = temp_workspace / "calculator.py"
            test_file = temp_workspace / "test_calculator.py"

            assert calc_file.exists(), "calculator.py should be created"
            assert test_file.exists(), "test_calculator.py should be created"

            # Verify tests were run (check history for pytest execution)
            test_runs = [
                event
                for event in controller.state.history
                if hasattr(event, "command") and "pytest" in str(event.command)
            ]

            assert len(test_runs) > 0, "Should have run pytest"

            print(
                f"✅ Successfully built calculator with tests in {state.iteration} iterations"
            )

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_task_validation_prevents_premature_completion(
        self, safety_enabled_config, temp_workspace
    ):
        """Test that task validator prevents agent from finishing without completing task."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction, PlaybookFinishAction

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=20,
            config=safety_enabled_config,
        )

        task = """
        Create three files:
        1. file1.txt with "Hello"
        2. file2.txt with "World"
        3. file3.txt with "Test"
        
        All three files must exist.
        """

        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        # Simulate agent trying to finish early (before all files created)
        # Create only 2 files
        (temp_workspace / "file1.txt").write_text("Hello")
        (temp_workspace / "file2.txt").write_text("World")

        # Try to finish
        finish_action = PlaybookFinishAction()

        try:
            # This should be rejected by task validator
            await controller._handle_finish_action(finish_action)

            # Agent should still be running, not finished
            assert controller.state.agent_state.value != "FINISHED", (
                "Task validator should prevent premature completion"
            )

            print("✅ Task validator correctly prevented premature completion")

        finally:
            await runtime.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_audit_logging_captures_actions(
        self, safety_enabled_config, temp_workspace
    ):
        """Test that audit logger captures all agent actions."""
        from backend.controller.agent_controller import AgentController
        from backend.core.setup import create_agent, create_runtime
        from backend.events.action import MessageAction

        runtime = await create_runtime(
            safety_enabled_config, workspace_base=str(temp_workspace)
        )
        agent = create_agent(safety_enabled_config)

        controller = AgentController(
            agent=agent,
            event_stream=runtime.event_stream,
            max_iterations=10,
            config=safety_enabled_config,
        )

        task = "Create a file called test.txt with content 'Audit test'"

        controller.state.history.append(
            MessageAction(content=task, wait_for_response=False)
        )

        try:
            state = await controller.run()

            # Check audit logs
            if hasattr(controller, "telemetry_logger"):
                audit_logs = controller.telemetry_logger.get_recent_entries(limit=100)

                assert len(audit_logs) > 0, "Should have audit log entries"

                # Verify audit logs contain file write action
                file_actions = [
                    log
                    for log in audit_logs
                    if "test.txt" in str(log.get("action_data", {}))
                ]

                assert len(file_actions) > 0, "Should have logged file creation"

                print(f"✅ Captured {len(audit_logs)} audit log entries")
            else:
                print("⚠️  Audit logger not available (may not be initialized)")

        finally:
            await runtime.close()


@pytest.mark.e2e
@pytest.mark.playwright
class TestAutonomousWithPlaywright:
    """Test autonomous system through the web UI using Playwright."""

    @pytest.mark.asyncio
    async def test_ui_build_app_workflow(self, page):
        """Test building an app through the UI."""
        # This requires Forge server to be running
        # Navigate to Forge UI
        await page.goto("http://localhost:3000")

        # Wait for UI to load
        await page.wait_for_selector('[data-testid="chat-input"]', timeout=10000)

        # Enter task
        task = "Build a simple HTML page with a button that changes color when clicked"
        await page.fill('[data-testid="chat-input"]', task)
        await page.click('[data-testid="send-button"]')

        # Wait for agent to start working
        await page.wait_for_selector('[data-testid="agent-thinking"]', timeout=5000)

        # Wait for completion (with timeout)
        await page.wait_for_selector('[data-testid="agent-finished"]', timeout=60000)

        # Verify file was created in file tree
        file_tree = page.locator('[data-testid="file-tree"]')
        assert await file_tree.is_visible()

        # Check for HTML file
        html_file = page.locator("text=/.*\\.html/i").first
        assert await html_file.is_visible(), "HTML file should be visible in file tree"

        print("✅ Successfully built app through UI")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e and not playwright"])
