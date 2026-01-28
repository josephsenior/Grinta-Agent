# Recent Project Changes (January 2025)

## Codebase Organization Improvements

### 1. Agent Hub Unification ✅
**Date:** January 2025

**Change:** All agents unified into single location
- **Before:** Agents split between `backend/agenthub/` and `backend/forge/agenthub/`
- **After:** All agents consolidated in `backend/forge/agenthub/`
- **Agents:** codeact_agent, browsing_agent, readonly_agent, loc_agent, dummy_agent
- **Benefit:** Cleaner structure, no legacy path hacks, easier maintenance

### 2. Scripts Directory Reorganization ✅
**Date:** January 2025

**Change:** Organized scripts into logical subdirectories
- **Before:** All scripts in flat `backend/scripts/` directory
- **After:** Organized into:
  - `backend/scripts/database/` - Database operations
  - `backend/scripts/setup/` - Installation & configuration
  - `backend/scripts/dev/` - Development utilities
  - `backend/scripts/verify/` - Verification scripts
  - `backend/scripts/build/` - Build & code generation
- **Benefit:** Better organization, easier to find scripts, clearer purpose

### 3. Codebase Cleanup ✅
**Date:** January 2025

**Removed:**
- Debug scripts and artifacts (30+ files)
- Test cache directories (`.hypothesis/`, `.pytest_cache/`)
- Temporary files (`tmp_*.py`, `tmp_*.txt`)
- TypeScript error logs (12 files)
- Diagnostic/probe scripts (15+ files)
- Test mock directories (`MagicMock/`, `~/`)

**Updated:**
- `.gitignore` enhanced with cache patterns
- All references updated to new structure

### 4. Updated Codebase Statistics ✅
**Date:** January 2025

**Current Stats:**
- **191,955 lines** of production code (110K backend + 82K frontend)
- **541 Python files** in backend
- **763 frontend files** (TypeScript/TSX)
- **0% high-complexity functions** (industry-leading)

## Migration Notes

### Import Paths
All imports continue to work as before:
```python
from forge.agenthub import codeact_agent, browsing_agent
```

### Script Paths
Script paths have been updated:
```bash
# Before
python backend/scripts/compile_protos.py
python backend/scripts/backup_database.py

# After
python backend/scripts/build/compile_protos.py
python backend/scripts/database/backup_database.py
```

See `backend/scripts/README.md` for complete script organization.
