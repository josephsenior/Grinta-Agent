# Tool Quick Reference

One-page guide to Forge's tools.

---

## File Operations

### **Create NEW File**
```python
str_replace_editor(
    command="create",
    path="/workspace/index.html",
    file_text="<!DOCTYPE html>...",
    security_risk="LOW"
)
```

### **Edit EXISTING File (by function name)**
```python
ultimate_editor(
    command="edit_function",
    file_path="/workspace/app.py",
    function_name="calculate_total",
    new_body="    return sum(items) * 1.08",
    security_risk="LOW"
)
```

### **Rename Symbol (all occurrences)**
```python
ultimate_editor(
    command="rename_symbol",
    file_path="/workspace/utils.py",
    old_name="oldName",
    new_name="newName",
    security_risk="LOW"
)
```

### **Find Symbol Location**
```python
ultimate_editor(
    command="find_symbol",
    file_path="/workspace/models.py",
    symbol_name="User",
    security_risk="LOW"
)
```

### **Replace Line Range**
```python
ultimate_editor(
    command="replace_range",
    file_path="/workspace/app.py",
    start_line=10,
    end_line=20,
    new_code="# Updated code here",
    security_risk="LOW"
)
```

---

## Command Execution

### **Run Bash Command**
```python
execute_bash(
    command="python app.py",
    timeout=30
)
```

### **Background Process**
```python
execute_bash(
    command="pnpm run dev &",
    timeout=120
)
```

### **Chained Commands**
```python
execute_bash(
    command="cd /workspace && pip install -r requirements.txt && python app.py"
)
```

---

## Task Management

### **Create Task Plan**
```python
task_tracker(
    command="plan",
    task_list=[
        {"id": "task-1", "title": "Create models", "status": "todo"},
        {"id": "task-2", "title": "Add API routes", "status": "todo"},
        {"id": "task-3", "title": "Write tests", "status": "todo"}
    ]
)
```

### **Update Task Status**
```python
task_tracker(
    command="update",
    task_id="task-1",
    status="done"
)
```

---

## Web & Browser

### **Fetch URL (Fast)**
```python
fetch(url="https://docs.python.org/3/library/asyncio.html")
# ⚡ 1-2 seconds - use this first!
```

### **Search Web**
```python
duckduckgo_search(
    query="Python asyncio best practices",
    max_results=5
)
```

### **Browser Automation (Last Resort)**
```python
browser(
    code="""
goto("http://localhost:3000")
click("button[id='login']")
fill("input[name='email']", "test@example.com")
screenshot()
"""
)
# 🐌 5-10 seconds - only for interactions!
```

---

## UI Components (shadcn-ui)

### **Search Components**
```python
search_items_in_registries(
    registries=["@shadcn"],
    query="button primary"
)
```

### **Get Component Code**
```python
view_items_in_registries(
    items=["@shadcn/button", "@shadcn/card"]
)
```

### **Get Usage Examples**
```python
get_item_examples_from_registries(
    registries=["@shadcn"],
    query="button-demo"
)
```

---

## Reasoning & Planning

### **Think Through Problem**
```python
think(
    thought="Analyzing three approaches to fix this bug: 1) Refactor class hierarchy 2) Add caching layer 3) Optimize query. Approach 2 is simplest and most effective."
)
```

---

## Security Levels

Always specify `security_risk` for operations:

- **`"LOW"`** - Safe operations (reading, creating test files)
- **`"MEDIUM"`** - Modifying code, running commands
- **`"HIGH"`** - System changes, network access, deletions

---

## Language Support (45+)

### Core
Python, JavaScript, TypeScript, Go, Rust, Java, C/C++

### JVM
Kotlin, Scala, Clojure

### .NET
C#, F#

### Scripting
Ruby, PHP, Perl, Lua, R

### Web
HTML, CSS/SCSS, Vue, Svelte

### Functional
Haskell, Elixir, Erlang, OCaml, Elm

### Systems
Zig, Nim, V, D

### Mobile
Swift, Objective-C, Dart

### Data
JSON, YAML, TOML, XML

### Shell
Bash, Zsh, Fish

### Query
SQL, GraphQL

### Other
Protocol Buffers, Markdown, LaTeX, Julia

---

## Best Practices

### ✅ DO:
- NEW file → `str_replace_editor` create
- EDIT file → `ultimate_editor` edit_function
- Simple URL → `fetch` (not browser!)
- Multi-step → Use `task_tracker`
- 2-3 tool calls max for simple tasks

### ❌ DON'T:
- Edit by line numbers (use function names!)
- Use browser for simple content (use fetch!)
- Explore unnecessarily (be decisive!)
- Use ultimate_editor on non-existent files
- Repeat failed approaches (try alternatives!)

---

## Common Workflows

### Create Landing Page (2 calls)
```python
1. str_replace_editor(command="create", path="/workspace/index.html", ...)
2. execute_bash("python -m http.server 8000 &")
✅ Done! App auto-navigates to browser
```

### Build React App (3-4 calls)
```python
1. execute_bash("npm create vite@latest app -- --template react")
2. execute_bash("cd app && pnpm install")
3. str_replace_editor(command="create", path="/workspace/app/src/App.jsx", ...)
4. execute_bash("cd app && pnpm run dev &")
✅ Done! Dev server auto-navigates
```

### Debug Error (2-3 calls)
```python
1. execute_bash("cat error.log | grep -A 5 ERROR")
2. ultimate_editor(command="edit_function", ...)  # Fix
3. execute_bash("python app.py")  # Verify
✅ Done!
```

### Refactor Function (1-2 calls)
```python
1. ultimate_editor(command="find_symbol", ...)  # Locate (optional)
2. ultimate_editor(command="edit_function", ...)  # Edit
✅ Done! No verification needed if confident
```

---

## Speed Optimization

**Bolt.new-style execution:**
- Simple tasks: 2-3 calls MAX
- No exploratory `ls`, `cat`, `find` unless necessary
- Trust yourself, act decisively
- Create → Serve → Done!

---

## Error Recovery

If operation fails:
1. **Read error carefully** - extract actual problem
2. **Try alternative** - different tool/approach/path
3. **Max 3 attempts** - then ask user with context
4. **Never repeat** same failing approach

---

## See Also

- [Ultimate Editor](./ultimate-editor.md) - Detailed examples
- [Production Setup](./production-setup.md) - Deployment guide
- [Forge Improvements](./forge-improvements.md) - Recent changes

