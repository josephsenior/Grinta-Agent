# Cursor Integration

Integrate the shadcn/ui MCP Server with Cursor for AI-powered component development.

## 🚀 Quick Setup

### Method 1: Global Configuration

1. **Open Cursor Settings**:
   - Go to Settings (Cmd/Ctrl + ,)
   - Search for "MCP" or "Model Context Protocol"

2. **Add MCP Server Configuration**:

```json
{
  "mcpServers": {
    "shadcn-ui": {
      "command": "npx",
      "args": ["@jpisnice/shadcn-ui-mcp-server", "--github-api-key", "ghp_your_token_here"]
    }
  }
}
```

### Method 2: Workspace Configuration

Create a `.cursorrules` file in your project root:

```json
{
  "mcpServers": {
    "shadcn-ui": {
      "command": "npx",
      "args": ["@jpisnice/shadcn-ui-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

## 🎨 Framework-Specific Configurations

### React (Default)

```json
{
  "mcpServers": {
    "shadcn-ui": {
      "command": "npx",
      "args": ["@jpisnice/shadcn-ui-mcp-server", "--github-api-key", "ghp_your_token_here"]
    }
  }
}
```

### Svelte

```json
{
  "mcpServers": {
    "shadcn-ui-svelte": {
      "command": "npx",
      "args": [
        "@jpisnice/shadcn-ui-mcp-server",
        "--framework",
        "svelte",
        "--github-api-key",
        "ghp_your_token_here"
      ]
    }
  }
}
```

### Vue

```json
{
  "mcpServers": {
    "shadcn-ui-vue": {
      "command": "npx",
      "args": [
        "@jpisnice/shadcn-ui-mcp-server",
        "--framework",
        "vue",
        "--github-api-key",
        "ghp_your_token_here"
      ]
    }
  }
}
```

## 🔧 Multiple Framework Setup

Configure multiple frameworks for comparison:

```json
{
  "mcpServers": {
    "shadcn-ui-react": {
      "command": "npx",
      "args": [
        "@jpisnice/shadcn-ui-mcp-server",
        "--framework",
        "react",
        "--github-api-key",
        "ghp_your_token_here"
      ]
    },
    "shadcn-ui-svelte": {
      "command": "npx",
      "args": [
        "@jpisnice/shadcn-ui-mcp-server",
        "--framework",
        "svelte",
        "--github-api-key",
        "ghp_your_token_here"
      ]
    },
    "shadcn-ui-vue": {
      "command": "npx",
      "args": [
        "@jpisnice/shadcn-ui-mcp-server",
        "--framework",
        "vue",
        "--github-api-key",
        "ghp_your_token_here"
      ]
    }
  }
}
```

## 🎯 Usage Examples

### Chat with AI

1. **Open Cursor Chat** (Cmd/Ctrl + L)
2. **Ask for components**:
   ```
   "Show me the shadcn/ui button component"
   "Get the dashboard-01 block implementation"
   "List all available components"
   ```

### Code Generation

1. **Use Cursor's AI features**:
   ```
   "Generate a login form using shadcn/ui components"
   "Create a dashboard with shadcn/ui blocks"
   "Show me how to use the card component"
   ```

### Framework Comparison

```
"Compare the button component implementations between React and Svelte"
"Show me the Vue version of the card component"
"Get the React dialog component with TypeScript"
```

## 🔍 Environment Variable Setup

Use environment variables for better security:

```json
{
  "mcpServers": {
    "shadcn-ui": {
      "command": "npx",
      "args": ["@jpisnice/shadcn-ui-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

## 🐛 Troubleshooting

### MCP Server Not Working

1. **Verify server runs standalone**:

   ```bash
   npx @jpisnice/shadcn-ui-mcp-server --help
   ```

2. **Check configuration syntax**:
   - Validate JSON format
   - Check for missing commas or brackets

3. **Restart Cursor** after configuration changes

4. **Check Cursor logs** for error messages

### Common Issues

**"Command not found"**:

```bash
# Ensure npx is available
npx --version
```

**"Rate limit exceeded"**:

```bash
# Add GitHub token to configuration
```

**"MCP server not recognized"**:

- Restart Cursor
- Check configuration file location
- Verify JSON syntax

## 🔗 Next Steps

- [Usage Examples](../usage/) - How to use after integration
- [Troubleshooting](../troubleshooting/) - Common issues and solutions
- [API Reference](../api/) - Complete tool reference
- [Other Integrations](README.md) - Connect to other tools
