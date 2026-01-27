# Forge UI/UX Design System & Page Structure

## Overview

This document defines the complete UI/UX design system, page structure, navigation architecture, and user flows for the Forge platform. The design emphasizes a modern, professional, enterprise-grade interface optimized for productivity and developer experience.

## Design Philosophy

**Core Principles:**
- **Clarity First**: Information hierarchy guides user attention
- **Performance**: Fast, responsive interactions with smooth animations
- **Accessibility**: WCAG 2.1 AA compliance
- **Consistency**: Unified design language across all pages
- **Developer-Focused**: Optimized for technical workflows
- **Luxury Feel**: Premium aesthetics without sacrificing functionality

---

## Design System

### Color Palette

#### Primary Colors
```
Background: #000000 (Pure Black - OLED optimized)
Brand Violet: #8b5cf6 (Primary brand color)
Brand Violet Dark: #7c3aednah still same i
Brand Violet Light: #a78bfa
```

#### Semantic Colors
```
Success: #10B981 (Emerald)
Warning: #F59E0B (Gold)
Danger: #EF4444 (Red)
Info: #3B82F6 (Sapphire)
```

#### Text Hierarchy
```
Primary: #FFFFFF (Main content)
Secondary: #F1F5F9 (Secondary text)
Tertiary: #94A3B8 (Muted text)
Muted: #6a6f7f (Very muted)
Accent: #8b5cf6 (Brand violet)
```

#### Border Colors
```
Primary: #1a1a1a
Secondary: #0f0f0f
Accent: #8b5cf6
Subtle: #151515
Glass: rgba(139, 92, 246, 0.1)
```

### Typography

**Font Families:**
- **Primary**: Inter (Sans-serif)
  - Weights: 300, 400, 500, 600, 700, 800, 900
- **Monospace**: JetBrains Mono
  - Weights: 400, 500, 600

**Type Scale:**
```
xxs: 0.75rem (12px) - Labels, captions
xs: 0.875rem (14px) - Small text, metadata
s: 1rem (16px) - Body text
m: 1.125rem (18px) - Large body
l: 1.5rem (24px) - Headings
xl: 2rem (32px) - Large headings
xxl: 2.25rem (36px) - Hero headings
xxxl: 3rem (48px) - Display headings
```

**Line Heights:**
- Tight: 1.2 (Headings)
- Normal: 1.5 (Body)
- Relaxed: 1.75 (Long-form content)

### Spacing System

**Base Unit**: 4px (0.25rem)

```
xs: 0.25rem (4px)
sm: 0.5rem (8px)
md: 1rem (16px)
lg: 1.5rem (24px)
xl: 2rem (32px)
2xl: 3rem (48px)
3xl: 4rem (64px)
4xl: 6rem (96px)
```

### Border Radius

```
sm: 0.25rem (4px)
md: 0.5rem (8px)
lg: 0.75rem (12px)
xl: 1rem (16px)
2xl: 1.5rem (24px)
3xl: 2rem (32px)
full: 9999px (Pills, circles)
```

### Shadows & Effects

```
luxury: 0 4px 20px rgba(0, 0, 0, 0.15)
luxury-lg: 0 8px 40px rgba(0, 0, 0, 0.2)
luxury-xl: 0 20px 60px rgba(0, 0, 0, 0.3)
glow: 0 0 20px rgba(245, 158, 11, 0.3)
glow-lg: 0 0 40px rgba(245, 158, 11, 0.4)
```

### Animations

**Transitions:**
- Fast: 150ms (Micro-interactions)
- Normal: 300ms (Standard transitions)
- Slow: 500ms (Page transitions)

**Easing:**
- Ease-out: `cubic-bezier(0.16, 1, 0.3, 1)` (Entrance)
- Ease-in: `cubic-bezier(0.4, 0, 1, 1)` (Exit)
- Spring: `cubic-bezier(0.68, -0.55, 0.265, 1.55)` (Bouncy)

---

## Component Library

### Buttons

**Primary Button:**
- Background: Violet gradient (`#8b5cf6` → `#7c3aed`)
- Text: White
- Padding: 12px 24px
- Border radius: 8px
- Hover: Brightness 110%
- Active: Brightness 95%

