"""Tests for tool-specific prompt optimization."""

import pytest
from unittest.mock import Mock
from forge.prompt_optimization.tool_optimizer import ToolOptimizer
from forge.prompt_optimization.models import PromptCategory, PromptVariant
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.tracker import PerformanceTracker
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.tool_descriptions import get_optimized_description
from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk


class TestToolOptimizer:
    @staticmethod
    def _get_function_block(tool):
        return tool.function if hasattr(tool, "function") else tool.get("function", {})

    @staticmethod
    def _get_description(block):
        return block.description if hasattr(block, "description") else block.get("description")

    """Test cases for ToolOptimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = PromptRegistry()
        self.tracker = PerformanceTracker({
            'success_weight': 0.4,
            'time_weight': 0.2,
            'error_weight': 0.2,
            'cost_weight': 0.2
        })
        self.optimizer = Mock(spec=PromptOptimizer)
        self.tool_optimizer = ToolOptimizer(self.registry, self.tracker, self.optimizer)
    
    def test_tool_optimizer_initialization(self):
        """Test tool optimizer initialization."""
        assert self.tool_optimizer.registry == self.registry
        assert self.tool_optimizer.tracker == self.tracker
        assert self.tool_optimizer.optimizer == self.optimizer
        assert len(self.tool_optimizer.tool_prompt_ids) > 0
    
    def test_optimize_tool_without_optimizer(self):
        """Test tool optimization when optimizer is None."""
        tool_optimizer = ToolOptimizer(self.registry, self.tracker, None)
        
        original_tool = ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name="test_tool",
                description="Test description",
                parameters={"type": "object", "properties": {}}
            )
        )
        
        optimized_tool = tool_optimizer.optimize_tool(original_tool, "test_tool")
        assert optimized_tool == original_tool
    
    def test_optimize_tool_with_variant_dict_input(self):
        """Test tool optimization with a variant."""
        # Mock the optimizer to return a variant
        mock_variant = PromptVariant(
            id="test-variant-1",
            content="DESCRIPTION: Optimized test description\n\nPARAMETERS:\n- param1:\n  description: Optimized parameter description",
            version=1
        )
        self.optimizer.select_variant.return_value = mock_variant
        
        original_tool = ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name="test_tool",
                description="Original description",
                parameters={
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "Original param description"}
                    }
                }
            )
        )
        
        optimized_tool = self.tool_optimizer.optimize_tool(original_tool, "think")
        function_block = optimized_tool["function"]
        assert function_block["description"].startswith("Optimized")
    
    def test_optimize_think_tool(self):
        """Test optimization of the think tool."""
        # Mock the optimizer to return a variant
        mock_variant = PromptVariant(
            id="think-variant-1",
            content="DESCRIPTION: Enhanced thinking tool with improved reasoning capabilities\n\nPARAMETERS:\n- thought:\n  description: Your detailed analytical thought process with step-by-step reasoning",
            version=1
        )
        self.optimizer.select_variant.return_value = mock_variant
        
        original_tool = ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name="think",
                description="Original think description",
                parameters={
                    "type": "object",
                    "properties": {
                        "thought": {"type": "string", "description": "Original thought description"}
                    }
                }
            )
        )
        
        optimized_tool = self.tool_optimizer.optimize_tool(original_tool, "think")
        
        # Should return optimized tool
        assert optimized_tool != original_tool
        function_block = self._get_function_block(optimized_tool)
        description = self._get_description(function_block)
        assert description and "Enhanced thinking tool" in description
    
    def test_parse_tool_variant(self):
        """Test parsing of tool variant content."""
        content = """DESCRIPTION: This is an optimized description

PARAMETERS:
- param1:
  description: This is parameter 1
  type: string
- param2:
  description: This is parameter 2
  type: number"""
        
        parsed = self.tool_optimizer._parse_tool_variant(content)
        
        assert parsed['description'] == "This is an optimized description"
        assert 'parameters' in parsed
        assert 'param1' in parsed['parameters']['properties']
        assert 'param2' in parsed['parameters']['properties']
        assert parsed['parameters']['properties']['param1']['description'] == "This is parameter 1"

    def test_parse_tool_variant_handles_simple_values(self):
        """Ensure parser handles non-dict parameter descriptions."""
        content = """DESCRIPTION: Simple description

PARAMETERS:
- paramX:
  description: Simple
