# Tutorial: Setting Up Your Development Environment

Complete guide to setting up Forge for development.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Node.js 18+** installed
- **Docker** installed and running
- **Git** installed
- **Poetry** (recommended) or pip for Python package management

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Forge.git
cd Forge
```

## Step 2: Install Python Dependencies

### Option A: Using Poetry (Recommended)

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Option B: Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Install Frontend Dependencies

```bash
cd frontend
pnpm install
# Or, if necessary:
# npm install
cd ..
```

## Step 4: Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```bash
# LLM Configuration (at least one required)
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Additional providers
OPENAI_API_KEY=sk-your-key-here
OPENROUTER_API_KEY=sk-or-your-key-here

# Server Configuration
PORT=3000
HOST=0.0.0.0

# Optional: Authentication
AUTH_ENABLED=false

# Optional: Redis (for caching/rate limiting)
REDIS_URL=redis://localhost:6379

# Optional: Database
DATABASE_URL=postgresql://user:pass@localhost/forge
```

## Step 5: Verify Docker is Running

```bash
# Check Docker is running
docker ps

# If Docker is not running, start it:
# - Docker Desktop: Open Docker Desktop application
# - Linux: sudo systemctl start docker
```

## Step 6: Test the Installation

### Test Backend

```bash
# Run backend tests
poetry run pytest tests/unit/ -v

# Or with pip:
pytest tests/unit/ -v
```

### Test Frontend

```bash
cd frontend
pnpm run type-check
pnpm test
cd ..
```

## Step 7: Start the Development Servers

### Terminal 1: Backend

```bash
# Using Poetry
poetry run python -m forge.server

# Or with pip
python -m forge.server
```

The backend should start on `http://localhost:3000`

### Terminal 2: Frontend

```bash
cd frontend
pnpm run dev
```

The frontend should start on `http://localhost:5173`

## Step 8: Verify Everything Works

1. **Open your browser** to `http://localhost:5173`
2. **Check the backend** is responding at `http://localhost:3000/api/health`
3. **Create a test conversation** in the UI

## Common Setup Issues

### Python Version Issues

**Problem:** "Python 3.11+ required"

**Solution:**
```bash
# Check your Python version
python --version

# If using pyenv, install Python 3.11+
pyenv install 3.11.0
pyenv local 3.11.0
```

### Poetry Installation Issues

**Problem:** "Poetry command not found"

**Solution:**
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

### Docker Issues

**Problem:** "Docker daemon not running"

**Solution:**
- **Docker Desktop**: Open Docker Desktop application
- **Linux**: `sudo systemctl start docker`
- **Verify**: `docker ps` should work without errors

### Port Already in Use

**Problem:** "Port 3000 already in use"

**Solution:**
```bash
# Find process using port 3000
# Linux/Mac:
lsof -i :3000
# Windows:
netstat -ano | findstr :3000

# Kill the process or change PORT in .env
PORT=3001
```

### Frontend Build Issues

**Problem:** "pnpm install fails"

**Solution:**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm store prune
pnpm install
```

## Development Tools

### Code Formatting

```bash
# Format Python code
poetry run black forge/
poetry run ruff format forge/

# Format frontend code
cd frontend
pnpm run format
```

### Linting

```bash
# Lint Python code
poetry run ruff check forge/
poetry run mypy forge/

# Lint frontend code
cd frontend
pnpm run lint
```

### Type Checking

```bash
# Python type checking
poetry run mypy forge/

# Frontend type checking
cd frontend
pnpm run type-check
```

## Next Steps

- [Your First Conversation](01-first-conversation.md) - Start using Forge
- [Configuring LLM Providers](03-configure-llm.md) - Set up multiple providers
- [Development Guide](../development.md) - Learn about the codebase

## Summary

You've learned:
- ✅ How to install all dependencies
- ✅ How to configure environment variables
- ✅ How to start development servers
- ✅ How to troubleshoot common issues

Your development environment is now ready!

