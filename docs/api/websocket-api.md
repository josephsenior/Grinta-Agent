# 🔌 **WebSocket API**

> **Real-time bidirectional communication for live updates and streaming**

---

## 📖 **Table of Contents**

- [Overview](#overview)
- [Connection](#connection)
- [Events](#events)
- [Client Examples](#client-examples)
- [Error Handling](#error-handling)

---

## 🌟 **Overview**

The WebSocket API provides real-time, bidirectional communication between the backend and frontend. It's used for:

- Live agent status updates
- Streaming agent responses
- Real-time monitoring data

**Protocol**: Socket.IO (compatible with WebSocket)  
**Endpoint**: `http://localhost:3000` (Socket.IO path: `/socket.io`)  
**Authentication**: Session-based via query parameters

---

## 🔗 **Connection**

### **Connection URL**

```
http://localhost:3000/socket.io?conversationId=<id>&session_api_key=<key>
```

**Note:** The server runs on port 3000 by default. Socket.IO automatically handles the WebSocket upgrade.

### **Query Parameters**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `conversationId` | Yes | Conversation/session ID |
| `token` | No | Authentication token (if required) |

### **Connection Example (JavaScript)**

```typescript
import { io } from 'socket.io-client';

const socket = io('http://localhost:3000', {
  path: '/socket.io',
  query: {
    conversationId: 'abc123',
    session_api_key: 'your-session-key', // Optional, if required
  },
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5,
});

socket.on('connect', () => {
  console.log('Connected:', socket.id);
});

socket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
});
```

---

## 📡 **Events**

### **System Events**

#### **`connect`**
Fired when connection is established.

```typescript
socket.on('connect', () => {
  console.log('WebSocket connected');
});
```

#### **`disconnect`**
Fired when connection is lost.

```typescript
socket.on('disconnect', (reason: string) => {
  console.log('Disconnected:', reason);
  // Reasons: 'transport close', 'ping timeout', etc.
});
```

#### **`error`**
Fired on connection errors.

```typescript
socket.on('error', (error: Error) => {
  console.error('Socket error:', error);
});
```

---

### **Agent Events**

#### **`agent_state_changed`**
Agent status update.

**Payload:**
```typescript
interface AgentStateChanged {
  id: number;
  timestamp: string;
  source: 'environment';
  observation: 'agent_state_changed';
  extras: {
    agent_state: 'loading' | 'running' | 'awaiting_user_input' | 'finished' | 'error';
    reason?: string;
  };
}
```

**Example:**
```typescript
socket.on('message', (event: AgentStateChanged) => {
  if (event.observation === 'agent_state_changed') {
    console.log('Agent state:', event.extras.agent_state);
  }
});
```

#### **`agent_message`**
Message from agent.

**Payload:**
```typescript
interface AgentMessage {
  id: number;
  timestamp: string;
  source: 'agent';
  message: string;
  action?: string;
}
```

---

---

## 💻 **Client Examples**

### **React Hook Example**

```typescript
import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export function useWebSocket(conversationId: string) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const newSocket = io('http://localhost:3000', {
      path: '/socket.io',
      query: { conversationId },
      transports: ['websocket', 'polling'],
    });

    newSocket.on('connect', () => {
      console.log('Connected');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected');
      setConnected(false);
    });

    newSocket.on('message', (event) => {
      console.log('Event received:', event);
      setEvents((prev) => [...prev, event]);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [conversationId]);

  return { socket, connected, events };
}
```

### **Python Client Example**

```python
import socketio

# Create Socket.IO client
sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to WebSocket')

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from WebSocket')

@sio.on('message')
def on_message(data):
    print('Received:', data)
    
    if data.get('event_type') == 'agent_state_changed':
        print(f"Agent state: {data['extras']['agent_state']}")

# Connect
sio.connect(
    'http://localhost:3000',
    socketio_path='/socket.io',
    wait_timeout=10,
    headers={'conversationId': 'abc123'}
)

# Wait for events
sio.wait()
```

---

## 🚨 **Error Handling**

### **Connection Errors**

```typescript
socket.on('connect_error', (error: Error) => {
  console.error('Connection failed:', error.message);
  
  // Common causes:
  // - Backend not running
  // - CORS issues
  // - Invalid conversationId
});
```

### **Reconnection Logic**

```typescript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

socket.on('disconnect', (reason) => {
  if (reason === 'io server disconnect') {
    // Server disconnected, reconnect manually
    socket.connect();
  }
  // Otherwise Socket.IO will reconnect automatically
});

socket.on('reconnect_attempt', (attemptNumber) => {
  reconnectAttempts = attemptNumber;
  console.log(`Reconnection attempt ${attemptNumber}`);
  
  if (attemptNumber >= maxReconnectAttempts) {
    socket.disconnect();
    console.error('Max reconnection attempts reached');
  }
});

socket.on('reconnect', () => {
  console.log('Reconnected successfully');
  reconnectAttempts = 0;
});
```

### **Event Validation**

```typescript
function isValidEvent(event: any) {
  return event && typeof event.event_type === 'string';
}

socket.on('message', (event) => {
  if (isValidEvent(event)) {
    // Process event
    handleEvent(event);
  }
});
```

---

## 📊 **Event Flow Diagram**

```
Frontend                          Backend
   |                                 |
   |-------- Connect --------------->|
   |<------- Connected --------------|
   |                                 |
   |-- Send User Message ----------->|
   |                                 |
   |<-- agent_state_changed ---------|  (loading)
   |<-- agent_message ---------------|  (thinking)
   |<-- agent_message ---------------|  (executing)
   |<-- agent_state_changed ---------|  (awaiting_user_input)
```

---

## 🎯 **Best Practices**

### **1. Handle Reconnection**

Always implement reconnection logic:
```typescript
reconnection: true,
reconnectionDelay: 1000,
reconnectionAttempts: 5,
```

### **2. Validate Events**

Check event structure before using:
```typescript
if (event && typeof event === 'object' && 'event_type' in event) {
  // Safe to process
}
```

### **3. Debounce UI Updates**

For high-frequency events, debounce UI updates:
```typescript
const debouncedUpdate = debounce((event) => {
  updateUI(event);
}, 100);

socket.on('message', debouncedUpdate);
```

### **4. Cleanup on Unmount**

Always disconnect socket when component unmounts:
```typescript
useEffect(() => {
  return () => {
    socket?.disconnect();
  };
}, [socket]);
```

---

## 📚 **Related Documentation**

- [REST API](rest-api.md)
- [Streaming Processing](../features/streaming-processing.md)
- [Live Monitoring](../features/live-monitoring.md)

---

**WebSocket provides the real-time backbone of Forge, enabling live updates and responsive user experiences!**

