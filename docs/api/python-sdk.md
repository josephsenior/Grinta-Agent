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
        
    @property
    def metasop(self) -> MetaSOPAPI:
        """Access MetaSOP API."""
        
    @property
    def optimization(self) -> OptimizationAPI:
        """Access optimization API."""
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
        message: str,
        enable_metasop: bool = False
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
    message="Create a REST API for a blog",
    enable_metasop=True
)

# Get messages
messages = client.conversations.get_messages(conv.id)
for msg in messages:
    print(f"{msg.source}: {msg.content}")
```

---

### **`MetaSOPAPI`**

MetaSOP orchestration.

```python
class MetaSOPAPI:
    def start_orchestration(
        self,
        conversation_id: str,
        user_request: str,
        template: str = "full_stack_dev"
    ) -> Orchestration:
        """Start MetaSOP orchestration."""
        
    def get_orchestration(
        self,
        orchestration_id: str
    ) -> Orchestration:
        """Get orchestration status."""
        
    def get_artifacts(
        self,
        orchestration_id: str
    ) -> Dict[str, Any]:
        """Get all artifacts from orchestration."""
```

**Example:**

```python
# Start MetaSOP
orch = client.metasop.start_orchestration(
    conversation_id=conv.id,
    user_request="Build a todo app with auth",
    template="full_stack_dev"
)

# Wait for completion
import time
while True:
    status = client.metasop.get_orchestration(orch.id)
    if status.status in ['completed', 'failed']:
        break
    time.sleep(5)

# Get artifacts
artifacts = client.metasop.get_artifacts(orch.id)
print("PM Spec:", artifacts['pm_spec'])
print("Architecture:", artifacts['architect'])
print("File Structure:", artifacts['engineer'])
```

---

### **`OptimizationAPI`**

Prompt optimization.

```python
class OptimizationAPI:
    def get_metrics(self) -> OptimizationMetrics:
        """Get optimization metrics."""
        
    def get_variants(self, prompt_id: str) -> List[Variant]:
        """Get prompt variants."""
        
    def get_best_variant(self, prompt_id: str) -> Variant:
        """Get best performing variant."""
```

**Example:**

```python
# Get optimization metrics
metrics = client.optimization.get_metrics()
print(f"Success rate: {metrics.success_rate}")
print(f"Avg latency: {metrics.avg_latency}s")

# Get best variant
variant = client.optimization.get_best_variant("codeact_main")
print(f"Best variant: {variant.id}")
print(f"Performance: {variant.success_rate}")
```

---

## 💡 **Examples**

### **Example 1: Complete Workflow**

```python
from forge import forge
import time

# Initialize
client = Forge(base_url="http://localhost:8000")

# Create conversation
conv = client.conversations.create()
print(f"Created conversation: {conv.id}")

# Start MetaSOP orchestration
orch = client.metasop.start_orchestration(
    conversation_id=conv.id,
    user_request="""
    Build a task management app with:
    - User authentication
    - CRUD operations for tasks
    - Task categories and priorities
    - Due dates and reminders
    """,
    template="full_stack_dev"
)

print(f"Orchestration started: {orch.id}")

# Poll for completion
while True:
    status = client.metasop.get_orchestration(orch.id)
    print(f"Status: {status.status}")
    
    if status.status == 'completed':
        print("✅ Orchestration completed!")
        break
    elif status.status == 'failed':
        print("❌ Orchestration failed!")
        break
    
    time.sleep(10)

# Get artifacts
artifacts = client.metasop.get_artifacts(orch.id)

# Process artifacts
pm_spec = artifacts.get('pm_spec')
if pm_spec:
    print(f"\n📋 Product Manager Output:")
    print(f"User Stories: {len(pm_spec['user_stories'])}")
    for story in pm_spec['user_stories']:
        print(f"  - {story['title']} [{story['priority']}]")

architect = artifacts.get('architect')
if architect:
    print(f"\n🏗️ Architect Output:")
    print(f"API Endpoints: {len(architect['api_endpoints'])}")
    print(f"Database Tables: {len(architect.get('database_schema', {}).get('tables', []))}")

engineer = artifacts.get('engineer')
if engineer:
    print(f"\n👨‍💻 Engineer Output:")
    print(f"Files: {len(engineer.get('file_structure', {}).get('files', []))}")
```

---

### **Example 2: Async Usage**

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

### **Example 3: Streaming Responses**

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

### **Example 4: Error Handling**

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

#### **`Orchestration`**

```python
@dataclass
class Orchestration:
    id: str
    conversation_id: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    template: str
    user_request: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    artifacts: Optional[Dict[str, Any]] = None
```

#### **`Variant`**

```python
@dataclass
class Variant:
    id: str
    prompt_id: str
    content: str
    success_rate: float
    avg_latency: float
    sample_size: int
    created_at: datetime
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
        if event.type == 'metasop_step_complete':
            print(f"Step completed: {event.step_id}")
            print(f"Artifact: {event.artifact}")

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

## 📖 **Complete Example: Build Full App**

```python
from forge import forge
import json
import time

def build_app(requirements: str):
    """Complete workflow to build an app."""
    
    # Initialize
    client = Forge(base_url="http://localhost:8000")
    
    # Create conversation
    conv = client.conversations.create()
    print(f"📝 Created conversation: {conv.id}")
    
    # Start MetaSOP
    print("🚀 Starting MetaSOP orchestration...")
    orch = client.metasop.start_orchestration(
        conversation_id=conv.id,
        user_request=requirements,
        template="full_stack_dev"
    )
    
    # Wait for completion
    print("⏳ Waiting for completion...")
    while True:
        status = client.metasop.get_orchestration(orch.id)
        
        if status.status == 'completed':
            print("✅ Orchestration completed!")
            break
        elif status.status == 'failed':
            print("❌ Orchestration failed!")
            return None
            
        time.sleep(10)
    
    # Get artifacts
    artifacts = client.metasop.get_artifacts(orch.id)
    
    # Save artifacts
    with open('artifacts.json', 'w') as f:
        json.dump(artifacts, f, indent=2)
    
    print("💾 Artifacts saved to artifacts.json")
    
    return artifacts

# Run
if __name__ == "__main__":
    requirements = """
    Build a blog platform with:
    - User authentication and profiles
    - Create, edit, delete posts
    - Comments system
    - Categories and tags
    - Search functionality
    - Admin dashboard
    """
    
    artifacts = build_app(requirements)
    
    if artifacts:
        print("\n📊 Summary:")
        print(f"User Stories: {len(artifacts['pm_spec']['user_stories'])}")
        print(f"API Endpoints: {len(artifacts['architect']['api_endpoints'])}")
        print(f"Database Tables: {len(artifacts['architect']['database_schema']['tables'])}")
        print(f"Files: {len(artifacts['engineer']['file_structure']['files'])}")
```

---

## 📚 **Related Documentation**

- [REST API](rest-api.md)
- [WebSocket API](websocket-api.md)
- [MetaSOP Overview](../features/metasop.md)
- [Getting Started Guide](../guides/getting-started.md)

---

**The Python SDK provides a powerful, Pythonic interface to all Forge functionality!**

