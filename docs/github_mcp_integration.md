# GitHub MCP Server Integration Guide

**Status**: Post-Beta Enhancement (Optional Upgrade)

**Current Approach**: curl + GITHUB_TOKEN (works well for beta)

**This Guide**: How to upgrade to GitHub MCP for easier GitHub automation

---

## Table of Contents

1. [What is GitHub MCP?](#what-is-github-mcp)
2. [When to Upgrade](#when-to-upgrade)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Available Tools](#available-tools)
6. [Migration Examples](#migration-examples)
7. [Benefits](#benefits)
8. [Troubleshooting](#troubleshooting)

---

## What is GitHub MCP?

**GitHub MCP Server** is a Model Context Protocol server that provides structured tools for GitHub operations, replacing manual curl + GitHub API calls with function-based tools.

### Current Approach (Beta - curl + GITHUB_TOKEN):
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/owner/repo/pulls/123/reviews" \
  -d '{"body": "LGTM", "event": "APPROVE"}'
```

### GitHub MCP Approach (Post-Beta):
```python
mcp_github_pull_request_review_write(
    method="create",
    owner="owner",
    repo="repo",
    pullNumber=123,
    body="LGTM",
    event="APPROVE"
)
```

**Key Difference**: Structured function calls vs raw API requests.

---

## When to Upgrade

### ✅ **Upgrade When:**

1. **User Demand** - Users request automated PR workflows
2. **Enterprise Customers** - Organizations want GitHub bot features
3. **Code Review Automation** - Frequent automated reviews needed
4. **Issue Management** - Auto-creating issues from errors/logs
5. **Cross-Repo Operations** - Managing multiple repositories
6. **Competitive Pressure** - Other tools add GitHub automation

### ❌ **Skip If:**

1. **Users prefer manual git** - Most solo developers do
2. **Beta focus** - Focusing on core code generation quality
3. **Complexity concerns** - Want to keep setup simple
4. **Current setup works** - curl + GITHUB_TOKEN is sufficient

### 📊 **Decision Matrix:**

| Factor | curl + GITHUB_TOKEN | GitHub MCP |
|--------|---------------------|------------|
| **Setup complexity** | ⭐ Simple | ⭐⭐ Moderate |
| **Code maintainability** | ⭐⭐ Bash scripts | ⭐⭐⭐ Structured |
| **Error handling** | ⭐⭐ Manual parsing | ⭐⭐⭐ Built-in |
| **Type safety** | ⭐ None | ⭐⭐⭐ Full |
| **Learning curve** | ⭐⭐ GitHub API docs | ⭐⭐⭐ Tool definitions |
| **Flexibility** | ⭐⭐⭐ Full API access | ⭐⭐ Tool-limited |

---

## Installation

### Step 1: Install GitHub MCP Server

```bash
# Install via pnpm (globally)
pnpm add -g @modelcontextprotocol/server-github

# Or use npx (no installation)
npx @modelcontextprotocol/server-github --help
```

### Step 2: Set Up GitHub Token

The server requires a GitHub Personal Access Token with appropriate permissions.

**Create Token**:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic or fine-grained)
3. Select scopes:
   - `repo` (full repository access)
   - `read:org` (read organization data)
   - `write:discussion` (for discussions)
   - `read:project` (for projects)

**Save Token**:
```bash
# Option 1: Environment variable (recommended)
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_your_token_here"

# Option 2: Via config (see Configuration section)
```

---

## Configuration

### Add to config.toml

Update your `config.toml` MCP configuration:

```toml
[mcp]
stdio_servers = [
    # Existing servers
    { name = "shadcn-ui", command = "npx", args = ["-y", "@jpisnice/shadcn-ui-mcp-server"], 
      env = { "FRAMEWORK" = "react" } },
    { name = "fetch", command = "uvx", args = ["mcp-server-fetch"] },
    { name = "duckduckgo", command = "duckduckgo-mcp-server", args = [] },
    { name = "playwright", command = "npx", args = ["-y", "@modelcontextprotocol/server-playwright"] },
    
    # NEW: GitHub MCP Server
    { name = "github", command = "npx", args = ["-y", "@modelcontextprotocol/server-github"],
      env = { "GITHUB_PERSONAL_ACCESS_TOKEN" = "${GITHUB_TOKEN}" } },
]
```

**Note**: Uses your existing `GITHUB_TOKEN` environment variable.

### Restart Application

```bash
# Rebuild Docker container
docker-compose down
docker-compose up -d --build forge

# Verify GitHub MCP loaded
docker-compose logs forge | grep github
```

---

## Available Tools

Once installed, your agent has access to these tools:

### Pull Request Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `mcp_github_pull_request_read` | Get PR details, diff, files, comments, reviews, status | Get PR diff |
| `mcp_github_pull_request_review_write` | Create, submit, delete reviews | Approve/reject PR |
| `mcp_github_add_comment_to_pending_review` | Add inline comments to review | Comment on line 42 |
| `mcp_github_create_pull_request` | Create new PR | PR from feature branch |
| `mcp_github_update_pull_request` | Update PR title, description, reviewers, state | Change PR title |
| `mcp_github_merge_pull_request` | Merge PR | Merge with squash |
| `mcp_github_list_pull_requests` | List PRs by state, author, label | All open PRs |
| `mcp_github_search_pull_requests` | Search PRs across repos | PRs with "bug" |
| `mcp_github_update_pull_request_branch` | Update PR branch from base | Sync with main |
| `mcp_github_request_copilot_review` | Request AI code review | Auto-review PR |

### Issue Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `mcp_github_issue_read` | Get issue details, comments, sub-issues, labels | Get issue #42 |
| `mcp_github_issue_write` | Create, update issues | Create bug report |
| `mcp_github_add_issue_comment` | Add comment to issue | Reply to issue |
| `mcp_github_list_issues` | List issues by state, labels, date | All open bugs |
| `mcp_github_search_issues` | Search issues across repos | Issues mentioning "auth" |
| `mcp_github_sub_issue_write` | Add, remove, reprioritize sub-issues | Task breakdown |

### Repository Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `mcp_github_get_file_contents` | Read file or directory | Get README.md |
| `mcp_github_create_or_update_file` | Create/update single file | Update config.json |
| `mcp_github_delete_file` | Delete file | Remove old file |
| `mcp_github_push_files` | Push multiple files in one commit | Batch update |
| `mcp_github_search_code` | Search code across repos | Find "authenticate" |
| `mcp_github_search_repositories` | Find repositories | Repos with "react" |
| `mcp_github_create_repository` | Create new repo | New project |
| `mcp_github_fork_repository` | Fork repo | Fork to account |
| `mcp_github_list_branches` | List branches | All branches |
| `mcp_github_create_branch` | Create branch | New feature branch |

### Commit & Release Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `mcp_github_get_commit` | Get commit details | View commit abc123 |
| `mcp_github_list_commits` | List commits | Recent commits |
| `mcp_github_get_latest_release` | Get latest release | Check version |
| `mcp_github_get_release_by_tag` | Get specific release | Get v1.0.0 |
| `mcp_github_list_releases` | List all releases | All versions |
| `mcp_github_list_tags` | List git tags | All tags |
| `mcp_github_get_tag` | Get tag details | Tag info |

### User & Organization

| Tool | Purpose | Example |
|------|---------|---------|
| `mcp_github_get_me` | Get authenticated user info | Who am I? |
| `mcp_github_search_users` | Search users | Find developers |
| `mcp_github_get_teams` | Get user's teams | My teams |
| `mcp_github_get_team_members` | Get team members | Team roster |

**Total**: 40+ tools for comprehensive GitHub automation

---

## Migration Examples

### Example 1: Get PR Diff

**Before (curl + GITHUB_TOKEN):**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3.diff" \
  "https://api.github.com/repos/owner/repo/pulls/123" \
  > pr.diff
```

**After (GitHub MCP):**
```python
diff = mcp_github_pull_request_read(
    method="get_diff",
    owner="owner",
    repo="repo",
    pullNumber=123
)
```

**Benefit**: Structured response, automatic error handling, no file I/O needed.

---

### Example 2: Add Review Comment

**Before (curl + GITHUB_TOKEN):**
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/owner/repo/pulls/123/comments" \
  -d '{
    "body": "Security issue here",
    "commit_id": "abc123",
    "path": "src/auth.py",
    "line": 42
  }'
```

**After (GitHub MCP):**
```python
mcp_github_add_comment_to_pending_review(
    owner="owner",
    repo="repo",
    pullNumber=123,
    path="src/auth.py",
    line=42,
    body="Security issue here"
)
```

**Benefit**: Type-safe parameters, clear function signature, no JSON escaping.

---

### Example 3: Approve PR

**Before (curl + GITHUB_TOKEN):**
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/owner/repo/pulls/123/reviews" \
  -d '{"body": "LGTM!", "event": "APPROVE"}'
```

**After (GitHub MCP):**
```python
mcp_github_pull_request_review_write(
    method="create",
    owner="owner",
    repo="repo",
    pullNumber=123,
    body="LGTM!",
    event="APPROVE"
)
```

**Benefit**: Clear method name, enum for event types, validated parameters.

---

### Example 4: Complete Review Workflow

**Before (curl + GITHUB_TOKEN):**
```bash
#!/bin/bash
OWNER="user"
REPO="repo"
PR=123

# Get PR
PR_DATA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR")

# Get diff
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3.diff" \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR" > pr.diff

# Analyze...

# Post review
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$OWNER/$REPO/pulls/$PR/reviews" \
  -d '{
    "body": "Review complete",
    "event": "REQUEST_CHANGES",
    "comments": [
      {"path": "file.py", "line": 42, "body": "Fix this"}
    ]
  }'
```

**After (GitHub MCP):**
```python
# Get PR details
pr = mcp_github_pull_request_read(
    method="get",
    owner="user",
    repo="repo",
    pullNumber=123
)

# Get diff
diff = mcp_github_pull_request_read(
    method="get_diff",
    owner="user",
    repo="repo",
    pullNumber=123
)

# Analyze...

# Create review
mcp_github_pull_request_review_write(
    method="create",
    owner="user",
    repo="repo",
    pullNumber=123,
    body="Review complete"
)

# Add comment
mcp_github_add_comment_to_pending_review(
    owner="user",
    repo="repo",
    pullNumber=123,
    path="file.py",
    line=42,
    body="Fix this"
)

# Submit review
mcp_github_pull_request_review_write(
    method="submit_pending",
    owner="user",
    repo="repo",
    pullNumber=123,
    body="Please address comments",
    event="REQUEST_CHANGES"
)
```

**Benefit**: Clear workflow, no bash scripting, type-safe, easier to maintain.

---

## Benefits

### 1. **Code Maintainability**

**Before**: Bash scripts with curl, JSON parsing with jq, string escaping
**After**: Python-like function calls with clear parameters

**Impact**: Easier to read, modify, and debug.

---

### 2. **Error Handling**

**Before**: Parse curl exit codes and HTTP status manually
**After**: Structured error responses with clear messages

**Example**:
```python
# Automatic error handling
try:
    result = mcp_github_pull_request_read(...)
except Exception as e:
    # Clear error message
    print(f"Failed to fetch PR: {e}")
```

---

### 3. **Type Safety**

**Before**: No validation, easy to pass wrong parameters
**After**: Tool definitions enforce parameter types

**Example**:
```python
# This will fail validation before API call
mcp_github_pull_request_read(
    pullNumber="not_a_number"  # ❌ Error: expected int
)
```

---

### 4. **Discoverability**

**Before**: Read GitHub API docs to find endpoints
**After**: Tool names and parameters are self-documenting

**Example**:
```python
# Clear what this does just from function name
mcp_github_pull_request_review_write(method="create", ...)
```

---

### 5. **Reduced Boilerplate**

**Before**: Repeat curl headers, authentication, JSON formatting
**After**: Authentication and headers handled automatically

**Code Reduction**: ~70% less boilerplate per operation.

---

## Updating Microagents

Once GitHub MCP is installed, update your microagents:

### 1. Update `code-review.md`

Replace curl examples with MCP tool calls (examples provided above).

### 2. Update `github.md`

Document GitHub MCP tools alongside curl alternatives:

```markdown
## GitHub Operations

### Option 1: GitHub MCP Tools (Recommended)

[Tool examples]

### Option 2: curl + GITHUB_TOKEN (Fallback)

[curl examples]
```

### 3. Update `system_prompt_forge.j2`

Add GitHub MCP to MCP tools section (if not already there).

---

## Troubleshooting

### Issue: GitHub MCP Not Loading

**Symptoms**: Tools not available

**Solution**:
```bash
# Check container logs
docker-compose logs forge | grep -i github

# Verify token is set
docker-compose exec forge env | grep GITHUB

# Test server manually
npx @modelcontextprotocol/server-github
```

---

### Issue: Authentication Errors

**Symptoms**: 401 Unauthorized responses

**Solution**:
```bash
# Verify token has correct scopes
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# Check token expiration
# Regenerate at: https://github.com/settings/tokens
```

---

### Issue: Rate Limiting

**Symptoms**: 403 responses with rate limit errors

**Solution**:
```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Authenticated: 5,000 requests/hour
# Unauthenticated: 60 requests/hour

# Use caching to reduce API calls
```

---

### Issue: Tool Not Found

**Symptoms**: Agent doesn't recognize `mcp_github_*` tools

**Solution**:
```bash
# Restart container after config changes
docker-compose restart forge

# Verify MCP enabled in config.toml
grep "enable_mcp" config.toml
```

---

## Performance Considerations

### API Rate Limits

**GitHub API Limits**:
- Authenticated: 5,000 requests/hour
- Search API: 30 requests/minute

**Best Practices**:
- Cache PR data when possible
- Batch operations
- Use conditional requests (ETags)

### MCP Server Overhead

**Resource Usage**:
- Memory: ~50-100MB per instance
- Startup: ~2-3 seconds
- API latency: ~100-500ms per call

**Optimization**:
- Keep server alive (stdio mode)
- Reuse connections
- Batch related operations

---

## Comparison: curl vs GitHub MCP

| Feature | curl + GITHUB_TOKEN | GitHub MCP |
|---------|---------------------|------------|
| **Setup Time** | 0 (already have) | ~5 minutes |
| **Dependencies** | curl, jq, bash | Node.js, npm |
| **Code Lines** | More (30-50% more) | Less |
| **Error Handling** | Manual | Built-in |
| **Type Safety** | None | Full |
| **Maintenance** | Bash scripts | Structured code |
| **Flexibility** | Full API access | Tool-limited |
| **Learning Curve** | GitHub API docs | Tool definitions |
| **Performance** | Direct (faster) | +MCP overhead (~100ms) |
| **Debugging** | curl -v | MCP logs |

**Recommendation**: Start with curl (beta), upgrade to GitHub MCP when automation demands increase.

---

## Migration Checklist

Planning to migrate? Follow these steps:

### Pre-Migration
- [ ] Review current GitHub automation usage
- [ ] Identify most-used operations
- [ ] Test GitHub MCP in development environment
- [ ] Create GitHub token with correct scopes
- [ ] Document current workflows

### Migration
- [ ] Add GitHub MCP to config.toml
- [ ] Set GITHUB_PERSONAL_ACCESS_TOKEN
- [ ] Restart application
- [ ] Verify tools load correctly
- [ ] Test basic operations (get PR, create comment)

### Post-Migration
- [ ] Update code-review.md microagent
- [ ] Update github.md microagent
- [ ] Update system prompt (if needed)
- [ ] Monitor error logs
- [ ] Gather user feedback
- [ ] Update documentation

---

## When NOT to Migrate

Stay with curl + GITHUB_TOKEN if:

1. **Current setup works well** - No user complaints
2. **Simple automation** - Basic PR creation only
3. **Resource constraints** - Every MB of memory matters
4. **Flexibility needs** - Need access to ALL GitHub API endpoints
5. **Team preference** - Team prefers bash over structured tools

**Remember**: curl + GITHUB_TOKEN is a perfectly valid long-term solution. GitHub MCP is an enhancement, not a requirement.

---

## Summary

**GitHub MCP Server** provides structured tools for GitHub operations, replacing manual API calls with function-based interactions.

**When to Use**:
- ✅ Frequent GitHub automation
- ✅ Code review workflows
- ✅ Enterprise customers
- ✅ Complex multi-repo operations

**When to Skip**:
- ✅ Beta/MVP stage (current)
- ✅ Simple git workflows
- ✅ Users prefer manual control
- ✅ curl + GITHUB_TOKEN works fine

**Bottom Line**: GitHub MCP is a nice-to-have enhancement for post-beta. Your current curl + GITHUB_TOKEN approach is production-ready and sufficient for beta launch.

---

**Questions? Issues? Feedback?**

Open an issue or discussion on GitHub to share your experience with GitHub MCP integration!

