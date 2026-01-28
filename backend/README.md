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

Backend scripts are organized in `backend/scripts/` subdirectories:

- **`database/`** - Database setup, backup, and query scripts
- **`setup/`** - Installation and configuration scripts
- **`dev/`** - Development utilities and test helpers
- **`verify/`** - Verification and check scripts
- **`build/`** - Build and code generation scripts
- **`mcp/`** - MCP-related scripts

Run them from the project root:
```bash
python backend/scripts/build/compile_protos.py
python backend/scripts/database/setup_database.py
```

## Development

All Python imports should continue to use `from forge.` - the package structure is abstracted by Poetry's package configuration.
