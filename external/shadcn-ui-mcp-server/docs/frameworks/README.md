# Frameworks

Framework-specific documentation for React, Svelte, and Vue implementations.

## 🎨 Supported Frameworks

## 📋 Framework Comparison

| Framework           | Repository                                      | Maintainer                                | File Extension | Description                          |
| ------------------- | ----------------------------------------------- | ----------------------------------------- | -------------- | ------------------------------------ |
| **React** (default) | [shadcn/ui](https://ui.shadcn.com/)             | [shadcn](https://github.com/shadcn)       | `.tsx`         | React components from shadcn/ui v4   |
| **Svelte**          | [shadcn-svelte](https://www.shadcn-svelte.com/) | [huntabyte](https://github.com/huntabyte) | `.svelte`      | Svelte components from shadcn-svelte |
| **Vue**             | [shadcn-vue](https://www.shadcn-vue.com/)       | [unovue](https://github.com/unovue)       | `.vue`         | Vue components from shadcn-vue       |

## 🚀 Quick Framework Selection

### React (Default)

```bash
npx @jpisnice/shadcn-ui-mcp-server
```

### Svelte

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework svelte
```

### Vue

```bash
npx @jpisnice/shadcn-ui-mcp-server --framework vue
```

## 🔄 Switching Between Frameworks

### Command Line

```bash
# Switch to Svelte
npx @jpisnice/shadcn-ui-mcp-server --framework svelte

# Switch to Vue
npx @jpisnice/shadcn-ui-mcp-server --framework vue

# Switch back to React
npx @jpisnice/shadcn-ui-mcp-server --framework react
```

### Environment Variable

```bash
# Use Svelte
export FRAMEWORK=svelte
npx @jpisnice/shadcn-ui-mcp-server

# Use Vue
export FRAMEWORK=vue
npx @jpisnice/shadcn-ui-mcp-server

# Use React
export FRAMEWORK=react
npx @jpisnice/shadcn-ui-mcp-server
```

## 🎯 Framework-Specific Use Cases

### React

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

## 🔍 Framework Detection

The server logs which framework is being used:

```bash
INFO: Framework set to 'svelte' via command line argument
INFO: MCP Server configured for SVELTE framework
INFO: Repository: huntabyte/shadcn-svelte
INFO: File extension: .svelte
```

## 🔗 Next Steps

- [Configuration](../configuration/) - Framework configuration options
- [Usage Examples](../usage/) - Framework-specific examples
- [Integration](../integration/) - Editor and tool integrations
