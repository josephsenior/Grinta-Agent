# Security & Robustness Enhancements

## Overview

This document describes the security and robustness enhancements implemented in Forge, including sentinel objects, type-safe wrappers, and defensive programming patterns.

**Status:** ✅ **Production-Ready**  
**Last Updated:** 2025-01-27

> **Note:** This document covers the foundational security patterns. For recent security enhancements (request limits, SQL injection blocking, resource limits, timeouts), see [Additional Security Enhancements](./additional-security-enhancements.md).

## Design Philosophy

### Principles

1. **Explicit over Implicit**: Use sentinel objects to distinguish states
2. **Fail Fast**: Validate inputs early and clearly
3. **Type Safety**: Runtime validation for critical types
4. **Security Boundaries**: Enforce boundaries at every layer
5. **Defensive Programming**: Assume inputs are malicious until proven safe

## Sentinel Objects

### Problem

Python's `None` is ambiguous:
- Does `None` mean "not set" or "explicitly set to None"?
- Hard to distinguish between missing values and empty values
- Leads to bugs where `None` checks are incorrect

### Solution

**Sentinel objects** are special marker objects that represent distinct states:

```python
from forge.core.security import MISSING, NOT_SET, is_missing, is_set

# Before (ambiguous):
def process(value: str | None = None):
    if value is None:  # Is this "not set" or "explicitly None"?
        ...

# After (explicit):
def process(value: str | None | Sentinel = MISSING):
    if is_missing(value):  # Clearly "not set"
        ...
    elif value is None:  # Clearly "explicitly None"
        ...
    else:  # Has actual value
        ...
```

### Available Sentinels

- **`MISSING`**: Value was never set (default state)
- **`NOT_SET`**: Value was explicitly not set (different from MISSING)

### Usage Examples

```python
from forge.core.security import MISSING, default_if_missing, coalesce

# Default value handling
value = default_if_missing(user_input, "default")

# Coalesce multiple values
result = coalesce(MISSING, None, "actual_value")  # Returns "actual_value"

# Explicit state checking
if is_missing(config_value):
    # Handle missing configuration
    ...
```

## Type-Safe Wrappers

### NonEmptyString

Prevents empty string bugs:

```python
from forge.core.security import NonEmptyString

# Validates at creation
name = NonEmptyString.validate("hello")  # ✅ OK
name = NonEmptyString.validate("")  # ❌ ValueError

# Use in function signatures
def create_user(name: NonEmptyString) -> User:
    # Guaranteed to be non-empty
    ...
```

### PositiveInt

Ensures positive integers:

```python
from forge.core.security import PositiveInt

count = PositiveInt.validate(5)  # ✅ OK
count = PositiveInt.validate(-1)  # ❌ ValueError
count = PositiveInt.validate(0)  # ❌ ValueError
```

### SafeList & SafeDict

Safe collection access:

```python
from forge.core.security import SafeList, SafeDict

# Safe list access
items = SafeList([1, 2, 3])
value = items.safe_get(10, default=0)  # Returns 0 instead of IndexError

# Safe dict access
data = SafeDict({"key": "value"})
value = data.safe_get("missing", default="default")  # Returns "default"
required = data.require("key")  # Raises KeyError if missing
```

## Path Validation

### Problem

File path operations are a major security risk:
- Directory traversal attacks (`../../../etc/passwd`)
- Path injection
- Workspace boundary violations

### Solution

**SafePath** and **PathValidator** provide production-grade path validation:

```python
from forge.core.security import SafePath, PathValidator

# Create validator
validator = PathValidator(workspace_root="/workspace")

# Validate path
safe_path = validator.validate("app.py", must_exist=True)

# Use safe path
content = safe_path.path.read_text()  # Guaranteed safe
relative = safe_path.relative_to_workspace()  # "app.py"
```

### Security Features

1. **Traversal Prevention**: Blocks `..`, `../`, encoded variants
2. **Boundary Enforcement**: Ensures paths stay within workspace
3. **Length Limits**: Prevents path length attacks
4. **Character Validation**: Blocks dangerous characters
5. **Depth Limits**: Prevents deep nesting attacks

### Validation Rules

```python
# ✅ Allowed
"app.py"
"src/utils/helper.py"
"config.json"

# ❌ Blocked
"../etc/passwd"  # Traversal
"/absolute/path"  # Outside workspace (if relative required)
"file\x00name"  # Null bytes
"file<script>"  # Dangerous characters
```

## Integration Points

### FileEditor Enhancement

```python
from forge.core.security import SafePath, MISSING

class FileEditor:
    def __call__(
        self,
        *,
        command: str,
        path: str,
        file_text: str | Sentinel = MISSING,  # Use sentinel instead of None
        ...
    ) -> ToolResult:
        # Validate path
        safe_path = SafePath.validate(path, workspace_root=str(self.workspace_root))
        
        # Check if file_text was provided
        if is_missing(file_text):
            # Handle missing file_text
            ...
        elif file_text is None:
            # Handle explicit None
            ...
        else:
            # Use file_text
            ...
```

### Runtime Path Handling

