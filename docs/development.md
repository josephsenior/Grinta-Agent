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
   git clone https://github.com/All-Hands-AI/Forge.git
   cd Forge
   ```

2. **Install Python dependencies:**
   ```bash
   poetry install
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   npm run build
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
   python -m openhands.server
   ```

2. **Start the frontend (in another terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application:**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000

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
- MetaSOP: Multi-agent orchestration
- Custom agents via plugin system

### Runtime
- Docker containers
- Local execution
- Sandboxed environments

### Note on Internal Structure
Forge maintains "openhands" as the internal Python package name for backward compatibility and stability. User-facing commands and branding use "Forge".

## Debugging

### Backend Debugging
```bash
# Enable debug logging
export DEBUG=1
python -m openhands.server
```

### Frontend Debugging
```bash
cd frontend
npm run dev
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
npm run build
```

### Docker
```bash
docker build -t openhands .
