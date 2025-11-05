# 📚 **Complete Usage Guide**

> **Comprehensive guide to using all OpenHands features, from basic setup to advanced optimization.**

---

## 📖 **Table of Contents**

- [🚀 Getting Started](#-getting-started)
- [⚙️ Configuration](#️-configuration)
- [🤖 Multi-Agent System](#-multi-agent-system)
- [🚀 Dynamic Prompt Optimization](#-dynamic-prompt-optimization)
- [💻 Terminal Usage](#-terminal-usage)
- [📊 Analytics & Monitoring](#-analytics--monitoring)
- [🎨 UI/UX Features](#-uiux-features)
- [🔧 Advanced Features](#-advanced-features)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📈 Performance Tuning](#-performance-tuning)

---

## 🚀 **Getting Started**

### **Initial Setup**

1. **Installation**
```bash
# Clone repository
git clone https://github.com/your-org/openhands.git
cd openhands

# Backend setup
pip install -e .

# Frontend setup
cd frontend
npm install
npm run dev

# Start system
python -m openhands.server  # Backend
npm run dev                 # Frontend
```

2. **Environment Configuration**
```bash
# .env file
OPENHANDS_BACKEND_URL=http://localhost:8000
OPENHANDS_LLM_PROVIDER=openai
OPENHANDS_LLM_MODEL=gpt-4
OPENHANDS_ENABLE_PROMPT_OPTIMIZATION=true
VITE_BACKEND_BASE_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000
```

### **First Project**

1. **Create New Project**
   - Open http://localhost:3000
   - Click "New Project"
   - Select project type (Full-stack, API, ML, etc.)

2. **Configure Agents**
   - Enable MetaSOP multi-agent system
   - Configure CodeAct agent settings
   - Set up prompt optimization preferences

---

## ⚙️ **Configuration**

### **System Configuration**

```toml
# config.toml
[system]
debug_mode = false
log_level = "INFO"
max_concurrent_agents = 5

[llm]
provider = "openai"
model = "gpt-4"
temperature = 0.7
max_tokens = 4000

[optimization]
enabled = true
ab_split = 0.2
confidence_threshold = 0.95
min_samples = 50
```

### **Agent Configuration**

```python
# MetaSOP Configuration
orchestrator = MetaSOPOrchestrator(
    llm=llm,
    memory=memory,
    settings=MetaSOPSettings(
        enable_prompt_optimization=True,
        prompt_opt_ab_split=0.2,
        prompt_opt_min_samples=30,
        role_optimization={
            "engineer": {"weight": 0.5, "focus": "execution"},
            "architect": {"weight": 0.4, "focus": "technical_depth"},
            "product_manager": {"weight": 0.3, "focus": "clarity"}
        }
    )
)

# CodeAct Configuration
agent = CodeActAgent(
    llm=llm,
    config=AgentConfig(
        enable_prompt_optimization=True,
        prompt_opt_storage_path="./codeact_optimization",
        prompt_opt_success_weight=0.4,
        prompt_opt_time_weight=0.3,
        prompt_opt_cost_weight=0.2
    )
)
```

---

## 🤖 **Multi-Agent System**

### **MetaSOP Orchestration**

The MetaSOP system coordinates multiple specialized agents with **real-time visualizations**:

```python
# Initialize orchestrator
orchestrator = MetaSOPOrchestrator(
    llm=llm,
    memory=memory,
    ace_framework=ace
)

# Create task
task = Task(
    description="Build a REST API with authentication",
    priority="high",
    context={"framework": "FastAPI", "database": "PostgreSQL"}
)

# Execute with agents
result = await orchestrator.execute_task(task)
# Automatically uses: Product Manager → Architect → Engineer → QA → UI Designer
# Frontend displays real-time visualizations for each agent's output!
```

### **🎨 MetaSOP Visualization System** (NEW!)

#### **Overview**
The MetaSOP visualization system provides beautiful, real-time diagrams for each agent's work:

```bash
# Chat Interface Usage
1. Open chat at http://localhost:3000
2. Type: sop: Build a REST API with user authentication
3. Watch the orchestration panel appear with live diagrams
```

#### **Visualization Components**

**Product Manager View** (Purple Theme)
- User story cards with priority badges (High/Medium/Low)
- Acceptance criteria checklists
- Clean, glassmorphic design
- No raw JSON or code visible

**Architect View** (Blue Theme)
- Animated SVG architecture diagrams
- API endpoint cards with method badges (GET, POST, PUT, DELETE)
- Architectural decision cards with rationale
- Professional, technical aesthetic

**Engineer View** (Green Theme)
- Interactive file structure tree
- Expandable folders with file/folder icons
- Implementation plan step-by-step
- Development-focused UI

**QA View** (Orange Theme)
- Test results dashboard with pass/fail metrics
- Individual test cards with checkmark/X icons
- Lint status indicators
- Quality assurance metrics

#### **Real-Time Updates**
```typescript
// Frontend automatically receives updates via WebSocket
socket.on('metasop_step_update', (data) => {
  // Parse artifact data
  const artifact = parseArtifact(data.artifact, data.role);
  
  // Render visualization
  <CleanVisualAdapter 
    role={data.role}
    artifact={artifact}
    animated={true}
  />
});
```

#### **Type-Safe Architecture**
```typescript
// All artifacts have strict TypeScript interfaces
interface PMSpecArtifact {
  user_stories: UserStory[];
  acceptance_criteria: AcceptanceCriteria[];
  priority?: string;
}

interface ArchitectArtifact {
  architecture_diagram?: string;
  api_endpoints: APIEndpoint[];
  architectural_decisions: ArchitecturalDecision[];
}

// Parser validates and normalizes all data
const artifact = parseArtifact(rawData, 'product_manager');
```

### **Agent Roles**

1. **Product Manager**: Requirements analysis and user story creation
2. **Architect**: System design and technology decisions  
3. **Engineer**: Code implementation and technical execution
4. **QA**: Testing strategy and quality assurance
5. **UI Designer**: User interface and experience design

### **Live Monitoring**

```python
# Monitor agent activity in real-time
@orchestrator.on_agent_status_change
async def on_status_change(agent_id: str, status: AgentStatus):
    print(f"Agent {agent_id}: {status}")

# View live agent diagrams
dashboard.connect_ws()  # WebSocket connection for live updates
```

---

## 🚀 **Dynamic Prompt Optimization**

### **Basic Optimization Setup**

```python
from openhands.prompt_optimization import PromptOptimizer

# Initialize optimizer
optimizer = PromptOptimizer(
    category="system_prompt",
    ab_split=0.2,  # 20% traffic to variants
    min_samples=50,
    confidence_threshold=0.95
)

# Register variants
base_variant = optimizer.register_variant(
    prompt_id="codeact_system",
    content="You are CodeAct...",
    description="Base system prompt"
)

enhanced_variant = optimizer.register_variant(
    prompt_id="codeact_system", 
    content="You are CodeAct with enhanced reasoning...",
    description="Improved reasoning capabilities"
)
```

### **Performance Tracking**

```python
# Track performance after each execution
optimizer.track_performance(
    prompt_id="codeact_system",
    variant_id=variant.variant_id,
    success=True,
    execution_time=1.2,
    token_count=150,
    cost=0.003,
    user_satisfaction=4.8
)

# Get analysis
analysis = optimizer.get_performance_analysis("codeact_system")
print(f"Best variant: {analysis.best_variant}")
print(f"Improvement: {analysis.improvement:.2%}")
```

### **Real-Time Optimization**

```python
from openhands.prompt_optimization import LiveOptimizer

# Enable real-time optimization
live_optimizer = LiveOptimizer(
    optimization_threshold=0.05,  # 5% improvement threshold
    confidence_threshold=0.8
)

await live_optimizer.start()
# System automatically optimizes prompts in real-time
```

### **Advanced Strategies**

```python
from openhands.prompt_optimization.advanced import MultiObjectiveOptimizer

# Multi-objective optimization
multi_optimizer = MultiObjectiveOptimizer(
    objectives={
        "success_rate": {"weight": 0.4, "minimize": False},
        "execution_time": {"weight": 0.3, "minimize": True},
        "cost": {"weight": 0.2, "minimize": True},
        "user_satisfaction": {"weight": 0.1, "minimize": False}
    }
)

result = multi_optimizer.optimize(variants, historical_data)
```

---

## 💻 **Terminal Usage**

### **Modern Terminal Interface**

The redesigned terminal provides premium functionality:

1. **Basic Usage**
   - Commands execute with real-time streaming
   - Status indicators show running/success/error states
   - Auto-scroll to latest output

2. **Interactive Features**
   ```bash
   # Copy output
   Click copy button or Ctrl+C
   
   # Download output
   Click download button to save as text file
   
   # Expand/collapse
   Click expand button for long outputs
   
   # More actions
   Click "..." menu for additional options
   ```

3. **Mobile Gestures**
   - Swipe left/right for navigation
   - Pull down to refresh
   - Touch and hold for context menu

### **Terminal Customization**

```typescript
// Terminal configuration
const terminalConfig = {
  fontSize: 14,
  maxHeight: '60vh',
  streamingChunkSize: 3,
  streamingInterval: 20,
  enableAnimations: true,
  enableDownload: true
};
```

---

## 📊 **Analytics & Monitoring**

### **Real-Time Dashboard**

Access live performance metrics:

```python
from openhands.prompt_optimization.analytics import AnalyticsDashboard

dashboard = AnalyticsDashboard()

# Get live metrics
metrics = dashboard.get_live_metrics()
print(f"Active optimizations: {metrics.active_optimizations}")
print(f"Average improvement: {metrics.avg_improvement:.2%}")

# Detailed analytics
analytics = dashboard.get_detailed_analytics(
    time_range="24h",
    include_breakdown=True
)
```

### **REST API Monitoring**

```bash
# Check optimization status
curl -X GET "http://localhost:8000/api/v1/prompt-optimization/status"

# Get prompt performance
curl -X GET "http://localhost:8000/api/v1/prompt-optimization/prompts/codeact_system/performance"

# Trigger manual optimization
curl -X POST "http://localhost:8000/api/v1/prompt-optimization/prompts/codeact_system/optimize" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "strategy": "multi_objective"}'
```

### **WebSocket Live Updates**

```typescript
// Connect to live updates
const ws = new WebSocket('ws://localhost:8000/ws/optimization');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Live update:', data);
  
  // Update UI with real-time metrics
  updateDashboard(data);
};
```

---

## 🎨 **UI/UX Features**

### **Interactive Components**

1. **Live Agent Visualization**
   - Real-time agent status indicators
   - Animated agent avatars
   - Activity feed with live updates

2. **Enhanced Code Blocks**
   ```typescript
   // Advanced code display with actions
   <CodeBlockEnhanced
     code={code}
     language="typescript"
     onRun={handleRun}
     onDownload={handleDownload}
     showLineNumbers
   />
   ```

3. **Mobile Gestures**
   - Swipe navigation between sections
   - Pull-to-refresh functionality
   - Touch-optimized interactions

### **Theme Customization**

```typescript
// Theme switching
const { theme, setTheme } = useTheme();

// Available themes
const themes = ['light', 'dark', 'system', 'oled'];

// OLED optimization
if (theme === 'oled') {
  // Automatic OLED-optimized styling applied
  // Pure black backgrounds, reduced motion
}
```

### **Micro-interactions**

- Ripple button effects
- Magnetic hover cards
- Parallax scrolling elements
- Staggered animations
- Glow effects on interaction

---

## 🔧 **Advanced Features**

### **Agentic Context Engineering (ACE)**

```python
from openhands.metasop.ace import ACEFramework

ace = ACEFramework(
    llm=llm,
    memory=memory
)

# Generate context improvements
improvements = await ace.generate_improvements(
    current_context=context,
    performance_feedback=feedback
)

# Apply incremental updates
await ace.apply_delta_updates(improvements)
```

### **Memory System Integration**

```python
from openhands.memory import ConversationMemory

memory = ConversationMemory(
    max_tokens=10000,
    enable_condensation=True
)

# Store conversation
await memory.add_exchange(
    human="Create a React component",
    assistant=response,
    metadata={"success": True, "time": 2.3}
)

# Retrieve relevant context
context = await memory.get_relevant_context(
    query="React component with hooks",
    max_tokens=2000
)
```

### **Tool-Specific Optimization**

```python
from openhands.prompt_optimization.tools import ToolOptimizer

tool_optimizer = ToolOptimizer()

# Optimize specific tools
tools = ["think", "bash", "editor", "browser"]
for tool_id in tools:
    await tool_optimizer.optimize_tool(
        tool_id=tool_id,
        strategy="context_aware"
    )
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Optimization Not Working**
   ```bash
   # Check configuration
   grep -r "enable_prompt_optimization" config/
   
   # Verify storage path
   ls -la ./prompt_data/
   
   # Check logs
   tail -f logs/optimization.log
   ```

2. **Terminal Display Issues**
   ```typescript
   // Clear terminal cache
   localStorage.removeItem('terminal-state');
   
   // Reset terminal styles
   document.documentElement.style.setProperty('--terminal-font-size', '14px');
   ```

3. **WebSocket Connection Problems**
   ```bash
   # Test WebSocket connection
   curl -i -N -H "Connection: Upgrade" \
        -H "Upgrade: websocket" \
        -H "Sec-WebSocket-Version: 13" \
        -H "Sec-WebSocket-Key: test" \
        http://localhost:8000/ws/optimization
   ```

### **Performance Issues**

1. **Slow Optimization**
   - Reduce `min_samples` in configuration
   - Lower `confidence_threshold`
   - Enable caching in storage configuration

2. **Memory Usage**
   - Adjust `max_tokens` in memory settings
   - Enable memory condensation
   - Regular cleanup of old optimization data

---

## 📈 **Performance Tuning**

### **Optimization Settings**

```toml
[prompt_optimization]
# Reduce for faster results, increase for accuracy
min_samples = 30
confidence_threshold = 0.8
ab_split = 0.15

[optimization.performance]
# Enable caching
enable_cache = true
cache_size = 1000

# Reduce latency
streaming_enabled = true
batch_size = 10
```

### **System Optimization**

```bash
# Environment variables for performance
export OPENHANDS_OPTIMIZATION_THREADS=4
export OPENHANDS_CACHE_SIZE=2000
export OPENHANDS_ENABLE_COMPRESSION=true

# Frontend optimization
export VITE_TERMINAL_VIRTUAL_SCROLLING=true
export VITE_ENABLE_HARDWARE_ACCELERATION=true
```

### **Monitoring Performance**

```python
# Performance monitoring
from openhands.prompt_optimization.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
metrics = monitor.get_system_metrics()

print(f"Optimization latency: {metrics.avg_latency}ms")
print(f"Memory usage: {metrics.memory_usage}MB")
print(f"Cache hit rate: {metrics.cache_hit_rate:.2%}")
```

---

## 🎯 **Best Practices**

### **Optimization Strategy**

1. **Start Conservative**
   - Begin with 10-15% traffic to variants
   - Use higher confidence thresholds initially
   - Monitor closely for first week

2. **Gradual Rollout**
   - Increase traffic after validation
   - A/B test one variable at a time
   - Maintain fallback strategies

3. **Regular Monitoring**
   - Weekly performance reviews
   - Monthly optimization audits
   - Quarterly strategy updates

### **Development Workflow**

1. **Version Control**
   - Tag optimization milestones
   - Document configuration changes
   - Maintain rollback procedures

2. **Testing**
   - Test optimization changes in staging
   - Validate performance improvements
   - Ensure system stability

3. **Documentation**
   - Document optimization decisions
   - Track performance baselines
   - Maintain change logs

---

*This comprehensive guide covers all major features and capabilities of the OpenHands platform. For specific implementation details, refer to the individual component documentation in the features directory.*
