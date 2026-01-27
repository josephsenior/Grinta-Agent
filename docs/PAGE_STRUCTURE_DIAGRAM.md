# Forge Page Structure Diagram

## Complete Application Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         FORGE PLATFORM                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        PUBLIC PAGES                             │
└─────────────────────────────────────────────────────────────────┘

/ (Landing)
├── Hero Section
├── Features Grid
├── How It Works
├── Testimonials
├── Pricing Preview
└── CTA

/auth/login
/auth/register
/auth/forgot-password
/auth/reset-password

/about
/contact
/pricing
/terms
/privacy

┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATED PAGES                          │
└─────────────────────────────────────────────────────────────────┘

/dashboard
├── Quick Stats (4 cards)
├── Quick Actions
├── Recent Conversations
└── Activity Feed

/conversations
├── Search & Filters
├── Conversation List
└── Create New Button

/conversations/:id
├── / (Workspace Tab)
│   ├── Chat Panel (Left)
│   ├── File Explorer (Right Top)
│   ├── Code Editor (Right Middle)
│   └── Terminal (Right Bottom)
│
├── /browser
│   └── Interactive Browser View
│
├── /served
│   └── Served Application View
│
├── /terminal
│   └── Terminal View
│
└── /profile
├── User Info Card
├── Statistics
└── Activity Timeline

/notifications
├── Notification List
└── Mark as Read

/help
├── Documentation
├── FAQ
└── Support

┌─────────────────────────────────────────────────────────────────┐
│                        SETTINGS PAGES                           │
└─────────────────────────────────────────────────────────────────┘

/settings (LLM Settings)
├── Model Selection
├── API Key Management
├── Temperature & Tokens
└── Advanced Options

/settings/mcp
├── MCP Server List
├── Tool Management
└── Marketplace

/settings/user
├── Profile Information
├── Preferences
└── Theme Settings

/settings/integrations
├── GitHub Integration
├── GitLab Integration
├── Bitbucket Integration
└── Slack Integration

/settings/databases
├── Connection List
├── Query History
└── Schema Browser

/settings/knowledge-base
├── Document Management
├── Vector Store Settings
└── Search Configuration

/settings/memory
├── Memory Settings
├── Condensation Preferences
└── Context Window

/settings/analytics
├── Usage Statistics
├── Cost Tracking
└── Performance Metrics

/settings/prompts
├── Custom Prompts
├── Template Management
└── Prompt Optimization

/settings/snippets
├── Snippet Library
├── Categories
└── Search

/settings/slack
├── Workspace Connection
├── Channel Configuration
└── Notifications

/settings/backup
├── Backup Settings
├── Restore Options
└── Export/Import

/settings/app
├── General Preferences
├── UI Customization
└── Keyboard Shortcuts

/settings/billing
├── Subscription Management
├── Payment Methods
├── Usage Limits
└── Invoice History

/settings/secrets
├── Encrypted Secrets
├── Environment Variables
└── Security Settings

/settings/api-keys
├── API Key Generation
├── Key Management
└── Permissions

┌─────────────────────────────────────────────────────────────────┐
│                      SPECIALIZED PAGES                          │
└─────────────────────────────────────────────────────────────────┘

/database-browser
├── Schema Browser (Left)
├── Query Editor (Right Top)
└── Results Table (Right Bottom)

/microagent-management
├── Microagent List
├── Create Microagent
└── Microagent Details

┌─────────────────────────────────────────────────────────────────┐
│                         ADMIN PAGES                             │
└─────────────────────────────────────────────────────────────────┘

/admin/users
├── User Table
├── Search & Filters
└── User Actions

/admin/users/:userId
├── User Details
├── Activity Log
└── Admin Actions

┌─────────────────────────────────────────────────────────────────┐
│                      LAYOUT STRUCTURE                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Header                                                         │
│  [Logo] [Search] [Notifications] [User Menu] [Settings]        │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│ Sidebar  │  Main Content Area                                  │
│          │                                                      │
│ • Main   │  ┌──────────────────────────────────────────────┐   │
│ • Settings│ │                                              │   │
│ • Account │ │  Page Content                                │   │
│ • Data    │ │                                              │   │
│          │ │                                              │   │
│          │ └──────────────────────────────────────────────┘   │
│          │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

## Navigation Flow

