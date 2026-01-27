# Migration Notes: File Editing System

## Overview

This document describes the migration from external `Forge_aci` package to custom Forge implementations.

## Migration Summary

### What Changed

**Before:**
- Used `Forge_aci` package for file editing operations
- Mixed concerns: structure-aware editing and low-level I/O in one package
- External dependency with limited customization

**After:**
- **Ultimate Editor:** Custom structure-aware editing (agent-level)
- **FileEditor:** Custom low-level file I/O (runtime-level)
- Clear separation of concerns
- Full control and customization

### Key Improvements

1. **Architectural Clarity**
   - Two-layer design: agent-level vs runtime-level
   - Clear boundaries and responsibilities
   - Better integration with Forge architecture

2. **Production Features**
   - Transaction support for multi-file operations
   - Atomic file writes (temp file + rename)
   - Incremental code indexing
   - Linter result caching
   - Binary file detection in diffs
   - Import/export tracking

3. **Maintainability**
   - Our code, our standards
   - Easier to debug and extend
   - No external dependency management

4. **Branding**
   - Removed all "OH" (Forge) prefixes
   - Consistent "Forge" branding throughout
   - Clearer naming (`FileEditor` vs `OHEditor`)

## Code Changes

### Class Renames

```python
# Before
from Forge_aci.editor.editor import OHEditor
editor = OHEditor()

# After
from forge.runtime.utils.file_editor import FileEditor
editor = FileEditor()
```

### Enum Changes

```python
# Before
FileEditSource.OH_ACI
FileReadSource.OH_ACI

# After
FileEditSource.FILE_EDITOR
FileReadSource.FILE_EDITOR
```

### Socket.IO Events

```javascript
// Before
socket.on('oh_event', (data) => { ... });
socket.emit('oh_user_action', payload);

// After
socket.on('forge_event', (data) => { ... });
socket.emit('forge_user_action', payload);
```

### Environment Variables

```bash
# Before
OH_RUNTIME_RUNTIME_IMAGE_REPO=...
OH_INTERPRETER_PATH=...

# After
FORGE_RUNTIME_IMAGE_REPO=...
FORGE_INTERPRETER_PATH=...
```

## Migration Checklist

- [x] Remove `Forge_aci` dependency from `pyproject.toml`
- [x] Implement `FileEditor` class
- [x] Implement diff generation utilities
- [x] Implement linter with caching
- [x] Implement code indexing with incremental updates
- [x] Update all imports and references
- [x] Update enum values (`OH_ACI` → `FILE_EDITOR`)
- [x] Update Socket.IO event names
- [x] Update environment variables
- [x] Update version tags (`oh_v*` → `forge_v*`)
- [x] Remove CLI alias `oh` (keep only `Forge`)
- [x] Update all test files
- [x] Update documentation

## Breaking Changes

### Frontend Updates Required

**Socket.IO Events:**
- `oh_event` → `forge_event`
- `oh_user_action` → `forge_user_action`
- `oh_action` → `forge_action`

**Action:** Update frontend Socket.IO event listeners to use new event names.

### Environment Variables

**Runtime Configuration:**
- `OH_RUNTIME_RUNTIME_IMAGE_REPO` → `FORGE_RUNTIME_IMAGE_REPO`
- `OH_INTERPRETER_PATH` → `FORGE_INTERPRETER_PATH`

**Action:** Update any scripts or configurations using these variables.

### Docker Image Tags

**Image Naming:**
- Tags now use `forge_v*` prefix instead of `oh_v*`

**Action:** Update any hardcoded image tags or references.

## Testing

All existing tests have been updated to use the new naming:
- ✅ Unit tests updated
- ✅ Integration tests updated
- ✅ Test data files updated
- ✅ Mock objects updated

## Rollback Plan

If issues arise, the migration can be rolled back by:
1. Re-adding `Forge_aci` dependency
2. Reverting import changes
3. Reverting enum values
4. Reverting Socket.IO event names

However, this is **not recommended** as the new implementation provides better architecture and features.

## Related Documentation

- [File Editing System Architecture](./file-editing-system.md)
- [Ultimate File Editor Guide](../features/ultimate-file-editor.md)
- [Changelog](../changelog.md)

---

**Migration Date:** 2025-01-27  
**Status:** ✅ Complete


