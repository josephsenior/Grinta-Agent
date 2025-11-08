"""Example of using tool-specific prompt optimization.

This example shows how to enable and configure tool optimization
for individual tools in the CodeAct agent.
"""

import os
from forge.core.config import AgentConfig
from forge.llm.llm_registry import LLMRegistry
from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent


def create_optimized_agent():
    """Create a CodeAct agent with tool optimization enabled."""
    # Create agent configuration with tool optimization enabled
    config = AgentConfig(
        # Enable prompt optimization
        enable_prompt_optimization=True,
        
        # Tool optimization specific settings
        prompt_opt_storage_path="~/.Forge/prompt_optimization/tools/",
        prompt_opt_ab_split=0.8,  # 80% best, 20% experiments
        prompt_opt_min_samples=3,  # Lower threshold for tools
        prompt_opt_confidence_threshold=0.9,
        
        # Weights for tool optimization (focus on success and speed)
        prompt_opt_success_weight=0.5,  # Higher weight on success
        prompt_opt_time_weight=0.3,     # Higher weight on speed
        prompt_opt_error_weight=0.1,    # Lower weight on errors
        prompt_opt_cost_weight=0.1,     # Lower weight on cost
        
        # Evolution settings
        prompt_opt_enable_evolution=True,
        prompt_opt_evolution_threshold=0.6,  # Lower threshold for tools
        prompt_opt_max_variants_per_prompt=5,  # Fewer variants for tools
        
        # Storage settings
        prompt_opt_sync_interval=50,  # More frequent sync for tools
        prompt_opt_auto_save=True
    )
    
    # Create LLM registry (you would configure this with your LLM)
    llm_registry = LLMRegistry()
    
    # Create the agent
    agent = CodeActAgent(config, llm_registry)
    
    return agent


def demonstrate_tool_optimization():
    """Demonstrate tool optimization features."""
    agent = create_optimized_agent()
    
    if not agent.tool_optimizer:
        print("Tool optimization not enabled")
        return
    
    # Get current tool optimization status
    tool_status = agent.tool_optimizer.get_all_tool_status()
    print("Tool Optimization Status:")
    for tool_name, status in tool_status.items():
        print(f"  {tool_name}: {status.get('total_variants', 0)} variants")
    
    # Get performance summary
    performance = agent.tool_optimizer.get_tool_performance_summary()
    print("\nTool Performance Summary:")
    for tool_name, perf in performance.items():
        print(f"  {tool_name}: {perf.get('variants', 0)} variants, best score: {perf.get('best_score', 0):.3f}")
    
    # Force optimize a specific tool
    print("\nForce optimizing 'think' tool...")
    variant_id = agent.tool_optimizer.force_optimize_tool(
        tool_name='think',
        description="Enhanced thinking tool with improved reasoning capabilities",
        parameters={
            'thought': {
                'description': 'Your detailed analytical thought process with step-by-step reasoning',
                'type': 'string'
            }
        }
    )
    print(f"Created variant: {variant_id}")
    
    # Evolve underperforming tools
    print("\nEvolving underperforming tools...")
    evolution_results = {}
    for tool_name in agent.tool_optimizer.tool_prompt_ids.keys():
        new_variants = agent.tool_optimizer.evolve_tool(tool_name)
        if new_variants:
            evolution_results[tool_name] = new_variants
            print(f"  {tool_name}: Created {len(new_variants)} new variants")
    
    if not evolution_results:
        print("  No tools needed evolution")
    
    return agent


def monitor_tool_performance():
    """Monitor tool performance over time."""
    agent = create_optimized_agent()
    
    if not agent.tool_optimizer:
        print("Tool optimization not enabled")
        return
    
    # Simulate some tool usage and tracking
    print("Simulating tool usage...")
    
    # Track some successful tool executions
    agent._track_tool_execution('think', True, 1.5, 0.1)
    agent._track_tool_execution('execute_bash', True, 2.3, 0.2)
    agent._track_tool_execution('think', True, 1.2, 0.1)
    agent._track_tool_execution('execute_bash', False, 0.5, 0.05, "Command not found")
    
    # Get updated performance
    performance = agent.tool_optimizer.get_tool_performance_summary()
    print("\nUpdated Performance:")
    for tool_name, perf in performance.items():
        print(f"  {tool_name}: {perf.get('variants', 0)} variants, best score: {perf.get('best_score', 0):.3f}")


if __name__ == "__main__":
    print("Tool-Specific Prompt Optimization Example")
    print("=" * 50)
    
    # Demonstrate tool optimization
    agent = demonstrate_tool_optimization()
    
    print("\n" + "=" * 50)
    
    # Monitor performance
    monitor_tool_performance()
    
    print("\nTool optimization example completed!")
