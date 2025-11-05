# Contributing to OpenHands

Thank you for your interest in contributing to OpenHands! This guide will help you get started.

## Quick Start

1. **Fork the repository**
2. **Clone your fork:** `git clone https://github.com/YOUR_USERNAME/openhands.git`
3. **Create a branch:** `git checkout -b feature/your-feature-name`
4. **Make changes** and commit
5. **Push to your fork:** `git push origin feature/your-feature-name`
6. **Open a Pull Request**

## Development Setup

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
poetry run python -m openhands.server.listen
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Code Style

### Python

- **Formatter:** Black (automatically formats code)
- **Linter:** Ruff (fast linter)
- **Type Checker:** mypy (static type checking)
- **Style Guide:** PEP 8

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy openhands
```

### TypeScript

- **Formatter:** Prettier
- **Linter:** ESLint
- **Style:** Airbnb + custom rules

```bash
cd frontend
npm run lint
npm run format
```

## Coding Standards

### Python

```python
# Good: Type hints, docstrings, clear names
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
        
    Example:
        >>> calculate_fibonacci(5)
        5
    """
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
```

### TypeScript/React

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
npm run test
```

### Writing Tests

```python
# Python example
def test_fibonacci():
    assert calculate_fibonacci(5) == 5
    assert calculate_fibonacci(10) == 55
```

```typescript
// TypeScript example
import { render, screen } from '@testing-library/react';

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
});
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guide
- [ ] Tests pass locally
- [ ] New features have tests
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear

### PR Guidelines

**Good PR Title:**
```
Add support for Grok 4 Fast model
Fix file edit bug in CodeAct agent
Improve error messages for rate limiting
```

**Bad PR Title:**
```
Update
Fix bug
Changes
```

**PR Description Should Include:**
- What changed and why
- How to test the changes
- Screenshots (if UI changes)
- Related issues (Fixes #123)

### PR Template

When you open a PR, please include:

```markdown
## Description
Brief description of what this PR does.

## Changes
- Added X
- Fixed Y
- Improved Z

## Testing
How to test these changes

## Screenshots (if applicable)
[Add screenshots here]

## Related Issues
Fixes #123
Related to #456
```

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
- Research implementations (ACE, MetaSOP)

## Adding a New LLM Provider

See `docs/examples/02_custom_provider.py` for a complete guide.

**Quick version:**

1. Add provider config to `openhands/core/config/provider_config.py`
2. Add model patterns to `openhands/llm/model_features.py` (if needed)
3. Add models to `openhands/utils/llm.py` (if needed)
4. Test with your API key
5. Submit PR with documentation

## Documentation

When adding features, please update:

- **Code:** Add docstrings to all public functions/classes
- **README:** Update relevant README files
- **Examples:** Add example usage if applicable
- **API Docs:** Update OpenAPI examples if API changes

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

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Open a GitHub Issue
- **Features:** Open a GitHub Issue with [Feature Request] tag
- **Security:** Email security@openhands.dev (do NOT open public issue)

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md). We're committed to providing a welcoming and inclusive environment.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README contributors section
- Release notes
- Monthly contributor highlights

Thank you for contributing! 🚀

