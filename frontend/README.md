# Forge Frontend

## Overview

Modern React frontend with 300+ components, real-time WebSocket communication, and a polished UX.

## Authentication

Forge OSS uses a session API key for both HTTP and Socket.IO. The single source of truth is [docs/AUTH.md](../docs/AUTH.md).

## Technology Stack

- **Framework:** React 18 with TypeScript
- **State Management:** Redux Toolkit + React Query
- **Styling:** Tailwind CSS v4
- **Build Tool:** Vite
- **Real-Time:** WebSocket client
- **Icons:** Lucide React
- **Animations:** CSS transitions + custom animations
- **Forms:** React Hook Form
- **Routing:** React Router v6

## Project Structure

```
frontend/src/
├── api/                    # API client and generated types
├── assets/                 # Images, fonts, static files
├── components/             # React components (300+)
│   ├── features/          # Feature-specific components
│   │   ├── chat/          # Chat interface (68 files)
│   │   ├── settings/      # Settings UI (52 files)
│   │   ├── monitoring/    # Monitoring dashboards (7 files)
│   │   ├── analytics/     # Analytics (4 files)
│   │   └── ...            # 20+ feature areas
│   ├── shared/            # Reusable components
│   ├── ui/                # Base UI components
│   └── landing/           # Landing page components
├── context/               # React Context providers
├── hooks/                 # Custom React hooks
│   ├── query/            # React Query hooks
│   └── mutation/         # Mutation hooks
├── store/                 # Redux store configuration
├── types/                 # TypeScript type definitions
├── utils/                 # Utility functions
└── i18n/                  # Internationalization (English only for beta)
```

## Key Components

### Chat Interface

**Main File:** `src/components/features/chat/chat-interface.tsx`

**Features:**
- Real-time message streaming
- Markdown rendering with syntax highlighting
- Code diff viewer
- File attachments
- Agent control (pause, resume, stop)
- Cost tracking display
- Typing indicators
- Error handling

**Sub-components (68 files):**
- `messages.tsx` - Message list with virtualization
- `chat-message.tsx` - Individual message rendering
- `modern-chat-input.tsx` - Message input with attachments
- `streaming-chat-message.tsx` - Real-time streaming display
- `error-message.tsx` - User-friendly error display
- `code-artifact.tsx` - Code block with copy button
- And 60+ more...

### Settings UI

**Location:** `src/components/features/settings/`

**52 Setting Components:**
- Model selection (200+ models)
- API key management
- Agent configuration
- Security settings
- Cost quotas
- Theme preferences
- Advanced options

### Monitoring Dashboards

**Location:** `src/components/features/monitoring/`

**7 Monitoring Components:**
- `live-metrics-cards.tsx` - Real-time metrics
- `autonomous-monitor.tsx` - Agent activity
- `risk-level-chart.tsx` - Security visualization
- `safety-score-gauge.tsx` - Safety metrics
- `enhanced-audit-trail.tsx` - Action history
- `command-blocking-card.tsx` - Blocked actions
- `animated-alert-banner.tsx` - Alert notifications

### Analytics

**Location:** `src/components/features/analytics/`

**Components:**
- `cost-chart.tsx` - Cost over time
- `model-usage-table.tsx` - Model statistics
- `stat-card.tsx` - Metric cards
- `analytics-consent-form-modal.tsx` - Privacy consent

## State Management

### Redux Store

**File:** `src/store.ts`

**Slices:**
```typescript
{
  settings: SettingsState,      // User preferences
  conversations: ConversationsState, // Conversation list
  chat: ChatState,               // Current conversation
  ws: WebSocketState,            // WebSocket connection
  ui: UIState                    // UI state (modals, etc.)
}
```

### React Query

**File:** `src/hooks/query/`

**Queries:**
- `use-config.ts` - Fetch server config
- `use-active-conversation.ts` - Current conversation
- `use-settings.ts` - User settings
- And 20+ more...

**Mutations:**
- `use-create-conversation.ts` - Create conversation
- `use-update-settings.ts` - Update settings
- `use-upload-files.ts` - Upload files
- And 15+ more...

### WebSocket Integration

**File:** `src/context/ws-client-provider.tsx`

**Features:**
- Automatic reconnection
- Event parsing and distribution
- Optimistic updates
- Error handling
- State synchronization

**Usage:**
```typescript
import { useWsClient } from "#/context/ws-client-provider";

function MyComponent() {
  const { send, isConnected, parsedEvents } = useWsClient();
  
  // Send message
  send({ type: 'message', content: 'Hello' });
  
  // Access events
  parsedEvents.forEach(event => {
    // Process event
  });
}
```

## Development

### Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

### Environment Variables

```bash
# frontend/.env
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000
VITE_POSTHOG_API_KEY=...
```

### Scripts

```bash
npm run dev          # Start dev server
npm run build        # Release build
npm run preview      # Preview release build
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler
```

## Component Patterns

### Functional Components with Hooks

```typescript
import React from "react";

export function MyComponent() {
  const [state, setState] = React.useState(initial);
  
  React.useEffect(() => {
    // Side effects
  }, [dependencies]);
  
  return <div>{content}</div>;
}
```

### Custom Hooks

```typescript
// src/hooks/use-example.ts
export function useExample() {
  const [data, setData] = React.useState(null);
  
  const fetchData = async () => {
    const result = await api.get('/data');
    setData(result);
  };
  
  return { data, fetchData };
}
```

### React Query Patterns

