---
name: add_agent
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - new agent
  - new microagent
  - create agent
  - create microagent
  - add agent
  - add microagent
---

# Creating Microagents

Microagents are contextual prompts activated by trigger words for specific tasks.

## Quick Template

Create `.Forge/microagents/yourname.md`:

```markdown
---
name: yourname
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - trigger word
  - another trigger
---

# Your Agent Guide

[Brief description of what this provides]

## Environment Variables
- `VAR_NAME`: Description

## Usage
[2-3 concrete examples]

## Common Issues
[Troubleshooting tips]
```

## Example: Slack Agent

```markdown
---
name: slack
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - slack
  - slack bot
---

# Slack Integration

Environment: `SLACK_BOT_TOKEN`, `SLACK_WEBHOOK_URL`

## Post Message
\```bash
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "#general", "text": "Hello!"}'
\```

## Common Issues
- Token format: Must start with `xoxb-`
- Permissions: Needs `chat:write` scope
```

## Best Practices

- Keep triggers specific (avoid false activations)
- Include 2-3 examples (not 20!)
- Document required env vars
- Keep it under 120 lines
- Show patterns, not rules
