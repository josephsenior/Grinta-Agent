# Ultimate Editor Guide

Structure-aware code editing powered by Tree-sitter.

## Why Use This

**Problem with line-based editing:**
- Breaks when file changes
- Fragile line number dependencies
- No code structure understanding

**Ultimate Editor solution:**
- Edit by function/class name (not line numbers)
- Immune to whitespace changes
- Syntax validation before saving
- Works for 45+ languages

## Supported Languages (45+)

**Core:** Python, JavaScript, TypeScript, Go, Rust, Java, C/C++

**JVM:** Kotlin, Scala, Clojure

**.NET:** C#, F#

**Scripting:** Ruby, PHP, Perl, Lua, R

**Web:** HTML, CSS/SCSS, Vue, Svelte, GraphQL

**Functional:** Haskell, Elixir, Erlang, OCaml, Elm

**Systems:** Zig, Nim, V, D

**Mobile:** Swift, Objective-C, Dart

**Data:** JSON, YAML, TOML, XML, SQL

**Shell:** Bash, Zsh, Fish

**Other:** Protocol Buffers, Markdown, LaTeX, Julia

## Commands

### Edit Function
```python
ultimate_editor(
    command="edit_function",
    file_path="/workspace/billing.py",
    function_name="calculate_total",
    new_body="    return sum(items) * 1.08",
    security_risk="LOW"
)
```

### Rename Symbol
```python
ultimate_editor(
    command="rename_symbol",
    file_path="/workspace/utils.py",
    old_name="oldName",
    new_name="newName",
    security_risk="LOW"
)
```

### Find Symbol
```python
ultimate_editor(
    command="find_symbol",
    file_path="/workspace/models.py",
    symbol_name="User",
    security_risk="LOW"
)
```

### Replace Line Range
```python
ultimate_editor(
    command="replace_range",
    file_path="/workspace/app.py",
    start_line=10,
    end_line=20,
    new_code="# Updated code",
    security_risk="LOW"
)
```

### Normalize Indentation
```python
ultimate_editor(
    command="normalize_indent",
    file_path="/workspace/messy.py",
    security_risk="LOW"
)
```

## Examples

### Python - Add Tax
```python
ultimate_editor(
    command="edit_function",
    file_path="/workspace/billing.py",
    function_name="calculate_total",
    new_body="""    subtotal = sum(item.price for item in items)
    tax = subtotal * 0.08
    return subtotal + tax""",
    security_risk="LOW"
)
```

### JavaScript - Async Refactor
```python
ultimate_editor(
    command="edit_function",
    file_path="/workspace/api.js",
    function_name="fetchUser",
    new_body="""  const response = await fetch(`/api/users/${id}`);
  return await response.json();""",
    security_risk="LOW"
)
```

### Go - Error Handling
```python
ultimate_editor(
    command="edit_function",
    file_path="/workspace/handler.go",
    function_name="ProcessRequest",
    new_body="""    if err := validate(req); err != nil {
        return fmt.Errorf("validation failed: %w", err)
    }
    return process(req)""",
    security_risk="LOW"
)
```

## Best Practices

**DO:**
- Use `edit_function` for code changes
- Use `find_symbol` first if unsure
- Trust auto-indentation
- Check error messages (fuzzy matching suggestions)

**DON'T:**
- Use on non-existent files (use `str_replace_editor` create instead)
- Edit by line numbers when you can use function names
- Manually format indentation

## Troubleshooting

**"Tree-sitter not available"**
```bash
pip install tree-sitter tree-sitter-language-pack
```

**"Function not found"**
- Check spelling (error suggests corrections)
- Verify file path
- Use `find_symbol` to locate it

**"Language not supported"**
- Check file extension is in supported list
- Add to `LANGUAGE_EXTENSIONS` if needed

## Implementation

**File:** `Forge/agenthub/codeact_agent/tools/universal_editor.py`

**Key classes:**
- `UniversalEditor` - Main editor interface
- `UltimateEditor` - High-level unified API
- `WhitespaceHandler` - Indentation normalization
- `AtomicRefactor` - Multi-file transactions

## See Also

- [Tool Quick Reference](./tool-quick-reference.md)
- [Forge Improvements](./forge-improvements.md)
- [Production Setup](./production-setup.md)