```
┌─────────────┐
│   Landing   │
└──────┬──────┘
       │
       ├──→ Register/Login
       │         │
       │         └──→ Dashboard
       │                   │
       │                   ├──→ Conversations
       │                   │         │
       │                   │         └──→ Conversation Workspace
       │                   │
       │                   ├──→ Settings
       │                   │         │
       │                   │         ├──→ LLM Settings
       │                   │         ├──→ MCP Settings
       │                   │         ├──→ User Settings
       │                   │         ├──→ Integrations
       │                   │         ├──→ Databases
       │                   │         ├──→ Knowledge Base
       │                   │         ├──→ Memory
       │                   │         ├──→ Analytics
       │                   │         ├──→ Prompts
       │                   │         ├──→ Snippets
       │                   │         ├──→ Slack
       │                   │         ├──→ Backup
       │                   │         ├──→ App Settings
       │                   │         ├──→ Billing
       │                   │         ├──→ Secrets
       │                   │         └──→ API Keys
       │                   │
       │                   ├──→ Profile
       │                   ├──→ Notifications
       │                   ├──→ Help
       │                   ├──→ Database Browser
       │                   └──→ Microagent Management
       │
       └──→ About/Contact/Pricing/Terms/Privacy
```

## Component Hierarchy

```
App
├── RootLayout
│   ├── Header
│   │   ├── Logo
│   │   ├── SearchBar
│   │   ├── Notifications
│   │   └── UserMenu
│   │
│   ├── Sidebar
│   │   ├── Navigation Groups
│   │   │   ├── Main
│   │   │   ├── Settings
│   │   │   ├── Account
│   │   │   └── Data & Tools
│   │   └── Collapse Toggle
│   │
│   └── Main Content
│       └── [Page Content]
│
└── Footer (Landing only)
```

## Conversation Workspace Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header: [Tabs] [Controls] [Status]                        │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  Chat Panel  │  Workspace Area                             │
│              │  ┌────────────────────────────────────────┐  │
│  Messages    │  │ File Explorer                         │  │
│              │  └────────────────────────────────────────┘  │
│              │  ┌────────────────────────────────────────┐  │
│              │  │ Code Editor                           │  │
│              │  │                                       │  │
│              │  └────────────────────────────────────────┘  │
│              │  ┌────────────────────────────────────────┐  │
│              │  │ Terminal                              │  │
│              │  └────────────────────────────────────────┘  │
│              │                                              │
│  Input Area  │                                              │
│  [Message]   │                                              │
│  [Send]      │                                              │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

## Settings Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Settings Header                                            │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ Settings │  Settings Content                                │
│ Sidebar  │  ┌────────────────────────────────────────────┐  │
│          │  │ Page Title                                 │  │
│ • LLM    │  │ Description                                │  │
│ • MCP    │  └────────────────────────────────────────────┘  │
│ • User   │                                                  │
│ • ...    │  ┌────────────────────────────────────────────┐  │
│          │  │ Section 1                                  │  │
│          │  │ • Setting 1                                │  │
│          │  │ • Setting 2                                │  │
│          │  └────────────────────────────────────────────┘  │
│          │                                                  │
│          │  ┌────────────────────────────────────────────┐  │
│          │  │ Section 2                                  │  │
│          │  └────────────────────────────────────────────┘  │
│          │                                                  │
│          │  [Save Changes]                                 │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

## Mobile Layout

```
┌─────────────────────────┐
│  [☰] Logo    [🔔] [👤] │
├─────────────────────────┤
│                         │
│  Main Content           │
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
└─────────────────────────┘

Sidebar (Overlay):
┌─────────────────────────┐
│  Forge                  │
│  [✕]                    │
├─────────────────────────┤
│  • Dashboard            │
│  • Conversations        │
│  • Profile              │
│  • Settings             │
│  • ...                  │
└─────────────────────────┘
```

## Responsive Breakpoints

```
Mobile (< 640px)
├── Single column layout
├── Collapsed sidebar (overlay)
└── Stacked panels

Tablet (640px - 1024px)
├── 2-column layout
├── Collapsible sidebar
└── Resizable panels

Desktop (1024px - 1536px)
├── 3-column layout
├── Fixed sidebar
└── Multi-panel workspace

Large Desktop (> 1536px)
├── 4-column layout
├── Expanded sidebar
└── Maximum workspace
```

