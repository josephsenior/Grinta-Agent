"""
Integration tests for ACE framework with MetaSOP and CodeAct
"""

import pytest
from unittest.mock import Mock, patch
from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
from openhands.metasop.ace.models import ACETrajectory, ACEExecutionResult


class TestACEIntegration:
    """Test ACE framework integration with other components"""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing"""
        llm = Mock()
        llm.generate.return_value = "Mocked LLM response"
        return llm
    
    @pytest.fixture
    def ace_framework(self, mock_llm):
        """Create an ACE framework instance for testing"""
        config = ACEConfig(enable_ace=True, max_bullets=100)
        playbook = ContextPlaybook(max_bullets=100)
        
        return ACEFramework(
            llm=mock_llm,
            context_playbook=playbook,
            config=config
        )
    
    def test_ace_with_metasop_simulation(self, ace_framework):
        """Test ACE framework with simulated MetaSOP step execution"""
        # Simulate a MetaSOP step execution
        step_task = "Implement user authentication system"
        step_role = "engineer"
        
        # Process through ACE framework
        result = ace_framework.process_task(
            query=step_task,
            task_type="metasop",
            role=step_role,
            expected_outcome="Secure authentication system implemented"
        )
        
        # Verify result structure
        assert hasattr(result, 'generation_result')
        assert hasattr(result, 'execution_result')
        assert hasattr(result, 'reflection_result')
        assert hasattr(result, 'curation_result')
        assert hasattr(result, 'success')
        assert hasattr(result, 'processing_time')
    
    def test_ace_with_codeact_simulation(self, ace_framework):
        """Test ACE framework with simulated CodeAct agent execution"""
        # Simulate a CodeAct task
        codeact_task = "Write a Python function to calculate fibonacci numbers"
        
        # Process through ACE framework
        result = ace_framework.process_task(
            query=codeact_task,
            task_type="code_generation"
        )
        
        # Verify result structure
        assert hasattr(result, 'generation_result')
        assert hasattr(result, 'execution_result')
        assert hasattr(result, 'reflection_result')
        assert hasattr(result, 'curation_result')
        assert hasattr(result, 'success')
        assert hasattr(result, 'processing_time')
    
    def test_playbook_growth_over_multiple_tasks(self, ace_framework):
        """Test that playbook grows and improves over multiple tasks"""
        initial_size = len(ace_framework.context_playbook.bullets)
        
        # Process multiple related tasks
        tasks = [
            "Implement user authentication",
            "Add password validation",
            "Implement session management",
            "Add two-factor authentication"
        ]
        
        for task in tasks:
            result = ace_framework.process_task(
                query=task,
                task_type="metasop",
                role="engineer"
            )
            # Simulate successful execution
            if result.generation_result and result.generation_result.success:
                # Simulate adding insights to playbook
                ace_framework.context_playbook.add_bullet(
                    content=f"Strategy for {task}",
                    section=ace_framework.context_playbook.BulletSection.STRATEGIES_AND_HARD_RULES
                )
        
        final_size = len(ace_framework.context_playbook.bullets)
        
        # Playbook should have grown
        assert final_size > initial_size
    
    def test_ace_performance_metrics(self, ace_framework):
        """Test ACE performance metrics tracking"""
        # Process some tasks
        tasks = ["Task 1", "Task 2", "Task 3"]
        
        for task in tasks:
            ace_framework.process_task(query=task, task_type="general")
        
        # Check metrics
        metrics = ace_framework.get_performance_summary()
        
        assert "framework_metrics" in metrics
        assert metrics["framework_metrics"]["total_tasks"] >= len(tasks)
        assert "generator_metrics" in metrics
        assert "reflector_metrics" in metrics
        assert "curator_metrics" in metrics
        assert "playbook_statistics" in metrics
    
    def test_ace_with_different_task_types(self, ace_framework):
        """Test ACE framework with different task types"""
        task_configs = [
            {"query": "Build a web app", "task_type": "appworld", "role": None},
            {"query": "Write Python code", "task_type": "code_generation", "role": None},
            {"query": "Design system architecture", "task_type": "metasop", "role": "architect"},
            {"query": "Test the application", "task_type": "metasop", "role": "qa"},
            {"query": "General problem solving", "task_type": "general", "role": None}
        ]
        
        for config in task_configs:
            result = ace_framework.process_task(**config)
            
            # All should have basic result structure
            assert hasattr(result, 'success')
            assert hasattr(result, 'generation_result')
            assert hasattr(result, 'execution_result')
            assert hasattr(result, 'reflection_result')
            assert hasattr(result, 'curation_result')
    
    def test_ace_error_handling(self, ace_framework):
        """Test ACE framework error handling"""
        # Test with invalid task type
        result = ace_framework.process_task(
            query="Test task",
            task_type="invalid_type"
        )
        
        # Should handle gracefully
        assert hasattr(result, 'success')
        # May or may not succeed depending on implementation
    
    def test_ace_configuration_validation(self):
        """Test ACE configuration validation"""
        # Test valid configuration
        valid_config = ACEConfig(
            enable_ace=True,
            max_bullets=1000,
            num_epochs=5,
            reflector_max_iterations=3
        )
        
        assert valid_config.enable_ace is True
        assert valid_config.max_bullets == 1000
        assert valid_config.num_epochs == 5
        assert valid_config.reflector_max_iterations == 3
        
        # Test default values
        default_config = ACEConfig()
        assert default_config.enable_ace is False
        assert default_config.max_bullets == 1000
        assert default_config.num_epochs == 5
    
    def test_ace_playbook_persistence(self, ace_framework, tmp_path):
        """Test ACE playbook persistence"""
        # Add some content to playbook
        ace_framework.context_playbook.add_bullet(
            content="Test strategy",
            section=ace_framework.context_playbook.BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Save playbook
        filepath = tmp_path / "test_playbook.json"
        success = ace_framework.save_playbook(str(filepath))
        
        assert success
        assert filepath.exists()
        
        # Create new framework and load playbook
        new_framework = ACEFramework(
            llm=ace_framework.llm,
            context_playbook=ContextPlaybook(),
            config=ace_framework.config
        )
        
        success = new_framework.load_playbook(str(filepath))
        assert success
        
        # Verify content was loaded
        assert len(new_framework.context_playbook.bullets) > 0
