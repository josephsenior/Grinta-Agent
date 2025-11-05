# Framework Selection

The shadcn/ui MCP Server supports three popular framework implementations. Choose the one that matches your project needs.

## 🎨 Available Frameworks

| Framework           | Repository                                      | Maintainer                                | File Extension | Description                          |
| ------------------- | ----------------------------------------------- | ----------------------------------------- | -------------- | ------------------------------------ |
| **React** (default) | [shadcn/ui](https://ui.shadcn.com/)             | [shadcn](https://github.com/shadcn)       | `.tsx`         | React components from shadcn/ui v4   |
| **Svelte**          | [shadcn-svelte](https://www.shadcn-svelte.com/) | [huntabyte](https://github.com/huntabyte) | `.svelte`      | Svelte components from shadcn-svelte |
| **Vue**             | [shadcn-vue](https://www.shadcn-vue.com/)       | [unovue](https://github.com/unovue)       | `.vue`         | Vue components from shadcn-vue       |

## 🚀 How to Switch Frameworks

### Method 1: Command Line Argument (Recommended)

```bash
# React (default)
npx @jpisnice/shadcn-ui-mcp-server

# Svelte
npx @jpisnice/shadcn-ui-mcp-server --framework svelte
npx @jpisnice/shadcn-ui-mcp-server -f svelte

# Vue
npx @jpisnice/shadcn-ui-mcp-server --framework vue
npx @jpisnice/shadcn-ui-mcp-server -f vue

# Switch back to React
npx @jpisnice/shadcn-ui-mcp-server --framework react
npx @jpisnice/shadcn-ui-mcp-server -f react
```

### Method 2: Environment Variable

```bash
# Use Svelte
export FRAMEWORK=svelte
npx @jpisnice/shadcn-ui-mcp-server

# Use React
export FRAMEWORK=react
npx @jpisnice/shadcn-ui-mcp-server

# Use Vue
export FRAMEWORK=vue
npx @jpisnice/shadcn-ui-mcp-server

# Or set for single command
FRAMEWORK=svelte npx @jpisnice/shadcn-ui-mcp-server
FRAMEWORK=vue npx @jpisnice/shadcn-ui-mcp-server
```

### Method 3: Combined with GitHub Token

```bash
# Svelte with GitHub token
npx @jpisnice/shadcn-ui-mcp-server --framework svelte --github-api-key ghp_your_token_here

# React with GitHub token (default)
npx @jpisnice/shadcn-ui-mcp-server --github-api-key ghp_your_token_here

# Vue with GitHub token
npx @jpisnice/shadcn-ui-mcp-server --framework vue --github-api-key ghp_your_token_here
```

## 🔍 Framework Detection

The server will log which framework is being used:

```bash
INFO: Framework set to 'svelte' via command line argument
INFO: MCP Server configured for SVELTE framework
INFO: Repository: huntabyte/shadcn-svelte
INFO: File extension: .svelte
```

```bash
INFO: Framework set to 'vue' via command line argument
INFO: MCP Server configured for VUE framework
INFO: Repository: unovue/shadcn-vue
INFO: File extension: .vue
```

## 💡 Use Cases by Framework

### React (Default)

- **React/Next.js applications**
- **TypeScript projects**
- **Most common use case**
- **Full shadcn/ui v4 compatibility**

### Svelte

- **Svelte/SvelteKit applications**
- **Svelte component development**
- **Learning Svelte with shadcn patterns**

### Vue

- **Vue/Nuxt applications**
- **Vue component development**
- **Learning Vue with shadcn patterns**

## 🔄 Multi-Framework Development

You can easily switch between frameworks to compare implementations:

```bash
# Compare React and Svelte button components
npx @jpisnice/shadcn-ui-mcp-server --framework react
# Get React button component

npx @jpisnice/shadcn-ui-mcp-server --framework svelte
# Get Svelte button component

npx @jpisnice/shadcn-ui-mcp-server --framework vue
# Get Vue button component
```

## ⚠️ Important Notes

### Environment Variable Syntax

When using environment variables, make sure to use the correct syntax:

- ✅ Correct: `export FRAMEWORK=svelte && npx @jpisnice/shadcn-ui-mcp-server`
- ✅ Correct: `FRAMEWORK=svelte npx @jpisnice/shadcn-ui-mcp-server`
- ❌ Incorrect: `FRAMEWORK=svelte npx @jpisnice/shadcn-ui-mcp-server` (without proper spacing)

### Framework-Specific Features

Each framework may have slightly different:

- Component APIs
- Styling approaches
- Dependencies
- File structures

## 🔗 Next Steps

- [First Steps](first-steps.md) - Make your first component request
- [Framework Documentation](../frameworks/) - Detailed framework guides
- [Usage Examples](../usage/) - See framework-specific examples
- [Integration](../integration/) - Connect to your editor or tool
