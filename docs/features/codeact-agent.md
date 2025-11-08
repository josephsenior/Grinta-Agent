# 👨‍💻 **CodeAct Agent**

> **Revolutionary minimalist agent that consolidates LLM actions into a unified code action space, embodying the philosophy of engineering excellence.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🔧 Core Components](#-core-components)
- [⚙️ Configuration](#️-configuration)
- [🚀 Usage](#-usage)
- [📊 Monitoring](#-monitoring)
- [🎯 Advanced Features](#-advanced-features)
- [📚 API Reference](#-api-reference)
- [🎯 Examples](#-examples)
- [🔍 Troubleshooting](#-troubleshooting)

---

## 🌟 **Overview**

CodeAct Agent is a revolutionary minimalist agent that consolidates all LLM actions into a unified code action space. It embodies the philosophy of engineering excellence, focusing on clean, efficient, and maintainable code generation.

### **Key Features**
- **Unified Code Actions**: All actions consolidated into code execution
- **Linus Torvalds Philosophy**: Engineering excellence and clean code
- **Think Tool**: Step-by-step reasoning capabilities
- **Dynamic Prompt Optimization**: Real-time prompt adaptation
- **Tool-Specific Optimization**: Optimized tool descriptions
- **Advanced Memory Management**: Intelligent context handling

### **Revolutionary Capabilities**
- **Code-First Approach**: Everything is code, nothing is abstract
- **Self-Improving**: Learns from execution feedback
- **Context-Aware**: Intelligent context understanding
- **Performance Optimized**: Real-time optimization and adaptation
- **Enterprise-Ready**: Production-grade reliability and monitoring

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    CodeAct Agent                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Think     │  │    Code     │  │   Memory    │        │
│  │    Tool     │  │  Execution  │  │  Management │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Prompt     │  │    Tool     │  │   Context   │        │
│  │Optimization │  │Optimization │  │  Injection  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  LLM Integration │ Function Calling │ Performance Tracking │
└─────────────────────────────────────────────────────────────┘
```

### **Core Principles**

1. **Code-First**: Everything is code, nothing is abstract
2. **Engineering Excellence**: Clean, efficient, maintainable code
3. **Unified Actions**: All actions consolidated into code execution
4. **Self-Improvement**: Continuous learning and adaptation
5. **Performance Focus**: Optimized for speed and efficiency

---

## 🔧 **Core Components**

### **1. Think Tool**
Advanced reasoning capabilities for step-by-step problem solving.

**Features:**
- Step-by-step reasoning
- Problem decomposition
- Solution validation
- Error analysis
- Learning from failures

**Usage:**
```python
# Think tool usage
think_result = await agent.think(
    "How to implement user authentication in a web application?",
    steps=[
        "Analyze requirements",
        "Choose authentication method",
        "Design database schema",
        "Implement security measures",
        "Create user interface"
    ]
)

print(f"Reasoning steps: {len(think_result.steps)}")
print(f"Confidence: {think_result.confidence}")
print(f"Next actions: {think_result.next_actions}")
```

### **2. Code Execution Engine**
Unified code execution with advanced capabilities.

**Features:**
- Multi-language support
- Sandboxed execution
- Error handling and recovery
- Performance monitoring
- Security validation

**Code Execution:**
```python
# Execute code with monitoring
execution_result = await agent.execute_code(
    code="""
    def authenticate_user(username, password):
        # Implementation here
        pass
    """,
    language="python",
    context={"user_data": user_data},
    timeout=30
)

print(f"Execution success: {execution_result.success}")
print(f"Output: {execution_result.output}")
print(f"Errors: {execution_result.errors}")
print(f"Performance: {execution_result.performance}")
```

### **3. Memory Management**
Intelligent memory system with context condensation.

**Features:**
- Conversation memory
- Context condensation
- Memory indexing
- Context evolution
- Performance tracking

**Memory Operations:**
```python
# Store conversation in memory
memory_id = await agent.store_conversation(
    conversation={
        "user": "How to implement authentication?",
        "assistant": "Here's how to implement authentication...",
        "context": {"domain": "web_development"}
    }
)

# Retrieve relevant memory
relevant_memory = await agent.retrieve_memory(
    query="authentication implementation",
    max_results=5
)

# Update memory with feedback
await agent.update_memory(
    memory_id=memory_id,
    feedback="helpful",
    additional_context={"success": True}
)
```

### **4. Prompt Optimization**
Real-time prompt optimization and adaptation.

**Features:**
- Dynamic prompt variants
- A/B testing
- Performance-based adaptation
- Real-time switching
- Cost optimization

**Optimization Setup:**
```python
# Initialize prompt optimization
agent.enable_prompt_optimization(
    ab_split=0.1,
    min_samples=10,
    confidence_threshold=0.8
)

# Track performance
await agent.track_performance(
    prompt_id="system_prompt",
    success=True,
    execution_time=2.5,
    token_cost=0.01
)

# Get optimization status
status = agent.get_optimization_status()
print(f"Active variants: {status['active_variants']}")
print(f"Performance improvement: {status['performance_improvement']:.3f}")
```

### **5. Tool Optimization**
Dynamic tool description and parameter optimization.

**Features:**
- Tool-specific prompts
- Parameter optimization
- Usage tracking
- Performance analysis
- Dynamic adaptation

**Tool Optimization:**
```python
# Optimize tool descriptions
optimized_tools = await agent.optimize_tools([
    "think",
    "bash",
    "python",
    "git"
])

# Track tool usage
await agent.track_tool_usage(
    tool_name="think",
    success=True,
    execution_time=1.2,
    parameters={"steps": 5}
)

# Get tool performance
tool_metrics = agent.get_tool_metrics("think")
print(f"Success rate: {tool_metrics['success_rate']:.3f}")
print(f"Average time: {tool_metrics['avg_execution_time']:.3f}s")
```

---

## ⚙️ **Configuration**

### **Basic Configuration**
```toml
[agent]
# Agent settings
name = "CodeActAgent"
description = "Minimalist agent for code generation"
max_iterations = 10
timeout = 300

# LLM settings
llm_provider = "openai"
llm_model = "gpt-4"
llm_temperature = 0.1
llm_max_tokens = 4000

# Memory settings
enable_memory = true
memory_retention_days = 30
max_memory_size = 1000
memory_compression = true

# Prompt optimization
enable_prompt_optimization = true
prompt_opt_ab_split = 0.1
prompt_opt_min_samples = 10
prompt_opt_confidence_threshold = 0.8
prompt_opt_success_weight = 0.4
prompt_opt_time_weight = 0.3
prompt_opt_error_weight = 0.2
prompt_opt_cost_weight = 0.1

# Tool optimization
enable_tool_optimization = true
tool_opt_ab_split = 0.1
tool_opt_min_samples = 5
tool_opt_confidence_threshold = 0.7
```

### **Advanced Configuration**
```toml
[agent.advanced]
# ACE framework integration
enable_ace = true
ace_max_bullets = 1000
ace_similarity_threshold = 0.7
ace_max_refinement_rounds = 3

# Performance optimization
enable_performance_tracking = true
track_token_usage = true
track_execution_time = true
track_error_rates = true

# Security settings
enable_sandboxing = true
sandbox_timeout = 30
allowed_languages = ["python", "javascript", "bash"]
blocked_commands = ["rm", "del", "format"]

# Monitoring
enable_monitoring = true
log_level = "INFO"
metrics_retention_days = 7
alert_thresholds = { success_rate = 0.8, execution_time = 10.0 }
```

### **Tool-Specific Configuration**
```toml
[agent.tools.think]
enabled = true
max_steps = 10
reasoning_depth = "deep"
confidence_threshold = 0.7

[agent.tools.bash]
enabled = true
timeout = 30
allowed_commands = ["ls", "cd", "mkdir", "git", "npm", "pip"]
blocked_commands = ["rm", "del", "format", "shutdown"]

[agent.tools.python]
enabled = true
timeout = 60
max_execution_time = 30
allowed_modules = ["os", "sys", "json", "requests", "pandas"]
blocked_modules = ["subprocess", "os.system", "eval"]
```

---

## 🚀 **Usage**

### **Python API**
```python
from forge.agenthub.codeact_agent import CodeActAgent
from forge.core.config.agent_config import AgentConfig

# Initialize agent
config = AgentConfig(
    name="CodeActAgent",
    description="Minimalist agent for code generation",
    enable_prompt_optimization=True,
    enable_tool_optimization=True,
    enable_memory=True
)

agent = CodeActAgent(config=config)

# Run agent
response = await agent.run(
    "Create a user authentication system with JWT tokens",
    context={
        "domain": "web_development",
        "framework": "FastAPI",
        "database": "PostgreSQL"
    }
)

print(f"Success: {response.success}")
print(f"Code generated: {response.code}")
print(f"Execution time: {response.execution_time}")
print(f"Memory used: {response.memory_usage}")
```

### **REST API**
```bash
# Run agent
curl -X POST http://localhost:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a user authentication system",
    "context": {
      "domain": "web_development",
      "framework": "FastAPI"
    }
  }'

# Get agent status
curl http://localhost:8000/api/agent/status

# Get performance metrics
curl http://localhost:8000/api/agent/metrics
```

### **WebSocket API**
```javascript
// Connect to agent WebSocket
const socket = io('ws://localhost:8000/agent');

// Listen for responses
socket.on('agent_response', (response) => {
  console.log('Agent response:', response);
});

// Send request
socket.emit('run_agent', {
  prompt: 'Create a user authentication system',
  context: { domain: 'web_development' }
});
```

---

## 📊 **Monitoring**

### **Agent Performance Metrics**
```python
# Get comprehensive metrics
metrics = agent.get_metrics()

print("=== Agent Performance Metrics ===")
print(f"Total runs: {metrics['total_runs']}")
print(f"Success rate: {metrics['success_rate']:.3f}")
print(f"Average execution time: {metrics['avg_execution_time']:.3f}s")
print(f"Memory usage: {metrics['memory_usage']:.2f} MB")
print(f"Token usage: {metrics['token_usage']}")
print(f"Error rate: {metrics['error_rate']:.3f}")
```

### **Tool Performance**
```python
# Get tool-specific metrics
for tool_name in agent.get_available_tools():
    tool_metrics = agent.get_tool_metrics(tool_name)
    print(f"\n=== {tool_name} Tool Metrics ===")
    print(f"Usage count: {tool_metrics['usage_count']}")
    print(f"Success rate: {tool_metrics['success_rate']:.3f}")
    print(f"Average time: {tool_metrics['avg_execution_time']:.3f}s")
    print(f"Error rate: {tool_metrics['error_rate']:.3f}")
```

### **Memory Statistics**
```python
# Get memory statistics
memory_stats = agent.get_memory_statistics()

print("=== Memory Statistics ===")
print(f"Total conversations: {memory_stats['total_conversations']}")
print(f"Memory size: {memory_stats['memory_size']:.2f} MB")
print(f"Compression ratio: {memory_stats['compression_ratio']:.3f}")
print(f"Retrieval accuracy: {memory_stats['retrieval_accuracy']:.3f}")
```

### **Optimization Status**
```python
# Get prompt optimization status
prompt_status = agent.get_prompt_optimization_status()
print(f"Active variants: {prompt_status['active_variants']}")
print(f"Performance improvement: {prompt_status['performance_improvement']:.3f}")
print(f"Cost savings: {prompt_status['cost_savings']:.3f}")

# Get tool optimization status
tool_status = agent.get_tool_optimization_status()
print(f"Optimized tools: {tool_status['optimized_tools']}")
print(f"Tool performance improvement: {tool_status['performance_improvement']:.3f}")
```

---

## 🎯 **Advanced Features**

### **Custom Tool Creation**
```python
from forge.agenthub.codeact_agent.tools import BaseTool

class CustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="Custom tool for specific tasks",
            parameters={
                "input": {"type": "string", "description": "Input data"},
                "options": {"type": "object", "description": "Tool options"}
            }
        )
    
    async def execute(self, input: str, options: dict = None) -> dict:
        """Execute the custom tool."""
        # Custom tool logic here
        result = self._process_input(input, options)
        
        return {
            "success": True,
            "output": result,
            "execution_time": self._get_execution_time()
        }

# Register custom tool
agent.register_tool(CustomTool())
```

### **Custom Prompt Templates**
```python
# Create custom prompt template
custom_template = """
You are a {role} with expertise in {domain}.
Your task is to {task_description}.

Context:
{context}

Instructions:
1. {instruction_1}
2. {instruction_2}
3. {instruction_3}

Generate clean, efficient code that follows best practices.
"""

# Register custom template
agent.register_prompt_template(
    name="custom_template",
    template=custom_template,
    variables=["role", "domain", "task_description", "context", "instruction_1", "instruction_2", "instruction_3"]
)
```

### **Advanced Memory Management**
```python
# Enable advanced memory features
agent.enable_advanced_memory(
    enable_compression=True,
    enable_indexing=True,
    enable_evolution=True,
    max_memory_size=2000
)

# Create memory index
await agent.create_memory_index()

# Search memory with advanced queries
results = await agent.search_memory(
    query="authentication implementation",
    filters={"domain": "web_development", "success": True},
    max_results=10,
    similarity_threshold=0.8
)
```

### **Performance Profiling**
```python
# Enable performance profiling
agent.enable_performance_profiling()

# Run with profiling
response = await agent.run(
    "Create a complex data processing pipeline",
    profile=True
)

# Get profiling results
profile = agent.get_performance_profile()
print(f"Total execution time: {profile['total_time']:.3f}s")
print(f"LLM time: {profile['llm_time']:.3f}s")
print(f"Tool execution time: {profile['tool_time']:.3f}s")
print(f"Memory operations: {profile['memory_time']:.3f}s")
```

---

## 📚 **API Reference**

### **CodeActAgent**

#### **Methods**

##### `__init__(config: AgentConfig)`
Initialize the CodeAct agent.

**Parameters:**
- `config`: Agent configuration object

##### `async run(prompt: str, context: Dict[str, Any] = None) -> AgentResponse`
Run the agent with a given prompt.

**Parameters:**
- `prompt`: Input prompt
- `context`: Additional context

**Returns:**
- `AgentResponse`: Agent response object

##### `async think(question: str, steps: List[str] = None) -> ThinkResult`
Use the think tool for reasoning.

**Parameters:**
- `question`: Question to think about
- `steps`: Optional reasoning steps

**Returns:**
- `ThinkResult`: Thinking result

##### `async execute_code(code: str, language: str = "python", context: Dict[str, Any] = None) -> CodeExecutionResult`
Execute code with monitoring.

**Parameters:**
- `code`: Code to execute
- `language`: Programming language
- `context`: Execution context

**Returns:**
- `CodeExecutionResult`: Execution result

##### `get_metrics() -> Dict[str, Any]`
Get agent performance metrics.

**Returns:**
- `Dict[str, Any]`: Performance metrics

##### `get_tool_metrics(tool_name: str) -> Dict[str, Any]`
Get tool-specific metrics.

**Parameters:**
- `tool_name`: Name of the tool

**Returns:**
- `Dict[str, Any]`: Tool metrics

### **AgentResponse**

#### **Properties**
- `success: bool`: Whether the operation was successful
- `code: str`: Generated code
- `output: str`: Execution output
- `errors: List[str]`: Error messages
- `execution_time: float`: Execution time in seconds
- `memory_usage: float`: Memory usage in MB
- `token_usage: int`: Number of tokens used
- `confidence: float`: Confidence score

### **ThinkResult**

#### **Properties**
- `steps: List[str]`: Reasoning steps
- `confidence: float`: Confidence score
- `next_actions: List[str]`: Recommended next actions
- `reasoning: str`: Detailed reasoning
- `conclusions: List[str]`: Key conclusions

---

## 🎯 **Examples**

### **Example 1: Basic Code Generation**
```python
import asyncio
from forge.agenthub.codeact_agent import CodeActAgent
from forge.core.config.agent_config import AgentConfig

async def basic_code_generation():
    # Initialize agent
    config = AgentConfig(
        name="CodeActAgent",
        enable_prompt_optimization=True,
        enable_tool_optimization=True
    )
    
    agent = CodeActAgent(config=config)
    
    # Generate code
    response = await agent.run(
        "Create a REST API endpoint for user registration",
        context={
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "authentication": "JWT"
        }
    )
    
    print("=== Code Generation Result ===")
    print(f"Success: {response.success}")
    print(f"Code:\n{response.code}")
    print(f"Execution time: {response.execution_time:.3f}s")
    print(f"Confidence: {response.confidence:.3f}")

asyncio.run(basic_code_generation())
```

### **Example 2: Advanced Problem Solving**
```python
async def advanced_problem_solving():
    # Initialize with advanced configuration
    config = AgentConfig(
        name="AdvancedCodeActAgent",
        enable_prompt_optimization=True,
        enable_tool_optimization=True,
        enable_memory=True,
        max_iterations=20
    )
    
    agent = CodeActAgent(config=config)
    
    # Use think tool for complex problem
    think_result = await agent.think(
        "How to design a scalable microservices architecture for an e-commerce platform?",
        steps=[
            "Analyze requirements and constraints",
            "Identify service boundaries",
            "Design data flow and communication",
            "Plan for scalability and reliability",
            "Consider security and monitoring"
        ]
    )
    
    print("=== Thinking Process ===")
    for i, step in enumerate(think_result.steps, 1):
        print(f"{i}. {step}")
    
    print(f"\nConfidence: {think_result.confidence:.3f}")
    print(f"Next actions: {think_result.next_actions}")
    
    # Generate implementation based on thinking
    response = await agent.run(
        "Implement the microservices architecture based on the analysis",
        context={
            "analysis": think_result.reasoning,
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "message_queue": "Redis"
        }
    )
    
    print(f"\n=== Implementation Result ===")
    print(f"Success: {response.success}")
    print(f"Code length: {len(response.code)} characters")
```

### **Example 3: Memory-Enhanced Development**
```python
async def memory_enhanced_development():
    # Initialize with memory
    config = AgentConfig(
        name="MemoryCodeActAgent",
        enable_memory=True,
        memory_retention_days=30,
        max_memory_size=1000
    )
    
    agent = CodeActAgent(config=config)
    
    # First conversation - learn about project
    response1 = await agent.run(
        "I'm building a web application with FastAPI and PostgreSQL. What should I consider?",
        context={"project_type": "web_application"}
    )
    
    # Store in memory
    await agent.store_conversation({
        "user": "I'm building a web application with FastAPI and PostgreSQL. What should I consider?",
        "assistant": response1.output,
        "context": {"project_type": "web_application"}
    })
    
    # Second conversation - use memory
    response2 = await agent.run(
        "Now I need to implement user authentication. What's the best approach?",
        context={"project_type": "web_application"}
    )
    
    # Check if memory was used
    memory_stats = agent.get_memory_statistics()
    print(f"Memory size: {memory_stats['memory_size']:.2f} MB")
    print(f"Retrieval accuracy: {memory_stats['retrieval_accuracy']:.3f}")
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Agent Not Responding**
```python
# Check agent status
status = agent.get_status()
if not status['is_running']:
    # Restart agent
    await agent.restart()
    
    # Check configuration
    config = agent.get_config()
    print(f"Configuration valid: {config['valid']}")
```

#### **Low Success Rate**
```python
# Check performance metrics
metrics = agent.get_metrics()
if metrics['success_rate'] < 0.8:
    # Adjust configuration
    agent.update_config({
        'max_iterations': 15,
        'timeout': 600
    })
    
    # Enable additional tools
    agent.enable_tool('debug')
    agent.enable_tool('validate')
```

#### **Memory Issues**
```python
# Check memory usage
memory_stats = agent.get_memory_statistics()
if memory_stats['memory_size'] > 100:  # MB
    # Clean old memory
    await agent.clean_memory(days=7)
    
    # Enable compression
    agent.enable_memory_compression()
```

### **Performance Optimization**

#### **Optimize Prompt Performance**
```python
# Check prompt optimization status
status = agent.get_prompt_optimization_status()
if status['performance_improvement'] < 0.1:
    # Adjust optimization parameters
    agent.update_optimization_config({
        'ab_split': 0.2,
        'min_samples': 20,
        'confidence_threshold': 0.7
    })
```

#### **Optimize Tool Performance**
```python
# Check tool performance
for tool_name in agent.get_available_tools():
    metrics = agent.get_tool_metrics(tool_name)
    if metrics['success_rate'] < 0.8:
        # Optimize tool description
        agent.optimize_tool(tool_name)
```

---

## 📈 **Best Practices**

### **Agent Configuration**
1. **Start Simple**: Begin with basic configuration and add features gradually
2. **Monitor Performance**: Track metrics and adjust configuration accordingly
3. **Use Appropriate Tools**: Enable only the tools you need
4. **Set Realistic Limits**: Configure appropriate timeouts and limits

### **Code Generation**
1. **Provide Clear Context**: Include relevant context in prompts
2. **Use Specific Instructions**: Be specific about requirements and constraints
3. **Iterate and Refine**: Use multiple iterations to improve results
4. **Validate Output**: Always validate generated code before use

### **Memory Management**
1. **Regular Cleanup**: Periodically clean old memory
2. **Monitor Usage**: Track memory usage and adjust limits
3. **Use Relevant Context**: Store only relevant conversations
4. **Enable Compression**: Use compression to save space

### **Performance Optimization**
1. **Enable Optimization**: Use prompt and tool optimization
2. **Monitor Metrics**: Track performance metrics regularly
3. **Adjust Thresholds**: Tune optimization thresholds based on results
4. **Use Caching**: Enable caching for frequently used operations

---

**CodeAct Agent - The future of intelligent code generation.** 👨‍💻
