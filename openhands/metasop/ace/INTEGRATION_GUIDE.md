# ACE Framework Integration Guide

This guide explains how to integrate the ACE Framework into your OpenHands application and customize it for your specific needs.

## Quick Start

### 1. Enable ACE in Configuration

Add to your `config.toml`:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 1000
ace_playbook_persistence_path = "~/.openhands/ace_playbooks/"
```

### 2. Initialize ACE in Your Code

```python
from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig

# Create configuration
config = ACEConfig(enable_ace=True)

# Create context playbook
playbook = ContextPlaybook(max_bullets=1000)

# Initialize ACE framework
ace = ACEFramework(
    llm=your_llm_instance,
    context_playbook=playbook,
    config=config
)
```

### 3. Process Tasks

```python
# Process a single task
result = ace.process_task(
    query="Implement user authentication",
    task_type="metasop",
    role="engineer",
    expected_outcome="Secure authentication system"
)

# Run multi-epoch training
results = ace.multi_epoch_training(
    queries=["task1", "task2", "task3"],
    task_type="metasop",
    roles=["engineer", "engineer", "engineer"],
    ground_truths=["outcome1", "outcome2", "outcome3"]
)
```

## Integration Points

### MetaSOP Orchestrator Integration

ACE automatically integrates with MetaSOP when enabled:

1. **Automatic Initialization**: ACE is initialized when MetaSOP starts
2. **Context Injection**: Playbook context is injected into role prompts
3. **Real-time Reflection**: Performance is analyzed after each step
4. **Automatic Updates**: Playbook is updated based on execution results

**Configuration:**
```toml
[metasop]
enable_ace = true
ace_max_bullets = 1000
ace_enable_online_adaptation = true
ace_playbook_persistence_path = "~/.openhands/ace_playbooks/metasop/"
```

### CodeAct Agent Integration

ACE integrates with CodeAct agent for self-improving code generation:

1. **Playbook Context**: Relevant strategies are injected into system prompts
2. **Task-Specific Learning**: Agent learns from code generation tasks
3. **Execution Tracking**: Code execution results are used for reflection
4. **Strategy Accumulation**: Successful patterns are added to playbook

**Configuration:**
```toml
[agent]
enable_ace = true
ace_max_bullets = 1000
ace_playbook_path = "~/.openhands/ace_playbooks/codeact/"
```

## Customization

### Custom Task Types

Define custom task types for your specific use cases:

```python
from openhands.metasop.ace.context_playbook import BulletSection

# Add custom section
class CustomBulletSection(BulletSection):
    CUSTOM_DOMAIN = "custom_domain"

# Use in playbook
playbook.add_bullet(
    content="Custom strategy for your domain",
    section=CustomBulletSection.CUSTOM_DOMAIN,
    tags=["custom", "domain-specific"]
)
```

### Custom Reflection Prompts

Override reflection prompts for specific domains:

```python
from openhands.metasop.ace.reflector import ACEReflector

class CustomReflector(ACEReflector):
    def _load_reflection_prompt(self) -> str:
        return """
        Custom reflection prompt for your domain...
        """
```

### Custom Curation Logic

Implement domain-specific curation:

```python
from openhands.metasop.ace.curator import ACECurator

class CustomCurator(ACECurator):
    def curate(self, insights, current_playbook, task_context, max_retries=3):
        # Custom curation logic
        result = super().curate(insights, current_playbook, task_context, max_retries)
        
        # Add custom processing
        result.delta_updates.extend(self._custom_updates(insights))
        
        return result
```

## Performance Tuning

### Memory Optimization

For memory-constrained environments:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 200                    # Smaller playbook
ace_max_playbook_content_length = 20     # Less context
ace_cleanup_interval_days = 7            # More frequent cleanup
ace_redundancy_threshold = 0.7           # More aggressive cleanup
```

### Speed Optimization

For high-performance scenarios:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 2000                   # Larger playbook
ace_max_playbook_content_length = 100    # More context
ace_num_epochs = 3                       # Fewer epochs
ace_reflector_max_iterations = 3         # Fewer iterations
ace_min_helpfulness_threshold = 0.3      # Higher threshold
```

### Quality Optimization

For maximum learning quality:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 5000                   # Large playbook
ace_num_epochs = 10                      # More epochs
ace_reflector_max_iterations = 10        # More iterations
ace_min_helpfulness_threshold = 0.1      # Lower threshold
ace_redundancy_threshold = 0.9           # Strict redundancy
```

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger("openhands.metasop.ace").setLevel(logging.DEBUG)
```

### Performance Monitoring

```python
# Get performance metrics
metrics = ace.get_performance_summary()

print(f"Success rate: {metrics['framework_metrics']['success_rate']:.2f}")
print(f"Total tasks: {metrics['framework_metrics']['total_tasks']}")
print(f"Context updates: {metrics['framework_metrics']['context_updates']}")

