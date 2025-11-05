---
name: agent_memory
type: knowledge
version: 2.0.0
agent: CodeActAgent
triggers:
  - /remember
  - repository memory
  - repo memory
---

# Agent Memory System

Two complementary memory systems:

## 1. Repository Memory (repo.md)

**Location:** `.openhands/microagents/repo.md` in each repo

**Purpose:** Project-specific knowledge (manual, curated)

**What to store:**
- Repository structure & architecture
- Common commands (build, test, deploy)
- Code style & conventions
- Development workflows
- Setup instructions

**What NOT to store:**
- Issue-specific info
- Temporary workarounds
- User preferences
- Secrets

**Auto-loads** when working in repository.

## 2. Vector Memory (Automatic)

**Location:** Backend (ChromaDB/Qdrant)

**Purpose:** Semantic search across all conversations

**What's stored automatically:**
- User requests & questions
- Your responses & actions
- Code changes
- Decisions & rationale
- Error resolutions

**Performance:**
- ~110ms first query, ~35ms cached
- 92% accuracy
- Hybrid retrieval (vector + BM25 + re-ranking)

## When to Use Each

| Scenario | repo.md | Vector Memory |
|----------|---------|---------------|
| Project commands | ✅ | Auto-captured |
| Code style | ✅ | Auto-captured |
| Bug we fixed | ❌ | ✅ |
| Past conversation | ❌ | ✅ |
| Team conventions | ✅ | Auto-captured |

**Golden rule:** General project knowledge → repo.md. Everything else → vector memory (automatic).

## Example: Save to repo.md

**User:** "/remember the build process"

**You:**
```
I'll save to repo.md:

1. Build: npm run build
2. Test: npm test -- --coverage
3. Lint: npm run lint
4. Pre-commit: Husky (lint + tests)

Save all or skip any?
```

After approval → Update `.openhands/microagents/repo.md`

## Best Practices

**repo.md:**
- Concise (one-liners for commands)
- Organized sections
- Current info only

**Vector Memory:**
- No action needed (automatic)
- Trust the system
- Reference past: "Similar to yesterday"
