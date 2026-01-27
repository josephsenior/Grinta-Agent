# 📚 **Complete Usage Guide**

> **Comprehensive guide to using all Forge features, from basic setup to advanced optimization.**

---

## 📖 **Table of Contents**

- [🚀 Getting Started](#-getting-started)
- [⚙️ Configuration](#️-configuration)
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
git clone https://github.com/your-org/Forge.git
cd Forge

# Backend setup
pip install -e .

# Frontend setup
cd frontend
pnpm install
pnpm run dev

# Start system
python -m Forge.server  # Backend
pnpm run dev                 # Frontend
```

2. **Environment Configuration**
```bash
# .env file
FORGE_BACKEND_URL=http://localhost:3000
FORGE_LLM_PROVIDER=openai
FORGE_LLM_MODEL=gpt-4
VITE_BACKEND_BASE_URL=http://localhost:3000
VITE_WEBSOCKET_URL=http://localhost:3000/socket.io
```

### **First Project**

1. **Create New Project**
   - Open http://localhost:3000
   - Click "New Project"
   - Select project type (Full-stack, API, ML, etc.)

2. **Configure Agents**
   - Configure CodeAct agent settings

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
# CodeAct Configuration
agent = CodeActAgent(
    llm=llm,
    config=AgentConfig(
        enable_memory=True
    )
)
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
from forge.prompt_optimization.analytics import AnalyticsDashboard

dashboard = AnalyticsDashboard()

# Get live metrics
metrics = dashboard.get_live_metrics()
print(f"Total runs: {metrics.total_runs}")
print(f"Success rate: {metrics.success_rate:.2%}")

# Detailed analytics
analytics = dashboard.get_detailed_analytics(
    time_range="24h",
    include_breakdown=True
)
```

### **REST API Monitoring**

```bash
# Get system status
curl -X GET "http://localhost:3000/api/status"
```

### **WebSocket Live Updates**

```typescript
// Connect to live updates
const socket = io('http://localhost:3000', {
  path: '/socket.io',
  query: { conversationId: 'your-conversation-id' }
});

socket.on('message', (event) => {
  // Event is already parsed JSON
  console.log('Live update:', event);
  
  // Update UI with real-time metrics
  updateDashboard(event);
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

### **Memory System Integration**

```python
from forge.memory import ConversationMemory

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
from forge.prompt_optimization.tools import ToolOptimizer

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

1. **Agent Not Responding**
   ```bash
   # Check logs
   tail -f logs/forge.log
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
        http://localhost:3000/socket.io
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

### **System Optimization**

```bash
# Environment variables for performance
export FORGE_CACHE_SIZE=2000
export FORGE_ENABLE_COMPRESSION=true

# Frontend optimization
export VITE_TERMINAL_VIRTUAL_SCROLLING=true
export VITE_ENABLE_HARDWARE_ACCELERATION=true
```

### **Monitoring Performance**

```python
# Performance monitoring
from forge.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
metrics = monitor.get_system_metrics()

print(f"Average latency: {metrics.avg_latency}ms")
print(f"Memory usage: {metrics.memory_usage}MB")
```

---

## 🎯 **Best Practices**

### **Development Workflow**

1. **Version Control**
   - Tag milestones
   - Document configuration changes

2. **Testing**
   - Test changes in staging
   - Validate performance improvements
   - Ensure system stability

3. **Documentation**
   - Document decisions
   - Track performance baselines
   - Maintain change logs

---

*This comprehensive guide covers all major features and capabilities of the Forge platform. For specific implementation details, refer to the individual component documentation in the features directory.*
