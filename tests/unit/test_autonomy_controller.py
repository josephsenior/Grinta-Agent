"""Unit tests for AutonomyController."""

import pytest
from openhands.controller.autonomy import AutonomyController, AutonomyLevel
from openhands.core.config.agent_config import AgentConfig
from openhands.events.action import CmdRunAction, FileReadAction
from openhands.llm.llm import ContentPolicyViolationError, RateLimitError


class TestAutonomyController:
    """Test suite for AutonomyController."""
    
    def test_full_autonomy_never_confirms(self):
        """Full autonomy should never request confirmation."""
        config = AgentConfig(autonomy_level="full")
        controller = AutonomyController(config)
        
        # Test with various action types
        cmd_action = CmdRunAction(command="ls -la")
        file_action = FileReadAction(path="test.py")
        destructive_action = CmdRunAction(command="rm -rf /tmp/test")
        
        assert controller.should_request_confirmation(cmd_action) == False
        assert controller.should_request_confirmation(file_action) == False
        assert controller.should_request_confirmation(destructive_action) == False
    
    def test_supervised_always_confirms(self):
        """Supervised mode should always request confirmation."""
        config = AgentConfig(autonomy_level="supervised")
        controller = AutonomyController(config)
        
        cmd_action = CmdRunAction(command="echo hello")
        assert controller.should_request_confirmation(cmd_action) == True
    
    def test_balanced_confirms_high_risk(self):
        """Balanced mode should confirm high-risk actions only."""
        config = AgentConfig(autonomy_level="balanced")
        controller = AutonomyController(config)
        
        # Safe action
        safe_action = CmdRunAction(command="ls -la")
        assert controller.should_request_confirmation(safe_action) == False
        
        # High-risk action
        dangerous_action = CmdRunAction(command="rm -rf /important/data")
        assert controller.should_request_confirmation(dangerous_action) == True
    
    def test_retry_on_retryable_error(self):
        """Should retry on retryable errors."""
        config = AgentConfig(auto_retry_on_error=True)
        controller = AutonomyController(config)
        
        # Retryable errors
        import_error = ImportError("No module named 'foo'")
        assert controller.should_retry_on_error(import_error, attempts=0) == True
        
        rate_limit = RateLimitError("Rate limit exceeded")
        assert controller.should_retry_on_error(rate_limit, attempts=0) == True
    
    def test_no_retry_on_non_retryable_error(self):
        """Should not retry on non-retryable errors."""
        config = AgentConfig(auto_retry_on_error=True)
        controller = AutonomyController(config)
        
        # Non-retryable errors
        policy_error = ContentPolicyViolationError("Content policy violated")
        assert controller.should_retry_on_error(policy_error, attempts=0) == False
        
        value_error = ValueError("Invalid value")
        assert controller.should_retry_on_error(value_error, attempts=0) == False
    
    def test_max_retries_reached(self):
        """Should not retry after max attempts."""
        config = AgentConfig(auto_retry_on_error=True)
        controller = AutonomyController(config)
        
        import_error = ImportError("No module named 'foo'")
        
        # Should retry on first 2 attempts
        assert controller.should_retry_on_error(import_error, attempts=0) == True
        assert controller.should_retry_on_error(import_error, attempts=1) == True
        assert controller.should_retry_on_error(import_error, attempts=2) == True
        
        # Should not retry on 3rd attempt
        assert controller.should_retry_on_error(import_error, attempts=3) == False
    
    def test_auto_retry_disabled(self):
        """Should not retry when auto_retry is disabled."""
        config = AgentConfig(auto_retry_on_error=False)
        controller = AutonomyController(config)
        
        import_error = ImportError("No module named 'foo'")
        assert controller.should_retry_on_error(import_error, attempts=0) == False
    
    def test_retry_strategy_for_rate_limit(self):
        """Rate limit errors should have longer delays."""
        config = AgentConfig(auto_retry_on_error=True)
        controller = AutonomyController(config)
        
        rate_limit = RateLimitError("Rate limit exceeded")
        strategy = controller.get_retry_strategy(rate_limit)
        
        assert strategy["delay"] >= 5
        assert strategy["max_delay"] >= 60
    
    def test_high_risk_detection(self):
        """Should detect high-risk commands correctly."""
        config = AgentConfig(autonomy_level="balanced")
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
            assert controller._is_high_risk_action(action) == True, f"Failed to detect risk in: {cmd}"
        
        # Safe commands
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "python script.py",
            "npm install",
        ]
        
        for cmd in safe_commands:
            action = CmdRunAction(command=cmd)
            assert controller._is_high_risk_action(action) == False, f"False positive for: {cmd}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