```python
from forge.core.security import PathValidator

class DockerRuntime:
    def __init__(self, ...):
        self.path_validator = PathValidator(
            workspace_root=self.config.workspace_mount_path_in_sandbox
        )
    
    def _resolve_path(self, path: str) -> SafePath:
        return self.path_validator.validate(path, must_be_relative=True)
```

### API Input Validation

```python
from forge.core.security import NonEmptyString, validate_non_empty_string

@router.post("/api/files")
async def create_file(
    filename: str,
    content: str,
):
    # Validate inputs
    safe_filename = NonEmptyString.validate(filename)
    safe_content = validate_non_empty_string(content, name="content")
    
    # Use validated inputs
    ...
```

## Benefits

### 1. Bug Prevention

**Before:**
```python
def process(value: str | None = None):
    if value:  # Bug: empty string is falsy!
        ...
```

**After:**
```python
def process(value: NonEmptyString | Sentinel = MISSING):
    if is_missing(value):
        # Handle missing
    else:
        # Guaranteed non-empty
        ...
```

### 2. Security

**Before:**
```python
file_path = user_input  # Dangerous!
with open(file_path) as f:  # Path traversal possible
    ...
```

**After:**
```python
safe_path = SafePath.validate(user_input, workspace_root="/workspace")
with open(safe_path.path) as f:  # Guaranteed safe
    ...
```

### 3. Clarity

**Before:**
```python
if value is None:  # What does this mean?
    ...
```

**After:**
```python
if is_missing(value):  # Clear: value was never set
    ...
elif value is None:  # Clear: explicitly None
    ...
```

## Migration Guide

### Step 1: Add Sentinels to Optional Parameters

```python
# Before
def process(value: str | None = None):
    if value is None:
        return "default"

# After
from forge.core.security import MISSING, is_missing

def process(value: str | None | Sentinel = MISSING):
    if is_missing(value):
        return "default"
    if value is None:
        return "explicit_none"
    return value
```

### Step 2: Use Type-Safe Wrappers

```python
# Before
def create_user(name: str):
    if not name:
        raise ValueError("Name required")

# After
from forge.core.security import NonEmptyString

def create_user(name: NonEmptyString):
    # Guaranteed non-empty
    ...
```

### Step 3: Validate Paths

```python
# Before
file_path = Path(user_input)

# After
from forge.core.security import SafePath

safe_path = SafePath.validate(user_input, workspace_root="/workspace")
file_path = safe_path.path
```

## Performance Considerations

- **Sentinel Objects**: Zero overhead (singleton objects)
- **Type Wrappers**: Minimal overhead (validation at creation)
- **Path Validation**: ~0.1-1ms per path (acceptable for security)

## Best Practices

1. **Use sentinels for optional parameters** that need to distinguish "not set" from "None"
2. **Validate paths early** in the request pipeline
3. **Use type-safe wrappers** for critical parameters
4. **Fail fast** with clear error messages
5. **Document sentinel usage** in function docstrings

## Storage Layer Integration

### LocalFileStore

Enhanced with SafePath validation for all path operations:

```python
from forge.core.security.path_validation import SafePath

class LocalFileStore(FileStore):
    def get_full_path(self, path: str) -> str:
        # Validates paths against storage root boundaries
        safe_path = SafePath.validate(
            path,
            workspace_root=self.root,
            must_be_relative=True,
        )
        return str(safe_path.path)
```

### FileUserStore

Storage path initialization with validation:

```python
def __init__(self, storage_path: str | None = None):
    # Validates storage path for security
    safe_path = SafePath.validate(
        storage_path,
        workspace_root=os.getcwd(),
        must_be_relative=False,  # Storage paths can be absolute
    )
    self.storage_path = safe_path.path
```

## Exception Handling

### PathValidationError

Added to core exceptions for consistent error handling:

```python
from forge.core.exceptions import PathValidationError

try:
    safe_path = SafePath.validate(path, workspace_root="/workspace")
except PathValidationError as e:
    # Handle path validation failure
    logger.error(f"Path validation failed: {e.message}, path: {e.path}")
```

## Complete Integration Summary

### ✅ Core Framework
- Sentinel objects (`MISSING`, `NOT_SET`)
- Type-safe wrappers (`NonEmptyString`, `PositiveInt`, `SafeList`, `SafeDict`)
- Enhanced path validation (`SafePath`, `PathValidator`)
- Comprehensive documentation

### ✅ Runtime Layer
- FileEditor with sentinels and SafePath
- Action execution server with path validation
- CLI runtime with enhanced filename sanitization

### ✅ API Layer
- File routes with type-safe validation
- Auth routes with enhanced input validation
- Upload endpoints with security checks

### ✅ Configuration Layer
- MCP config validation with type-safe wrappers
- Provider config with enhanced API key validation
- Configuration models with validation

### ✅ Storage Layer
- LocalFileStore with SafePath validation
- FileUserStore with path security
- All storage operations protected

### ✅ Exception Handling
- PathValidationError in core exceptions
- Consistent error messages
- Better error classification

## Related Documentation

- [File Editing System](./file-editing-system.md)
- [Security Policy](../security.md)
- [Input Validation](../server/utils/input_validation.py)
- [Docker Volumes Migration](./docker-volumes-migration.md)

---

**Status:** ✅ **Production-Ready - Complete Integration**
