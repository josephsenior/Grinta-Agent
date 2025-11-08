"""Tool-Specific Prompt Optimization.

Extends the prompt optimization system to individual tools,
allowing each tool to have optimized descriptions and parameters.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Union

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

from .models import PromptCategory, PromptVariant
from .optimizer import PromptOptimizer
from .registry import PromptRegistry
from .tracker import PerformanceTracker


class ToolOptimizer:
    """Optimizes individual tool prompts and descriptions."""
    
    def __init__(self, registry: PromptRegistry, tracker: PerformanceTracker, 
                 optimizer: PromptOptimizer):
        """Initialize the tool optimizer.
        
        Args:
            registry: Prompt registry for managing variants
            tracker: Performance tracker for metrics
            optimizer: Main prompt optimizer

        """
        self.registry = registry
        self.tracker = tracker
        self.optimizer = optimizer
        
        # Tool-specific prompt IDs
        self.tool_prompt_ids = {
            'think': 'tool_think',
            'execute_bash': 'tool_bash',
            'execute_powershell': 'tool_powershell',
            'finish': 'tool_finish',
            'browse_interactive': 'tool_browser',
            'str_replace_editor': 'tool_editor',
            'llm_based_edit': 'tool_llm_editor',
            'ipython_run_cell': 'tool_ipython',
            'condensation_request': 'tool_condensation',
            'task_tracker': 'tool_task_tracker'
        }
    
    def optimize_tool(self, tool: ChatCompletionToolParam, 
                     tool_name: str) -> ChatCompletionToolParam:
        """Optimize a tool's description and parameters.
        
        Args:
            tool: The tool to optimize
            tool_name: Name of the tool
            
        Returns:
            Optimized tool with better description/parameters

        """
        if not self.optimizer:
            return tool
        
        try:
            # Get prompt ID for this tool
            prompt_id = self.tool_prompt_ids.get(tool_name)
            if not prompt_id:
                return tool
            
            # Get optimized variant
            variant = self.optimizer.select_variant(prompt_id, PromptCategory.TOOL_PROMPT)
            if not variant:
                return tool
            
            # Create optimized tool
            return self._create_optimized_tool(tool, variant)
            
        except Exception as e:
            print(f"Tool optimization failed for {tool_name}: {e}")
            return tool
    
    def _create_optimized_tool(
        self,
        original_tool: ChatCompletionToolParam,
        variant: PromptVariant,
    ) -> ChatCompletionToolParam:
        """Create an optimized tool from a variant."""
        # Parse the variant content to extract optimized parts
        optimized_parts = self._parse_tool_variant(variant.content)

        def _extract_description(value: Any) -> Any:
            if isinstance(value, dict):
                return value.get('description', value)
            return value

        if isinstance(original_tool, dict):
            new_tool = copy.deepcopy(original_tool)
            function_block = new_tool.setdefault('function', {})

            if 'description' in optimized_parts:
                function_block['description'] = optimized_parts['description']

            if 'parameters' in optimized_parts:
                original_params = function_block.setdefault('parameters', {})
                properties = original_params.setdefault('properties', {})
                for param_name, param_desc in optimized_parts['parameters'].get('properties', {}).items():
                    if param_name in properties:
                        properties[param_name]['description'] = _extract_description(param_desc)
            return new_tool

        # Fallback to attribute-style objects (e.g. ChatCompletionToolParamFunctionChunk)
        new_function = copy.deepcopy(original_tool.function)

        if 'description' in optimized_parts:
            new_function.description = optimized_parts['description']

        if 'parameters' in optimized_parts and 'properties' in optimized_parts['parameters']:
            target_properties = new_function.parameters.get('properties', {})
            for param_name, param_desc in optimized_parts['parameters']['properties'].items():
                if param_name in target_properties:
                    target_properties[param_name]['description'] = _extract_description(param_desc)

        return ChatCompletionToolParam(type=original_tool.type, function=new_function)
    
    def _parse_tool_variant(self, content: str) -> Dict[str, Any]:
        """Parse tool variant content to extract optimized parts."""
        # This is a simplified parser - in practice, you'd want more robust parsing
        parts = {}
        
        # Look for description section
        if "DESCRIPTION:" in content:
            desc_start = content.find("DESCRIPTION:") + len("DESCRIPTION:")
            desc_end = content.find("PARAMETERS:", desc_start)
            if desc_end == -1:
                desc_end = len(content)
            parts['description'] = content[desc_start:desc_end].strip()
        
        # Look for parameters section
        if "PARAMETERS:" in content:
            params_start = content.find("PARAMETERS:") + len("PARAMETERS:")
            params_content = content[params_start:].strip()
            
            # Simple parameter parsing (would need more sophisticated parsing in practice)
            params = {}
            lines = params_content.split('\n')
            current_param = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    # New parameter
                    param_name = line[2:].split(':')[0].strip()
                    current_param = param_name
                    params[param_name] = {}
                elif current_param and ':' in line:
                    # Parameter description
                    key, value = line.split(':', 1)
                    params[current_param][key.strip()] = value.strip()
            
            if params:
                parts['parameters'] = {'properties': params}
        
        return parts
    
    def track_tool_execution(self, tool_name: str, success: bool, 
                           execution_time: float, token_cost: float = 0.0,
                           error_message: Optional[str] = None,
                           metadata: Optional[Dict] = None):
        """Track tool execution for optimization."""
        if not self.optimizer:
            return
        
        prompt_id = self.tool_prompt_ids.get(tool_name)
        if not prompt_id:
            return
        
        try:
            self.optimizer.record_execution(
                variant_id=getattr(self, f'_current_{tool_name}_variant_id', None),
                prompt_id=prompt_id,
                category=PromptCategory.TOOL_PROMPT,
                success=success,
                execution_time=execution_time,
                token_cost=token_cost,
                error_message=error_message,
                metadata=metadata or {}
            )
        except Exception as e:
            print(f"Failed to track tool execution for {tool_name}: {e}")
    
    def create_tool_variants(self, tool_name: str, original_description: str,
                           original_parameters: Dict[str, Any]) -> List[str]:
        """Create optimized variants for a tool."""
        if not self.optimizer:
            return []
        
        prompt_id = self.tool_prompt_ids.get(tool_name)
        if not prompt_id:
            return []
        
        # Create initial variant from original tool
        initial_variant_id = self.optimizer.add_variant(
            prompt_id=prompt_id,
            content=f"DESCRIPTION: {original_description}\n\nPARAMETERS: {original_parameters}",
            category=PromptCategory.TOOL_PROMPT,
            metadata={
                'tool_name': tool_name,
                'original': True
            }
        )
        
        # Store the initial variant ID for tracking
        setattr(self, f'_current_{tool_name}_variant_id', initial_variant_id)
        
        return [initial_variant_id]
    
    def get_tool_optimization_status(self, tool_name: str) -> Dict[str, Any]:
        """Get optimization status for a specific tool."""
        prompt_id = self.tool_prompt_ids.get(tool_name)
        if not prompt_id or not self.optimizer:
            return {'status': 'not_optimized'}
        
        return self.optimizer.get_optimization_status(prompt_id)
    
    def get_all_tool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get optimization status for all tools."""
        if not self.optimizer:
            return {}
        
        status = {}
        for tool_name, prompt_id in self.tool_prompt_ids.items():
            status[tool_name] = self.optimizer.get_optimization_status(prompt_id)
        
        return status
    
    def force_optimize_tool(self, tool_name: str, description: str, 
                          parameters: Dict[str, Any]) -> str:
        """Force create an optimized variant for a tool."""
        if not self.optimizer:
            return None
        
        prompt_id = self.tool_prompt_ids.get(tool_name)
        if not prompt_id:
            return None
        
        variant_id = self.optimizer.add_variant(
            prompt_id=prompt_id,
            content=f"DESCRIPTION: {description}\n\nPARAMETERS: {parameters}",
            category=PromptCategory.TOOL_PROMPT,
            metadata={
                'tool_name': tool_name,
                'manual': True
            }
        )
        
        # Set as active variant
        self.optimizer.force_switch_variant(prompt_id, variant_id)
        
        return variant_id
    
    def evolve_tool(self, tool_name: str) -> List[str]:
        """Evolve a tool's prompts using LLM."""
        if not self.optimizer:
            return []
        
        prompt_id = self.tool_prompt_ids.get(tool_name)
        if not prompt_id:
            return []
        
        # Check if tool needs evolution
        if not self.optimizer.should_evolve_prompt(prompt_id):
            return []
        
        # Get evolution candidates
        candidates = self.optimizer.get_candidates_for_evolution(prompt_id)
        if not candidates:
            return []
        
        # Use the evolver to create new variants
        from .evolver import PromptEvolver
        evolver = PromptEvolver(
            llm=self.optimizer.llm if hasattr(self.optimizer, 'llm') else None,
            registry=self.registry,
            tracker=self.tracker,
            optimizer=self.optimizer
        )
        
        return evolver.evolve_prompt(prompt_id, max_variants=3)
    
    def get_tool_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all tools."""
        if not self.optimizer:
            return {}
        
        summary = {}
        for tool_name, prompt_id in self.tool_prompt_ids.items():
            prompt_metrics = self.tracker.get_prompt_metrics(prompt_id)
            if not prompt_metrics:
                continue

            if isinstance(prompt_metrics, dict):
                items = list(prompt_metrics.items())
            else:
                items = list(prompt_metrics)

            if not items:
                continue

            best_variant_id, best_metrics = max(
                items,
                key=lambda item: getattr(item[1], 'composite_score', 0.0),
            )

            summary[tool_name] = {
                'prompt_id': prompt_id,
                'variants': len(items),
                'best_variant': best_variant_id,
                'best_score': getattr(best_metrics, 'composite_score', 0.0),
            }
        
        return summary
