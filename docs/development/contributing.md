# Contributing to Forge

Thank you for your interest in contributing to Forge! This guide will help you get started.

## Quick Start

1. **Fork the repository**
2. **Clone your fork:** `git clone https://github.com/YOUR_USERNAME/Forge.git`
3. **Create a branch:** `git checkout -b feature/your-feature-name`
4. **Make changes** and commit
5. **Push to your fork:** `git push origin feature/your-feature-name`
6. **Open a Pull Request**

## Development Setup

See [Development Guide](./development.md) for detailed setup instructions.

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker
- Git

### Backend Setup

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Add your API keys to .env

# Run backend
poetry run python -m forge.server.listen
```

### Frontend Setup

```bash
cd frontend
pnpm install
pnpm run dev:local  # Fastest for day-to-day development
# or
pnpm run dev  # React Router CLI (for typegen)
```

**Note:** On Windows, if you see "React Router Vite plugin not found", use `pnpm run dev:local` as a fallback.

## Code Style

### Python

- **Formatter:** Black
- **Linter:** Ruff
- **Type Checker:** mypy
- **Style Guide:** PEP 8

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy forge
```

### TypeScript

- **Formatter:** Prettier
- **Linter:** ESLint
- **Style:** Airbnb + custom rules

```bash
cd frontend
pnpm run lint
pnpm run format
```

## Code Quality Standards

**Forge maintains industry-leading code quality:**
- ✅ Backend average complexity: **3.06** (A-rated) across 8,100 functions/methods
- ✅ Frontend average complexity: **2.21** (A-rated)
- ✅ **0% high-complexity functions**
- ✅ **85.8%** A-rated functions (complexity 1-5)
- ✅ **14.2%** B-rated functions (complexity 6-10)

**Before submitting PR:**
```bash
# Check complexity
radon cc forge/path/to/your/file.py -s

# Target: A-rated (complexity 1-5)
# Acceptable: B-rated (complexity 6-10)
# Requires refactoring: C+ (complexity > 10)
```

See [Code Quality Guide](./code-quality.md) for detailed guidelines.

### Code Examples

**Python:**
```python
# Good: Type hints, docstrings, clear names, low complexity
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
```

**TypeScript/React:**
```typescript
// Good: Props interface, functional component, TypeScript
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
}
```

## Testing

### Running Tests

```bash
# Python tests
poetry run pytest

# Frontend tests  
cd frontend
pnpm run test
```

See [Testing Guide](./testing.md) for detailed testing instructions.

## Pull Request Process

### Before Submitting

- [ ] Code follows style guide
- [ ] Tests pass locally
- [ ] New features have tests
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear

### PR Guidelines

**PR Title Format:**
```
feat(llm): add support for Grok 4 Fast model
fix(agent): fix file edit bug in CodeAct agent
docs(readme): improve error messages for rate limiting
```

**PR Description Should Include:**
- What changed and why
- How to test the changes
- Screenshots (if UI changes)
- Related issues (Fixes #123)

## Areas to Contribute

### 🟢 Good First Issues

- Documentation improvements
- Bug fixes in existing features
- UI/UX enhancements
- Test coverage improvements

### 🟡 Intermediate

- New LLM provider support
- Performance optimizations
- Security improvements
- New agent actions/tools

### 🔴 Advanced

- Agent algorithm improvements
- Runtime architecture changes
- Scaling optimizations
- Research implementations

## Adding a New LLM Provider

1. Add provider config to `forge/core/config/provider_config.py`
2. Add model patterns to `forge/llm/model_features.py` (if needed)
3. Test with your API key
4. Submit PR with documentation

See [examples](./examples/README.md) for complete guides.

## Commit Messages

**Format:**
```
type(scope): brief description

Longer description if needed.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Add/update tests
- `chore`: Maintenance (dependencies, build, etc.)

**Examples:**
```
feat(llm): add support for Grok 4 Fast model
fix(agent): prevent infinite loop in stuck detection
docs(readme): add getting started guide
chore(deps): upgrade axios to fix security vulnerability
```

## Running Heavy / Integration Tests

Some tests require large ML / native dependencies and are marked as `heavy`, `integration`, or `benchmark`. These are skipped by default on local runs and in PR CI jobs.

**Local (recommended):**
```bash
# Install heavy extras
poetry install --with heavy

# Run heavy/integration tests
poetry run pytest -m "heavy or integration or benchmark" -vv
```

**CI behavior:**
- By default, PR CI runs skip heavy tests
- A `heavy-tests` job runs on `workflow_dispatch`, scheduled runs, or on `main`

## Quick Test Targets (Makefile)

```bash
# Run all unit tests (fast)
make test-unit
```

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Open a GitHub Issue
- **Features:** Open a GitHub Issue with [Feature Request] tag
- **Security:** Email security@forge.dev (do NOT open public issue)

## Code of Conduct

Please read our [Code of Conduct](./CODE_OF_CONDUCT.md). We're committed to providing a welcoming and inclusive environment.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing! 🚀
