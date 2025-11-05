# ACE (Agentic Context Engineering) Framework

A self-improving AI system that learns from its own performance through evolving context playbooks that prevent context collapse and accumulate domain-specific knowledge.

## Overview

The ACE Framework implements the research from "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" and integrates seamlessly with OpenHands' MetaSOP and CodeAct systems.

### Key Features

- **Self-Improving Agents**: Agents learn from their own performance and improve over time
- **Context Playbooks**: Structured knowledge management that prevents context collapse
- **Three-Agent Architecture**: Generator, Reflector, and Curator work together for optimal learning
- **Incremental Updates**: Delta-based context updates for efficient adaptation
- **Grow-and-Refine**: Automatic playbook maintenance and redundancy removal
- **Multi-Epoch Training**: Progressive refinement through multiple training cycles
- **Online Adaptation**: Real-time learning during task execution

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Generator    │───▶│    Reflector    │───▶│     Curator     │
│                 │    │                 │    │                 │
│ Generates       │    │ Analyzes        │    │ Synthesizes     │
│ trajectories    │    │ performance     │    │ insights into   │
│ using playbook  │    │ and extracts    │    │ context updates │
│                 │    │ insights        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │    Context Playbook     │
                    │                         │
                    │ • Strategies & Rules    │
                    │ • APIs & Tools          │
                    │ • Verification Lists    │
                    │ • Common Mistakes       │
                    │ • Domain Insights       │
                    │ • Debugging Tips        │
                    └─────────────────────────┘
```

## Components

### 1. ContextPlaybook
Structured knowledge management system that organizes insights into categorized sections:

- **Strategies & Hard Rules**: Core strategies and principles
- **APIs to Use**: Specific API usage patterns and examples
- **Verification Checklist**: Step-by-step verification procedures
- **Common Mistakes**: Known pitfalls and how to avoid them
- **Domain Insights**: Specialized knowledge for specific domains
- **Tools & Utilities**: Available tools and their usage patterns
- **Code Patterns**: Reusable code patterns and templates
- **Debugging Tips**: Troubleshooting and debugging strategies

### 2. ACEGenerator
Produces reasoning trajectories using the context playbook:

- Retrieves relevant strategies from the playbook
- Formats playbook content for LLM consumption
- Generates step-by-step reasoning trajectories
- Tracks which strategies were used
- Supports feedback-aware generation for iterative improvement

### 3. ACEReflector
Analyzes execution performance and extracts insights:

- Performs error identification and root cause analysis
- Extracts key insights and lessons learned
- Tags playbook bullets as helpful/harmful/neutral
- Supports iterative refinement for deep reasoning
- Generates structured insights in JSON format

### 4. ACECurator
Synthesizes insights into context updates:

- Reviews insights from the Reflector
- Generates delta context items (incremental updates)
- Prevents redundancy through similarity checking
- Maintains grow-and-refine balance
- Supports batched curation for efficiency

### 5. ACEFramework
Main orchestrator that coordinates all components:

- Implements the complete self-improvement loop
- Supports both online and offline adaptation
- Provides multi-epoch training capabilities
- Tracks performance metrics and statistics
- Handles playbook persistence and loading

## Configuration

### MetaSOP Settings

Add to your `config.toml`:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 1000
ace_multi_epoch = true
ace_num_epochs = 5
ace_reflector_max_iterations = 5
ace_playbook_persistence_path = "~/.openhands/ace_playbooks/"
ace_enable_online_adaptation = true
ace_min_helpfulness_threshold = 0.0
ace_max_playbook_content_length = 50
ace_enable_grow_and_refine = true
ace_cleanup_interval_days = 30
ace_redundancy_threshold = 0.8
ace_auto_save_playbook = true
ace_playbook_save_interval = 10
```

### CodeAct Agent Settings

Add to your agent configuration:

```toml
[agent]
enable_ace = true
ace_max_bullets = 1000
ace_multi_epoch = true
ace_num_epochs = 5
ace_reflector_max_iterations = 5
ace_playbook_path = "~/.openhands/ace_playbooks/codeact/"
ace_enable_online_adaptation = true
ace_min_helpfulness_threshold = 0.0
ace_max_playbook_content_length = 50
ace_enable_grow_and_refine = true
ace_cleanup_interval_days = 30
ace_redundancy_threshold = 0.8
```

## Usage Examples

### Basic Usage

```python
from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
from openhands.llm.llm import LLM

# Create configuration
config = ACEConfig(
    enable_ace=True,
    max_bullets=1000,
    multi_epoch=True,
    num_epochs=5
)

# Create context playbook
playbook = ContextPlaybook(max_bullets=1000)

# Initialize ACE framework
ace = ACEFramework(
    llm=your_llm_instance,
    context_playbook=playbook,
    config=config
)

# Process a task
result = ace.process_task(
    query="Implement user authentication system",
    task_type="metasop",
    role="engineer",
    expected_outcome="Secure authentication system implemented"
)

print(f"Success: {result.success}")
print(f"Processing time: {result.processing_time:.2f}s")
```

