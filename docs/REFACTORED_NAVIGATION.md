# Refactored Navigation Structure

## Overview
This document outlines the refactored navigation structure that consolidates settings, reduces cognitive load, and improves discoverability.

---

## Main Sidebar Navigation (Simplified)

### Structure
```
┌─────────────────────────────┐
│  FORGE LOGO                 │
├─────────────────────────────┤
│  MAIN                       │
│  • Dashboard                │
│  • Conversations            │
│  • Search                   │
│  • Database Browser         │
│  • Profile                  │
│  • Notifications            │
│  • Help & Support           │
│  • Pricing                  │
├─────────────────────────────┤
│  SETTINGS (Single Entry)    │
│  • Settings                 │
│    └─ Opens Settings Hub    │
├─────────────────────────────┤
│  HELP                       │
│  • Keyboard Shortcuts       │
└─────────────────────────────┘
```

### Key Changes
1. **Consolidated Settings**: All settings moved under single "Settings" entry
2. **Removed Redundancy**: No more "AI & Models", "Account", "Integrations" groups in main nav
3. **Cleaner Hierarchy**: Only 2 main groups (Main + Settings)
4. **Settings Hub**: Clicking "Settings" opens a hub page with categorized cards

---

## Settings Hub Page (`/settings`)

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│  Settings                                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  [Search Settings...]                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 🤖 AI &      │  │ 👤 Account   │  │ 🔌 Integrations│    │
│  │    Models    │  │              │  │               │     │
│  │              │  │              │  │               │     │
│  │ • LLM        │  │ • Profile    │  │ • Git         │     │
│  │ • MCP        │  │ • Billing    │  │ • Slack       │     │
│  │ • Prompts    │  │ • API Keys   │  │               │     │
│  │ • Memory     │  │ • App        │  │               │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 💾 Data &    │  │ 💻 Development│  │ 📊 Analytics │     │
│  │    Storage   │  │               │  │              │     │
│  │              │  │               │  │              │     │
│  │ • Databases  │  │ • Snippets   │  │ • Analytics  │     │
│  │ • Knowledge  │  │ • Secrets    │  │              │     │
│  │   Base       │  │              │  │              │     │
│  │ • Backup     │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Settings Categories

#### 1. AI & Models
- **LLM Settings** (`/settings/llm`) - Model selection, API keys, temperature
- **MCP** (`/settings/mcp`) - MCP server management
- **Prompts** (`/settings/prompts`) - Custom prompts library
- **Memory** (`/settings/memory`) - Memory settings and condensation

#### 2. Account (SaaS only)
- **User Settings** (`/settings/user`) - Profile, email, preferences
- **Billing** (`/settings/billing`) - Subscription, payment methods
- **API Keys** (`/settings/api-keys`) - API key management
- **Application** (`/settings/app`) - App preferences, language

#### 3. Integrations
- **Git Integration** (`/settings/integrations`) - GitHub, GitLab, Bitbucket
- **Slack** (`/settings/slack`) - Slack workspace connection

#### 4. Data & Storage
- **Databases** (`/settings/databases`) - Database connections
- **Knowledge Base** (`/settings/knowledge-base`) - Document management
- **Backup & Restore** (`/settings/backup`) - Backup settings

#### 5. Development
- **Code Snippets** (`/settings/snippets`) - Snippet library
- **Secrets** (`/settings/secrets`) - Encrypted secrets management
- **API Keys** (`/settings/api-keys`) - For OSS mode

#### 6. Analytics
- **Analytics** (`/settings/analytics`) - Usage stats, costs, metrics

---

## Navigation Data Structure

