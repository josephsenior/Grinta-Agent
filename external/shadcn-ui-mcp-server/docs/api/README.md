# API Reference

Complete reference for the shadcn/ui MCP Server tools and capabilities.

## 🛠️ Available Tools

### Component Tools

- [get_component](get-component.md) - Get component source code
- [get_component_demo](get-component-demo.md) - Get component usage examples
- [list_components](list-components.md) - List all available components
- [get_component_metadata](get-component-metadata.md) - Get component dependencies and info

### Block Tools

- [get_block](get-block.md) - Get complete block implementations
- [list_blocks](list-blocks.md) - List all available blocks with categories

### Repository Tools

- [get_directory_structure](get-directory-structure.md) - Explore repository structure

## 🔧 Tool Usage Examples

### Component Tools

```typescript
// Get button component source
{
  "tool": "get_component",
  "arguments": { "componentName": "button" }
}

// List all components
{
  "tool": "list_components",
  "arguments": {}
}

// Get component demo
{
  "tool": "get_component_demo",
  "arguments": { "componentName": "card" }
}
```

### Block Tools

```typescript
// Get dashboard block
{
  "tool": "get_block",
  "arguments": { "blockName": "dashboard-01" }
}

// List all blocks
{
  "tool": "list_blocks",
  "arguments": {}
}
```

### Repository Tools

```typescript
// Get directory structure
{
  "tool": "get_directory_structure",
  "arguments": { "path": "components" }
}
```

## 🎨 Framework Support

All tools support three frameworks:

- **React** (default) - shadcn/ui v4
- **Svelte** - shadcn-svelte
- **Vue** - shadcn-vue

## 🔗 Next Steps

- [get_component](get-component.md) - Component source code tool
- [get_component_demo](get-component-demo.md) - Component demo tool
- [list_components](list-components.md) - Component listing tool
- [get_block](get-block.md) - Block implementation tool
- [list_blocks](list-blocks.md) - Block listing tool
