# Backend

This folder contains all backend-related code and resources for the Forge project.

## Structure

```
backend/
├── forge/          # Main Python package (imported as `forge`)
├── tests/          # Test suite
├── scripts/        # Backend utility scripts
├── tools/          # Development tools
└── conftest.py     # Pytest configuration
```

## Package Structure

The `forge/` package is located at `backend/forge/` but is still imported as `forge` (not `backend.forge`). This is configured in `pyproject.toml` to maintain backward compatibility with existing imports.

## Running Tests

From the project root:
```bash
poetry run pytest backend/tests
```

Or use the Makefile:
```bash
make test-unit
```

## Scripts

Backend scripts are located in `backend/scripts/`. Run them from the project root:
```bash
python backend/scripts/compile_protos.py
```

## Development

All Python imports should continue to use `from forge.` - the package structure is abstracted by Poetry's package configuration.