```typescript
// src/hooks/query/use-data.ts
export function useData() {
  return useQuery({
    queryKey: ['data'],
    queryFn: () => api.getData(),
    staleTime: 60_000,  // 1 minute
  });
}

// Usage:
const { data, isLoading, error } = useData();
```

### Redux Toolkit Slices

```typescript
import { createSlice } from '@reduxjs/toolkit';

const mySlice = createSlice({
  name: 'myFeature',
  initialState: {},
  reducers: {
    updateState: (state, action) => {
      state.value = action.payload;
    },
  },
});

export const { updateState } = mySlice.actions;
export default mySlice.reducer;
```

## Styling

### Tailwind CSS

**Configuration:** `tailwind.config.js`

**Common Patterns:**
```tsx
// Responsive design
<div className="w-full md:w-1/2 lg:w-1/3">

// State variants
<button className="bg-blue-500 hover:bg-blue-600 focus:ring-2">

// Dark mode (via CSS variables)
<div className="bg-background text-foreground">
```

### Custom Components

**Location:** `src/components/ui/`

**shadcn/ui components:**
- `button.tsx`
- `card.tsx`
- `input.tsx`
- `dialog.tsx`
- `dropdown-menu.tsx`
- `tabs.tsx`
- And more...

## WebSocket Communication

### Connection Management

```typescript
// Connect to conversation
const ws = new WebSocket(`ws://localhost:3000/ws/conversations/${id}`);

// Handle events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'action':
      // Agent action
      break;
    case 'observation':
      // Action result
      break;
    case 'state_change':
      // Agent state changed
      break;
  }
};

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'Build a todo app'
}));
```

### Event Types

```typescript
type WSEvent = 
  | { type: 'action', content: Action }
  | { type: 'observation', content: Observation }
  | { type: 'state_change', state: AgentState }
  | { type: 'error', error: Error };
```

## Performance Optimizations

### Already Implemented

**1. Code Splitting:**
- Lazy loading for routes
- Dynamic imports for heavy components

**2. React.memo:**
- Expensive components memoized
- Prevent unnecessary re-renders

**3. Virtualization:**
- Long message lists virtualized
- File lists virtualized

**4. Image Optimization:**
- Lazy loading for images
- Responsive images
- WebP format support

**5. Debouncing:**
- Input debouncing (300ms)
- Scroll event debouncing

## Accessibility

### Current Implementation

- ARIA labels on interactive elements
- Keyboard navigation for chat
- Screen reader support for messages
- Focus indicators
- Color contrast (basic)

### Keyboard Shortcuts

**File:** `src/components/features/chat/keyboard-shortcuts-panel.tsx`

**Shortcuts (disabled for beta, can be re-enabled):**
- `Enter` - Send message
- `Cmd+N` - New conversation
- `Cmd+K` - Search
- `Cmd+.` - Stop agent
- `Esc` - Cancel

## Testing

### Run Tests

```bash
npm run test         # Run all tests
npm run test:watch   # Watch mode
npm run test:coverage # Coverage report
```

### Test Structure

```typescript
// src/components/MyComponent.test.tsx
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

## Build & Deployment

### Development Build

```bash
npm run dev
```

### Release Build

```bash
npm run build

# Output in dist/
# Ready to serve with nginx, Caddy, etc.
```

### Environment-Specific Builds

```bash
# Staging
VITE_API_URL=https://staging-api.Forge.dev npm run build

# Hosted
VITE_API_URL=https://api.Forge.dev npm run build
```

## Contributing

### Code Style

- **ESLint:** Enforced via `.eslintrc.json`
- **Prettier:** Code formatting (run `npm run format`)
- **TypeScript:** Strict mode enabled

### Component Guidelines

1. **Functional components only** (no class components)
2. **TypeScript for all files** (.tsx, .ts)
3. **Props interfaces** at top of file
4. **Exported component** at bottom
5. **Hooks before return**

**Example:**
```typescript
interface MyComponentProps {
  title: string;
  onSave: () => void;
}

export function MyComponent({ title, onSave }: MyComponentProps) {
  const [state, setState] = React.useState(false);
  
  return <div>{title}</div>;
}
```

### Adding New Components

1. Create in appropriate directory (`features/` vs `shared/` vs `ui/`)
2. Export from index file
3. Add prop types
4. Add basic tests
5. Update documentation

## Common Patterns

### Error Boundaries

```typescript
<ErrorBoundary fallback={<ErrorFallback />}>
  <MyComponent />
</ErrorBoundary>
```

### Loading States

```typescript
if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorDisplay error={error} />;
return <Content data={data} />;
```

### Conditional Rendering

```typescript
{isEnabled && <Feature />}
{user ? <Authenticated /> : <Login />}
```

## Troubleshooting

### "Module not found"

```bash
# Clear cache
rm -rf node_modules
npm install
```

### "Type errors"

```bash
# Regenerate types from OpenAPI
cd ..
./scripts/generate-api-types.sh

# Or manually:
npx openapi-typescript http://localhost:3000/openapi.json -o frontend/src/api/schema.ts
```

### "WebSocket not connecting"

```bash
# Check backend is running
curl http://localhost:3000/api/monitoring/health

# Check WebSocket URL in .env
VITE_WS_URL=ws://localhost:3000
```

## References

- [Architecture](../docs/ARCHITECTURE.md) - System overview
- [API Reference](../docs/API_REFERENCE.md) - API documentation
- [Development Guide](../docs/development.md) - Dev setup
- [React Docs](https://react.dev) - React documentation
- [Tailwind Docs](https://tailwindcss.com) - Tailwind CSS documentation

For questions, see [Troubleshooting](../docs/TROUBLESHOOTING.md) or open a GitHub issue.
