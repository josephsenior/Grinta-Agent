# Testing

This guide covers the testing framework and practices for Forge.

## Test Structure

Forge uses pytest for testing with the following test categories:

- **Unit tests** (`tests/unit/`): Test individual components in isolation
- **Integration tests** (`tests/integration/`): Test component interactions
- **End-to-end tests** (`tests/e2e/`): Test complete user workflows
- **Heavy tests**: Tests requiring large ML dependencies (marked with `@pytest.mark.heavy`)
- **Benchmark tests**: Performance and accuracy evaluations

## Running Tests

### Unit Tests (Fast)
```bash
# Run all unit tests
poetry run pytest backend/tests/unit/

# Run specific test file
poetry run pytest backend/tests/unit/test_agent.py

# Run with coverage
poetry run pytest --cov=forge backend/tests/unit/
```

### Integration Tests
```bash
# Run integration tests
poetry run pytest tests/integration/
```

### End-to-End Tests
```bash
# Run e2e tests
poetry run pytest backend/tests/e2e/
```

### Heavy/Benchmark Tests
```bash
# Install heavy dependencies first
poetry install --with heavy

# Run heavy tests
poetry run pytest -m heavy

# Run benchmark tests
poetry run pytest -m benchmark
```

### Quick Test Commands
```bash
# Fast unit tests only (skip heavy/integration)
make test-unit
```

## Test Configuration

### Markers
Tests use pytest markers to categorize and control execution:

- `@pytest.mark.heavy`: Requires large ML dependencies
- `@pytest.mark.integration`: Component integration tests
- `@pytest.mark.benchmark`: Performance benchmarks
- `@pytest.mark.docker`: Requires Docker
- `@pytest.mark.windows`: Windows-specific tests

### Skipping Tests
```bash
# Skip heavy tests
pytest -m "not heavy"

# Run only integration tests
pytest -m integration

# Skip Docker-dependent tests
pytest -m "not docker"
```

## Writing Tests

### Unit Test Example
```python
import pytest
from forge.agenthub.codeact_agent import CodeActAgent

def test_agent_initialization():
    agent = CodeActAgent()
    assert agent.name == "CodeAct"
    assert agent.capabilities is not None

def test_agent_action():
    agent = CodeActAgent()
    action = agent.act("print('hello')")
    assert action is not None
```

### Integration Test Example
```python
import pytest
from forge.runtime.local import LocalRuntime

@pytest.mark.integration
def test_runtime_execution():
    runtime = LocalRuntime()
    result = runtime.execute("echo 'test'")
    assert result.success
    assert "test" in result.output
```

### Mocking
```python
from unittest.mock import Mock, patch

def test_with_mock():
    with patch('Forge.llm.LLMClient') as mock_llm:
        mock_llm.generate.return_value = "mock response"
        agent = CodeActAgent()
        response = agent.think("test prompt")
        assert response == "mock response"
```

## Test Data

### Fixtures
Common test fixtures are defined in `conftest.py`:

- `config`: Default configuration
- `runtime`: Test runtime environment
- `agent`: Pre-configured agent instance

### Sample Data
Use realistic but minimal test data:
```python
@pytest.fixture
def sample_code():
    return """
def hello_world():
    print("Hello, World!")
    return True
"""
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Main branch pushes
- Scheduled nightly runs

### CI Configuration
- Unit tests: Run on every PR
- Heavy tests: Run nightly and on workflow dispatch
- Integration tests: Run on main branch

## Debugging Tests

### Common Issues

**Docker not available:**
```bash
# Check Docker status
docker --version
docker ps
```

**Heavy dependencies missing:**
```bash
# Install heavy extras
poetry install --with heavy
```

**Windows console issues:**
```bash
# Use PowerShell or cmd instead of some terminals
# Or run subset: pytest -m "not integration"
```

### Test Debugging
```bash
# Run with verbose output
pytest -v tests/unit/test_agent.py

# Debug specific test
pytest --pdb tests/unit/test_agent.py::test_specific_function

# Show print statements
pytest -s tests/unit/test_agent.py
```

## Performance Testing

### Benchmarking
```python
import pytest
import time

@pytest.mark.benchmark
def test_agent_performance(benchmark):
    agent = CodeActAgent()

    def run_task():
        return agent.act("print('benchmark')")

    result = benchmark(run_task)
    assert result is not None
```

### Profiling
```bash
# Profile test execution
pytest --profile tests/unit/
```

## Best Practices

### Test Organization
- One test file per module
- Descriptive test function names
- Arrange-Act-Assert pattern

### Test Coverage
- Aim for >80% code coverage
- Cover edge cases and error conditions
- Test both success and failure paths

### Test Maintenance
- Keep tests fast and reliable
- Update tests when refactoring code
- Remove obsolete tests

### CI/CD Integration
- Tests must pass before merge
- Use pre-commit hooks for local validation
- Monitor flaky tests and fix them
