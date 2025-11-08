# Building CodeAct: An AI Coding Agent That Actually Works

## Introduction

Most AI coding tools are just fancy autocomplete. We built something different: an autonomous agent that can read, edit, test, and debug code like a senior developer.

This post explains how we architected CodeAct, Forge' flagship coding agent.

## The Problem with Current AI Coding Tools

**Cursor, Copilot, and others:**
- Great at code completion
- Require constant human guidance
- Can't execute complex multi-step tasks
- No context about your full codebase

**What we wanted:**
- Fully autonomous coding (give it a task, it completes it)
- Multi-step reasoning (plan → implement → test → fix)
- Real code execution (not just suggestions)
- Safe (sandboxed, with human oversight)

## The CodeAct Paradigm

We implement the CodeAct research paper (https://arxiv.org/abs/2402.01030) which consolidates agent actions into a unified code action space.

**Key insight:** Instead of specialized actions (edit_file, run_test, debug_error), use **code as the universal interface**.

### Traditional Approach

```
Agent has 20 specialized actions:
- edit_file(path, content)
- run_test(test_name)
- install_package(name)
- create_directory(path)
- ... 16 more actions
```

**Problems:**
- Limited to predefined actions
- Can't handle edge cases
- Rigid and inflexible

### CodeAct Approach

```
Agent has 2 actions:
- run_bash(command)  # Any Linux command
- run_python(code)   # Any Python code
```

**Benefits:**
- Infinite flexibility (any bash/Python operation)
- Handles edge cases naturally
- Simpler architecture
- More powerful

## Architecture

### The ReAct Loop

```
1. Observe: Read current state
   ↓
2. Think: Reason about next action
   ↓
3. Act: Execute code (bash or Python)
   ↓
4. Observe: Get result
   ↓
5. Repeat until done
```

### Example: "Fix TypeError in main.py line 42"

```
Step 1: Read file
Bash: cat main.py
Observation: Variable 'count' used before definition

Step 2: Edit file
Bash: sed -i '40i\\    count = 0' main.py
Observation: File edited

Step 3: Test fix
Bash: python main.py
Observation: No errors, program runs successfully

Step 4: Complete
Message: "Fixed! Variable 'count' initialized to 0 on line 40"
```

## Technical Implementation

### Structure-Aware Editing

We use Tree-sitter to parse code structure:

```python
# Parse Python file
tree = parser.parse(bytes(code, "utf8"))

# Find function by name
function_node = find_function(tree, "calculate_total")

# Edit at AST level, not text level
```

**Why this matters:**
- No line number fragility (code can change)
- Semantic understanding (knows what's a class, function, import)
- Safer edits (syntax-aware)

### Sandbox Execution

Every command runs in a Docker container:

```python
# User input (untrusted)
command = "rm -rf /"  # Dangerous!

# Executed in isolated Docker container
result = docker_exec(command)
# Result: Only deletes files in container, not host
```

**Safety layers:**
1. AI risk assessment (flags high-risk commands)
2. User confirmation (for destructive operations)
3. Docker isolation (can't access host system)
4. Resource limits (CPU, memory, time)

## Performance Optimizations

### 1. Compact Prompts

**Before:** 300+ line system prompt
**After:** 166 lines (45% reduction)
**Result:** Faster responses, lower costs

### 2. Few-Shot Learning

We include 3 examples of common patterns:
- Reading and editing files
- Running tests
- Debugging errors

**Result:** Agent learns patterns, fewer mistakes

### 3. Circuit Breaker

Auto-pause after:
- 3 consecutive failures
- Same action repeated 5 times (stuck)
- High-risk action without confirmation

**Result:** Prevents runaway costs, infinite loops

## Results

**Performance (vs. competitors):**
- **Cursor:** Autocomplete only, requires guidance
- **Copilot:** Inline suggestions, no execution
- **Devin:** Autonomous but $500/month
- **CodeAct:** Autonomous AND affordable ($1-10/day)

**Typical task completion:**
- Simple bug fix: 2-3 actions, ~15 seconds
- Feature implementation: 5-10 actions, ~45 seconds  
- Complex refactoring: 10-20 actions, 1-3 minutes

## Lessons Learned

### 1. Simple is Better

We started with complex multi-agent orchestration. We simplified to single CodeAct agent for beta.

**Result:** 10x easier to debug, 5x faster to iterate, happier users.

### 2. Safety is Non-Negotiable

We added circuit breakers, risk assessment, and sandboxing after early tests showed agents could go rogue.

**Result:** 0 security incidents in beta.

### 3. Cost Tracking is Essential

Users want predictability. We show costs in real-time.

**Result:** Trust and transparency.

## Open Source

CodeAct is open source. Check it out:
- GitHub: https://github.com/yourusername/Forge
- Docs: https://docs.Forge.dev
- Try it: https://Forge.dev

## Conclusion

Building an autonomous coding agent is hard. But by focusing on simplicity (CodeAct paradigm), safety (sandboxing), and cost transparency, we created something that actually works.

Try it yourself and let us know what you build!

---

**Next in series:**
- Part 2: Supporting 200+ LLM Models - Our Provider System
- Part 3: Self-Improving Agents - The ACE Framework (post-beta)