### Main Navigation
```typescript
const mainNavGroups = [
  {
    title: "Main",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/conversations", label: "Conversations", icon: MessageSquare },
      { to: "/search", label: "Search", icon: Search },
      { to: "/database-browser", label: "Database Browser", icon: Database },
      { to: "/profile", label: "Profile", icon: User },
      { to: "/notifications", label: "Notifications", icon: Bell },
      { to: "/help", label: "Help & Support", icon: HelpCircle },
      { to: "/pricing", label: "Pricing", icon: DollarSign },
    ],
  },
  {
    title: "Settings",
    items: [
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];
```

### Settings Hub Categories
```typescript
const settingsCategories = [
  {
    id: "ai-models",
    title: "AI & Models",
    icon: Bot,
    description: "Configure AI models, MCP servers, prompts, and memory",
    items: [
      { to: "/settings/llm", label: "LLM Settings", icon: Bot, requiresPro: false },
      { to: "/settings/mcp", label: "MCP", icon: Workflow },
      { to: "/settings/prompts", label: "Prompts", icon: FileText },
      { to: "/settings/memory", label: "Memory", icon: Brain },
    ],
  },
  {
    id: "account",
    title: "Account",
    icon: User,
    description: "Manage your profile, billing, and account settings",
    items: [
      { to: "/settings/user", label: "User Settings", icon: User, saasOnly: true },
      { to: "/settings/billing", label: "Billing", icon: CreditCard, saasOnly: true },
      { to: "/settings/api-keys", label: "API Keys", icon: Key, saasOnly: true },
      { to: "/settings/app", label: "Application", icon: Settings },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    icon: Plug,
    description: "Connect external services and tools",
    items: [
      { to: "/settings/integrations", label: "Git Integration", icon: GitBranch },
      { to: "/settings/slack", label: "Slack", icon: MessageCircle },
    ],
  },
  {
    id: "data-storage",
    title: "Data & Storage",
    icon: Database,
    description: "Manage databases, knowledge base, and backups",
    items: [
      { to: "/settings/databases", label: "Databases", icon: Database },
      { to: "/settings/knowledge-base", label: "Knowledge Base", icon: BookOpen },
      { to: "/settings/backup", label: "Backup & Restore", icon: Download },
    ],
  },
  {
    id: "development",
    title: "Development",
    icon: Code,
    description: "Code snippets, secrets, and development tools",
    items: [
      { to: "/settings/snippets", label: "Code Snippets", icon: Code },
      { to: "/settings/secrets", label: "Secrets", icon: Lock },
      { to: "/settings/api-keys", label: "API Keys", icon: Key, ossOnly: true },
    ],
  },
  {
    id: "analytics",
    title: "Analytics",
    icon: BarChart3,
    description: "Usage statistics, costs, and performance metrics",
    items: [
      { to: "/settings/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
];
```

---

## Implementation Plan

### Phase 1: Create Settings Hub Page
1. Create `/settings` index route with hub layout
2. Display categorized cards with icons
3. Add search functionality
4. Show "Recently Used" section

### Phase 2: Update Main Navigation
1. Simplify `AppNavigation.tsx` to only show Main + Settings
2. Remove all settings items from main nav
3. Update active state logic

### Phase 3: Enhance Settings Hub
1. Add quick access to frequently used settings
2. Add descriptions for each category
3. Add keyboard navigation
4. Add "Recently Visited" tracking

### Phase 4: Update Routes
1. Ensure all settings routes still work
2. Update redirects if needed
3. Update breadcrumbs

---

## Benefits

1. **Reduced Cognitive Load**: Main nav goes from 6+ groups to 2 groups
2. **Better Discoverability**: Settings hub shows all options at once
3. **Cleaner UI**: Less clutter in sidebar
4. **Scalability**: Easy to add new settings without cluttering main nav
5. **Consistency**: All settings in one place
6. **Better UX**: Users can see all settings categories at a glance

---

## Migration Notes

- Existing routes remain unchanged (`/settings/*` paths stay the same)
- Settings sidebar within settings pages remains (nested navigation)
- Main sidebar becomes much simpler
- Settings hub acts as landing page for `/settings`

