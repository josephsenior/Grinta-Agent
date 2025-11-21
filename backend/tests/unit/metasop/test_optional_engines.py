from __future__ import annotations

import types
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from forge.metasop.core.engines import OptionalEnginesFacade
from forge.metasop.models import StepResult
from forge.metasop.settings import MetaSOPSettings


class TestOptionalEnginesFacade(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = MetaSOPSettings()
        self.orch = MagicMock()
        self.orch.settings = self.settings
        self.orch.llm_registry = None
        self.orch.learning_storage = None
        self.orch.causal_engine = None
        self.orch.ace_framework = None
        self.orch.prompt_optimizer = None
        self.orch.parallel_engine = None
        self.orch.predictive_planner = None
        self.orch.collaborative_streaming = None
        self.orch._emit_event = MagicMock()
        self.facade = OptionalEnginesFacade(self.orch)

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    @patch("forge.metasop.learning_storage.LearningStorage")
    def test_initialize_learning_storage_enabled(self, mock_storage) -> None:
        self.settings.enable_learning = True
        self.settings.learning_persistence_path = "/tmp/learning"

        storage_instance = mock_storage.return_value
        self.facade.initialize_learning_storage()

        mock_storage.assert_called_once_with(base_path="/tmp/learning")
        self.assertIs(self.orch.learning_storage, storage_instance)

    @patch("forge.metasop.causal_reasoning.CausalReasoningEngine")
    def test_initialize_causal_engine_with_llm_and_patterns(
        self, mock_engine_class
    ) -> None:
        self.settings.enable_causal_reasoning = True

        llm = SimpleNamespace(config=SimpleNamespace(model="gpt-test"))
        self.orch.llm_registry = MagicMock()
        self.orch.llm_registry.get_active_llm.return_value = llm

        engine_instance = mock_engine_class.return_value
        engine_instance.conflict_patterns = {}
        engine_instance.resource_usage_history = {}
        engine_instance.performance_stats = {}

        self.orch.learning_storage = MagicMock()
        self.orch.learning_storage.load_causal_patterns.return_value = {
            "conflict_patterns": {"step": "data"},
            "resource_usage_history": {"hist": 1},
            "performance_stats": {"stats": 2},
        }

        self.facade.initialize_causal_engine()

        mock_engine_class.assert_called_once_with(llm=llm)
        self.assertIs(self.orch.causal_engine, engine_instance)
        self.assertIn("step", engine_instance.conflict_patterns)

    @patch("forge.metasop.ace.ACEFramework")
    @patch("forge.metasop.ace.ContextPlaybook")
    @patch("forge.metasop.ace.ACEConfig")
    def test_initialize_ace_framework_success(
        self, mock_config, mock_playbook, mock_framework
    ) -> None:
        self.settings.enable_ace = True
        self.settings.ace_playbook_persistence_path = None

        llm = SimpleNamespace()
        self.orch.llm_registry = MagicMock()
        self.orch.llm_registry.get_active_llm.return_value = llm

        self.facade.initialize_ace_framework()

        mock_config.assert_called_once()
        mock_playbook.assert_called_once()
        mock_framework.assert_called_once()
        self.assertIs(self.orch.ace_framework, mock_framework.return_value)

    @patch("forge.prompt_optimization.storage.PromptStorage")
    @patch("forge.prompt_optimization.optimizer.PromptOptimizer")
    @patch("forge.prompt_optimization.tracker.PerformanceTracker")
    @patch("forge.prompt_optimization.registry.PromptRegistry")
    @patch("forge.prompt_optimization.models.OptimizationConfig")
    def test_initialize_prompt_optimization_success(
        self,
        mock_config,
        mock_registry,
        mock_tracker,
        mock_optimizer,
        mock_storage,
    ) -> None:
        self.settings.enable_prompt_optimization = True

        storage_instance = mock_storage.return_value
        self.facade.initialize_prompt_optimization()

        mock_config.assert_called_once()
        mock_registry.assert_called_once()
        mock_tracker.assert_called_once()
        mock_optimizer.assert_called_once()
        storage_instance.load_all.assert_called_once()
        self.assertIn("optimizer", self.orch.prompt_optimizer)

    @patch("forge.metasop.parallel_execution.ParallelExecutionEngine")
    def test_initialize_parallel_engine(self, mock_parallel) -> None:
        self.settings.enable_parallel_execution = True
        mock_parallel.return_value = SimpleNamespace()

        self.facade.initialize_parallel_engine()

        mock_parallel.assert_called_once()
        self.assertIs(self.orch.parallel_engine, mock_parallel.return_value)

    @patch("forge.metasop.predictive_execution.PredictiveExecutionPlanner")
    def test_initialize_predictive_planner(self, mock_planner) -> None:
        self.settings.enable_predictive_planning = True
        self.orch.parallel_engine = SimpleNamespace()
        self.orch.causal_engine = SimpleNamespace()

        self.facade.initialize_predictive_planner()

        mock_planner.assert_called_once()
        self.assertIs(self.orch.predictive_planner, mock_planner.return_value)

    @patch("forge.metasop.collaborative_streaming.ContextAwareStreamingEngine")
    def test_initialize_collaborative_streaming(self, mock_streaming) -> None:
        self.settings.enable_collaborative_streaming = True
        self.orch.parallel_engine = SimpleNamespace()
        self.orch.causal_engine = SimpleNamespace()
        self.orch.predictive_planner = SimpleNamespace()

        self.facade.initialize_collaborative_streaming()

        mock_streaming.assert_called_once()
        self.assertIs(self.orch.collaborative_streaming, mock_streaming.return_value)

    # ------------------------------------------------------------------
    # Prompt optimization helpers
    # ------------------------------------------------------------------
    def test_apply_prompt_optimization_returns_variant(self) -> None:
        variant = SimpleNamespace(content="optimized prompt", id="variant-123")
        optimizer = MagicMock()
        optimizer.select_variant.return_value = variant
        self.orch.prompt_optimizer = {
            "optimizer": optimizer,
            "storage": MagicMock(),
        }

        step = SimpleNamespace(role="builder")
        profile = {"role_description": "original"}

        result = self.facade.apply_prompt_optimization(step, profile)

        optimizer.select_variant.assert_called_once()
        self.assertEqual(result["role_description"], "optimized prompt")
        self.assertEqual(result["_prompt_variant_id"], "variant-123")

    def test_track_prompt_performance_records_execution(self) -> None:
        optimizer = MagicMock()
        storage = MagicMock()
        self.orch.prompt_optimizer = {
            "optimizer": optimizer,
            "storage": storage,
        }

        step = SimpleNamespace(role="builder", _prompt_variant_id="variant-123", id="s1")
        result = StepResult(ok=True)

        self.facade.track_prompt_performance(step, result, execution_time=1.23, token_cost=4.56)

        optimizer.record_execution.assert_called_once()
        storage.auto_save.assert_called()

    # ------------------------------------------------------------------
    # Learning & feedback helpers
    # ------------------------------------------------------------------
    def test_collect_causal_feedback_invokes_engine(self) -> None:
        self.settings.enable_learning = True
        self.orch.causal_engine = MagicMock()

        with patch.object(self.facade, "save_causal_patterns") as mock_save:
            step = SimpleNamespace(id="s1")
            artifacts: Dict[str, SimpleNamespace] = {"s1": SimpleNamespace()}
            active_steps = [SimpleNamespace(id="s2")]

            self.facade.collect_causal_feedback(step, True, artifacts, active_steps)

            self.orch.causal_engine.learn_from_execution.assert_called_once()
            mock_save.assert_called_once()

    def test_collect_execution_feedback_updates_learning(self) -> None:
        self.settings.enable_learning = True
        self.settings.predictive_learn_from_execution = True

        self.orch.causal_engine = MagicMock()
        self.orch.predictive_planner = MagicMock()
        self.orch.parallel_engine = MagicMock()
        self.orch.parallel_engine.get_execution_stats.return_value = {"workers": 2}

        learning_storage = MagicMock()
        self.orch.learning_storage = learning_storage

        step = SimpleNamespace(id="s1", role="builder")
        artifacts: Dict[str, SimpleNamespace] = {}
        active_steps = [SimpleNamespace(id="s2")]

        with patch.object(self.facade, "collect_causal_feedback") as mock_collect:
            self.facade.collect_execution_feedback(step, True, artifacts, active_steps)

        mock_collect.assert_called_once()
        self.orch.predictive_planner.learn_from_execution.assert_called_once()
        learning_storage.save_parallel_stats.assert_called_once()
        learning_storage.save_performance_history.assert_called_once()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def test_save_ace_playbook_invokes_framework(self) -> None:
        self.settings.ace_playbook_persistence_path = "/tmp/playbook.json"
        self.orch.ace_framework = MagicMock()

        self.facade.save_ace_playbook()

        self.orch.ace_framework.save_playbook.assert_called_once_with(
            "/tmp/playbook.json"
        )

    @patch.dict(
        "sys.modules",
        {
            "forge.agenthub": ModuleType("forge.agenthub"),
            "forge.agenthub.codeact_agent": ModuleType("forge.agenthub.codeact_agent"),
            "forge.agenthub.codeact_agent.tools": ModuleType(
                "forge.agenthub.codeact_agent.tools"
            ),
        },
    )
    @patch("forge.agenthub.codeact_agent.tools.str_replace_editor", create=True)
    def test_check_agent_tool_persistence_emits_event(self, mock_editor) -> None:
        tool = MagicMock()
        tool.function = SimpleNamespace(description="State is persistent for tool")
        mock_editor.create_str_replace_editor_tool.return_value = tool

        self.facade.check_agent_tool_persistence()

        self.orch._emit_event.assert_called_once()


if __name__ == "__main__":
    unittest.main()