- paramY:
  value: Example"""

        parsed = self.tool_optimizer._parse_tool_variant(content)
        assert parsed["parameters"]["properties"]["paramX"]["description"] == "Simple"
        assert parsed["parameters"]["properties"]["paramY"]["value"] == "Example"
    
    def test_track_tool_execution(self):
        """Test tracking tool execution."""
        self.optimizer.record_execution = Mock()
        
        self.tool_optimizer.track_tool_execution(
            tool_name="think",
            success=True,
            execution_time=1.5,
            token_cost=0.1,
            error_message=None,
            metadata={"test": "data"}
        )
        
        self.optimizer.record_execution.assert_called_once()
        call_args = self.optimizer.record_execution.call_args
        assert call_args[1]['success'] is True
        assert call_args[1]['execution_time'] == 1.5
        assert call_args[1]['token_cost'] == 0.1
        assert call_args[1]['metadata']['test'] == "data"
    
    def test_track_tool_execution_without_optimizer(self):
        """Tracking should no-op when optimizer missing."""
        tool_optimizer = ToolOptimizer(self.registry, self.tracker, None)
        tool_optimizer.track_tool_execution("think", True, 1.0)

    def test_create_tool_variants(self):
        """Test creating tool variants."""
        self.optimizer.add_variant = Mock(return_value="variant-id-1")
        
        variants = self.tool_optimizer.create_tool_variants(
            tool_name="think",
            original_description="Original description",
            original_parameters={"param1": {"type": "string"}}
        )
        
        assert len(variants) == 1
        assert variants[0] == "variant-id-1"
        self.optimizer.add_variant.assert_called_once()

    def test_create_tool_variants_unknown_tool(self):
        """Should return empty list for unknown tool."""
        variants = self.tool_optimizer.create_tool_variants(
            tool_name="unknown",
            original_description="Original description",
            original_parameters={},
        )
        assert variants == []
    
    def test_get_tool_optimization_status(self):
        """Test getting tool optimization status."""
        self.optimizer.get_optimization_status = Mock(return_value={"status": "optimized"})
        
        status = self.tool_optimizer.get_tool_optimization_status("think")
        
        assert status == {"status": "optimized"}
        self.optimizer.get_optimization_status.assert_called_once_with("tool_think")
    
    def test_get_all_tool_status(self):
        """Test getting status for all tools."""
        self.optimizer.get_optimization_status = Mock(return_value={"status": "optimized"})
        
        status = self.tool_optimizer.get_all_tool_status()
        
        assert len(status) > 0
        assert "think" in status
        assert status["think"] == {"status": "optimized"}
    
    def test_force_optimize_tool(self):
        """Test force optimizing a tool."""
        self.optimizer.add_variant = Mock(return_value="variant-id-1")
        self.optimizer.force_switch_variant = Mock()
        
        variant_id = self.tool_optimizer.force_optimize_tool(
            tool_name="think",
            description="Forced description",
            parameters={"param1": {"type": "string"}}
        )
        
        assert variant_id == "variant-id-1"
        self.optimizer.add_variant.assert_called_once()
        self.optimizer.force_switch_variant.assert_called_once_with("tool_think", "variant-id-1")
    
    def test_force_optimize_tool_unknown(self):
        """Force optimize should return None for unknown tool."""
        result = self.tool_optimizer.force_optimize_tool(
            tool_name="unknown",
            description="Forced description",
            parameters={},
        )
        assert result is None

    def test_get_tool_performance_summary(self):
        """Test getting tool performance summary."""
        self.tracker.get_prompt_metrics = Mock(return_value={
            "variant-1": Mock(composite_score=0.8),
            "variant-2": Mock(composite_score=0.9)
        })
        
        summary = self.tool_optimizer.get_tool_performance_summary()
        
        assert len(summary) > 0
        assert "think" in summary
        assert summary["think"]["variants"] == 2
        assert summary["think"]["best_score"] == 0.9

    def test_get_tool_performance_summary_with_iterable_metrics(self):
        """Ensure summary handles iterable metrics outputs."""
        self.tracker.get_prompt_metrics = Mock(return_value=[
            ("variant-1", Mock(composite_score=0.7)),
            ("variant-3", Mock(composite_score=0.95)),
        ])

        summary = self.tool_optimizer.get_tool_performance_summary()
        assert summary["think"]["best_score"] == 0.95
        assert summary["think"]["variants"] == 2

    def test_evolve_tool_flow(self, monkeypatch: pytest.MonkeyPatch):
        """Test evolve_tool invoking PromptEvolver."""
        self.optimizer.should_evolve_prompt.return_value = True
        self.optimizer.get_candidates_for_evolution.return_value = [PromptVariant(prompt_id="tool_think")]

        class _StubEvolver:
            def __init__(self, *args, **kwargs):
                pass

        from forge.prompt_optimization import evolver as evolver_module

        def _stub(*args, **kwargs):
            class _Stub:
                def evolve_prompt(self, prompt_id: str, max_variants: int = 3):
                    return ["variant_a", "variant_b"]

            return _Stub()

        monkeypatch.setattr(evolver_module, "PromptEvolver", _stub)

        variants = self.tool_optimizer.evolve_tool("think")
        assert variants == ["variant_a", "variant_b"]


class TestToolDescriptions:
    """Test cases for tool descriptions."""
    
    def test_get_optimized_description(self):
        """Test getting optimized description for a tool."""
        desc = get_optimized_description("think")
        
        assert desc is not None
        assert "description" in desc
        assert "parameters" in desc
        assert "thought" in desc["parameters"]
    
    def test_get_optimized_description_nonexistent(self):
        """Test getting optimized description for nonexistent tool."""
        desc = get_optimized_description("nonexistent_tool")
        
        assert desc == {}
    
    def test_get_all_optimized_descriptions(self):
        """Test getting all optimized descriptions."""
        from forge.prompt_optimization.tool_descriptions import get_all_optimized_descriptions

        all_descriptions = get_all_optimized_descriptions()

        assert isinstance(all_descriptions, dict)
        assert "think" in all_descriptions
        assert all_descriptions["think"]["parameters"]
    
    def test_create_tool_variant_content(self):
        """Test creating tool variant content."""
        from forge.prompt_optimization.tool_descriptions import create_tool_variant_content
        
        content = create_tool_variant_content(
            tool_name="think",
            description="Test description",
            parameters={
                "thought": {
                    "description": "Test thought parameter",
                    "type": "string"
                }
            }
        )
        
        assert "DESCRIPTION: Test description" in content
        assert "PARAMETERS:" in content
        assert "- thought:" in content
        assert "description: Test thought parameter" in content

    def test_create_tool_variant_content_with_string_parameter(self):
        """Test variant content creation when parameter is plain string."""
        from forge.prompt_optimization.tool_descriptions import create_tool_variant_content

        content = create_tool_variant_content(
            tool_name="notes",
            description="Simple",
            parameters={"note": "Use carefully"},
        )
        assert "note" in content
        assert "Use carefully" in content

if __name__ == "__main__":
    pytest.main([__file__])