**Secondary Button:**
- Background: Transparent
- Border: 1px solid `#1a1a1a`
- Text: White
- Hover: Background `rgba(139, 92, 246, 0.1)`

**Ghost Button:**
- Background: Transparent
- Text: Secondary
- Hover: Background `rgba(255, 255, 255, 0.05)`

**Icon Button:**
- Size: 40px × 40px
- Border radius: 50%
- Background: `rgba(0, 0, 0, 0.6)`
- Hover: Background `rgba(139, 92, 246, 0.1)`

### Cards

**Standard Card:**
- Background: `#000000`
- Border: 1px solid `#1a1a1a`
- Border radius: 12px
- Padding: 24px
- Shadow: `luxury`

**Elevated Card:**
- Same as standard + `luxury-lg` shadow
- Border: `rgba(139, 92, 246, 0.1)`

**Glass Card:**
- Background: `rgba(0, 0, 0, 0.75)`
- Backdrop blur: 12px
- Border: `rgba(139, 92, 246, 0.1)`

### Inputs

**Text Input:**
- Background: `#000000`
- Border: 1px solid `#1a1a1a`
- Border radius: 8px
- Padding: 12px 16px
- Focus: Border `#8b5cf6`, Ring `rgba(139, 92, 246, 0.2)`

**Textarea:**
- Same as text input
- Min height: 100px
- Resize: Vertical

**Select:**
- Same as text input
- Dropdown arrow: Violet

### Badges

**Status Badge:**
- Padding: 4px 12px
- Border radius: 9999px
- Font size: 12px
- Font weight: 500

**Color Variants:**
- Success: `rgba(16, 185, 129, 0.12)` bg, `#10B981` text
- Warning: `rgba(245, 158, 11, 0.12)` bg, `#F59E0B` text
- Danger: `rgba(239, 68, 68, 0.12)` bg, `#EF4444` text
- Info: `rgba(59, 130, 246, 0.12)` bg, `#3B82F6` text

### Modals

**Modal Overlay:**
- Background: `rgba(0, 0, 0, 0.8)`
- Backdrop blur: 8px

**Modal Content:**
- Background: `#000000`
- Border: 1px solid `#1a1a1a`
- Border radius: 16px
- Padding: 32px
- Max width: 600px
- Shadow: `luxury-xl`

### Tooltips

- Background: `rgba(0, 0, 0, 0.9)`
- Border: 1px solid `#1a1a1a`
- Padding: 8px 12px
- Border radius: 6px
- Font size: 12px
- Arrow: Violet

---

## Page Structure & Navigation

### Navigation Architecture

**Primary Navigation (Sidebar):**
```
┌─────────────────────────┐
│  Forge Logo             │
├─────────────────────────┤
│  MAIN                   │
│  • Dashboard            │
│  • Conversations        │
│  • Profile              │
│  • Notifications        │
│  • Help & Support       │
├─────────────────────────┤
│  SETTINGS               │
│  • LLM Settings         │
│  • MCP                  │
│  • Prompts              │
│  • Memory               │
│  • Analytics            │
├─────────────────────────┤
│  ACCOUNT                │
│  • User Settings        │
│  • Billing              │
│  • API Keys             │
├─────────────────────────┤
│  DATA & TOOLS           │
│  • Databases            │
│  • Code Snippets        │
│  • Integrations         │
│  • Backup & Restore     │
└─────────────────────────┘
```

**Top Navigation (Header):**
- Logo (left)
- Search bar (center)
- Notifications (right)
- User menu (right)
- Settings icon (right)

### Page Hierarchy

