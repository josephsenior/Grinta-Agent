# Development

This guide covers setting up Forge for development and contributing to the project.

## Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry
- Docker
- Git

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Forge/Forge.git
   cd Forge
   ```

2. **Install Python dependencies:**
   ```bash
   poetry install
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   pnpm install
   pnpm run build
   cd ..
   ```

4. **Set up configuration:**
   ```bash
   cp config.template.toml config.toml
   # Edit config.toml with your settings
   ```

## Running in Development

1. **Start the backend:**
   ```bash
   python -m forge.server
   ```
   
   The backend will start on `http://localhost:3000` by default (configurable via `port` environment variable). The backend serves both the REST API and the frontend SPA from the same port.

2. **Start the frontend (in another terminal, for development):**
   ```bash
   cd frontend
   pnpm run dev
   ```
   
   This will start the frontend dev server on `http://localhost:5173` (Vite default).

3. **Access the application:**
   - **Production mode:** http://localhost:3000 (backend serves built frontend)
   - **Development mode:** http://localhost:5173 (Vite dev server with hot reload)
   - **Backend API:** http://localhost:3000/api/*
   - **API Docs:** http://localhost:3000/docs

## Testing

### Unit Tests
```bash
poetry run pytest tests/unit/
```

### Integration Tests
```bash
poetry run pytest tests/integration/
```

### End-to-End Tests
```bash
poetry run pytest tests/e2e/
```

## Code Quality

Forge maintains **exceptional code quality** with an average cyclomatic complexity of **3.06** (A-rated) across **8,100 backend functions/methods** and **2.21** for frontend. The codebase consists of **245,527 lines of production code** (144K backend + 101K frontend) with **0% high-complexity functions** (0 above B complexity level). See [code-quality.md](code-quality.md) for detailed metrics and standards.

### Complexity Analysis
```bash
# Check cyclomatic complexity
poetry run radon cc forge -s -a

# Detailed complexity report
poetry run radon cc forge -s
```

**Our Standards:**
- ✅ A-rated (1-5): Target for all functions
- ✅ B-rated (6-10): Acceptable
- ⚠️ C-rated (11-20): Needs refactoring
- ❌ D+ rated (>20): Must refactor before merge

**Achievement:** 🏆 **ZERO C, D, E, or F rated functions**

### Linting
```bash
poetry run ruff check .
poetry run mypy .
```

### Formatting
```bash
poetry run black .
poetry run isort .
```

## Contributing

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Code Standards
- Follow PEP 8 for Python
- Use type hints
- Write comprehensive tests
- Update documentation

### Commit Messages
Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring

## Architecture

### Backend (Python/FastAPI)
- REST API endpoints
- WebSocket support
- Agent orchestration
- Runtime management

### Frontend (React/TypeScript)
- Web interface
- Real-time updates
- Agent interaction
- File management

### Agents
- CodeAct: Code execution and editing
- Custom agents via plugin system

### Runtime
- Docker containers
- Local execution
- Sandboxed environments

### Note on Internal Structure
Forge maintains "Forge" as the internal Python package name for backward compatibility and stability. User-facing commands and branding use "Forge".

## Debugging

### Backend Debugging
```bash
# Enable debug logging
export DEBUG=1
python -m forge.server
```

### Frontend Debugging
```bash
cd frontend
pnpm run dev
# Open browser dev tools
```

### Runtime Debugging
```toml
[core]
debug = true

[sandbox]
timeout = 300
```

## Building

### Backend
```bash
poetry build
```

### Frontend
```bash
cd frontend
pnpm run build
```

### Docker
```bash
docker build -t Forge .

