# Code Examples and Recipes

Practical code examples and recipes for common Forge use cases.

## Basic Examples

- [**Basic CodeAct Usage**](01_basic_codeact.py) - Simple agent interaction
- [**Custom Provider Setup**](02_custom_provider.py) - Configure custom LLM providers
- [**Cost Tracking**](03_cost_tracking.py) - Monitor API costs

## API Examples

### REST API

```python
# Example: Create a conversation via REST API
import requests

response = requests.post(
    "http://localhost:3000/api/conversations",
    json={
        "title": "My Project",
        "workspace": "/path/to/workspace"
    },
    headers={"Authorization": "Bearer <token>"}
)
conversation = response.json()
```

### WebSocket API

```python
# Example: Real-time communication via WebSocket
import socketio

sio = socketio.Client()

@sio.on('message')
def on_message(data):
    print(f"Received: {data}")

sio.connect('http://localhost:3000')
sio.emit('join_conversation', {'conversation_id': '...'})
sio.emit('message', {'content': 'Hello, agent!'})
```

## SDK Examples

### Python SDK

```python
from forge.client import ForgeClient

client = ForgeClient(base_url="http://localhost:3000")

# Create conversation
conversation = client.conversations.create(
    title="My Project",
    workspace="/path/to/workspace"
)

# Send message
response = client.conversations.send_message(
    conversation_id=conversation.id,
    content="Build a REST API for a todo app"
)
```

### TypeScript SDK

```typescript
import { ForgeClient } from '@forge/sdk';

const client = new ForgeClient({
  baseURL: 'http://localhost:3000'
});

// Create conversation
const conversation = await client.conversations.create({
  title: 'My Project',
  workspace: '/path/to/workspace'
});

// Send message
const response = await client.conversations.sendMessage(
  conversation.id,
  'Build a REST API for a todo app'
);
```

## Agent Examples

### CodeAct Agent

```python
from forge.agenthub.codeact_agent import CodeActAgent

agent = CodeActAgent()

# Simple code execution
result = agent.execute("print('Hello, World!')")

# File editing
agent.edit_file(
    path="main.py",
    edits=[{
        "type": "insert",
        "line": 10,
        "content": "    # Added by agent\n"
    }]
)
```

### MetaSOP Orchestration

```python
from forge.metasop import MetaSOPOrchestrator

orchestrator = MetaSOPOrchestrator()

# Complex multi-agent project
result = orchestrator.execute(
    goal="Build a REST API for a todo app with authentication",
    steps=[
        "Design the API structure",
        "Implement the database schema",
        "Create the API endpoints",
        "Add authentication",
        "Write tests"
    ]
)
```

## Integration Examples

### GitHub Integration

```python
from forge.integrations.github import GitHubIntegration

github = GitHubIntegration(token="your-token")

# Create issue
issue = github.create_issue(
    repo="owner/repo",
    title="Bug: Login not working",
    body="Description of the bug"
)

# Create pull request
pr = github.create_pull_request(
    repo="owner/repo",
    title="Fix login bug",
    body="Fixes the login issue",
    head="feature-branch",
    base="main"
)
```

### Database Integration

```python
from forge.integrations.database import DatabaseConnection

db = DatabaseConnection(url="postgresql://...")

# Execute query
results = db.execute("SELECT * FROM users WHERE active = true")

# Execute with parameters
user = db.execute_one(
    "SELECT * FROM users WHERE id = %s",
    params=[user_id]
)
```

## Advanced Examples

### Custom Agent

```python
from forge.agenthub.base import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MyAgent")
    
    def act(self, state):
        # Custom agent logic
        action = self.think(state)
        return self.execute(action)
```

### Error Recovery

```python
from forge.controller.error_recovery import ErrorRecoveryStrategy

strategy = ErrorRecoveryStrategy()

try:
    result = agent.execute(action)
except Exception as e:
    error_type = strategy.classify_error(e)
    recovery_actions = strategy.get_recovery_actions(error_type, e)
    
    for action in recovery_actions:
        try:
            result = agent.execute(action)
            break
        except Exception:
            continue
```

### Monitoring

```python
from forge.monitoring import metrics

# Record custom metric
metrics.record_latency("custom.operation", duration_ms)

# Increment counter
metrics.increment("custom.events.processed")

# Set gauge
metrics.set_gauge("custom.queue.size", queue_size)
```

## Recipes

### Recipe: Automated Testing

```python
# Generate and run tests for a module
agent.execute("""
Generate comprehensive unit tests for the UserService class.
Include tests for:
- User creation
- User retrieval
- User update
- User deletion
- Error cases
""")

# Run the generated tests
agent.execute("pytest tests/test_user_service.py -v")
```

### Recipe: Code Refactoring

```python
# Refactor a large function into smaller functions
agent.execute("""
Refactor the process_order() function in order_service.py.
Break it down into smaller, more focused functions:
- validate_order()
- calculate_total()
- apply_discounts()
- process_payment()
- send_confirmation()
""")
```

### Recipe: Documentation Generation

```python
# Generate API documentation
agent.execute("""
Generate comprehensive API documentation for all endpoints in the api/ directory.
Include:
- Endpoint descriptions
- Request/response schemas
- Example requests
- Error codes
""")
```

## More Examples

See the [examples directory](../examples/) for more code examples.

## Contributing Examples

We welcome contributions! See [Contributing](../contributing.md) for guidelines.

To add an example:
1. Create a new file in `docs/examples/`
2. Include clear comments and documentation
3. Test the example works
4. Submit a pull request