```
/
├── / (Landing Page)
│   ├── Hero Section
│   ├── Features Grid
│   ├── How It Works
│   ├── Testimonials
│   ├── Pricing Preview
│   └── CTA Section
│
├── /auth/*
│   ├── /auth/login
│   ├── /auth/register
│   ├── /auth/forgot-password
│   └── /auth/reset-password
│
├── /dashboard (Authenticated)
│   ├── Quick Stats
│   ├── Recent Conversations
│   ├── Quick Actions
│   └── Activity Feed
│
├── /conversations
│   ├── List View
│   ├── Search & Filters
│   └── Create New
│
├── /conversations/:id
│   ├── / (Workspace Tab)
│   ├── /browser
│   ├── /served
│   ├── /terminal
│   └── /vscode
│
├── /settings/*
│   ├── /settings (LLM Settings)
│   ├── /settings/mcp
│   ├── /settings/user
│   ├── /settings/integrations
│   ├── /settings/databases
│   ├── /settings/knowledge-base
│   ├── /settings/memory
│   ├── /settings/analytics
│   ├── /settings/prompts
│   ├── /settings/snippets
│   ├── /settings/slack
│   ├── /settings/backup
│   ├── /settings/app
│   ├── /settings/billing
│   ├── /settings/secrets
│   └── /settings/api-keys
│
├── /profile
├── /notifications
├── /help
├── /database-browser
├── /microagent-management
│
├── /admin/* (Admin Only)
│   ├── /admin/users
│   └── /admin/users/:userId
│
└── /legal/*
    ├── /terms
    ├── /privacy
    ├── /about
    ├── /contact
    └── /pricing
```

---

## Detailed Page Specifications

### 1. Landing Page (`/`)

**Layout:**
```
┌─────────────────────────────────────────┐
│  Header (Transparent)                   │
├─────────────────────────────────────────┤
│                                         │
│  Hero Section                           │
│  - Headline                             │
│  - Subheadline                          │
│  - CTA Buttons                          │
│  - Hero Visual                          │
│                                         │
├─────────────────────────────────────────┤
│  Features Grid                          │
│  - 6 Feature Cards                      │
│                                         │
├─────────────────────────────────────────┤
│  How It Works                           │
│  - 3 Step Process                       │
│                                         │
├─────────────────────────────────────────┤
│  Testimonials                           │
│  - Carousel                             │
│                                         │
├─────────────────────────────────────────┤
│  Pricing Preview                        │
│  - 3 Tiers                              │
│                                         │
├─────────────────────────────────────────┤
│  Final CTA                              │
│                                         │
├─────────────────────────────────────────┤
│  Footer                                 │
└─────────────────────────────────────────┘
```

**Components:**
- `HeroSection` - Full-width hero with gradient background
- `FeaturesGrid` - 3-column grid of feature cards
- `SimpleHowItWorks` - Step-by-step process
- `TestimonialsSection` - User testimonials carousel
- `ValueProposition` - Key benefits
- `FinalCTA` - Call-to-action section
- `Footer` - Site footer with links

### 2. Dashboard (`/dashboard`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Page Title: Dashboard       │
│          │                              │
│          │  ┌─────────┬──────────────┐  │
│          │  │ Quick   │ Quick        │  │
│          │  │ Stats   │ Actions      │  │
│          │  └─────────┴──────────────┘  │
│          │                              │
│          │  Recent Conversations        │
│          │  ┌────────────────────────┐  │
│          │  │ Conversation Card 1    │  │
│          │  │ Conversation Card 2    │  │
│          │  │ Conversation Card 3    │  │
│          │  └────────────────────────┘  │
│          │                              │
│          │  Activity Feed               │
│          │  ┌────────────────────────┐  │
│          │  │ Activity Item 1        │  │
│          │  │ Activity Item 2        │  │
│          │  └────────────────────────┘  │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Components:**
- `QuickStats` - 4 stat cards (Total conversations, Active, Cost, Success rate)
- `QuickActions` - Action buttons (New Conversation, View All, Analytics)
- `RecentConversations` - List of recent conversations
- `ActivityFeed` - Recent activity timeline

### 3. Conversations List (`/conversations`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Conversations               │
│          │  [Search] [Filter] [+ New]   │
│          │                              │
│          │  ┌────────────────────────┐  │
│          │  │ Conversation 1         │  │
│          │  │ • Title                │  │
│          │  │ • Preview              │  │
│          │  │ • Date & Status        │  │
│          │  └────────────────────────┘  │
│          │  ┌────────────────────────┐  │
│          │  │ Conversation 2         │  │
│          │  └────────────────────────┘  │
│          │  ...                         │
│          │                              │
│          │  [Load More]                 │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Components:**
- `ConversationSearch` - Search input with filters
- `ConversationCard` - Individual conversation card
- `ConversationFilters` - Filter dropdowns (Status, Date, Model)
- `CreateConversationButton` - Floating action button

