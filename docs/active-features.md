# Active Features

Current production configuration for Forge.

## Core Features (Active)

### ✅ Ultimate Editor
**Status:** ENABLED  
**Config:** `enable_ultimate_editor = true`  
**What it does:** Structure-aware editing with Tree-sitter (45+ languages)  
**Why important:** Competitive moat - edit by function name, not line numbers

### ✅ Vector Memory
**Status:** ENABLED  
**Config:** `enable_vector_memory = true`  
**What it does:** Persistent semantic memory with 92% accuracy  
**Stack:** ConversationMemory → EnhancedVectorStore → ChromaDB/Qdrant  
**Files:** `conversation_memory.py`, `enhanced_vector_store.py`, `cloud_vector_store.py`

### ✅ Hybrid Retrieval
**Status:** ENABLED  
**Config:** `enable_hybrid_retrieval = true`  
**What it does:** Vector embeddings + BM25 lexical + cross-encoder re-ranking  
**Why important:** Better context retrieval than basic vector search

### ✅ Browser Automation
**Status:** ENABLED  
**Config:** `enable_browsing = true`  
**What it does:** Playwright-based browser automation  
**When used:** Form interactions, JS-heavy pages, screenshots

### ✅ Command Execution
**Status:** ENABLED  
**Config:** `enable_cmd = true`  
**What it does:** Execute bash/PowerShell commands  
**Why important:** Core functionality for file operations, server running

### ✅ Think Tool
**Status:** ENABLED  
**Config:** `enable_think = true`  
**What it does:** Explicit reasoning for complex problems  
**When used:** Multi-step planning, debugging, architecture decisions

### ✅ Internal Task Tracker
**Status:** ENABLED  
**Config:** `enable_internal_task_tracker = true`  
**What it does:** Structured task management for complex workflows  
**When used:** Multi-phase projects (3+ steps)

### ✅ Auto-Lint
**Status:** ENABLED  
**Config:** `enable_auto_lint = true`  
**What it does:** Automatic syntax validation before saving  
**Why important:** Prevents broken code

### ✅ Self-Remediation
**Status:** ENABLED  
**Config:** `enable_self_remediation = true`  
**What it does:** Auto-retry errors with different approaches  
**When used:** Recoverable failures

### ✅ MCP Integration
**Status:** ENABLED  
**Config:** `enable_mcp = true`  
**Servers active:**
- shadcn-ui (UI components)
- Fetch (HTTP requests)
- DuckDuckGo (web search)
- Playwright (browser automation)

---

## Disabled Features

### ❌ LLM-Based Editor
**Status:** DISABLED  
**Config:** `enable_llm_editor = false`  
**Why:** Ultimate Editor is better (structure-aware vs LLM-based)

### ❌ Jupyter
**Status:** DISABLED  
**Config:** `enable_jupyter = false`  
**Why:** Not needed for current use cases

### ❌ Condensation Request
**Status:** DISABLED  
**Config:** `enable_condensation_request = false`  
**Why:** Memory system handles context better

### ❌ Micro-Iterations
**Status:** DISABLED  
**Config:** `enable_micro_iterations = false`  
**Why:** Experimental feature, not production-ready

---

## Agent Modes

### Current Mode: Simple
**Config:** `agent_mode = "simple"`  
**What it means:** Fast autonomous execution (bolt.new style)  
**Alternative:** `"enterprise"` for MetaSOP multi-role orchestration

### System Prompt
**Active:** `system_prompt_forge.j2` (166 lines, optimized)  
**Location:** `Forge/agenthub/codeact_agent/prompts/`

---

## LLM Configuration

### Primary Model
**Model:** `gpt-4o-mini`  
**Temperature:** 0.1 (deterministic)  
**Timeout:** 120 seconds  
**Max tokens:** 4096  
**Features:** Caching enabled, vision disabled

### Heavy Model (Planning)
**Model:** `gemini-2.5-pro`  
**When used:** Complex planning, finalization  
**Temperature:** 0.1  
**Timeout:** 180 seconds

---

## MCP Servers (All Active)

### 1. shadcn-ui
**Purpose:** UI components (React/Vue/Svelte)  
**Speed:** ~100ms cached, ~2s first fetch  
**Resource:** 50MB RAM  
**When used:** Building UIs, dashboards, forms

