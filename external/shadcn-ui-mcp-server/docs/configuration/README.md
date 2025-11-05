# Configuration

Detailed configuration options for the shadcn/ui MCP Server.

## ⚙️ Configuration Options

- [Framework Selection](framework-selection.md) - Choosing between React, Svelte, and Vue
- [GitHub Token Setup](github-token-setup.md) - Setting up GitHub API access
- [Environment Variables](environment-variables.md) - Using environment variables
- [Command Line Options](command-line-options.md) - All available CLI options
- [Advanced Configuration](advanced-configuration.md) - Advanced setup options

## 🚀 Quick Configuration

### Basic Setup

```bash
# React (default)
npx @jpisnice/shadcn-ui-mcp-server

# Svelte
npx @jpisnice/shadcn-ui-mcp-server --framework svelte

# Vue
npx @jpisnice/shadcn-ui-mcp-server --framework vue
```

### With GitHub Token

```bash
# React with token
npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token_here

# Svelte with token
npx @jpisnice/shadcn-ui-mcp-server --framework svelte --github-api-key ghp_your_token_here

# Vue with token
npx @jpisnice/shadcn-ui-mcp-server --framework vue --github-api-key ghp_your_token_here
```

## 🔧 Command Line Options

```bash
shadcn-ui-mcp-server [options]

Options:
  --github-api-key, -g <token>    GitHub Personal Access Token
  --framework, -f <framework>     Framework to use: 'react', 'svelte' or 'vue' (default: react)
  --help, -h                      Show help message
  --version, -v                   Show version information
```

## 🌍 Environment Variables

```bash
# GitHub token
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# Framework selection
export FRAMEWORK=svelte

# Run server
npx @jpisnice/shadcn-ui-mcp-server
```

## 🎨 Framework Configuration

### React (Default)

```bash
npx @jpisnice/shadcn-ui-mcp-server
# or
npx @jpisnice/shadcn-ui-mcp-server --framework react
```

### Svelte

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework svelte
```

### Vue

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework vue
```

## 🔗 Next Steps

- [Framework Selection](framework-selection.md) - Detailed framework configuration
- [GitHub Token Setup](github-token-setup.md) - Setting up optimal performance
- [Environment Variables](environment-variables.md) - Using environment variables
- [Command Line Options](command-line-options.md) - Complete CLI reference
- [Advanced Configuration](advanced-configuration.md) - Advanced setup options