### 4. Conversation Workspace (`/conversations/:id`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  [Tabs: Workspace|Browser|...]│
│          ├──────────┬───────────────────┤
│          │          │                   │
│          │ Chat     │ Workspace         │
│          │ Panel    │                   │
│          │          │ File Explorer     │
│          │          │                   │
│          │          │ Code Editor       │
│          │          │                   │
│          │          │ Terminal          │
│          │          │                   │
│          ├──────────┴───────────────────┤
│          │  Input Area                  │
│          │  [Message Input] [Send]      │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Components:**
- `ConversationTabs` - Tab navigation (Workspace, Browser, App, etc.)
- `ChatPanel` - Message history with streaming
- `FileExplorer` - File tree sidebar
- `CodeEditor` - Monaco editor with syntax highlighting
- `Terminal` - XTerm.js terminal
- `MessageInput` - Rich text input with attachments
- `AgentControls` - Play/Pause/Stop controls
- `AgentStatusBar` - Status indicators

### 5. Settings Pages (`/settings/*`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Settings                    │
│          │  [Sub-nav: LLM|MCP|User|...] │
│          ├──────────────────────────────┤
│          │                              │
│          │  Page Title                  │
│          │  Description                 │
│          │                              │
│          │  ┌────────────────────────┐  │
│          │  │ Setting Section 1      │  │
│          │  │ • Option 1             │  │
│          │  │ • Option 2             │  │
│          │  └────────────────────────┘  │
│          │                              │
│          │  ┌────────────────────────┐  │
│          │  │ Setting Section 2      │  │
│          │  └────────────────────────┘  │
│          │                              │
│          │  [Save Changes]              │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Settings Sub-pages:**
1. **LLM Settings** (`/settings`)
   - Model selection
   - API key management
   - Temperature, max tokens
   - Advanced options

2. **MCP Settings** (`/settings/mcp`)
   - MCP server configuration
   - Tool management
   - Marketplace integration

3. **User Settings** (`/settings/user`)
   - Profile information
   - Preferences
   - Theme settings

4. **Integrations** (`/settings/integrations`)
   - GitHub
   - Slack
   - API connections

5. **Databases** (`/settings/databases`)
   - Database connections
   - Query history
   - Schema browser

6. **Knowledge Base** (`/settings/knowledge-base`)
   - Document management
   - Vector store settings
   - Search configuration

7. **Memory** (`/settings/memory`)
   - Memory settings
   - Condensation preferences
   - Context window

8. **Analytics** (`/settings/analytics`)
   - Usage statistics
   - Cost tracking
   - Performance metrics

9. **Prompts** (`/settings/prompts`)
   - Custom prompts
   - Template management
   - Prompt optimization

10. **Snippets** (`/settings/snippets`)
    - Code snippets library
    - Categories
    - Search

11. **Slack** (`/settings/slack`)
    - Slack workspace connection
    - Channel configuration
    - Notifications

12. **Backup** (`/settings/backup`)
    - Backup settings
    - Restore options
    - Export/Import

13. **App Settings** (`/settings/app`)
    - General preferences
    - UI customization
    - Keyboard shortcuts

14. **Billing** (`/settings/billing`)
    - Subscription management
    - Payment methods
    - Usage limits
    - Invoice history

15. **Secrets** (`/settings/secrets`)
    - Encrypted secrets management
    - Environment variables
    - Security settings

16. **API Keys** (`/settings/api-keys`)
    - API key generation
    - Key management
    - Permissions

### 6. Profile Page (`/profile`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Profile                     │
│          ├──────────────────────────────┤
│          │  ┌────────────────────────┐  │
│          │  │ Avatar                 │  │
│          │  │ Name                   │  │
│          │  │ Email                  │  │
│          │  │ Role                   │  │
│          │  └────────────────────────┘  │
│          │                              │
│          │  Statistics                  │
│          │  ┌──────┬──────┬──────┐     │
│          │  │ Total│ Active│ Cost │     │
│          │  └──────┴──────┴──────┘     │
│          │                              │
│          │  Recent Activity             │
│          │  ┌────────────────────────┐  │
│          │  │ Activity Timeline      │  │
│          │  └────────────────────────┘  │
│          │                              │
└──────────┴──────────────────────────────┘
```

### 7. Database Browser (`/database-browser`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Database Browser            │
│          ├──────────┬───────────────────┤
│          │ Schema   │ Query Editor      │
│          │ Browser  │                   │
│          │          │ [SQL Input]       │
│          │          │                   │
│          │          │ [Execute]         │
│          │          │                   │
│          │          │ Results Table     │
│          │          │                   │
│          │          │                   │
└──────────┴──────────────────────────────┘
```

