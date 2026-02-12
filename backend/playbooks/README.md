# Playbooks

Specialized prompts that provide domain-specific knowledge.

## How It Works

**Global playbooks:** This folder (shareable knowledge)  
**Repo-specific:** `.Forge/playbooks/repo.md` (project context)

## Loading

1. Load repo-specific `.Forge/playbooks/repo.md` (if exists)
2. Load relevant playbooks based on trigger keywords

## Types

### Knowledge Agents
Triggered by keywords (e.g., "github", "kubernetes", "ssh")

Example:
```markdown
---
name: github
triggers:
  - github
  - pull request
---

# GitHub Guide
[Instructions here]
```

### Repository Agents
Auto-loaded for specific repos

Example `.Forge/playbooks/repo.md`:
```markdown
# My Project

## Build
npm run build

## Test
npm test

## Deploy
npm run deploy
```

## Creating Playbooks

See [add_agent.md](./add_agent.md) for template and examples.

## Available Playbooks

- `github.md` - GitHub operations
- `code-review.md` - PR reviews
- `kubernetes.md` - K8s with KIND
- `database.md` - Database setup
- `ssh.md` - SSH connections
- `agent_memory.md` - Memory system guide
- And more...

## Best Practices

- Keep under 100 lines
- Show examples, not rules
- Specific triggers
- Test thoroughly
