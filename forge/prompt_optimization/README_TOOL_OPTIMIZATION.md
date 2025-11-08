# Tool-Specific Prompt Optimization

This document describes the tool-specific prompt optimization system that extends the main prompt optimization framework to individual tools used by the CodeAct agent.

## Overview

Tool-specific prompt optimization allows each tool (think, bash, finish, etc.) to have its own optimized descriptions and parameters that improve over time based on usage patterns and performance metrics.

## Features

### 1. **Individual Tool Optimization**
- Each tool can have multiple optimized variants
- A/B testing for tool descriptions and parameters
- Performance tracking per tool
- Automatic variant selection based on success rates

### 2. **Enhanced Tool Descriptions**
- More detailed and helpful descriptions
- Better parameter specifications
- Context-aware guidance
- Best practices and usage examples

### 3. **Performance-Based Evolution**
- Tools evolve based on actual usage patterns
- LLM-powered description improvements
- Automatic promotion of better variants
- Fallback to original descriptions when needed

## Supported Tools

The following tools are supported for optimization:

- **think**: Analytical thinking and problem-solving
- **execute_bash**: Bash command execution
- **execute_powershell**: PowerShell command execution (Windows)
- **finish**: Task completion and summary
- **browse_interactive**: Web browser interaction
- **str_replace_editor**: File editing with string replacement
- **llm_based_edit**: LLM-based file editing
- **ipython_run_cell**: Python code execution
- **condensation_request**: Conversation condensation
- **task_tracker**: Task planning and tracking

## Configuration

### Agent Configuration

Enable tool optimization in your agent configuration:

```toml
[agent]
# Enable tool optimization
enable_prompt_optimization = true

# Tool-specific settings
prompt_opt_storage_path = "~/.Forge/prompt_optimization/tools/"
prompt_opt_ab_split = 0.8  # 80% best, 20% experiments
prompt_opt_min_samples = 3  # Lower threshold for tools
prompt_opt_confidence_threshold = 0.9

# Weights for tool optimization (focus on success and speed)
prompt_opt_success_weight = 0.5  # Higher weight on success
prompt_opt_time_weight = 0.3     # Higher weight on speed
prompt_opt_error_weight = 0.1    # Lower weight on errors
prompt_opt_cost_weight = 0.1     # Lower weight on cost

# Evolution settings
prompt_opt_enable_evolution = true
prompt_opt_evolution_threshold = 0.6  # Lower threshold for tools
prompt_opt_max_variants_per_prompt = 5  # Fewer variants for tools

# Storage settings
prompt_opt_sync_interval = 50  # More frequent sync for tools
prompt_opt_auto_save = true
```

## Usage

### Basic Usage

Tool optimization is automatically enabled when you create a CodeAct agent with the appropriate configuration:

```python
from forge.core.config import AgentConfig
from forge.llm.llm_registry import LLMRegistry
from forge.agenthub.codeact_agent.codeact_agent import CodeActAgent

# Create configuration with tool optimization
config = AgentConfig(
    enable_prompt_optimization=True,
    prompt_opt_storage_path="~/.Forge/prompt_optimization/tools/"
)

# Create agent
llm_registry = LLMRegistry()
agent = CodeActAgent(config, llm_registry)

# Tool optimization is now active
if agent.tool_optimizer:
    print("Tool optimization enabled")
```

### Advanced Usage

#### Manual Tool Optimization

```python
# Force optimize a specific tool
variant_id = agent.tool_optimizer.force_optimize_tool(
    tool_name='think',
    description="Enhanced thinking tool with improved reasoning",
    parameters={
        'thought': {
            'description': 'Your detailed analytical thought process',
            'type': 'string'
        }
    }
)

# Evolve underperforming tools
new_variants = agent.tool_optimizer.evolve_tool('think')
```

#### Monitoring Tool Performance

```python
# Get optimization status for all tools
tool_status = agent.tool_optimizer.get_all_tool_status()
print("Tool Status:", tool_status)

# Get performance summary
performance = agent.tool_optimizer.get_tool_performance_summary()
print("Performance:", performance)

# Get status for specific tool
think_status = agent.tool_optimizer.get_tool_optimization_status('think')
print("Think Tool Status:", think_status)
```

#### Tracking Tool Execution

```python
# Track tool execution (usually done automatically)
agent._track_tool_execution(
    tool_name='think',
    success=True,
    execution_time=1.5,
    token_cost=0.1,
    metadata={'task': 'debugging'}
)
```