### 2. Fetch
**Purpose:** HTTP requests + HTML→markdown  
**Speed:** 1-2 seconds  
**Resource:** 10MB RAM  
**When used:** Documentation, GitHub files, articles (Priority #1)

### 3. DuckDuckGo
**Purpose:** Web search for discovery  
**Speed:** 2-3 seconds  
**Resource:** 100MB RAM  
**When used:** Finding URLs, researching, latest info

### 4. Playwright
**Purpose:** Browser automation  
**Speed:** 5-10 seconds (heavy)  
**Resource:** 500MB RAM  
**When used:** Form interactions, login, JS-heavy pages (last resort)

---

## Advanced Features (Active)

### Checkpoints
**Status:** Configurable per autonomy level  
**What it does:** Snapshot agent state for rollback  
**When enabled:** Risky operations can be undone

### History Truncation
**Status:** ENABLED  
**Config:** `enable_history_truncation = true`  
**What it does:** Manages context window size

### Prompt Extensions
**Status:** ENABLED  
**Config:** `enable_prompt_extensions = true`  
**What it does:** Dynamic prompt injection based on context

---

## Feature Status Summary

| Feature | Status | Production Ready | Competitive Advantage |
|---------|--------|------------------|----------------------|
| Ultimate Editor | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐⭐⭐ |
| Vector Memory | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐⭐ |
| Hybrid Retrieval | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐⭐ |
| Atomic Refactor | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐⭐⭐ |
| Browser Auto | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐ |
| Task Tracker | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐ |
| Auto-Lint | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐ |
| Self-Remediation | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐ |
| MCP Servers | ✅ ACTIVE | ✅ Yes | ⭐⭐⭐⭐ |
| LLM Editor | ❌ DISABLED | ⚠️ Experimental | - |
| Jupyter | ❌ DISABLED | ✅ Yes | ⭐⭐ |
| Micro-Iterations | ❌ DISABLED | ❌ Experimental | - |

---

## Experimental/Unused Features

**These exist in code but are not active in production:**

### Prompt Optimization System
**Location:** `Forge/prompt_optimization/`  
**Status:** Unclear if used  
**Purpose:** Real-time prompt evolution and tool optimization  
**Files:** 29 Python files with advanced optimization

**Questions:**
- Is this being used in production?
- Is it experimental?
- Should it be documented or removed?

### Multiple Memory Implementations
**Location:** `Forge/memory/`  
**Files:**
- `memory.py` (base)
- `conversation_memory.py` (active)
- `enhanced_vector_store.py` (enhanced?)
- `production_vector_store.py` (production?)
- `cloud_vector_store.py` (cloud?)

**Questions:**
- Which one is actually used?
- Are others experimental or alternatives?

### ACE Framework
**Location:** `Forge/agenthub/codeact_agent/codeact_agent.py`  
**Status:** Initialized if enabled  
**Config:** Not in config.toml (unclear if active)  
**Purpose:** Self-improving playbook system

**Question:** Is this production-active or experimental?

---

## Recommendations

### Keep (Production Active):
- ✅ Ultimate Editor
- ✅ Vector Memory + Hybrid Retrieval
- ✅ Atomic Refactoring
- ✅ Browser automation
- ✅ Task tracker
- ✅ Auto-lint
- ✅ All MCP servers

### Investigate (Unclear Status):
- ❓ Prompt optimization system
- ❓ Multiple memory implementations
- ❓ ACE framework
- ❓ Various agent modes

### Document or Remove:
- Experimental features should be clearly marked
- Unused code should be removed or moved to `/experiments`
- Active features should be documented

---

## Configuration File

**Current:** `config.toml`  
**Location:** Project root  
**Purpose:** Production configuration

**Key settings:**
- `agent_mode = "simple"` (fast execution)
- `system_prompt_filename = "system_prompt_forge.j2"` (optimized 166-line prompt)
- All major features enabled
- MCP servers active

---

See also:
- [Forge Improvements](./forge-improvements.md)
- [Production Setup](./production-setup.md)
- [Ultimate Editor](./ultimate-editor.md)