### Multi-Epoch Training

```python
# Prepare training data
queries = [
    "Implement user authentication",
    "Add password validation", 
    "Implement session management",
    "Add two-factor authentication"
]

roles = ["engineer"] * len(queries)
expected_outcomes = [
    "Secure authentication system",
    "Password validation rules",
    "Session management system", 
    "2FA implementation"
]

# Run multi-epoch training
results = ace.multi_epoch_training(
    queries=queries,
    task_type="metasop",
    roles=roles,
    ground_truths=expected_outcomes
)

print(f"Processed {len(results)} training examples")
```

### Playbook Management

```python
# Save playbook
ace.save_playbook("my_playbook.json")

# Load playbook
ace.load_playbook("my_playbook.json")

# Get playbook statistics
stats = ace.context_playbook.get_statistics()
print(f"Total bullets: {stats['total_bullets']}")
print(f"Average helpfulness: {stats['avg_helpfulness']:.2f}")

# Get performance summary
performance = ace.get_performance_summary()
print(f"Success rate: {performance['framework_metrics']['success_rate']:.2f}")
```

## Performance Tuning

### Playbook Size Management

- **ace_max_bullets**: Maximum number of bullets in playbook (default: 1000)
- **ace_max_playbook_content_length**: Max bullets in LLM context (default: 50)
- **ace_enable_grow_and_refine**: Enable automatic cleanup (default: true)
- **ace_cleanup_interval_days**: Days between cleanup cycles (default: 30)

### Learning Parameters

- **ace_num_epochs**: Number of training epochs (default: 5)
- **ace_reflector_max_iterations**: Max reflection iterations (default: 5)
- **ace_min_helpfulness_threshold**: Min helpfulness for retrieval (default: 0.0)
- **ace_redundancy_threshold**: Similarity threshold for redundancy (default: 0.8)

### Performance Monitoring

```python
# Get detailed performance metrics
metrics = ace.get_performance_summary()

print("Framework Metrics:")
print(f"  Total tasks: {metrics['framework_metrics']['total_tasks']}")
print(f"  Success rate: {metrics['framework_metrics']['success_rate']:.2f}")
print(f"  Context updates: {metrics['framework_metrics']['context_updates']}")

print("Generator Metrics:")
print(f"  Success rate: {metrics['generator_metrics']['success_rate']:.2f}")
print(f"  Avg processing time: {metrics['generator_metrics']['avg_processing_time']:.2f}s")

print("Playbook Statistics:")
print(f"  Total bullets: {metrics['playbook_statistics']['total_bullets']}")
print(f"  Avg helpfulness: {metrics['playbook_statistics']['avg_helpfulness']:.2f}")
```

## Integration Points

### MetaSOP Integration

ACE integrates with MetaSOP orchestrator to provide self-improving step execution:

- Automatic playbook context injection into role prompts
- Real-time reflection after each step execution
- Automatic playbook updates based on execution results
- Configurable online adaptation settings

### CodeAct Integration

ACE integrates with CodeAct agent to provide self-improving code generation:

- Playbook context injection into system prompts
- Task-specific strategy retrieval
- Execution tracking for reflection
- Automatic playbook updates after code execution

## Best Practices

1. **Start Small**: Begin with a small playbook and let it grow organically
2. **Monitor Performance**: Regularly check performance metrics and adjust settings
3. **Clean Up Regularly**: Enable grow-and-refine to maintain playbook quality
4. **Use Appropriate Task Types**: Choose the right task type (metasop, code_generation, general)
5. **Provide Good Context**: Include role and expected outcome for MetaSOP tasks
6. **Persist Playbooks**: Save playbooks regularly to preserve learned knowledge
7. **Monitor Redundancy**: Watch for redundant strategies and adjust threshold if needed

## Troubleshooting

### Common Issues

1. **Playbook Not Growing**: Check if `ace_enable_online_adaptation` is enabled
2. **Poor Performance**: Try adjusting `ace_min_helpfulness_threshold` or `ace_redundancy_threshold`
3. **Memory Issues**: Reduce `ace_max_bullets` or `ace_max_playbook_content_length`
4. **Slow Processing**: Reduce `ace_reflector_max_iterations` or disable `ace_multi_epoch`

### Debug Mode

Enable debug logging to see ACE framework activity:

```python
import logging
logging.getLogger("openhands.metasop.ace").setLevel(logging.DEBUG)
```

## Research Background

This implementation is based on the research paper "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" by Zhang et al. The framework addresses two key limitations of existing context adaptation methods:

1. **Brevity Bias**: Prioritizing concise instructions over comprehensive knowledge
2. **Context Collapse**: Degradation into shorter, less informative summaries over time

ACE solves these issues through:
- Structured, itemized context bullets
- Incremental delta updates
- Grow-and-refine mechanism
- Three-agent architecture for specialized roles

## Contributing

To contribute to the ACE framework:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure backward compatibility
5. Test with both MetaSOP and CodeAct integrations

## License

This implementation is part of the OpenHands project and follows the same license terms.
