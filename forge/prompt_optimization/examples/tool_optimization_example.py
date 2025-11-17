"""Example of using tool-specific prompt optimization without a running agent.

The example wires the core prompt-optimization primitives together and shows how
`ToolOptimizer` can create/evolve tool variants and record execution metrics.
"""

from __future__ import annotations

from forge.prompt_optimization import (
    PerformanceTracker,
    PromptOptimizer,
    PromptRegistry,
    PromptVariant,
    ToolOptimizer,
)
from forge.prompt_optimization.models import OptimizationConfig, PromptCategory


def create_tool_optimizer() -> ToolOptimizer:
    """Instantiate a ToolOptimizer with custom weights suited for tools."""

    registry = PromptRegistry()
    tracker = PerformanceTracker(
        {
            "success_weight": 0.5,
            "time_weight": 0.3,
            "error_weight": 0.1,
            "cost_weight": 0.1,
        }
    )
    config = OptimizationConfig(
        storage_path="~/.Forge/prompt_optimization/tools/",
        ab_split_ratio=0.8,
        min_samples_for_switch=3,
        confidence_threshold=0.9,
        enable_evolution=True,
        evolution_threshold=0.6,
        max_variants_per_prompt=5,
        sync_interval=50,
        auto_save=True,
    )
    optimizer = PromptOptimizer(registry=registry, tracker=tracker, config=config)
    return ToolOptimizer(registry=registry, tracker=tracker, optimizer=optimizer)


def seed_prompt_variants(registry: PromptRegistry) -> None:
    """Create a couple of prompt variants for the built-in `think` tool."""
    base_prompt_id = "tool_think"
    for version in range(1, 3):
        registry.register_variant(
            PromptVariant(
                prompt_id=base_prompt_id,
                content=f"Think tool base prompt v{version}",
                category=PromptCategory.TOOL_PROMPT,
                version=version,
                is_active=version == 1,
            )
        )


def demonstrate_tool_optimization(tool_optimizer: ToolOptimizer) -> None:
    """Demonstrate creation, forcing, and evolution of tool variants."""
    seed_prompt_variants(tool_optimizer.registry)

    # Create optimized variants using a hand-crafted description
    created_variants = tool_optimizer.create_tool_variants(
        tool_name="think",
        original_description="Original think tool description",
        original_parameters={
            "thought": {
                "description": "Your internal monologue",
                "type": "string",
            }
        },
    )
    print(f"Created {len(created_variants)} optimized variant(s) for 'think'")

    # Force an optimization cycle for the think tool
    variant_id = tool_optimizer.force_optimize_tool(
        tool_name="think",
        description="Enhanced thinking tool with improved reasoning capabilities",
        parameters={
            "thought": {
                "description": "Provide a detailed analytical thought process",
                "type": "string",
            }
        },
    )
    print(f"Force optimized 'think' tool -> new variant id: {variant_id}")

    # Evolve any underperforming tools
    evolution_results: dict[str, list[str]] = {}
    for tool_name in tool_optimizer.tool_prompt_ids:
        variants = tool_optimizer.evolve_tool(tool_name)
        if variants:
            evolution_results[tool_name] = variants

    if evolution_results:
        print("\nEvolution results:")
        for tool_name, variants in evolution_results.items():
            print(f"  {tool_name}: {len(variants)} new variant(s)")
    else:
        print("\nNo tools required evolution.")


def monitor_tool_performance(tool_optimizer: ToolOptimizer) -> None:
    """Record synthetic tool executions and inspect the aggregated metrics."""
    print("\nSimulating tool executions...")
    tool_optimizer.track_tool_execution("think", success=True, execution_time=1.5)
    tool_optimizer.track_tool_execution("execute_bash", success=True, execution_time=2.3)
    tool_optimizer.track_tool_execution("think", success=True, execution_time=1.2)
    tool_optimizer.track_tool_execution(
        "execute_bash",
        success=False,
        execution_time=0.5,
        error_message="Command not found",
    )

    summary = tool_optimizer.get_tool_performance_summary()
    print("\nTool Performance Summary:")
    for tool_name, perf in summary.items():
        print(
            f"  {tool_name}: {perf.get('variants', 0)} variants, "
            f"best score {perf.get('best_score', 0.0):.3f}"
        )


if __name__ == "__main__":
    print("Tool-Specific Prompt Optimization Example")
    print("=" * 50)

    optimizer = create_tool_optimizer()
    demonstrate_tool_optimization(optimizer)
    monitor_tool_performance(optimizer)

    print("\nTool optimization example completed!")
