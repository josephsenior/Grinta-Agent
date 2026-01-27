# File Editing System Architecture

## Overview

Forge implements a **two-layer file editing architecture** that separates high-level agent operations from low-level runtime I/O. This design provides flexibility, maintainability, and production-grade reliability.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Ultimate Editor (Agent-Level)                     │
│  ─────────────────────────────────────────────────────────  │
│  • Structure-aware editing (Tree-sitter)                    │
│  • Symbol-based operations (edit by function/class name)    │
│  • Multi-file atomic refactoring                            │
│  • Syntax validation & auto-rollback                        │
│  • Language-agnostic (40+ languages)                        │
│                                                              │
│  Location: forge/agenthub/codeact_agent/tools/              │
│  Used by: CodeAct Agent                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Uses for low-level I/O
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 2: FileEditor (Runtime-Level)                        │
│  ─────────────────────────────────────────────────────────  │
│  • Basic file operations (view, edit, write)                │
│  • Atomic file writes (temp file + rename)                  │
│  • Transaction support (multi-file atomic operations)       │
│  • Error handling & validation                              │
│  • Workspace path resolution                                │
│                                                              │
│  Location: forge/runtime/utils/file_editor.py               │
│  Used by: Runtime execution, Action execution server        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Ultimate Editor (High-Level)

**Purpose:** Structure-aware code editing for AI agents

**Key Features:**
- **Tree-sitter parsing:** Understands code structure across 40+ languages
- **Symbol-based editing:** Edit by function/class name, not line numbers
- **Intelligent whitespace handling:** Auto-detects and matches file style
- **Syntax validation:** Validates before saving, auto-rollback on error
- **Multi-file refactoring:** Atomic operations across multiple files

**Usage:**
```python
from forge.agenthub.codeact_agent.tools.ultimate_editor import UltimateEditor

editor = UltimateEditor()

# Edit a function by name (not line numbers!)
result = editor.edit_function(
    file_path="/workspace/app.py",
    function_name="calculate_total",
    new_body="return sum(items) * 1.08"
)
```

**When to use:**
- Agent-level code editing operations
- Structure-aware refactoring
- Multi-file changes
- Symbol-based operations

**Documentation:** See [Ultimate File Editor Guide](../features/ultimate-file-editor.md)

### FileEditor (Low-Level)

**Purpose:** Production-grade file I/O operations for runtime execution

**Key Features:**
- **Atomic writes:** Write to temp file, then rename (prevents corruption)
- **Transaction support:** Multi-file atomic operations with rollback
- **Error handling:** Comprehensive error reporting and recovery
- **Path resolution:** Handles relative/absolute paths correctly
- **Workspace isolation:** Operates within sandboxed workspace

**Usage:**
```python
from forge.runtime.utils.file_editor import FileEditor, ToolResult

editor = FileEditor(workspace_root="/workspace")

# Basic file operations
result: ToolResult = editor(
    command="view",
    path="app.py"
)

# Atomic write
result = editor(
    command="write",
    path="config.json",
    file_text='{"key": "value"}'
)

# Transaction support
with editor.transaction():
    editor(command="write", path="file1.py", file_text="...")
    editor(command="write", path="file2.py", file_text="...")
    # All succeed or all rollback
```

**When to use:**
- Runtime file I/O operations
- Action execution server
- Low-level file manipulation
- Transaction-based multi-file operations

## Design Decisions

### Why Two Layers?

1. **Separation of Concerns**
   - Ultimate Editor: Agent intelligence (structure understanding)
   - FileEditor: Runtime reliability (I/O operations)

2. **Flexibility**
   - Agents can use Ultimate Editor for smart editing
   - Runtime can use FileEditor for reliable I/O
   - Can swap implementations independently

3. **Maintainability**
   - Clear boundaries between layers
   - Easier to test and debug
   - Independent evolution

4. **Production-Grade**
   - FileEditor handles edge cases (permissions, corruption, etc.)
   - Ultimate Editor focuses on code intelligence
   - Each layer optimized for its purpose

