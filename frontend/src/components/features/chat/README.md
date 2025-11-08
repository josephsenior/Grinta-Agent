# Chat Interface Architecture

This document explains the architecture and design patterns used in the chat interface components.

## Overview

The chat interface is built using a modular, hook-based architecture that separates concerns and makes the code more maintainable and testable.

## Architecture Patterns

### 1. Custom Hooks Pattern

Complex state and side effects are extracted into custom hooks:

- `useChatInterfaceState` - Manages all chat interface state
- `useChatKeyboardShortcuts` - Handles keyboard shortcuts
- `useChatMessageHandlers` - Manages message operations
- `useChatFeedbackActions` - Handles feedback and actions
- `useFilteredEvents` - Filters events based on settings

### 2. Component Composition

The main `ChatInterface` component is composed of smaller, focused components:

```tsx
<ChatInterface>
  <Header />
  <TaskPanel />
  <Messages />
  <Suggestions />
  <ChatInput />
  <Modals />
</ChatInterface>
```

### 3. Error Boundaries

Comprehensive error handling with recovery options:

- `GlobalErrorBoundary` - Catches application-wide errors
- `ChatErrorBoundary` - Specific to chat functionality

## Key Components

### ChatInterface

The main chat interface component that orchestrates all chat functionality.

**Responsibilities:**
- Layout and structure
- State coordination
- Event handling
- Modal management

**Props:** None (uses hooks for all state)

### Messages

Renders the conversation messages with turn-based grouping.

**Responsibilities:**
- Message rendering
- Turn grouping
- Microagent status
- Event filtering

**Props:**
```tsx
interface MessagesProps {
  messages: (ForgeAction | ForgeObservation)[];
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails?: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
}
```

### EventMessage

Renders individual events with appropriate styling and actions.

**Responsibilities:**
- Event type detection
- Content rendering
- Action buttons
- Error handling

### InteractiveChatBox

The chat input component with file upload and message sending.

**Responsibilities:**
- Message input
- File uploads
- Message sending
- Stop functionality

## State Management

### Local State

Component-specific state is managed using React hooks:

```tsx
const [isOpen, setIsOpen] = useState(false);
const [loading, setLoading] = useState(false);
```

### Global State

Shared state is managed through context:

- `TaskContext` - Task management
- `WsClientContext` - WebSocket connection
- Redux store - Agent state, metrics

### Derived State

Computed state is derived using `useMemo`:

```tsx
const filteredEvents = useMemo(() => 
  events.filter(shouldRenderEvent), 
  [events, showTechnicalDetails]
);
```

## Event Flow

1. **User Input** → `InteractiveChatBox`
2. **Message Creation** → `useChatMessageHandlers`
3. **WebSocket Send** → `WsClient`
4. **Event Processing** → `useFilteredEvents`
5. **UI Update** → `Messages` component

## Error Handling

### Error Boundaries

```tsx
<GlobalErrorBoundary>
  <ChatErrorBoundary>
    <ChatInterface />
  </ChatErrorBoundary>
</GlobalErrorBoundary>
```

### Error Recovery

- Retry mechanisms
- Graceful degradation
- User-friendly error messages
- Development error details

## Performance Optimizations

### Memoization

```tsx
const Messages = React.memo(function Messages({ messages, ... }) {
  // Component implementation
});
```

### Callback Optimization

```tsx
const handleClick = useCallback(() => {
  // Handle click
}, [dependencies]);
```

### Event Filtering

Events are filtered at the hook level to prevent unnecessary re-renders:

```tsx
const events = useFilteredEvents(parsedEvents, showTechnicalDetails);
```

## Testing Strategy

### Unit Tests

- Individual hook testing
- Component rendering tests
- Event handling tests

### Integration Tests

- Hook interaction tests
- Component composition tests
- Error boundary tests

### Test Utilities

```tsx
const renderWithProviders = (component) => {
  return render(
    <Provider store={mockStore}>
      <BrowserRouter>
        <TaskProvider>
          {component}
        </TaskProvider>
      </BrowserRouter>
    </Provider>
  );
};
```

## Best Practices

### 1. Separation of Concerns

- UI components focus on rendering
- Hooks handle logic and state
- Utilities handle data transformation

### 2. Error Handling

- Always wrap components in error boundaries
- Provide meaningful error messages
- Include recovery options

### 3. Performance

- Use React.memo for expensive components
- Memoize callbacks and computed values
- Filter data at the hook level

### 4. Testing

- Test hooks in isolation
- Mock external dependencies
- Test error scenarios

### 5. Accessibility

- Use semantic HTML
- Include ARIA labels
- Support keyboard navigation

## Future Improvements

1. **Virtualization** - For large message lists
2. **Offline Support** - Message queuing
3. **Real-time Collaboration** - Multiple users
4. **Advanced Filtering** - Message search
5. **Custom Themes** - User preferences
