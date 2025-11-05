# 💾 **Memory System**

> **Revolutionary intelligent memory management with conversation memory, context condensation, and advanced indexing for scalable AI development.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🔧 Core Components](#-core-components)
- [⚙️ Configuration](#️-configuration)
- [🚀 Usage](#-usage)
- [📊 Monitoring](#-monitoring)
- [🎯 Advanced Features](#-advanced-features)
- [📚 API Reference](#-api-reference)
- [🎯 Examples](#-examples)
- [🔍 Troubleshooting](#-troubleshooting)

---

## 🌟 **Overview**

The Memory System is a revolutionary intelligent memory management platform that provides advanced capabilities for storing, retrieving, and managing conversation history and context information. It's designed to scale with long-context models and complex AI applications.

### **Key Features**
- **Conversation Memory**: Advanced conversation storage and retrieval
- **Context Condensation**: Intelligent summarization and compression
- **Memory Indexing**: Vector + lexical search capabilities
- **Context Evolution**: Self-improving context management
- **Performance Tracking**: Memory usage and retrieval analytics
- **Scalable Design**: Built for long-context models

### **Revolutionary Capabilities**
- **Intelligent Compression**: Maintains quality while reducing size
- **Multi-Modal Search**: Vector and lexical search combined
- **Context Preservation**: Prevents information loss during condensation
- **Real-Time Updates**: Live memory management and updates
- **Enterprise-Grade**: Production-ready with monitoring and alerting

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory System                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │Conversation │  │   Context   │  │   Memory    │        │
│  │   Memory    │  │ Condenser   │  │  Indexing   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Vector    │  │  Lexical    │  │  Context    │        │
│  │   Search    │  │   Search    │  │  Evolution  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  Storage Engine │ Performance Tracker │ Monitoring System │
└─────────────────────────────────────────────────────────────┘
```

### **Core Principles**

1. **Intelligent Storage**: Efficient storage with quality preservation
2. **Multi-Modal Retrieval**: Vector and lexical search combined
3. **Context Preservation**: Maintains important information during compression
4. **Scalable Design**: Built for long-context models and large datasets
5. **Real-Time Updates**: Live memory management and updates

---

## 🔧 **Core Components**

### **1. Conversation Memory**
Advanced conversation storage and retrieval system.

**Features:**
- Conversation storage with metadata
- Context-aware retrieval
- Conversation threading
- Metadata management
- Performance tracking

**Usage:**
```python
from openhands.memory import ConversationMemory

# Initialize conversation memory
memory = ConversationMemory(
    max_conversations=1000,
    max_conversation_length=10000,
    enable_compression=True
)

# Store conversation
conversation_id = await memory.store_conversation(
    conversation={
        "user": "How to implement user authentication?",
        "assistant": "Here's how to implement authentication...",
        "context": {"domain": "web_development", "framework": "FastAPI"},
        "timestamp": datetime.now(),
        "metadata": {"success": True, "confidence": 0.9}
    }
)

# Retrieve conversation
conversation = await memory.retrieve_conversation(conversation_id)
print(f"Conversation: {conversation['user']} -> {conversation['assistant']}")
```

### **2. Context Condenser**
Intelligent context summarization and compression.

**Features:**
- Context summarization
- Information preservation
- Compression optimization
- Quality assessment
- Adaptive compression

**Condensation Process:**
```python
from openhands.memory.condenser import Condenser

# Initialize condenser
condenser = Condenser(
    compression_ratio=0.5,
    quality_threshold=0.8,
    preserve_key_info=True
)

# Condense context
condensed_context = await condenser.condense(
    context="Long context with detailed information...",
    target_length=1000,
    preserve_sections=["important", "key_points"]
)

print(f"Original length: {len(original_context)}")
print(f"Condensed length: {len(condensed_context)}")
print(f"Compression ratio: {len(condensed_context) / len(original_context):.3f}")
```

### **3. Memory Indexing**
Advanced search capabilities with vector and lexical search.

**Features:**
- Vector embeddings for semantic search
- Lexical search for exact matches
- Hybrid search combining both methods
- Relevance scoring
- Search result ranking

**Search Operations:**
```python
from openhands.memory.indexing import MemoryIndex

# Initialize memory index
index = MemoryIndex(
    vector_dimension=768,
    max_vectors=10000,
    similarity_threshold=0.7
)

# Add documents to index
await index.add_document(
    content="User authentication implementation guide",
    metadata={"type": "guide", "domain": "security"},
    embedding=embedding_vector
)

# Search documents
results = await index.search(
    query="authentication security",
    search_type="hybrid",  # vector + lexical
    max_results=10,
    filters={"domain": "security"}
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
```

### **4. Context Evolution**
Self-improving context management system.

**Features:**
- Context quality assessment
- Adaptive improvement
- Learning from feedback
- Performance optimization
- Evolution tracking

**Evolution Process:**
```python
from openhands.memory.evolution import ContextEvolver

# Initialize context evolver
evolver = ContextEvolver(
    evolution_threshold=0.05,
    learning_rate=0.1,
    max_evolution_cycles=100
)

# Evolve context based on feedback
evolution_result = await evolver.evolve_context(
    context=current_context,
    feedback={
        "helpful": True,
        "quality_score": 0.8,
        "improvement_suggestions": ["add_examples", "clarify_steps"]
    }
)

print(f"Evolution success: {evolution_result.success}")
print(f"Quality improvement: {evolution_result.quality_improvement:.3f}")
print(f"New context length: {len(evolution_result.evolved_context)}")
```

### **5. Performance Tracker**
Memory system performance monitoring and analytics.

**Features:**
- Memory usage tracking
- Retrieval performance metrics
- Compression efficiency
- Search accuracy
- System health monitoring

**Performance Monitoring:**
```python
from openhands.memory.tracker import MemoryTracker

# Initialize memory tracker
tracker = MemoryTracker(
    track_usage=True,
    track_performance=True,
    track_accuracy=True
)

# Track memory operation
await tracker.track_operation(
    operation="store_conversation",
    duration=0.5,
    memory_usage=1024,
    success=True
)

# Get performance metrics
metrics = tracker.get_metrics()
print(f"Total operations: {metrics['total_operations']}")
print(f"Average duration: {metrics['avg_duration']:.3f}s")
print(f"Success rate: {metrics['success_rate']:.3f}")
print(f"Memory usage: {metrics['memory_usage']:.2f} MB")
```

---

## ⚙️ **Configuration**

### **Basic Configuration**
```toml
[memory]
# Enable memory system
enable_memory = true

# Conversation memory settings
max_conversations = 1000
max_conversation_length = 10000
conversation_retention_days = 30
enable_compression = true

# Context condenser settings
compression_ratio = 0.5
quality_threshold = 0.8
preserve_key_info = true
max_compression_cycles = 3

# Memory indexing settings
vector_dimension = 768
max_vectors = 10000
similarity_threshold = 0.7
enable_lexical_search = true
enable_hybrid_search = true

# Context evolution settings
enable_evolution = true
evolution_threshold = 0.05
learning_rate = 0.1
max_evolution_cycles = 100
```

### **Advanced Configuration**
```toml
[memory.advanced]
# Performance optimization
enable_caching = true
cache_size = 1000
cache_ttl = 3600

# Memory management
enable_auto_cleanup = true
cleanup_frequency = 24  # hours
cleanup_threshold = 0.8

# Search optimization
enable_search_caching = true
search_cache_size = 500
search_cache_ttl = 1800

# Monitoring
enable_detailed_monitoring = true
track_search_accuracy = true
track_compression_efficiency = true
track_evolution_effectiveness = true
```

### **Component-Specific Configuration**
```toml
[memory.conversation]
# Conversation storage
storage_backend = "sqlite"  # sqlite, postgresql, mongodb
enable_threading = true
max_thread_depth = 10
enable_metadata_indexing = true

[memory.condenser]
# Context condensation
compression_algorithm = "adaptive"  # adaptive, fixed, quality_based
min_compression_ratio = 0.3
max_compression_ratio = 0.8
preserve_structure = true

[memory.indexing]
# Search indexing
vector_model = "sentence-transformers"  # sentence-transformers, openai, custom
lexical_analyzer = "standard"  # standard, custom
enable_fuzzy_search = true
fuzzy_threshold = 0.8
```

---

## 🚀 **Usage**

### **Python API**
```python
from openhands.memory import MemorySystem
from openhands.memory.models import Conversation, Context

# Initialize memory system
memory_system = MemorySystem(
    max_conversations=1000,
    enable_compression=True,
    enable_indexing=True
)

# Store conversation
conversation = Conversation(
    user_message="How to implement authentication?",
    assistant_message="Here's a comprehensive guide...",
    context={"domain": "web_development", "framework": "FastAPI"},
    metadata={"success": True, "confidence": 0.9}
)

conversation_id = await memory_system.store_conversation(conversation)

# Search conversations
results = await memory_system.search_conversations(
    query="authentication implementation",
    max_results=10,
    filters={"domain": "web_development"}
)

# Retrieve specific conversation
conversation = await memory_system.retrieve_conversation(conversation_id)
```

### **REST API**
```bash
# Store conversation
curl -X POST http://localhost:8000/api/memory/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "How to implement authentication?",
    "assistant_message": "Here is how to implement authentication...",
    "context": {"domain": "web_development"},
    "metadata": {"success": true}
  }'

# Search conversations
curl "http://localhost:8000/api/memory/conversations/search?query=authentication&max_results=10"

# Get conversation by ID
curl "http://localhost:8000/api/memory/conversations/{conversation_id}"

# Get memory statistics
curl "http://localhost:8000/api/memory/statistics"
```

### **WebSocket API**
```javascript
// Connect to memory WebSocket
const socket = io('ws://localhost:8000/memory');

// Listen for memory updates
socket.on('memory_update', (data) => {
  console.log('Memory updated:', data);
});

// Store conversation
socket.emit('store_conversation', {
  user_message: 'How to implement authentication?',
  assistant_message: 'Here is how to implement authentication...',
  context: { domain: 'web_development' }
});

// Search conversations
socket.emit('search_conversations', {
  query: 'authentication',
  max_results: 10
});
```

---

## 📊 **Monitoring**

### **Memory System Metrics**
```python
# Get comprehensive memory metrics
metrics = memory_system.get_metrics()

print("=== Memory System Metrics ===")
print(f"Total conversations: {metrics['total_conversations']}")
print(f"Memory usage: {metrics['memory_usage']:.2f} MB")
print(f"Compression ratio: {metrics['compression_ratio']:.3f}")
print(f"Search accuracy: {metrics['search_accuracy']:.3f}")
print(f"Retrieval speed: {metrics['avg_retrieval_time']:.3f}s")
```

### **Component-Specific Metrics**
```python
# Conversation memory metrics
conversation_metrics = memory_system.conversation_memory.get_metrics()
print(f"Stored conversations: {conversation_metrics['stored_conversations']}")
print(f"Average conversation length: {conversation_metrics['avg_length']:.1f}")
print(f"Storage efficiency: {conversation_metrics['storage_efficiency']:.3f}")

# Context condenser metrics
condenser_metrics = memory_system.condenser.get_metrics()
print(f"Compression operations: {condenser_metrics['compression_ops']}")
print(f"Average compression ratio: {condenser_metrics['avg_compression_ratio']:.3f}")
print(f"Quality preservation: {condenser_metrics['quality_preservation']:.3f}")

# Memory index metrics
index_metrics = memory_system.index.get_metrics()
print(f"Indexed documents: {index_metrics['indexed_documents']}")
print(f"Search operations: {index_metrics['search_ops']}")
print(f"Average search time: {index_metrics['avg_search_time']:.3f}s")
```

### **Performance Analytics**
```python
# Get performance analytics
analytics = memory_system.get_performance_analytics()

print("=== Performance Analytics ===")
print(f"Peak memory usage: {analytics['peak_memory_usage']:.2f} MB")
print(f"Average response time: {analytics['avg_response_time']:.3f}s")
print(f"Error rate: {analytics['error_rate']:.3f}")
print(f"Throughput: {analytics['throughput']:.1f} ops/sec")

# Get usage trends
trends = memory_system.get_usage_trends(days=7)
print(f"Memory growth rate: {trends['memory_growth_rate']:.3f}")
print(f"Search volume trend: {trends['search_volume_trend']:.3f}")
```

---

## 🎯 **Advanced Features**

### **Custom Memory Backends**
```python
from openhands.memory.backends import BaseMemoryBackend

class CustomMemoryBackend(BaseMemoryBackend):
    def __init__(self, config):
        super().__init__(config)
        # Custom backend initialization
    
    async def store_conversation(self, conversation):
        # Custom storage logic
        pass
    
    async def retrieve_conversation(self, conversation_id):
        # Custom retrieval logic
        pass
    
    async def search_conversations(self, query, filters=None):
        # Custom search logic
        pass

# Register custom backend
memory_system.register_backend("custom", CustomMemoryBackend)
```

### **Advanced Search Capabilities**
```python
# Multi-modal search
results = await memory_system.search_conversations(
    query="authentication implementation",
    search_types=["vector", "lexical", "hybrid"],
    filters={
        "domain": "web_development",
        "success": True,
        "confidence": {"$gte": 0.8}
    },
    sort_by="relevance",
    max_results=20
)

# Semantic search with context
semantic_results = await memory_system.semantic_search(
    query="How to secure user data?",
    context={"domain": "security", "framework": "FastAPI"},
    similarity_threshold=0.8
)

# Temporal search
temporal_results = await memory_system.search_by_time_range(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    query="authentication"
)
```

### **Memory Optimization**
```python
# Enable memory optimization
memory_system.enable_optimization(
    compression_optimization=True,
    indexing_optimization=True,
    storage_optimization=True
)

# Perform memory cleanup
cleanup_result = await memory_system.cleanup_memory(
    remove_old_conversations=True,
    compress_large_conversations=True,
    optimize_index=True
)

print(f"Cleanup completed: {cleanup_result.success}")
print(f"Space freed: {cleanup_result.space_freed:.2f} MB")
print(f"Conversations removed: {cleanup_result.conversations_removed}")
```

### **Context Evolution**
```python
# Enable context evolution
memory_system.enable_context_evolution(
    evolution_threshold=0.05,
    learning_rate=0.1,
    max_evolution_cycles=100
)

# Evolve context based on feedback
evolution_result = await memory_system.evolve_context(
    context_id="context_123",
    feedback={
        "helpful": True,
        "quality_score": 0.8,
        "improvement_suggestions": ["add_examples", "clarify_steps"]
    }
)

print(f"Evolution success: {evolution_result.success}")
print(f"Quality improvement: {evolution_result.quality_improvement:.3f}")
```

---

## 📚 **API Reference**

### **MemorySystem**

#### **Methods**

##### `__init__(max_conversations=1000, enable_compression=True, enable_indexing=True)`
Initialize the memory system.

**Parameters:**
- `max_conversations`: Maximum number of conversations to store
- `enable_compression`: Enable context compression
- `enable_indexing`: Enable search indexing

##### `async store_conversation(conversation: Conversation) -> str`
Store a conversation in memory.

**Parameters:**
- `conversation`: Conversation object to store

**Returns:**
- `str`: Conversation ID

##### `async retrieve_conversation(conversation_id: str) -> Conversation`
Retrieve a conversation by ID.

**Parameters:**
- `conversation_id`: ID of the conversation

**Returns:**
- `Conversation`: Conversation object

##### `async search_conversations(query: str, max_results: int = 10, filters: Dict = None) -> List[Conversation]`
Search conversations by query.

**Parameters:**
- `query`: Search query
- `max_results`: Maximum number of results
- `filters`: Optional filters

**Returns:**
- `List[Conversation]`: List of matching conversations

##### `get_metrics() -> Dict[str, Any]`
Get memory system metrics.

**Returns:**
- `Dict[str, Any]`: System metrics

### **Conversation**

#### **Properties**
- `id: str`: Unique conversation identifier
- `user_message: str`: User's message
- `assistant_message: str`: Assistant's response
- `context: Dict[str, Any]`: Conversation context
- `metadata: Dict[str, Any]`: Additional metadata
- `timestamp: datetime`: Conversation timestamp

### **ContextCondenser**

#### **Methods**

##### `async condense(context: str, target_length: int, preserve_sections: List[str] = None) -> str`
Condense context to target length.

**Parameters:**
- `context`: Context to condense
- `target_length`: Target length in characters
- `preserve_sections`: Sections to preserve

**Returns:**
- `str`: Condensed context

---

## 🎯 **Examples**

### **Example 1: Basic Memory Operations**
```python
import asyncio
from openhands.memory import MemorySystem
from openhands.memory.models import Conversation

async def basic_memory_operations():
    # Initialize memory system
    memory = MemorySystem(
        max_conversations=500,
        enable_compression=True,
        enable_indexing=True
    )
    
    # Store conversations
    conversations = [
        Conversation(
            user_message="How to implement user authentication?",
            assistant_message="Here's how to implement authentication with JWT tokens...",
            context={"domain": "web_development", "framework": "FastAPI"},
            metadata={"success": True, "confidence": 0.9}
        ),
        Conversation(
            user_message="What are best practices for API design?",
            assistant_message="Here are the key best practices for API design...",
            context={"domain": "web_development", "topic": "API_design"},
            metadata={"success": True, "confidence": 0.85}
        )
    ]
    
    for conv in conversations:
        conv_id = await memory.store_conversation(conv)
        print(f"Stored conversation: {conv_id}")
    
    # Search conversations
    results = await memory.search_conversations(
        query="authentication implementation",
        max_results=5
    )
    
    print(f"\nFound {len(results)} conversations:")
    for result in results:
        print(f"- {result.user_message} -> {result.assistant_message[:50]}...")

asyncio.run(basic_memory_operations())
```

### **Example 2: Advanced Memory Management**
```python
async def advanced_memory_management():
    # Initialize with advanced configuration
    memory = MemorySystem(
        max_conversations=2000,
        enable_compression=True,
        enable_indexing=True,
        enable_evolution=True
    )
    
    # Store large conversation
    large_conversation = Conversation(
        user_message="Design a complete microservices architecture",
        assistant_message="Here's a comprehensive microservices architecture design...",
        context={"domain": "system_design", "complexity": "high"},
        metadata={"success": True, "confidence": 0.95}
    )
    
    conv_id = await memory.store_conversation(large_conversation)
    
    # Test compression
    original_length = len(large_conversation.assistant_message)
    compressed_context = await memory.condenser.condense(
        large_conversation.assistant_message,
        target_length=original_length // 2
    )
    
    print(f"Original length: {original_length}")
    print(f"Compressed length: {len(compressed_context)}")
    print(f"Compression ratio: {len(compressed_context) / original_length:.3f}")
    
    # Test search with filters
    results = await memory.search_conversations(
        query="microservices architecture",
        filters={"domain": "system_design", "complexity": "high"},
        max_results=10
    )
    
    print(f"\nFound {len(results)} relevant conversations")
    
    # Get memory statistics
    stats = memory.get_metrics()
    print(f"\nMemory statistics:")
    print(f"Total conversations: {stats['total_conversations']}")
    print(f"Memory usage: {stats['memory_usage']:.2f} MB")
    print(f"Compression ratio: {stats['compression_ratio']:.3f}")
```

### **Example 3: Memory Evolution and Learning**
```python
async def memory_evolution_example():
    # Initialize with evolution enabled
    memory = MemorySystem(
        max_conversations=1000,
        enable_compression=True,
        enable_indexing=True,
        enable_evolution=True
    )
    
    # Store initial conversation
    initial_conv = Conversation(
        user_message="How to implement authentication?",
        assistant_message="Basic authentication implementation...",
        context={"domain": "web_development"},
        metadata={"success": True, "confidence": 0.7}
    )
    
    conv_id = await memory.store_conversation(initial_conv)
    
    # Provide feedback for evolution
    feedback = {
        "helpful": True,
        "quality_score": 0.8,
        "improvement_suggestions": [
            "add_security_best_practices",
            "include_code_examples",
            "mention_jwt_tokens"
        ]
    }
    
    # Evolve context based on feedback
    evolution_result = await memory.evolve_context(conv_id, feedback)
    
    print(f"Evolution success: {evolution_result.success}")
    print(f"Quality improvement: {evolution_result.quality_improvement:.3f}")
    
    # Store improved conversation
    improved_conv = Conversation(
        user_message="How to implement secure authentication?",
        assistant_message="Here's a comprehensive guide to secure authentication with JWT tokens, best practices, and code examples...",
        context={"domain": "web_development", "security": "high"},
        metadata={"success": True, "confidence": 0.95}
    )
    
    improved_conv_id = await memory.store_conversation(improved_conv)
    
    # Search for evolved content
    results = await memory.search_conversations(
        query="secure authentication JWT",
        max_results=5
    )
    
    print(f"\nFound {len(results)} evolved conversations")
    for result in results:
        print(f"- {result.user_message} (confidence: {result.metadata.get('confidence', 0):.2f})")
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Memory Usage Too High**
```python
# Check memory usage
stats = memory.get_metrics()
if stats['memory_usage'] > 1000:  # MB
    # Enable compression
    memory.enable_compression(compression_ratio=0.5)
    
    # Clean old conversations
    await memory.cleanup_memory(remove_old_conversations=True)
    
    # Optimize storage
    await memory.optimize_storage()
```

#### **Search Performance Issues**
```python
# Check search performance
index_metrics = memory.index.get_metrics()
if index_metrics['avg_search_time'] > 1.0:  # seconds
    # Optimize index
    await memory.index.optimize()
    
    # Enable search caching
    memory.enable_search_caching(cache_size=500)
    
    # Adjust similarity threshold
    memory.index.similarity_threshold = 0.8
```

#### **Compression Quality Issues**
```python
# Check compression quality
condenser_metrics = memory.condenser.get_metrics()
if condenser_metrics['quality_preservation'] < 0.8:
    # Adjust compression parameters
    memory.condenser.quality_threshold = 0.9
    memory.condenser.preserve_key_info = True
    
    # Enable adaptive compression
    memory.condenser.enable_adaptive_compression()
```

### **Performance Optimization**

#### **Optimize Memory Storage**
```python
# Enable storage optimization
memory.enable_storage_optimization(
    compression=True,
    deduplication=True,
    indexing=True
)

# Perform storage optimization
optimization_result = await memory.optimize_storage()
print(f"Storage optimized: {optimization_result.success}")
print(f"Space saved: {optimization_result.space_saved:.2f} MB")
```

#### **Optimize Search Performance**
```python
# Enable search optimization
memory.enable_search_optimization(
    caching=True,
    indexing=True,
    query_optimization=True
)

# Optimize search index
await memory.index.optimize()
```

---

## 📈 **Best Practices**

### **Memory Management**
1. **Regular Cleanup**: Periodically clean old conversations
2. **Monitor Usage**: Track memory usage and adjust limits
3. **Use Compression**: Enable compression for large conversations
4. **Optimize Storage**: Regularly optimize storage for efficiency

### **Search Optimization**
1. **Use Appropriate Filters**: Apply relevant filters to narrow results
2. **Optimize Queries**: Use specific, targeted queries
3. **Enable Caching**: Use search caching for frequently accessed data
4. **Monitor Performance**: Track search performance and optimize

### **Context Management**
1. **Preserve Key Information**: Ensure important information is preserved during compression
2. **Use Evolution**: Enable context evolution for continuous improvement
3. **Monitor Quality**: Track compression quality and adjust parameters
4. **Regular Updates**: Keep context information current and relevant

---

**Memory System - The future of intelligent memory management.** 💾