### Migration from External Package

**Previous:** Used `Forge_aci` package for file operations

**Current:** Custom implementation with:
- ✅ Full control over implementation
- ✅ Better integration with Forge architecture
- ✅ Production-grade features (transactions, atomic writes)
- ✅ Clear separation of concerns
- ✅ No external dependencies

**Benefits:**
- **Flexibility:** Can customize for specific needs
- **Performance:** Optimized for our use cases
- **Reliability:** Production-grade error handling
- **Maintainability:** Our code, our standards

## Integration Points

### CodeAct Agent

```python
# Agent uses Ultimate Editor for structure-aware editing
from forge.agenthub.codeact_agent.tools.ultimate_editor import UltimateEditor

editor = UltimateEditor()
result = editor.edit_function("app.py", "process_data", new_body)
```

### Runtime Execution

```python
# Runtime uses FileEditor for reliable I/O
from forge.runtime.utils.file_editor import FileEditor

editor = FileEditor(workspace_root=workspace)
result = editor(command="write", path="output.txt", file_text="...")
```

### Action Execution Server

```python
# Action execution server bridges agent actions to runtime
from forge.runtime.utils.file_editor import FileEditor

class ActionExecutor:
    def __init__(self):
        self.file_editor = FileEditor(workspace_root=self.workspace)
    
    def execute_file_edit(self, action):
        # Uses FileEditor for reliable execution
        return self.file_editor(...)
```

## File Operations Flow

### Agent-Level Edit Flow

```
1. Agent decides to edit a function
   ↓
2. Ultimate Editor parses file with Tree-sitter
   ↓
3. Finds function by symbol name
   ↓
4. Validates syntax of new code
   ↓
5. Uses FileEditor for atomic write
   ↓
6. Validates result, rolls back if needed
```

### Runtime-Level I/O Flow

```
1. Action execution server receives file operation
   ↓
2. FileEditor resolves path relative to workspace
   ↓
3. Performs atomic operation (temp file + rename)
   ↓
4. Returns ToolResult with success/error
   ↓
5. Observation generated from result
```

## Transaction Support

Both layers support transactions, but at different levels:

### Ultimate Editor Transactions

```python
# High-level: Multi-file refactoring
with editor.begin_refactoring() as refactor:
    refactor.edit_file("file1.py", new_content="...")
    refactor.edit_file("file2.py", new_content="...")
    # Commits automatically, or rolls back on error
```

### FileEditor Transactions

```python
# Low-level: Atomic multi-file I/O
with editor.transaction():
    editor(command="write", path="file1.py", file_text="...")
    editor(command="write", path="file2.py", file_text="...")
    # All succeed or all rollback
```

## Error Handling

### Ultimate Editor Errors

- **Syntax errors:** Detected before save, auto-rollback
- **Symbol not found:** Fuzzy matching suggestions
- **Validation failures:** Detailed error messages

### FileEditor Errors

- **Permission errors:** Clear error messages
- **Path resolution:** Handles edge cases
- **Write failures:** Atomic operations prevent corruption
- **Transaction failures:** Automatic rollback

## Performance Considerations

### Ultimate Editor
- **Parsing:** ~5-50ms for typical files (1000 lines)
- **Symbol location:** ~1-10ms
- **Edit operation:** ~10-100ms (includes validation)

### FileEditor
- **File read:** ~1-5ms (depends on file size)
- **Atomic write:** ~2-10ms (temp file + rename)
- **Transaction:** Minimal overhead (~1ms per file)

## Related Documentation

- [Ultimate File Editor Guide](../features/ultimate-file-editor.md)
- [CodeAct Agent Architecture](../features/codeact-agent.md)
- [Runtime Architecture](./runtime-orchestration-plan.md)
- [Tool Quick Reference](../tool-quick-reference.md)

---

**Status:** ✅ **Production-Ready**

**Last Updated:** 2025-01-27


