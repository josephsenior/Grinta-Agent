# 🚀 **Getting Started Guide**

> **Complete guide to get up and running with Forge in minutes.**

---

## 📖 **Table of Contents**

- [🌟 Quick Start](#-quick-start)
- [📋 Prerequisites](#-prerequisites)
- [⚙️ Installation](#️-installation)
- [🔧 Configuration](#-configuration)
- [🎯 First Steps](#-first-steps)
- [📚 Next Steps](#-next-steps)
- [🔍 Troubleshooting](#-troubleshooting)
- [💡 Tips & Tricks](#-tips--tricks)

---

## 🌟 **Quick Start**

Get Forge running in **5 minutes**:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/Forge.git
cd Forge

# 2. Install dependencies
pip install -e .
cd frontend && npm install

# 3. Start the system
# Terminal 1: Backend
python -m Forge.server

# Terminal 2: Frontend
cd frontend && npm run dev

# 4. Access the platform
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

**That's it!** 🎉 You now have Forge running locally.

---

## 📋 **Prerequisites**

### **System Requirements**
- **Python**: 3.8 or higher
- **Node.js**: 18 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 2GB free space
- **OS**: Windows, macOS, or Linux

### **Required Software**
- **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
- **Node.js 18+**: [Download Node.js](https://nodejs.org/)
- **Git**: [Download Git](https://git-scm.com/downloads)
- **Docker** (optional): [Download Docker](https://www.docker.com/products/docker-desktop)

### **API Keys** (Optional)
- **OpenAI API Key**: For GPT models
- **Anthropic API Key**: For Claude models
- **Other LLM Provider Keys**: As needed

---

## ⚙️ **Installation**

### **Method 1: Local Installation (Recommended)**

#### **Step 1: Clone Repository**
```bash
git clone https://github.com/your-org/Forge.git
cd Forge
```

#### **Step 2: Install Backend Dependencies**
```bash
# Install Python dependencies
pip install -e .

# Or using poetry (if available)
poetry install
```

#### **Step 3: Install Frontend Dependencies**
```bash
cd frontend
npm install

# Or using pnpm (if available)
pnpm install
```

#### **Step 4: Verify Installation**
```bash
# Check Python installation
python -c "import forge; print('Forge installed successfully')"

# Check Node.js installation
cd frontend && npm run build
```

### **Method 2: Docker Installation**

#### **Step 1: Clone Repository**
```bash
git clone https://github.com/your-org/Forge.git
cd Forge
```

#### **Step 2: Build and Run with Docker**
```bash
# Build the application
docker-compose build

# Start the services
docker-compose up -d

# Check status
docker-compose ps
```

#### **Step 3: Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **WebSocket**: ws://localhost:8000

### **Method 3: Development Installation**

#### **Step 1: Clone Repository**
```bash
git clone https://github.com/your-org/Forge.git
cd Forge
```

#### **Step 2: Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### **Step 3: Install Dependencies**
```bash
# Install backend dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend
npm install
```

#### **Step 4: Run Development Server**
```bash
# Terminal 1: Backend
python -m Forge.server --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 🔧 **Configuration**

> **💡 TIP**: For beta launch, use our [Recommended Model Strategy](recommended-model-strategy.md) with Claude 4.5 Haiku for optimal performance-to-cost ratio!

### **Basic Configuration**

#### **Step 1: Create Configuration File**
```bash
# Copy template configuration
cp config.template.toml config.toml
```

#### **Step 2: Edit Configuration**
```toml
# config.toml
[system]
name = "Forge"
environment = "development"
debug = true

[server]
host = "localhost"
port = 8000

[llm]
provider = "openai"
model = "gpt-4"
api_key = "your-api-key-here"
temperature = 0.1
max_tokens = 4000

[memory]
enable_memory = true
max_conversations = 1000

[optimization]
enable_optimization = true
ab_split = 0.1
min_samples = 10
```

#### **Step 3: Set Environment Variables**
```bash
# Set API keys
export FORGE_LLM_API_KEY="your-api-key-here"
export FORGE_LLM_PROVIDER="openai"
export FORGE_LLM_MODEL="gpt-4"

# Set other configuration
export FORGE_ENVIRONMENT="development"
export FORGE_DEBUG="true"
```

### **Advanced Configuration**

#### **Production Configuration**
```toml
# config.production.toml
[system]
environment = "production"
debug = false

[server]
host = "0.0.0.0"
port = 8000
workers = 4

[database]
url = "postgresql://user:pass@localhost/Forge"
pool_size = 20

[llm]
provider = "openai"
model = "gpt-4"
temperature = 0.1

[monitoring]
enable_monitoring = true
log_level = "WARNING"
```

#### **Feature-Specific Configuration**
```toml
# Enable specific features
[metasop]
enable_metasop = true
max_concurrent_agents = 5

[codeact]
enable_codeact = true
max_iterations = 10

[ace]
enable_ace = true
max_bullets = 1000

[real_time_optimization]
enable = true
optimization_threshold = 0.05
```

---

## 🎯 **First Steps**

### **Step 1: Start the System**

#### **Backend**
```bash
# Start backend server
python -m Forge.server

# Or with specific configuration
python -m Forge.server --config config.toml
```

#### **Frontend**
```bash
# Start frontend development server
cd frontend
npm run dev

# Or build and serve
npm run build
npm run preview
```

### **Step 2: Access the Platform**

#### **Web Interface**
1. Open your browser
2. Navigate to http://localhost:3000
3. You should see the Forge dashboard

#### **API Interface**
1. Open your browser
2. Navigate to http://localhost:8000/docs
3. You should see the API documentation

### **Step 3: Test Basic Functionality**

#### **Test Agent**
```bash
# Test CodeAct agent
curl -X POST http://localhost:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, can you help me?",
    "context": {"domain": "general"}
  }'
```

#### **Test Memory**
```bash
# Test memory system
curl -X POST http://localhost:8000/api/memory/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Hello",
    "assistant_message": "Hi! How can I help you?",
    "context": {"domain": "general"}
  }'
```

#### **Test Optimization**
```bash
# Test optimization system
curl -X GET http://localhost:8000/api/optimization/status
```

### **Step 4: Explore Features**

#### **Web Interface Features**
1. **Dashboard**: Overview of system status
2. **Agent Console**: Interact with agents
3. **Memory Browser**: View conversation history
4. **Optimization Panel**: Monitor prompt optimization
5. **Settings**: Configure system parameters
6. **🎨 MetaSOP Visualization**: Real-time agent collaboration diagrams

#### **Testing MetaSOP Visualization** (NEW!)
```bash
# 1. Open the chat interface at http://localhost:3000

# 2. Type a MetaSOP command:
sop: Create a todo application with React

# 3. Watch the magic happen:
# - Orchestration panel slides in from the right
# - Product Manager agent creates user stories (purple cards)
# - Architect agent designs system (blue diagrams + API endpoints)
# - Engineer agent generates file structure (green tree view)
# - QA agent shows test results (orange metrics dashboard)
# - All updates happen in real-time via WebSocket!

# 4. No code visible - only beautiful, user-friendly visualizations!
```

#### **API Features**
1. **Agent Endpoints**: Run agents programmatically
2. **Memory Endpoints**: Manage conversation memory
3. **Optimization Endpoints**: Control prompt optimization
4. **Monitoring Endpoints**: Check system health

---

## 📚 **Next Steps**

### **Learn the Basics**

#### **1. Understanding Agents**
- **CodeAct Agent**: For code generation and execution
- **MetaSOP Orchestrator**: For multi-agent coordination
- **ACE Framework**: For context engineering

#### **2. Memory Management**
- **Conversation Memory**: Store and retrieve conversations
- **Context Condensation**: Compress and optimize context
- **Memory Search**: Find relevant information

#### **3. Optimization Features**
- **Prompt Optimization**: Improve prompt performance
- **Real-Time Optimization**: Live adaptation
- **Tool Optimization**: Optimize tool descriptions

### **Advanced Usage**

#### **1. Custom Configuration**
- **Environment-Specific Configs**: Different settings for dev/staging/prod
- **Feature Flags**: Enable/disable specific features
- **Performance Tuning**: Optimize for your use case

#### **2. API Integration**
- **REST API**: HTTP endpoints for all features
- **WebSocket API**: Real-time communication
- **SDK Integration**: Python and TypeScript SDKs

#### **3. Monitoring and Analytics**
- **Performance Metrics**: Track system performance
- **Usage Analytics**: Understand usage patterns
- **Error Monitoring**: Track and debug issues

### **Development**

#### **1. Contributing**
- **Code Contributions**: Submit pull requests
- **Bug Reports**: Report issues
- **Feature Requests**: Suggest new features

#### **2. Customization**
- **Custom Tools**: Create your own tools
- **Custom Agents**: Build specialized agents
- **Custom Optimizations**: Implement custom optimization strategies

#### **3. Deployment**
- **Production Deployment**: Deploy to production
- **Scaling**: Scale for high availability
- **Monitoring**: Set up comprehensive monitoring

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Installation Issues**

**Problem**: Python dependencies not installing
```bash
# Solution: Upgrade pip and try again
pip install --upgrade pip
pip install -e .
```

**Problem**: Node.js dependencies not installing
```bash
# Solution: Clear cache and try again
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**Problem**: Permission errors
```bash
# Solution: Use virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .
```

#### **Configuration Issues**

**Problem**: Configuration not loading
```bash
# Solution: Check configuration file syntax
toml validate config.toml

# Check environment variables
env | grep Forge
```

**Problem**: API keys not working
```bash
# Solution: Verify API keys
curl -H "Authorization: Bearer $FORGE_LLM_API_KEY" \
  https://api.openai.com/v1/models
```

#### **Runtime Issues**

**Problem**: Server not starting
```bash
# Solution: Check port availability
netstat -an | grep 8000

# Check logs
tail -f logs/Forge.log
```

**Problem**: Frontend not loading
```bash
# Solution: Check if backend is running
curl http://localhost:8000/api/health

# Check frontend build
cd frontend && npm run build
```

**Problem**: Memory issues
```bash
# Solution: Check memory usage
free -h  # Linux/macOS
# or
wmic memorychip get size  # Windows

# Adjust memory limits in config
```

### **Debug Mode**

#### **Enable Debug Mode**
```bash
# Set environment variable
export FORGE_DEBUG=true

# Or in config file
[system]
debug = true
```

#### **Verbose Logging**
```bash
# Set log level
export FORGE_LOG_LEVEL=DEBUG

# Or in config file
[logging]
level = "DEBUG"
```

#### **Check System Status**
```bash
# Check system health
curl http://localhost:8000/api/monitoring/health

# Check component status
curl http://localhost:8000/api/monitoring/status
```

---

## 💡 **Tips & Tricks**

### **Performance Optimization**

#### **1. Memory Management**
```toml
# Optimize memory usage
[memory]
max_conversations = 500  # Reduce if memory limited
compression_ratio = 0.5  # Enable compression
cleanup_frequency = 24   # Clean up daily
```

#### **2. LLM Optimization**
```toml
# Optimize LLM usage
[llm]
temperature = 0.1        # Lower temperature for consistency
max_tokens = 2000       # Reduce token usage
timeout = 30            # Set reasonable timeout
```

#### **3. Caching**
```toml
# Enable caching
[caching]
enable_caching = true
cache_size = "512MB"
default_ttl = 3600
```

### **Development Tips**

#### **1. Use Development Mode**
```bash
# Start with development mode
python -m Forge.server --reload --debug
```

#### **2. Monitor Performance**
```bash
# Check system metrics
curl http://localhost:8000/api/monitoring/metrics

# Check agent performance
curl http://localhost:8000/api/agent/metrics
```

#### **3. Use WebSocket for Real-Time Updates**
```javascript
// Connect to WebSocket for real-time updates
const socket = io('ws://localhost:8000/ws');
socket.on('agent_response', (data) => {
  console.log('Real-time update:', data);
});
```

### **Production Tips**

#### **1. Use Production Configuration**
```bash
# Use production config
python -m Forge.server --config config.production.toml
```

#### **2. Enable Monitoring**
```toml
# Enable comprehensive monitoring
[monitoring]
enable_monitoring = true
log_level = "INFO"
metrics_enabled = true
alerts_enabled = true
```

#### **3. Set Up Logging**
```toml
# Configure logging
[logging]
level = "INFO"
file = "/var/log/Forge/app.log"
max_size = "100MB"
backup_count = 5
```

---

## 🎉 **Congratulations!**

You've successfully set up Forge! Here's what you can do next:

### **Immediate Next Steps**
1. **Explore the Web Interface**: Try the dashboard and agent console
2. **Test the API**: Use the API documentation to make requests
3. **Configure Your Environment**: Set up your preferred settings
4. **Try Different Agents**: Test CodeAct and MetaSOP agents

### **Learning Resources**
1. **Documentation**: Read the comprehensive documentation
2. **Examples**: Check out the example scripts
3. **Community**: Join the community discussions
4. **Tutorials**: Follow the step-by-step tutorials

### **Advanced Features**
1. **Custom Tools**: Create your own tools
2. **Custom Agents**: Build specialized agents
3. **Optimization**: Fine-tune prompt optimization
4. **Integration**: Integrate with your existing systems

---

**Welcome to Forge - The future of AI development!** 🚀

*Need help? Check out our [Troubleshooting Guide](troubleshooting.md) or [Community Support](https://github.com/your-org/Forge/discussions).*
