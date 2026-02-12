---
name: code_review
type: knowledge
version: 2.0.0
agent: Orchestrator
triggers:
  - /codereview
  - code review
  - review code
  - review pr
---

# Code Review Guide

Use GitHub REST API (curl) for PR reviews. Token: `GITHUB_TOKEN` env var.

## Quick Workflow

1. Fetch PR: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER`
2. Get diff: `curl -H "Accept: application/vnd.github.v3.diff" https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER`
3. Review code (focus: security, bugs, clarity)
4. Post comments via API
5. Submit review (APPROVE, REQUEST_CHANGES, or COMMENT)

## Review Template

```markdown
## Code Review

**Critical Issues 🚨**
[Must fix before merge]

**Suggestions 💡**
[Nice to have improvements]

**Highlights ✅**
[What's done well]
```

## Examples

### Post Comment
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/OWNER/REPO/issues/PR_NUMBER/comments" \
  -d '{"body": "Security issue in auth.py line 102: SQL injection risk. Use parameterized queries."}'
```

### Submit Review
```bash
# Approve
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/reviews" \
  -d '{"body": "LGTM! ✅", "event": "APPROVE"}'

# Request changes
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/reviews" \
  -d '{"body": "Please fix security issues.", "event": "REQUEST_CHANGES"}'
```

### Inline Comment on Specific Line
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER/comments" \
  -d '{
    "body": "🔒 SQL injection: Use cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))",
    "commit_id": "COMMIT_SHA",
    "path": "src/auth.py",
    "line": 102
  }'
```

## Focus Areas

**Security:** SQL injection, XSS, hardcoded secrets, weak crypto
**Bugs:** Null checks, error handling, edge cases
**Clarity:** Function length, nesting depth, naming

## Review Status

- `APPROVE` - Ready to merge
- `REQUEST_CHANGES` - Must fix issues
- `COMMENT` - Suggestions only