**Components:**
- `SchemaBrowser` - Database schema tree
- `QueryEditor` - SQL editor with autocomplete
- `QueryResults` - Results table with pagination
- `QueryHistory` - Previous queries

### 8. Microagent Management (`/microagent-management`)

**Layout:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  Microagent Management       │
│          │  [+ Create Microagent]       │
│          │                              │
│          │  ┌────────────────────────┐  │
│          │  │ Microagent Card 1      │  │
│          │  │ • Name                 │  │
│          │  │ • Description          │  │
│          │  │ • Status               │  │
│          │  │ • Actions              │  │
│          │  └────────────────────────┘  │
│          │  ...                         │
│          │                              │
└──────────┴──────────────────────────────┘
```

### 9. Admin Pages (`/admin/*`)

**User Management:**
```
┌──────────┬──────────────────────────────┐
│ Sidebar  │  Header                      │
│          ├──────────────────────────────┤
│          │  User Management             │
│          │  [Search] [Filter]           │
│          │                              │
│          │  ┌────────────────────────┐  │
│          │  │ User Table             │  │
│          │  │ • Name                 │  │
│          │  │ • Email                │  │
│          │  │ • Role                 │  │
│          │  │ • Status               │  │
│          │  │ • Actions              │  │
│          │  └────────────────────────┘  │
│          │                              │
└──────────┴──────────────────────────────┘
```

---

## User Flows

### Flow 1: New User Onboarding

```
Landing Page
    ↓
Register/Login
    ↓
Accept Terms of Service
    ↓
Welcome Tour (Optional)
    ↓
Dashboard (First Time)
    ↓
LLM Setup Wizard
    ↓
Create First Conversation
    ↓
Conversation Workspace
```

### Flow 2: Creating a Conversation

```
Dashboard
    ↓
Click "New Conversation"
    ↓
Conversation Created
    ↓
Redirect to Workspace
    ↓
Type First Message
    ↓
Agent Responds
    ↓
Continue Conversation
```

### Flow 3: Configuring LLM

```
Settings → LLM Settings
    ↓
Select Provider
    ↓
Enter API Key
    ↓
Select Model
    ↓
Configure Parameters
    ↓
Test Connection
    ↓
Save Settings
```

### Flow 4: Managing Integrations

```
Settings → Integrations
    ↓
Select Provider (GitHub)
    ↓
OAuth Flow
    ↓
Authorize Access
    ↓
Configure Settings
    ↓
Test Connection
    ↓
Save
```

---

## Responsive Design

### Breakpoints

```
Mobile: < 640px
Tablet: 640px - 1024px
Desktop: 1024px - 1536px
Large Desktop: > 1536px
```

### Mobile Adaptations

**Sidebar:**
- Collapsed by default
- Hamburger menu
- Overlay on mobile

**Conversation Workspace:**
- Stack panels vertically
- Tab navigation at top
- Full-width panels

**Settings:**
- Single column layout
- Accordion sections
- Bottom navigation

### Tablet Adaptations

**Sidebar:**
- Collapsible
- Overlay when open

**Workspace:**
- 2-column layout
- Resizable panels

---

## Accessibility

### WCAG 2.1 AA Compliance

**Color Contrast:**
- Text: 4.5:1 minimum
- Large text: 3:1 minimum
- Interactive elements: 3:1 minimum

**Keyboard Navigation:**
- All interactive elements keyboard accessible
- Focus indicators visible
- Tab order logical
- Skip links for main content

**Screen Readers:**
- Semantic HTML
- ARIA labels
- Alt text for images
- Live regions for dynamic content

**Motion:**
- Respect `prefers-reduced-motion`
- Disable animations when requested

---

## Component Patterns

### Loading States

**Skeleton Loaders:**
- Match content structure
- Shimmer animation
- Placeholder text

**Spinners:**
- Violet brand color
- Size variants (sm, md, lg)
- Centered or inline

### Error States

**Error Messages:**
- Red accent color
- Clear error text
- Actionable suggestions
- Dismissible

**Empty States:**
- Illustrative icon
- Helpful message
- Call-to-action

### Success States

**Success Messages:**
- Green accent color
- Checkmark icon
- Auto-dismiss after 3s

### Form Validation

**Inline Validation:**
- Real-time feedback
- Error messages below fields
- Success indicators

**Form Submission:**
- Loading state on submit
- Success/error toast
- Form reset on success

---

## Animation Guidelines

### Page Transitions

**Route Changes:**
- Fade out: 150ms
- Fade in: 300ms
- Total: 450ms

### Micro-interactions

**Button Hover:**
- Scale: 1.02
- Duration: 150ms

**Card Hover:**
- Elevate shadow
- Duration: 200ms

**Input Focus:**
- Border color change
- Ring animation
- Duration: 200ms

### Message Animations

**New Message:**
- Slide up + fade in
- Staggered for multiple
- Duration: 300ms

**Streaming Text:**
- Typewriter effect
- Cursor blink

---

## Performance Optimizations

### Code Splitting

- Route-based splitting
- Component lazy loading
- Dynamic imports

### Image Optimization

- WebP format
- Lazy loading
- Responsive images
- Placeholder blur

### Bundle Size

- Tree shaking
- Minification
- Compression (gzip/brotli)

### Caching

- Static assets: Long cache
- API responses: Short cache
- Service worker for offline

---

## Design Tokens

### Spacing Scale
```typescript
const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
  '4xl': '6rem',   // 96px
}
```

### Typography Scale
```typescript
const typography = {
  xxs: { size: '0.75rem', lineHeight: 1.5 },
  xs: { size: '0.875rem', lineHeight: 1.5 },
  s: { size: '1rem', lineHeight: 1.5 },
  m: { size: '1.125rem', lineHeight: 1.5 },
  l: { size: '1.5rem', lineHeight: 1.2 },
  xl: { size: '2rem', lineHeight: 1.2 },
  xxl: { size: '2.25rem', lineHeight: 1.2 },
  xxxl: { size: '3rem', lineHeight: 1.2 },
}
```

### Color Tokens
```typescript
const colors = {
  background: {
    primary: '#000000',
    surface: '#000000',
    elevated: '#000000',
  },
  brand: {
    violet: '#8b5cf6',
    violetDark: '#7c3aed',
    violetLight: '#a78bfa',
  },
  text: {
    primary: '#FFFFFF',
    secondary: '#F1F5F9',
    tertiary: '#94A3B8',
    muted: '#6a6f7f',
  },
  border: {
    primary: '#1a1a1a',
    secondary: '#0f0f0f',
    accent: '#8b5cf6',
  },
}
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Design system tokens
- [ ] Base components (Button, Input, Card)
- [ ] Layout components (Sidebar, Header, Footer)
- [ ] Typography system
- [ ] Color system

### Phase 2: Core Pages
- [ ] Landing page
- [ ] Authentication pages
- [ ] Dashboard
- [ ] Conversations list
- [ ] Conversation workspace

### Phase 3: Settings
- [ ] Settings layout
- [ ] LLM settings
- [ ] User settings
- [ ] Integrations
- [ ] Billing

### Phase 4: Advanced Features
- [ ] Database browser
- [ ] Microagent management
- [ ] Admin pages
- [ ] Analytics dashboards

### Phase 5: Polish
- [ ] Animations
- [ ] Loading states
- [ ] Error handling
- [ ] Accessibility audit
- [ ] Performance optimization

---

## Design Resources

### Icons
- **Lucide React** - Primary icon library
- **React Icons** - Additional icons
- **Custom SVG** - Brand-specific icons

### Illustrations
- Custom illustrations for empty states
- Hero graphics
- Feature illustrations

### Fonts
- **Inter** - Primary font (Google Fonts)
- **JetBrains Mono** - Code font (Google Fonts)

---

## Conclusion

This design system provides a comprehensive foundation for building a modern, professional, and user-friendly interface for the Forge platform. The design emphasizes clarity, performance, and accessibility while maintaining a premium aesthetic that reflects the quality of the underlying technology.

All components and pages should follow these guidelines to ensure consistency and a cohesive user experience across the entire application.

