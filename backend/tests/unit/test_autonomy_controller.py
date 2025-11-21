"""Unit tests for AutonomyController."""

from types import SimpleNamespace

import pytest

from forge.controller.autonomy import AutonomyController, AutonomyLevel
from forge.events.action import CmdRunAction, FileReadAction
from forge.llm.llm import ContentPolicyViolationError, RateLimitError


def make_config(**overrides):
    """Create a lightweight config stub with desired attributes."""
    defaults = {
        "autonomy_level": AutonomyLevel.BALANCED.value,
        "auto_retry_on_error": False,
        "max_autonomous_iterations": 0,
        "stuck_detection_enabled": False,
        "stuck_threshold_iterations": 0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestAutonomyController:
    """Test suite for AutonomyController."""

    def test_full_autonomy_never_confirms(self):
        """Full autonomy should never request confirmation."""
        config = make_config(autonomy_level=AutonomyLevel.FULL.value)
        controller = AutonomyController(config)

        # Test with various action types
        cmd_action = CmdRunAction(command="ls -la")
        file_action = FileReadAction(path="test.py")
        destructive_action = CmdRunAction(command="rm -rf /tmp/test")

        assert controller.should_request_confirmation(cmd_action) is False
        assert controller.should_request_confirmation(file_action) is False
        assert controller.should_request_confirmation(destructive_action) is False

    def test_supervised_always_confirms(self):
        """Supervised mode should always request confirmation."""
        config = make_config(autonomy_level=AutonomyLevel.SUPERVISED.value)
        controller = AutonomyController(config)

        cmd_action = CmdRunAction(command="echo hello")
        assert controller.should_request_confirmation(cmd_action) is True

    def test_balanced_confirms_high_risk(self):
        """Balanced mode should confirm high-risk actions only."""
        config = make_config(autonomy_level=AutonomyLevel.BALANCED.value)
        controller = AutonomyController(config)

        # Safe action
        safe_action = CmdRunAction(command="ls -la")
        assert controller.should_request_confirmation(safe_action) is False

        # High-risk action
        dangerous_action = CmdRunAction(command="rm -rf /important/data")
        assert controller.should_request_confirmation(dangerous_action) is True

    def test_retry_on_retryable_error(self):
        """Should retry on retryable errors."""
        config = make_config(auto_retry_on_error=True)
        controller = AutonomyController(config)

        import_error = ImportError("No module named 'foo'")
        assert controller.should_retry_on_error(import_error, attempts=0) is True

        # Non-import errors should not trigger retry (handled elsewhere)
        rate_limit = RateLimitError(
            "Rate limit exceeded", llm_provider="openai", model="gpt-4"
        )
        assert controller.should_retry_on_error(rate_limit, attempts=0) is False

    def test_no_retry_on_non_retryable_error(self):
        """Should not retry on non-retryable errors."""
        config = make_config(auto_retry_on_error=True)
        controller = AutonomyController(config)

        # Non-retryable errors
        policy_error = ContentPolicyViolationError(
            "Content policy violated",
            model="claude-sonnet-4-20250514",
            llm_provider="anthropic",
        )
        assert controller.should_retry_on_error(policy_error, attempts=0) is False

        value_error = ValueError("Invalid value")
        assert controller.should_retry_on_error(value_error, attempts=0) is False

    def test_max_retries_reached(self):
        """Should not retry after max attempts."""
        config = make_config(auto_retry_on_error=True)
        controller = AutonomyController(config)

        import_error = ImportError("No module named 'foo'")

        # Should retry on first attempt only
        assert controller.should_retry_on_error(import_error, attempts=0) is True
        assert controller.should_retry_on_error(import_error, attempts=1) is False
        assert controller.should_retry_on_error(import_error, attempts=2) is False

    def test_auto_retry_disabled(self):
        """Should not retry when auto_retry is disabled."""
        config = make_config(auto_retry_on_error=False)
        controller = AutonomyController(config)

        import_error = ImportError("No module named 'foo'")
        assert controller.should_retry_on_error(import_error, attempts=0) is False

    def test_rate_limit_errors_defer_to_llm_retry(self):
        """Rate limit errors are handled by the LLM retry mixin, not the autonomy controller."""
        config = make_config(auto_retry_on_error=True)
        controller = AutonomyController(config)

        rate_limit = RateLimitError(
            "Rate limit exceeded", llm_provider="openai", model="gpt-4"
        )
        assert controller.should_retry_on_error(rate_limit, attempts=0) is False

    def test_high_risk_detection(self):
        """Should detect high-risk commands correctly."""
        config = make_config(autonomy_level=AutonomyLevel.BALANCED.value)
        controller = AutonomyController(config)

        # Destructive patterns
        dangerous_commands = [
            "rm -rf /var",
            "dd if=/dev/zero of=/dev/sda",
            "chmod -R 777 /etc",
            "shutdown now",
        ]

        for cmd in dangerous_commands:
            action = CmdRunAction(command=cmd)
            assert controller._is_high_risk_action(action) is True, (
                f"Failed to detect risk in: {cmd}"
            )

        # Safe commands
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "python script.py",
            "npm install",
        ]

        for cmd in safe_commands:
            action = CmdRunAction(command=cmd)
            assert controller._is_high_risk_action(action) is False, (
                f"False positive for: {cmd}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
