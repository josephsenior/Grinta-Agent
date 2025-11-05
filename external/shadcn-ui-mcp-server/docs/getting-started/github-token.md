# GitHub Token Setup

Setting up a GitHub Personal Access Token will significantly improve your experience with the shadcn/ui MCP Server.

## 🎯 Why You Need a Token

| Without Token       | With Token           |
| ------------------- | -------------------- |
| 60 requests/hour    | 5,000 requests/hour  |
| Rate limit errors   | Reliable performance |
| Slower responses    | Faster responses     |
| Limited reliability | Better caching       |

## 📝 Getting Your Token (2 minutes)

### Step 1: Go to GitHub Settings

1. Visit [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Or navigate: GitHub Profile → Settings → Developer settings → Personal access tokens

### Step 2: Generate New Token

1. Click **"Generate new token (classic)"**
2. Add a note: `"shadcn-ui MCP server"`
3. **Expiration**: Choose your preference (90 days recommended)
4. **Scopes**: ✅ **No scopes needed!** (public repository access is sufficient)

### Step 3: Copy Your Token

1. Copy the generated token (starts with `ghp_`)
2. ⚠️ **Save it securely** - you won't see it again!

## 🚀 Using Your Token

### Method 1: Command Line (Quick testing)

```bash
npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token_here
```

### Method 2: Environment Variable (Recommended)

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# Then simply run:
npx @jpisnice/shadcn-ui-mcp-server
```

### Method 3: Single Command

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here npx @jpisnice/shadcn-ui-mcp-server
```

## 🔧 Framework-Specific Usage

### React (Default)

```bash
npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token_here
```

### Svelte

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework svelte --github-api-key ghp_your_token_here
```

### Vue

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework vue --github-api-key ghp_your_token_here
```

## 🔒 Security Best Practices

1. **Never commit tokens to version control**
2. **Use environment variables in production**
3. **Set appropriate expiration dates**
4. **Rotate tokens regularly**
5. **Use minimal required scopes** (none needed for this server)

## 🐛 Troubleshooting

### Token Not Working

```bash
# Check if token is valid
curl -H "Authorization: token ghp_your_token_here" https://api.github.com/user

# Should return your GitHub user info
```

### Rate Limit Still Exceeded

```bash
# Check your current rate limit
curl -H "Authorization: token ghp_your_token_here" https://api.github.com/rate_limit

# Look for "remaining" field in the response
```

### Environment Variable Not Recognized

```bash
# Verify the variable is set
echo $GITHUB_PERSONAL_ACCESS_TOKEN

# Should show your token (starts with ghp_)
```

## 🔗 Next Steps

- [Installation](installation.md) - Complete installation guide
- [Framework Selection](framework-selection.md) - Choose your framework
- [First Steps](first-steps.md) - Make your first component request
- [Integration](../integration/) - Connect to your editor or tool
