# 🐍 **Python SDK**

> **Python library for programmatic access to Forge functionality**

---

## 📖 **Table of Contents**

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Classes](#core-classes)
- [Examples](#examples)
- [API Reference](#api-reference)

---

## 📦 **Installation**

### **Install from PyPI**

```bash
pip install Forge-sdk
```

### **Install from Source**

```bash
git clone https://github.com/your-org/Forge.git
cd Forge
pip install -e .
```

---

## 🚀 **Quick Start**

### **Basic Usage**

```python
from forge import forge

# Initialize client
client = Forge(
    base_url="http://localhost:3000",
    api_key="your-api-key"  # Optional
)

# Create conversation
conversation = client.conversations.create()

# Send message
response = client.conversations.send_message(
    conversation_id=conversation.id,
    message="Build a todo app with React and FastAPI"
)

print(response.content)
```

### **With Environment Variables**

```bash
# Set environment variables
export FORGE_BASE_URL=http://localhost:3000
export FORGE_API_KEY=your-api-key
```

```python
from forge import forge

# Client automatically reads from environment
client = Forge()
```

---

## 🏗️ **Core Classes**

### **`Forge`**

Main client class.

```python
class Forge:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize Forge client."""
        
    @property
    def conversations(self) -> ConversationsAPI:
        """Access conversations API."""
```

---

### **`ConversationsAPI`**

Manage conversations.

```python
class ConversationsAPI:
    def create(self) -> Conversation:
        """Create new conversation."""
        
    def get(self, conversation_id: str) -> Conversation:
        """Get conversation by ID."""
        
    def list(self, limit: int = 50) -> List[Conversation]:
        """List conversations."""
        
    def send_message(
        self,
        conversation_id: str,
        message: str
    ) -> Message:
        """Send message to conversation."""
        
    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Message]:
        """Get conversation messages."""
```

**Example:**

```python
# Create conversation
conv = client.conversations.create()

# Send message
msg = client.conversations.send_message(
    conversation_id=conv.id,
    message="Create a REST API for a blog"
)

# Get messages
messages = client.conversations.get_messages(conv.id)
for msg in messages:
    print(f"{msg.source}: {msg.content}")
```

---

## 💡 **Examples**

### **Example 1: Async Usage**

```python
import asyncio
from forge import AsyncForge

async def main():
    # Async client
    client = AsyncForge(base_url="http://localhost:8000")
    
    # Create conversation
    conv = await client.conversations.create()
    
    # Send message
    msg = await client.conversations.send_message(
        conversation_id=conv.id,
        message="Create a REST API for user management"
    )
    
    print(msg.content)

# Run
asyncio.run(main())
```

---

### **Example 2: Streaming Responses**

```python
from forge import forge

client = Forge()
conv = client.conversations.create()

# Stream response
for chunk in client.conversations.send_message_stream(
    conversation_id=conv.id,
    message="Explain how React hooks work"
):
    print(chunk.content, end='', flush=True)
```

---

### **Example 3: Error Handling**

```python
from forge import forge
from forge.exceptions import (
    ForgeException,
    ConversationNotFound,
    RateLimitError,
    APIError
)

client = Forge()

try:
    conv = client.conversations.get("invalid-id")
except ConversationNotFound:
    print("Conversation not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except APIError as e:
    print(f"API error: {e.message}")
except ForgeException as e:
    print(f"General error: {e}")
```

---

## 📚 **API Reference**

### **Data Models**

#### **`Conversation`**

```python
@dataclass
class Conversation:
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
```

#### **`Message`**

```python
@dataclass
class Message:
    id: int
    conversation_id: str
    source: str  # 'user', 'agent', 'environment'
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
```

---

### **Configuration**

#### **Timeouts**

```python
client = Forge(
    base_url="http://localhost:3000",
    timeout=60,  # Request timeout in seconds
)
```

#### **Retry Logic**

```python
from forge import forge, RetryConfig

client = Forge(
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
    )
)
```

#### **Custom Headers**

```python
client = Forge(
    base_url="http://localhost:3000",
    headers={
        "X-Custom-Header": "value",
    }
)
```

---

## 🔧 **Advanced Usage**

### **Custom HTTP Client**

```python
import httpx
from forge import forge

# Custom HTTP client
http_client = httpx.Client(
    timeout=120.0,
    limits=httpx.Limits(max_connections=100),
)

client = Forge(
    base_url="http://localhost:3000",
    http_client=http_client,
)
```

### **WebSocket Support**

```python
from forge import forge
import asyncio

async def listen_to_events(conversation_id: str):
    client = Forge()
    
    async for event in client.stream_events(conversation_id):
        if event.type == 'agent_state_changed':
            print(f"Agent state changed: {event.extras['agent_state']}")

asyncio.run(listen_to_events("conv-123"))
```

---

## 🧪 **Testing**

### **Mock Client**

```python
from forge.testing import MockForge

# Create mock client
mock_client = MockForge()

# Set mock responses
mock_client.conversations.create.return_value = Conversation(
    id="test-123",
    status="active",
    created_at=datetime.now(),
    updated_at=datetime.now(),
)

# Use in tests
conv = mock_client.conversations.create()
assert conv.id == "test-123"
```

---

## 📖 **Complete Example: Code Generation Workflow**

```python
from forge import forge
import asyncio

async def run_code_generation(prompt: str):
    """Complete workflow to generate code."""
    
    # Initialize
    client = Forge(base_url="http://localhost:8000")
    
    # Create conversation
    conv = client.conversations.create()
    print(f"📝 Created conversation: {conv.id}")
    
    # Send message and stream response
    print("🚀 Sending request...")
    response = ""
    for chunk in client.conversations.send_message_stream(
        conversation_id=conv.id,
        message=prompt
    ):
        if chunk.content:
            response += chunk.content
            print(chunk.content, end='', flush=True)
    
    print("\n\n✅ Request completed!")
    return response

# Run
if __name__ == "__main__":
    prompt = "Create a FastAPI endpoint for user registration with JWT authentication"
    asyncio.run(run_code_generation(prompt))
```

---

## 📚 **Related Documentation**

- [REST API](rest-api.md)
- [WebSocket API](websocket-api.md)
- [Getting Started Guide](../guides/getting-started.md)

---

**The Python SDK provides a powerful, Pythonic interface to all Forge functionality!**

