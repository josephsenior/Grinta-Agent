"""Unit tests for ACE Framework."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from forge.metasop.ace.ace_framework import ACEFramework
from forge.metasop.ace.context_playbook import ContextPlaybook, BulletSection
from forge.metasop.ace.models import (
    ACEConfig,
    ACETrajectory,
    ACEExecutionResult,
    ACEGenerationResult,
    ACEReflectionResult,
    ACECurationResult,
    ACEDeltaUpdate,
    ACEInsight,
)


class TestACEFramework:
    """Test ACE Framework functionality."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = Mock()
        llm.generate.return_value = "Mocked LLM response"
        return llm

    @pytest.fixture
    def mock_context_playbook(self):
        """Create a real context playbook for testing."""
        return ContextPlaybook(enable_grow_and_refine=True)

    @pytest.fixture
    def ace_framework(self, mock_llm, mock_context_playbook):
        """Create an ACE framework instance for testing."""
        config = ACEConfig(enable_ace=True)
        framework = ACEFramework(
            llm=mock_llm, context_playbook=mock_context_playbook, config=config
        )
        framework.generator = Mock()
        framework.generator.generate = Mock()
        framework.generator.get_metrics = Mock(return_value={})
        framework.reflector = Mock()
        framework.reflector.analyze = Mock()
        framework.reflector.get_metrics = Mock(return_value={})
        framework.curator = Mock()
        framework.curator.curate = Mock()
        framework.curator.get_metrics = Mock(return_value={})
        return framework

    def test_ace_framework_initialization(self, mock_llm, mock_context_playbook):
        """Test ACE framework initialization."""
        config = ACEConfig(enable_ace=True)
        framework = ACEFramework(
            llm=mock_llm, context_playbook=mock_context_playbook, config=config
        )

        assert framework.llm == mock_llm
        assert framework.context_playbook == mock_context_playbook
        assert framework.config == config
        assert framework.generator is not None
        assert framework.reflector is not None
        assert framework.curator is not None

    def test_process_task_success(self, ace_framework, mock_llm):
        """Test successful task processing."""
        # Mock the components
        trajectory = ACETrajectory(
            content="Test trajectory content with enough length to succeed." * 2,
            task_type="general",
            used_bullet_ids=[],
            playbook_content="",
            generation_metadata={},
        )
        generation_result = ACEGenerationResult(
            trajectory=trajectory, success=True, processing_time=1.0, tokens_used=100
        )
        ace_framework.generator.generate = Mock(return_value=generation_result)

        insight = ACEInsight(
            reasoning="Detailed reasoning",
            error_identification="",
            root_cause_analysis="",
            correct_approach="Follow best practices",
            key_insight="Consistency matters",
            bullet_tags=[],
            success=True,
            confidence=0.8,
        )
        reflection_result = ACEReflectionResult(
            insights=[insight],
            success=True,
            confidence=0.8,
            processing_time=0.5,
            tokens_used=50,
        )
        ace_framework.reflector.analyze = Mock(return_value=reflection_result)

        curation_result = ACECurationResult(
            delta_updates=[],
            success=True,
            redundancy_removed=0,
            processing_time=0.2,
            tokens_used=25,
        )
        ace_framework.curator.curate = Mock(return_value=curation_result)

        # Process task
        result = ace_framework.process_task("Test task", "general")

        assert result.success
        assert result.generation_result.success
        assert result.reflection_result.success
        assert result.curation_result.success
        assert ace_framework.performance_metrics.total_tasks == 1
        assert ace_framework.performance_metrics.successful_tasks == 1

    def test_process_task_failure(self, ace_framework, mock_llm):
        """Test task processing failure."""
        # Mock generator failure
        trajectory = ACETrajectory(
            content="",
            task_type="general",
            used_bullet_ids=[],
            playbook_content="",
            generation_metadata={"error": "Generation failed"},
        )
        generation_result = ACEGenerationResult(
            trajectory=trajectory,
            success=False,
            processing_time=1.0,
            tokens_used=0,
            retries=3,
        )
        ace_framework.generator.generate = Mock(return_value=generation_result)

        # Process task
        result = ace_framework.process_task("Test task", "general")

        assert not result.success
        assert not result.generation_result.success
        assert ace_framework.performance_metrics.total_tasks == 1
        assert ace_framework.performance_metrics.failed_tasks == 1

    def test_multi_epoch_training(self, ace_framework):
        """Test multi-epoch training."""
        queries = ["Task 1", "Task 2", "Task 3"]

        # Mock successful processing
        ace_framework.process_task = Mock(return_value=Mock(success=True))

        # Run multi-epoch training
        results = ace_framework.multi_epoch_training(queries, "general")

        # Should process each query for each epoch
        expected_calls = len(queries) * ace_framework.config.num_epochs
        assert ace_framework.process_task.call_count == expected_calls
        assert len(results) == expected_calls

    def test_get_performance_summary(self, ace_framework):
        """Test getting performance summary."""
        # Set some metrics
        ace_framework.performance_metrics.total_tasks = 10
        ace_framework.performance_metrics.successful_tasks = 8
        ace_framework.performance_metrics.failed_tasks = 2

        # Mock component metrics
        ace_framework.generator.get_metrics = Mock(return_value={"generator_metric": 1})
        ace_framework.reflector.get_metrics = Mock(return_value={"reflector_metric": 2})
        ace_framework.curator.get_metrics = Mock(return_value={"curator_metric": 3})
        ace_framework.context_playbook.get_statistics = Mock(
            return_value={"playbook_stats": 4}
        )

        summary = ace_framework.get_performance_summary()

        assert "framework_metrics" in summary
        assert "generator_metrics" in summary
        assert "reflector_metrics" in summary
        assert "curator_metrics" in summary
        assert "playbook_statistics" in summary
        assert summary["framework_metrics"]["total_tasks"] == 10
        assert summary["framework_metrics"]["successful_tasks"] == 8

    def test_save_load_playbook(self, ace_framework, tmp_path):
        """Test saving and loading playbook."""
        filepath = tmp_path / "test_playbook.json"

        # Mock playbook export
        ace_framework.context_playbook.export_playbook = Mock(
            return_value={
                "bullets": {},
                "sections": {},
                "performance_metrics": {},
                "exported_at": "2024-01-01T00:00:00",
                "version": "1.0",
            }
        )

        # Test save
        success = ace_framework.save_playbook(str(filepath))
        assert success
        assert filepath.exists()

        # Test load
        ace_framework.context_playbook.import_playbook = Mock()
        success = ace_framework.load_playbook(str(filepath))
        assert success
        ace_framework.context_playbook.import_playbook.assert_called_once()

    def test_reset_metrics(self, ace_framework):
        """Test resetting metrics."""
        # Set some metrics
        ace_framework.performance_metrics.total_tasks = 10
        ace_framework.adaptation_history = [Mock(), Mock()]

        # Reset
        ace_framework.reset_metrics()

        assert ace_framework.performance_metrics.total_tasks == 0
        assert len(ace_framework.adaptation_history) == 0

    def test_simulate_execution(self, ace_framework):
        """Test execution simulation."""
        trajectory = ACETrajectory(
            content="Test trajectory content that is sufficiently long for success."
            * 2,
            task_type="general",
            used_bullet_ids=[],
            playbook_content="",
            generation_metadata={},
        )

        result = ace_framework._simulate_execution(trajectory, "Test query", "general")

        assert isinstance(result, ACEExecutionResult)
        assert result.success
        assert "Test query" in result.output
        assert result.metadata["simulated"] is True

    def test_apply_delta_updates(self, ace_framework):
        """Test applying delta updates."""
        # Mock context playbook methods
        ace_framework.context_playbook.add_bullet = Mock(return_value="new-bullet-id")
        ace_framework.context_playbook.update_bullet = Mock(return_value=True)
        ace_framework.context_playbook.remove_bullet = Mock(return_value=True)

        # Create delta updates
        updates = [
            ACEDeltaUpdate(
                type="ADD",
                section=BulletSection.STRATEGIES_AND_HARD_RULES,
                content="New strategy",
            ),
            ACEDeltaUpdate(type="UPDATE", bullet_id="existing-bullet", helpful=True),
            ACEDeltaUpdate(type="REMOVE", bullet_id="old-bullet"),
        ]

        # Apply updates
        ace_framework._apply_delta_updates(updates)

        # Verify calls
        ace_framework.context_playbook.add_bullet.assert_called_once()
        ace_framework.context_playbook.update_bullet.assert_called_once()
        ace_framework.context_playbook.remove_bullet.assert_called_once()

    def test_run_curation_phase_returns_none_without_insights(self, ace_framework):
        """_run_curation_phase should exit early when reflection fails."""
        reflection_result = SimpleNamespace(success=False, insights=[])
        result = ace_framework._run_curation_phase(
            reflection_result=reflection_result,
            query="Task",
            task_type="general",
            role=None,
            expected_outcome=None,
        )

        assert result is None
        ace_framework.curator.curate.assert_not_called()

    def test_update_metrics_handles_failure(self, ace_framework):
        """_update_metrics should track failure paths and helpfulness averages."""
        ace_framework.context_playbook.add_bullet(
            content="Existing insight",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            bullet_id="ctx-existing",
        )
        metrics_before = ace_framework.performance_metrics.failed_tasks

        generation_result = ACEGenerationResult(
            trajectory=ACETrajectory(
                content="",
                task_type="general",
                used_bullet_ids=[],
                playbook_content="",
                generation_metadata={},
            ),
            success=False,
            processing_time=0.1,
            tokens_used=0,
        )
        reflection_result = ACEReflectionResult(
            insights=[],
            success=False,
            confidence=0.0,
            processing_time=0.2,
            tokens_used=0,
        )

        ace_framework._update_metrics(
            generation_result=generation_result,
            reflection_result=reflection_result,
            curation_result=None,
            overall_success=False,
            processing_time=0.5,
        )

        assert ace_framework.performance_metrics.failed_tasks == metrics_before + 1
        assert ace_framework.performance_metrics.avg_helpfulness >= 0

    def test_process_task_applies_delta_updates(self, ace_framework):
        """process_task should apply delta updates when curation succeeds."""
        trajectory = ACETrajectory(
            content="Content long enough to succeed." * 2,
            task_type="general",
            used_bullet_ids=[],
            playbook_content="",
            generation_metadata={},
        )
        generation_result = ACEGenerationResult(
            trajectory=trajectory,
            success=True,
            processing_time=0.1,
            tokens_used=10,
        )
        ace_framework.generator.generate = Mock(return_value=generation_result)

        reflection_insight = ACEInsight(
            reasoning="",
            error_identification="",
            root_cause_analysis="",
            correct_approach="",
            key_insight="Add guard clauses",
            bullet_tags=[],
            success=True,
            confidence=0.7,
        )
        reflection_result = ACEReflectionResult(
            insights=[reflection_insight],
            success=True,
            confidence=0.7,
            processing_time=0.2,
            tokens_used=5,
        )
        ace_framework.reflector.analyze = Mock(return_value=reflection_result)

        delta_update = ACEDeltaUpdate(
            type="ADD",
            section=BulletSection.COMMON_MISTAKES,
            content="Avoid unchecked assumptions",
        )
        ace_framework.curator.curate = Mock(
            return_value=ACECurationResult(
                delta_updates=[delta_update],
                success=True,
                redundancy_removed=0,
                processing_time=0.1,
                tokens_used=3,
            )
        )
        ace_framework.context_playbook.add_bullet = Mock()

        result = ace_framework.process_task("Task", task_type="general")

        assert result.curation_result.delta_updates == [delta_update]
        assert ace_framework.performance_metrics.context_updates == 1
        ace_framework.context_playbook.add_bullet.assert_called_once()

    def test_process_task_with_feedback_branches(self, ace_framework):
        """process_task_with_feedback should handle missing and present generation results."""
        ace_framework.process_task = Mock(return_value="processed")
        ace_framework.generator.generate_with_feedback = Mock(return_value="improved")

        # Missing generation result branch
        fallback = ace_framework.process_task_with_feedback(
            query="Task",
            previous_result=SimpleNamespace(generation_result=None),
            task_type="general",
            role=None,
        )
        assert fallback == "processed"
        ace_framework.generator.generate_with_feedback.assert_not_called()

        # Present generation result branch
        ace_framework.generator.generate_with_feedback.reset_mock()
        previous = SimpleNamespace(
            generation_result=ACEGenerationResult(
                trajectory=ACETrajectory(
                    content="Existing",
                    task_type="general",
                    used_bullet_ids=[],
                    playbook_content="",
                    generation_metadata={},
                ),
                success=True,
                processing_time=0.1,
                tokens_used=1,
                retries=0,
            )
        )
        result = ace_framework.process_task_with_feedback(
            query="Task",
            previous_result=previous,
            task_type="general",
            role="engineer",
        )

        ace_framework.generator.generate_with_feedback.assert_called_once()
        assert result == "processed"

    def test_multi_epoch_training_disabled_short_circuit(self, ace_framework):
        """Disable multi-epoch training should return immediately."""
        ace_framework.config.multi_epoch = False
        assert ace_framework.multi_epoch_training(["Task"], "general") == []

    def test_multi_epoch_training_progress_logging(self, ace_framework, monkeypatch):
        """Progress logging should trigger after every tenth item."""
        ace_framework.config.num_epochs = 1
        ace_framework.process_task = Mock(return_value=Mock(success=True))

        log_calls = []

        def fake_logger(message):
            log_calls.append(message)

        monkeypatch.setattr("forge.metasop.ace.ace_framework.logger.info", fake_logger)
        queries = [f"Task {i}" for i in range(10)]
        ace_framework.multi_epoch_training(queries, task_type="general")

        assert any("Processed 10/10 queries" in call for call in log_calls)

    def test_apply_delta_updates_handles_exceptions(self, ace_framework, monkeypatch):
        """_apply_delta_updates should swallow exceptions and continue."""
        update = ACEDeltaUpdate(
            type="ADD",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            content="New insight",
        )
        ace_framework.context_playbook.add_bullet = Mock(
            side_effect=RuntimeError("failure")
        )

        warnings = []

        def fake_warning(message):
            warnings.append(message)

        monkeypatch.setattr(
            "forge.metasop.ace.ace_framework.logger.warning", fake_warning
        )

        ace_framework._apply_delta_updates([update])

        assert warnings

    def test_save_and_load_playbook_failure_paths(self, ace_framework, monkeypatch):
        """save_playbook and load_playbook should return False on errors."""
        monkeypatch.setattr("builtins.open", Mock(side_effect=OSError("io error")))

        assert ace_framework.save_playbook("path.json") is False

        monkeypatch.setattr(
            "builtins.open", Mock(side_effect=FileNotFoundError("missing"))
        )
        assert ace_framework.load_playbook("path.json") is False
