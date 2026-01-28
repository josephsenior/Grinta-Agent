# Development Scripts

Development utilities, test helpers, and code quality tools.

## Scripts

- **`dev_server.py`** - Development server helper
- **`auto_fix_d205.py`** - Auto-fix D205 docstring issues
- **`clean_pycache.sh`** - Clean Python cache files
- **`coverage_inspect.py`** - Inspect test coverage
- **`coverage_probe.py`** - Probe coverage data
- **`test_dispatch.py`** - Test dispatch functionality
- **`test_user_persistence.py`** - Test user persistence
- **`run-tests-windows.ps1`** - Run tests on Windows

## Usage

```bash
# Clean cache
bash backend/scripts/dev/clean_pycache.sh

# Run tests on Windows
.\backend\scripts\dev\run-tests-windows.ps1

# Inspect coverage
python backend/scripts/dev/coverage_inspect.py
```