## Architecture

### Components

1. **ToolOptimizer**: Main orchestrator for tool optimization
2. **Tool Descriptions**: Pre-optimized descriptions and parameters
3. **Tool Variants**: Individual optimized versions of tools
4. **Performance Tracking**: Metrics collection per tool
5. **Evolution Engine**: LLM-powered tool improvement

### Data Flow

```
Tool Usage → Performance Tracking → Variant Selection → Tool Optimization → Enhanced Tools
     ↑                                                                           ↓
     └─────────────────── A/B Testing ←─── Evolution Engine ←─── Performance Analysis
```

### Storage Structure

```
~/.Forge/prompt_optimization/tools/
├── variants.json          # Tool variants
├── metrics.json           # Performance metrics
├── active_variants.json   # Active variant mappings
└── categories.json        # Tool categories
```

## Optimization Process

### 1. **Initialization**
- Load existing tool variants from storage
- Create default variants if none exist
- Set up performance tracking

### 2. **Tool Selection**
- A/B testing selects variant (80% best, 20% experiment)
- Tool description and parameters are optimized
- Variant ID is stored for tracking

### 3. **Performance Tracking**
- Track success/failure of tool usage
- Measure execution time and token cost
- Record error messages and metadata

### 4. **Analysis and Evolution**
- Analyze performance patterns
- Identify underperforming tools
- Generate new variants using LLM
- Promote better variants automatically

### 5. **Persistence**
- Save variants and metrics to storage
- Sync across multiple agent instances
- Maintain optimization history

## Customization

### Adding New Tools

To add optimization for a new tool:

1. **Add tool mapping** in `ToolOptimizer.tool_prompt_ids`:
```python
self.tool_prompt_ids = {
    # ... existing tools ...
    'new_tool': 'tool_new_tool'
}
```

2. **Create optimized description** in `tool_descriptions.py`:
```python
OPTIMIZED_TOOL_DESCRIPTIONS = {
    # ... existing tools ...
    'new_tool': {
        'description': 'Optimized description for new tool',
        'parameters': {
            'param1': {
                'description': 'Parameter description',
                'type': 'string'
            }
        }
    }
}
```

3. **Add action mapping** in `_track_tool_usage`:
```python
tool_name_mapping = {
    # ... existing mappings ...
    'new_action': 'new_tool'
}
```

### Custom Optimization Strategies

You can customize the optimization process by:

1. **Adjusting weights** in configuration
2. **Modifying evolution prompts** in `PromptEvolver`
3. **Adding custom metrics** in `PerformanceTracker`
4. **Implementing custom variants** in `ToolOptimizer`

## Monitoring and Debugging

### Logs

Tool optimization logs are available at the DEBUG level:

```python
import logging
logging.getLogger('Forge.prompt_optimization').setLevel(logging.DEBUG)
```

### Metrics

Key metrics to monitor:

- **Success Rate**: Percentage of successful tool executions
- **Execution Time**: Average time per tool execution
- **Error Rate**: Percentage of failed executions
- **Token Cost**: Average cost per tool execution
- **Variant Performance**: Performance comparison between variants

### Common Issues

1. **Tool optimization not working**: Check if `enable_prompt_optimization` is True
2. **No variants created**: Ensure tool descriptions exist in `tool_descriptions.py`
3. **Poor performance**: Adjust weights in configuration
4. **Storage issues**: Check permissions on storage directory

## Examples

See `examples/tool_optimization_example.py` for comprehensive usage examples.

## Best Practices

1. **Start with good defaults**: Use the provided optimized descriptions as starting points
2. **Monitor performance**: Regularly check tool performance and adjust weights
3. **Test thoroughly**: Validate tool changes before deploying
4. **Backup data**: Keep backups of optimization data
5. **Gradual rollout**: Use A/B testing to gradually introduce changes

## Troubleshooting

### Tool optimization not enabled
- Check `enable_prompt_optimization` in configuration
- Verify `ToolOptimizer` is initialized in agent

### No variants being created
- Check if tool descriptions exist in `tool_descriptions.py`
- Verify tool name mapping in `tool_prompt_ids`

### Poor optimization results
- Adjust success/time/error/cost weights
- Lower evolution threshold for more aggressive optimization
- Check if enough samples are being collected

### Storage issues
- Verify storage directory permissions
- Check disk space availability
- Ensure proper JSON formatting in storage files
