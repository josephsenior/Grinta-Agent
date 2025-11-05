# Microagents

Specialized prompts that provide domain-specific knowledge.

## How It Works

**Global microagents:** This folder (shareable knowledge)  
**Repo-specific:** `.openhands/microagents/repo.md` (project context)

## Loading

1. Load repo-specific `.openhands/microagents/repo.md` (if exists)
2. Load relevant microagents based on trigger keywords

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

Example `.openhands/microagents/repo.md`:
```markdown
# My Project

## Build
npm run build

## Test
npm test

## Deploy
npm run deploy
```

## Creating Microagents

See [add_agent.md](./add_agent.md) for template and examples.

## Available Microagents

- `github.md` - GitHub operations
- `gitlab.md` - GitLab operations
- `bitbucket.md` - Bitbucket operations
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
