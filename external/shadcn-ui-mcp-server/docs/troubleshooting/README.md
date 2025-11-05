# Troubleshooting

Common issues and solutions for the shadcn/ui MCP Server.

## 🐛 Common Issues

- [Installation Issues](installation-issues.md) - Problems with installation and setup
- [Rate Limit Issues](rate-limit-issues.md) - GitHub API rate limiting problems
- [Framework Issues](framework-issues.md) - Framework-specific problems
- [Integration Issues](integration-issues.md) - Editor and tool integration problems
- [Network Issues](network-issues.md) - Connection and proxy problems

## 🚨 Quick Fixes

### Server Won't Start

```bash
# Check Node.js version
node --version  # Should be 18+

# Check if npx is available
npx --version
```

### Rate Limit Errors

```bash
# Add GitHub token
npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token_here
```

### Component Not Found

```bash
# Check available components first
# Ask AI assistant: "List all available components"
```

### Framework Issues

```bash
# Verify framework selection
npx @jpisnice/shadcn-ui-mcp-server --framework svelte --help
```

## 🔧 Debug Mode

Enable verbose logging:

```bash
# Set debug environment variable
DEBUG=* npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token
```

## 📞 Getting Help

- 🐛 [Report Issues](https://github.com/Jpisnice/shadcn-ui-mcp-server/issues)
- 💬 [Discussions](https://github.com/Jpisnice/shadcn-ui-mcp-server/discussions)
- 📖 [Documentation](https://github.com/Jpisnice/shadcn-ui-mcp-server#readme)

## 🔗 Next Steps

- [Installation Issues](installation-issues.md) - Detailed installation troubleshooting
- [Rate Limit Issues](rate-limit-issues.md) - GitHub API problems
- [Framework Issues](framework-issues.md) - Framework-specific problems
- [Integration Issues](integration-issues.md) - Editor integration problems