# Get playbook statistics
playbook_stats = metrics['playbook_statistics']
print(f"Playbook size: {playbook_stats['total_bullets']} bullets")
print(f"Average helpfulness: {playbook_stats['avg_helpfulness']:.2f}")
```

### Playbook Inspection

```python
# Get playbook content
content = ace.context_playbook.get_playbook_content(max_bullets=20)
print("Current playbook content:")
print(content)

# Get specific strategies
strategies = ace.context_playbook.get_relevant_bullets("authentication", limit=5)
for strategy in strategies:
    print(f"- {strategy.content}")

# Export playbook for analysis
ace.save_playbook("playbook_export.json")
```

## Best Practices

### 1. Start Small and Scale

Begin with a small playbook and let it grow organically:

```toml
[metasop]
enable_ace = true
ace_max_bullets = 100                    # Start small
ace_max_playbook_content_length = 10     # Minimal context
```

### 2. Monitor Performance

Regularly check performance metrics and adjust settings:

```python
# Check performance weekly
metrics = ace.get_performance_summary()
if metrics['framework_metrics']['success_rate'] < 0.7:
    # Adjust settings or investigate issues
    pass
```

### 3. Use Appropriate Task Types

Choose the right task type for your use case:

- `metasop`: For MetaSOP orchestration tasks
- `code_generation`: For code generation tasks
- `general`: For general reasoning tasks

### 4. Provide Good Context

Include role and expected outcome for MetaSOP tasks:

```python
result = ace.process_task(
    query="Implement user authentication",
    task_type="metasop",
    role="engineer",                      # Specify role
    expected_outcome="Secure auth system"  # Expected outcome
)
```

### 5. Persist Playbooks

Save playbooks regularly to preserve learned knowledge:

```toml
[metasop]
ace_auto_save_playbook = true
ace_playbook_save_interval = 10          # Save every 10 updates
```

### 6. Clean Up Regularly

Enable grow-and-refine to maintain playbook quality:

```toml
[metasop]
ace_enable_grow_and_refine = true
ace_cleanup_interval_days = 30           # Cleanup every 30 days
ace_redundancy_threshold = 0.8           # Remove redundant strategies
```

## Troubleshooting

### Common Issues

1. **Playbook Not Growing**
   - Check if `ace_enable_online_adaptation` is enabled
   - Verify that tasks are being processed successfully
   - Check if reflection is working properly

2. **Poor Performance**
   - Try adjusting `ace_min_helpfulness_threshold`
   - Increase `ace_num_epochs` for more training
   - Check if playbook content is relevant

3. **Memory Issues**
   - Reduce `ace_max_bullets`
   - Decrease `ace_max_playbook_content_length`
   - Enable more frequent cleanup

4. **Slow Processing**
   - Reduce `ace_reflector_max_iterations`
   - Disable `ace_multi_epoch` for faster processing
   - Increase `ace_min_helpfulness_threshold`

### Debug Mode

Enable debug logging to see ACE framework activity:

```python
import logging
logging.getLogger("openhands.metasop.ace").setLevel(logging.DEBUG)
```

### Performance Profiling

Profile ACE framework performance:

```python
import time

start_time = time.time()
result = ace.process_task(query, task_type, role)
processing_time = time.time() - start_time

print(f"Processing time: {processing_time:.2f}s")
print(f"Success: {result.success}")
```

## Advanced Usage

### Custom LLM Integration

Use different LLMs for different components:

```python
from openhands.metasop.ace import ACEFramework

# Use different LLMs for different components
ace = ACEFramework(
    llm=generator_llm,                    # For generation
    context_playbook=playbook,
    config=config
)

# Override LLMs for specific components
ace.reflector.llm = reflector_llm        # For reflection
ace.curator.llm = curator_llm            # For curation
```

### Batch Processing

Process multiple tasks in batches:

```python
# Process batch of tasks
queries = ["task1", "task2", "task3"]
results = []

for query in queries:
    result = ace.process_task(query, "metasop", "engineer")
    results.append(result)

# Or use multi-epoch training
results = ace.multi_epoch_training(
    queries=queries,
    task_type="metasop",
    roles=["engineer"] * len(queries)
)
```

### Custom Metrics

Track custom metrics:

```python
class CustomACEFramework(ACEFramework):
    def process_task(self, query, task_type="general", **kwargs):
        result = super().process_task(query, task_type, **kwargs)
        
        # Track custom metrics
        self.custom_metrics = getattr(self, 'custom_metrics', {})
        self.custom_metrics['custom_metric'] = self.custom_metrics.get('custom_metric', 0) + 1
        
        return result
```

## Support

For questions and support:

1. Check the [ACE Framework Documentation](README.md)
2. Review the [examples](examples/) directory
3. Check the [unit tests](tests/) for usage patterns
4. Open an issue on the OpenHands repository

## Contributing

To contribute to the ACE framework:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure backward compatibility
5. Test with both MetaSOP and CodeAct integrations
