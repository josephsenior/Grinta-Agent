# 📘 **TypeScript SDK**

> **Type-safe TypeScript library for Forge frontend integration**

---

## 📖 **Table of Contents**

- [Installation](#installation)
- [Quick Start](#quick-start)
- [React Hooks](#react-hooks)
- [Core API](#core-api)
- [Examples](#examples)

---

## 📦 **Installation**

### **npm**

```bash
npm install @Forge/sdk
```

### **yarn**

```bash
yarn add @Forge/sdk
```

### **pnpm**

```bash
pnpm add @Forge/sdk
```

---

## 🚀 **Quick Start**

### **Initialize Client**

```typescript
import { ForgeClient } from '@Forge/sdk';

// Create client
const client = new ForgeClient({
  baseUrl: 'http://localhost:3000',
  apiKey: process.env.FORGE_API_KEY,
});

// Create conversation
const conversation = await client.conversations.create();

// Send message
const response = await client.conversations.sendMessage({
  conversationId: conversation.id,
  message: 'Build a todo app with React',
});

console.log(response.content);
```

---

## ⚛️ **React Hooks**

### **`useForge`**

Main hook for Forge integration.

```typescript
import { useForge } from '@Forge/sdk/react';

function MyComponent() {
  const { client, conversation, messages, sendMessage, loading } = useForge({
    baseUrl: 'http://localhost:3000',
  });

  const handleSend = async () => {
    await sendMessage('Create a REST API');
  };

  return (
    <div>
      {messages.map((msg) => (
        <div key={msg.id}>{msg.content}</div>
      ))}
      <button onClick={handleSend} disabled={loading}>
        Send
      </button>
    </div>
  );
}
```

---

### **`useConversation`**

Manage a single conversation.

```typescript
import { useConversation } from '@Forge/sdk/react';

function Chat() {
  const {
    messages,
    sendMessage,
    loading,
    error,
  } = useConversation({
    conversationId: 'conv-123',
  });

  return (
    <div>
      {error && <div>Error: {error.message}</div>}
      
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}
      
      <input
        onSubmit={(text) => sendMessage(text)}
        disabled={loading}
      />
    </div>
  );
}
```

---

### **`useMetaSOP`**

MetaSOP orchestration hook.

```typescript
import { useMetaSOP } from '@Forge/sdk/react';

function MetaSOPPanel() {
  const {
    orchestration,
    artifacts,
    steps,
    startOrchestration,
    loading,
  } = useMetaSOP({
    conversationId: 'conv-123',
  });

  const handleStart = async () => {
    await startOrchestration({
      userRequest: 'Build a blog platform',
      template: 'full_stack_dev',
    });
  };

  return (
    <div>
      <button onClick={handleStart} disabled={loading}>
        Start MetaSOP
      </button>
      
      {steps.map((step) => (
        <StepCard key={step.id} step={step} />
      ))}
      
      {artifacts && (
        <ArtifactViewer artifacts={artifacts} />
      )}
    </div>
  );
}
```

---

### **`useWebSocket`**

WebSocket connection hook.

```typescript
import { useWebSocket } from '@Forge/sdk/react';

function LiveUpdates() {
  const { events, connected, error } = useWebSocket({
    conversationId: 'conv-123',
    onEvent: (event) => {
      console.log('Event received:', event);
    },
  });

  return (
    <div>
      <ConnectionStatus connected={connected} error={error} />
      
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </div>
  );
}
```

---

## 🏗️ **Core API**

### **`ForgeClient`**

Main client class.

```typescript
class ForgeClient {
  constructor(config: ClientConfig);
  
  // API namespaces
  conversations: ConversationsAPI;
  metasop: MetaSOPAPI;
  optimization: OptimizationAPI;
  
  // WebSocket
  connectWebSocket(conversationId: string): WebSocketConnection;
}
```

**Config:**

```typescript
interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  headers?: Record<string, string>;
}
```

---

### **`ConversationsAPI`**

Conversation management.

```typescript
class ConversationsAPI {
  // Create conversation
  create(): Promise<Conversation>;
  
  // Get conversation
  get(conversationId: string): Promise<Conversation>;
  
  // List conversations
  list(options?: ListOptions): Promise<Conversation[]>;
  
  // Send message
  sendMessage(params: SendMessageParams): Promise<Message>;
  
  // Get messages
  getMessages(conversationId: string): Promise<Message[]>;
  
  // Stream response
  streamMessage(
    params: SendMessageParams
  ): AsyncIterableIterator<MessageChunk>;
}
```

**Types:**

```typescript
interface Conversation {
  id: string;
  status: 'active' | 'archived';
  createdAt: Date;
  updatedAt: Date;
}

interface Message {
  id: number;
  conversationId: string;
  source: 'user' | 'agent' | 'environment';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

interface SendMessageParams {
  conversationId: string;
  message: string;
  enableMetaSOP?: boolean;
  metadata?: Record<string, any>;
}
```

---

### **`MetaSOPAPI`**

MetaSOP orchestration.

```typescript
class MetaSOPAPI {
  // Start orchestration
  startOrchestration(
    params: StartOrchestrationParams
  ): Promise<Orchestration>;
  
  // Get orchestration status
  getOrchestration(orchestrationId: string): Promise<Orchestration>;
  
  // Get artifacts
  getArtifacts(orchestrationId: string): Promise<Artifacts>;
  
  // Stream orchestration events
  streamOrchestration(
    orchestrationId: string
  ): AsyncIterableIterator<OrchestrationEvent>;
}
```

**Types:**

```typescript
interface Orchestration {
  id: string;
  conversationId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  template: string;
  userRequest: string;
  startedAt: Date;
  completedAt?: Date;
}

interface Artifacts {
  pm_spec?: PMSpecArtifact;
  architect?: ArchitectArtifact;
  engineer?: EngineerArtifact;
  qa?: QAArtifact;
  ui_designer?: UIDesignerArtifact;
}

interface StartOrchestrationParams {
  conversationId: string;
  userRequest: string;
  template?: string;
}
```

---

### **`OptimizationAPI`**

Prompt optimization.

```typescript
class OptimizationAPI {
  // Get metrics
  getMetrics(): Promise<OptimizationMetrics>;
  
  // Get variants
  getVariants(promptId: string): Promise<Variant[]>;
  
  // Get best variant
  getBestVariant(promptId: string): Promise<Variant>;
}
```

---

## 💡 **Examples**

### **Example 1: Basic Chat**

```typescript
import { ForgeClient } from '@Forge/sdk';

async function basicChat() {
  const client = new ForgeClient({
    baseUrl: 'http://localhost:3000',
  });

  // Create conversation
  const conv = await client.conversations.create();
  console.log('Conversation created:', conv.id);

  // Send message
  const response = await client.conversations.sendMessage({
    conversationId: conv.id,
    message: 'Explain how React hooks work',
  });

  console.log('Response:', response.content);
}
```

---

### **Example 2: Streaming Response**

```typescript
import { ForgeClient } from '@Forge/sdk';

async function streamingChat() {
  const client = new ForgeClient({
    baseUrl: 'http://localhost:3000',
  });

  const conv = await client.conversations.create();

  // Stream response
  const stream = client.conversations.streamMessage({
    conversationId: conv.id,
    message: 'Write a React component',
  });

  for await (const chunk of stream) {
    process.stdout.write(chunk.content);
  }
}
```

---

### **Example 3: MetaSOP Orchestration**

```typescript
import { ForgeClient } from '@Forge/sdk';

async function runMetaSOP() {
  const client = new ForgeClient({
    baseUrl: 'http://localhost:3000',
  });

  const conv = await client.conversations.create();

  // Start orchestration
  const orch = await client.metasop.startOrchestration({
    conversationId: conv.id,
    userRequest: 'Build a todo app with auth',
    template: 'full_stack_dev',
  });

  console.log('Orchestration started:', orch.id);

  // Stream events
  const eventStream = client.metasop.streamOrchestration(orch.id);

  for await (const event of eventStream) {
    if (event.type === 'metasop_step_complete') {
      console.log(`${event.role} completed:`, event.artifact);
    }
  }

  // Get final artifacts
  const artifacts = await client.metasop.getArtifacts(orch.id);
  console.log('PM Spec:', artifacts.pm_spec);
  console.log('Architecture:', artifacts.architect);
}
```

---

### **Example 4: React Component**

```tsx
import { useForge } from '@Forge/sdk/react';
import { useState } from 'react';

export function ChatInterface() {
  const [input, setInput] = useState('');
  const {
    messages,
    sendMessage,
    loading,
    error,
  } = useForge({
    baseUrl: process.env.REACT_APP_FORGE_URL!,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    await sendMessage(input);
    setInput('');
  };

  return (
    <div className="chat-interface">
      <div className="messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message message-${msg.source}`}
          >
            <div className="message-content">{msg.content}</div>
            <div className="message-timestamp">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {loading && <div className="loading">Thinking...</div>}
        {error && <div className="error">{error.message}</div>}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
```

---

### **Example 5: Error Handling**

```typescript
import { ForgeClient, ForgeError } from '@Forge/sdk';

async function handleErrors() {
  const client = new ForgeClient({
    baseUrl: 'http://localhost:3000',
  });

  try {
    const conv = await client.conversations.get('invalid-id');
  } catch (error) {
    if (error instanceof ForgeError) {
      switch (error.code) {
        case 'NOT_FOUND':
          console.error('Conversation not found');
          break;
        case 'RATE_LIMIT':
          console.error('Rate limited, retry after:', error.retryAfter);
          break;
        case 'API_ERROR':
          console.error('API error:', error.message);
          break;
        default:
          console.error('Unknown error:', error);
      }
    }
  }
}
```

---

## 🎨 **React Hook API Reference**

### **`useForge`**

```typescript
function useForge(config: UseForgeConfig): UseForgeReturn;

interface UseForgeConfig {
  baseUrl: string;
  apiKey?: string;
  autoConnect?: boolean;
}

interface UseForgeReturn {
  client: ForgeClient;
  conversation: Conversation | null;
  messages: Message[];
  sendMessage: (message: string) => Promise<void>;
  loading: boolean;
  error: Error | null;
}
```

### **`useMetaSOP`**

```typescript
function useMetaSOP(config: UseMetaSOPConfig): UseMetaSOPReturn;

interface UseMetaSOPConfig {
  conversationId: string;
  autoStart?: boolean;
}

interface UseMetaSOPReturn {
  orchestration: Orchestration | null;
  artifacts: Artifacts | null;
  steps: OrchestrationStep[];
  startOrchestration: (params: StartParams) => Promise<void>;
  loading: boolean;
  error: Error | null;
}
```

---

## 🧪 **Testing**

### **Mock Client**

```typescript
import { createMockClient } from '@Forge/sdk/testing';

// Create mock
const mockClient = createMockClient({
  conversations: {
    create: jest.fn().mockResolvedValue({
      id: 'test-123',
      status: 'active',
      createdAt: new Date(),
      updatedAt: new Date(),
    }),
  },
});

// Use in tests
const conv = await mockClient.conversations.create();
expect(conv.id).toBe('test-123');
```

### **React Testing**

```typescript
import { render, screen } from '@testing-library/react';
import { ForgeProvider } from '@Forge/sdk/react';
import { createMockClient } from '@Forge/sdk/testing';

test('renders chat interface', () => {
  const mockClient = createMockClient();

  render(
    <ForgeProvider client={mockClient}>
      <ChatInterface />
    </ForgeProvider>
  );

  expect(screen.getByPlaceholderText('Ask anything...')).toBeInTheDocument();
});
```

---

## 📚 **Related Documentation**

- [REST API](rest-api.md)
- [WebSocket API](websocket-api.md)
- [React Integration](../guides/react-integration.md)
- [Getting Started](../guides/getting-started.md)

---

**The TypeScript SDK provides a fully type-safe, modern interface for building Forge-powered applications!**

