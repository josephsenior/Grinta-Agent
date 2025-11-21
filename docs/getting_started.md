# Getting Started with Forge

## Quick Start (5 Minutes)

### Prerequisites

- **Python:** 3.11 or higher
- **Node.js:** 18 or higher  
- **Docker:** For sandbox execution
- **Git:** For version control

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/Forge.git
cd Forge
```

2. **Install backend dependencies:**
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

3. **Install frontend dependencies:**
```bash
cd frontend
npm install
cd ..
```

4. **Set up environment variables:**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
# At minimum, add one of:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# OPENROUTER_API_KEY=sk-or-...
```

### Configuration

**Option 1: Use Anthropic Claude (Recommended for Beta):**
```bash
# In .env file:
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Option 2: Use OpenRouter (200+ Models):**
```bash
# In .env file:
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet
OPENROUTER_API_KEY=sk-or-your-key-here
```

**Option 3: Use OpenAI:**
```bash
# In .env file:
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here
```

### Start the Application

1. **Start backend:**
```bash
poetry run python -m forge.server
```

Or alternatively:
```bash
python -m forge.server
```

Backend will start on `http://localhost:3000` (default port, configurable via `port` environment variable)

2. **Start frontend (in new terminal):**
```bash
cd frontend
npm run dev
```

Frontend will start on `http://localhost:5173`

3. **Open browser:**
```
http://localhost:5173
```

## Your First Conversation

### Example 1: Simple Code Generation

**Prompt:**
```
Build a Python function that calculates fibonacci numbers recursively.
Add docstrings and type hints.
```

**What happens:**
1. CodeAct agent receives your request
2. Agent analyzes the task
3. Agent creates a new file `fibonacci.py`
4. Agent writes the function with tests
5. You see the file appear in real-time

### Example 2: Bug Fix

**Prompt:**
```
I have a bug in main.py line 42. The variable 'count' is used before 
it's defined. Please fix it.
```

**What happens:**
1. Agent reads `main.py`
2. Agent identifies the issue
3. Agent edits the file (structure-aware)
4. Shows you the diff
5. You approve or reject

### Example 3: Full Feature

**Prompt:**
```
Add authentication to this Flask app:
1. User registration
2. Login/logout
3. Password hashing
4. Session management
```

**What happens:**
1. Agent plans the implementation
2. Creates necessary files (auth.py, models.py, etc.)
3. Modifies existing routes
4. Adds tests
5. Shows you the complete implementation

## Understanding the UI

### Main Interface

```
┌────────────────────────────────────────────────────────┐
│  [Conversation Panel]    │    [Chat Interface]         │
│                          │                             │
│  • Past conversations    │    Your message:            │
│  • New conversation      │    "Build a todo app"       │
│  • Settings              │                             │
│                          │    Agent response:          │
│                          │    ✓ Created app.py         │
│                          │    ✓ Created tests.py       │
│                          │    ⟳ Running tests...       │
│                          │                             │
│                          │    [Send] [Stop] [Retry]    │
└──────────────────────────┴─────────────────────────────┘
```

### Agent Controls

- **▶ Run** - Start agent execution
- **⏸ Pause** - Pause agent (safety check)
- **⏹ Stop** - Stop agent completely
- **🔄 Retry** - Retry last action

### Cost Tracking

**Budget Display** (top right):
```
Cost: $0.45 / $1.00 daily limit
```

**Analytics** (settings):
- Cost per conversation
- Token usage
- Model usage distribution

## Configuration Options

### Model Selection

**In Settings UI:**
1. Click ⚙️ Settings
2. Go to "LLM Configuration"
3. Select model from dropdown (200+ options)
4. Enter API key
5. Save

**Via config file (`config.toml`):**
```toml
[llm]
model = "claude-sonnet-4-20250514"
api_key = "sk-ant-..."
temperature = 0.0
max_output_tokens = 8000
```

### Advanced Options

```toml
[llm]
# Retry configuration
num_retries = 5
retry_min_wait = 8
retry_max_wait = 64

# Performance
caching_prompt = true  # Enable prompt caching (Claude)
disable_vision = false  # Enable vision for images

# Cost control
max_message_chars = 30000  # Truncate long messages
```

## Common Tasks

### Task 1: Generate a New Project

```
Build a React todo app with:
- Add/delete/toggle todos
- Local storage persistence  
- Tailwind CSS styling
- TypeScript
```

### Task 2: Debug Existing Code

```
Debug this error in server.py:
"TypeError: 'NoneType' object is not subscriptable on line 42"

Please fix it and explain what was wrong.
```

### Task 3: Refactor Code

```
Refactor the calculate_total() function in utils.py:
- Extract magic numbers to constants
- Add type hints
- Improve variable names
- Add docstring
```

### Task 4: Add Tests

```
Add pytest tests for the User model in models.py.
Test: creation, validation, edge cases.
```

## Troubleshooting

### Issue: "No API key found"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify API key is set
cat .env | grep API_KEY

# Restart backend after changing .env
```

### Issue: "Docker not available"

**Solution:**
```bash
# Check Docker is running
docker ps

# Start Docker Desktop (if using Mac/Windows)
# Or start Docker service (if using Linux)
sudo systemctl start docker
```

### Issue: "Port 3000 already in use"

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Kill process or change port
# In .env: PORT=3001
```

For more issues, see [Troubleshooting Guide](./troubleshooting.md)

## Next Steps

- **Read:** [Architecture Guide](./architecture.md) - Understand the system
- **Explore:** [API Reference](./api-reference.md) - Build integrations
- **Monitor:** [Monitoring Guide](./monitoring.md) - Track performance
- **Contribute:** [Contributing Guide](./CONTRIBUTING.md) - Help improve Forge

## Getting Help

- **Documentation:** Check other guides in `docs/`
- **Issues:** [GitHub Issues](https://github.com/yourusername/Forge/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/Forge/discussions)
- **Discord:** Join our community (link TBD)

## Advanced Topics

Once you're comfortable with basics:
- **Custom Providers:** Add your own LLM provider
- **Cost Optimization:** Strategies for reducing LLM costs
- **Performance Tuning:** Optimize for your use case
- **Security:** Configure risk levels and sandboxing

Happy coding! 🚀
