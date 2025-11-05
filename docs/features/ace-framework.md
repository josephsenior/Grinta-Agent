# 🧠 **Agentic Context Engineering (ACE) Framework**

> **Revolutionary self-improving context system that treats contexts as evolving playbooks, preventing context collapse and enabling scalable AI development.**

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

Agentic Context Engineering (ACE) is a revolutionary framework that treats contexts as evolving playbooks rather than static prompts. It addresses the critical limitations of existing context adaptation methods: **brevity bias** and **context collapse**.

### **Key Features**
- **Evolving Playbooks**: Contexts that grow and improve over time
- **Structured Updates**: Incremental, itemized context modifications
- **Multi-Agent Architecture**: Generator, Reflector, and Curator roles
- **Context Preservation**: Prevents information loss during adaptation
- **Self-Improvement**: Continuous learning from execution feedback
- **Scalable Design**: Works with long-context models

### **Revolutionary Capabilities**
- **Prevents Context Collapse**: Structured updates preserve detailed knowledge
- **Eliminates Brevity Bias**: Comprehensive contexts with domain insights
- **Self-Improving**: Learns from execution feedback without supervision
- **Scalable**: Designed for long-context models and complex tasks
- **Interpretable**: Human-readable context evolution

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    ACE Framework                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Generator  │  │  Reflector  │  │   Curator   │        │
│  │             │  │             │  │             │        │
│  │ • Trajectory│  │ • Insight   │  │ • Context   │        │
│  │   Generation│  │   Extraction│  │   Integration│        │
│  │ • Feedback  │  │ • Analysis  │  │ • Organization│       │
│  │   Collection│  │ • Refinement│  │ • De-duplication│     │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  Context Playbook │ Delta Updates │ Grow & Refine │ Memory │
└─────────────────────────────────────────────────────────────┘
```

### **Core Principles**

1. **Incremental Delta Updates**: Small, focused context modifications
2. **Grow-and-Refine**: Balance expansion with redundancy control
3. **Structured Contexts**: Itemized bullets with metadata
4. **Multi-Agent Design**: Specialized roles for different tasks
5. **Feedback-Driven**: Learning from execution results

---

## 🔧 **Core Components**

### **1. Context Playbook**
The central data structure that stores evolving context information.

**Features:**
- Structured bullet points with metadata
- Helpful/harmful counters for each bullet
- Unique identifiers for tracking
- Content organization by sections and tags
- Incremental updates and modifications

**Structure:**
```python
class ContextPlaybook:
    def __init__(self, max_bullets: int = 1000):
        self.bullets: Dict[str, ContextBullet] = {}
        self.max_bullets = max_bullets
        self.last_updated = datetime.now()
    
    def add_bullet(self, bullet: ContextBullet) -> str:
        """Add a new bullet to the playbook."""
        bullet_id = f"bullet_{len(self.bullets) + 1}"
        self.bullets[bullet_id] = bullet
        self.last_updated = datetime.now()
        return bullet_id
    
    def update_bullet(self, bullet_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing bullet."""
        if bullet_id in self.bullets:
            bullet = self.bullets[bullet_id]
            for key, value in updates.items():
                setattr(bullet, key, value)
            self.last_updated = datetime.now()
            return True
        return False
```

### **2. Generator**
Produces reasoning trajectories and collects feedback.

**Features:**
- Trajectory generation for new queries
- Feedback collection from execution
- Strategy identification and extraction
- Context relevance assessment
- Multi-epoch adaptation support

**Key Methods:**
```python
class ACEGenerator:
    async def generate_trajectory(self, query: str, context: ContextPlaybook) -> TrajectoryResult:
        """Generate reasoning trajectory for a query."""
        # Use context to inform trajectory generation
        relevant_bullets = self._get_relevant_bullets(query, context)
        
        # Generate trajectory with context awareness
        trajectory = await self._generate_with_context(query, relevant_bullets)
        
        return TrajectoryResult(
            trajectory=trajectory,
            used_bullets=relevant_bullets,
            feedback_collected=self._collect_feedback(trajectory)
        )
    
    def _get_relevant_bullets(self, query: str, context: ContextPlaybook) -> List[ContextBullet]:
        """Get bullets relevant to the query."""
        # Semantic similarity matching
        query_embedding = self._embed_query(query)
        relevant_bullets = []
        
        for bullet in context.bullets.values():
            similarity = self._calculate_similarity(query_embedding, bullet.embedding)
            if similarity > self.similarity_threshold:
                relevant_bullets.append(bullet)
        
        return sorted(relevant_bullets, key=lambda b: b.helpful_count, reverse=True)
```

### **3. Reflector**
Analyzes trajectories and extracts insights.

**Features:**
- Insight extraction from successes and failures
- Iterative refinement of insights
- Quality assessment and validation
- Pattern recognition and learning
- Multi-round reflection support

**Reflection Process:**
```python
class ACEReflector:
    async def reflect_on_trajectory(self, trajectory: TrajectoryResult) -> ReflectionResult:
        """Reflect on trajectory and extract insights."""
        insights = []
        
        # Analyze successes
        success_insights = await self._analyze_successes(trajectory)
        insights.extend(success_insights)
        
        # Analyze failures
        failure_insights = await self._analyze_failures(trajectory)
        insights.extend(failure_insights)
        
        # Refine insights iteratively
        refined_insights = await self._refine_insights(insights, trajectory)
        
        return ReflectionResult(
            insights=refined_insights,
            quality_score=self._assess_quality(refined_insights),
            patterns_detected=self._detect_patterns(refined_insights)
        )
    
    async def _refine_insights(self, insights: List[Insight], trajectory: TrajectoryResult) -> List[Insight]:
        """Refine insights through iterative reflection."""
        refined_insights = insights.copy()
        
        for round in range(self.max_refinement_rounds):
            # Get feedback on current insights
            feedback = await self._get_insight_feedback(refined_insights, trajectory)
            
            # Refine based on feedback
            refined_insights = await self._apply_feedback(refined_insights, feedback)
            
            # Check if refinement is complete
            if self._is_refinement_complete(refined_insights, feedback):
                break
        
        return refined_insights
```

### **4. Curator**
Integrates insights into the context playbook.

**Features:**
- Context integration and organization
- De-duplication and redundancy control
- Bullet creation and modification
- Section and tag management
- Quality maintenance

**Curation Process:**
```python
class ACECurator:
    async def curate_context(self, insights: List[Insight], context: ContextPlaybook) -> CurationResult:
        """Curate insights into the context playbook."""
        new_bullets = []
        updated_bullets = []
        
        for insight in insights:
            # Check for existing similar bullets
            existing_bullet = self._find_similar_bullet(insight, context)
            
            if existing_bullet:
                # Update existing bullet
                updated_bullet = self._update_bullet(existing_bullet, insight)
                updated_bullets.append(updated_bullet)
            else:
                # Create new bullet
                new_bullet = self._create_bullet(insight)
                new_bullets.append(new_bullet)
        
        # Apply updates to context
        for bullet in new_bullets:
            context.add_bullet(bullet)
        
        for bullet in updated_bullets:
            context.update_bullet(bullet.id, bullet.to_dict())
        
        # Perform de-duplication
        self._deduplicate_context(context)
        
        return CurationResult(
            new_bullets=len(new_bullets),
            updated_bullets=len(updated_bullets),
            context_size=len(context.bullets)
        )
    
    def _deduplicate_context(self, context: ContextPlaybook) -> None:
        """Remove duplicate bullets from context."""
        # Group bullets by content similarity
        bullet_groups = self._group_similar_bullets(context.bullets.values())
        
        for group in bullet_groups:
            if len(group) > 1:
                # Merge similar bullets
                merged_bullet = self._merge_bullets(group)
                
                # Remove duplicates
                for bullet in group[1:]:
                    del context.bullets[bullet.id]
                
                # Update with merged bullet
                context.bullets[group[0].id] = merged_bullet
```

### **5. ACE Framework**
Main orchestrator that coordinates all components.

**Features:**
- Component coordination and management
- Workflow orchestration
- Configuration management
- Performance monitoring
- Error handling and recovery

**Main Workflow:**
```python
class ACEFramework:
    async def process_query(self, query: str, context: ContextPlaybook) -> ACEResult:
        """Process a query through the ACE framework."""
        try:
            # 1. Generate trajectory
            trajectory_result = await self.generator.generate_trajectory(query, context)
            
            # 2. Reflect on trajectory
            reflection_result = await self.reflector.reflect_on_trajectory(trajectory_result)
            
            # 3. Curate insights into context
            curation_result = await self.curator.curate_context(
                reflection_result.insights, context
            )
            
            # 4. Update context playbook
            context.last_updated = datetime.now()
            
            return ACEResult(
                success=True,
                trajectory_result=trajectory_result,
                reflection_result=reflection_result,
                curation_result=curation_result,
                context_updated=True
            )
            
        except Exception as e:
            self.logger.error(f"ACE processing failed: {e}")
            return ACEResult(
                success=False,
                error=str(e),
                context_updated=False
            )
```

---

## ⚙️ **Configuration**

### **Basic Configuration**
```toml
[ace]
# Enable ACE framework
enable_ace = true

# Context playbook settings
max_bullets = 1000
max_bullet_length = 500
similarity_threshold = 0.7

# Generator settings
max_trajectory_length = 2000
feedback_collection_enabled = true
multi_epoch_enabled = true
num_epochs = 5

# Reflector settings
max_refinement_rounds = 3
insight_quality_threshold = 0.6
pattern_detection_enabled = true

# Curator settings
deduplication_enabled = true
merge_similar_bullets = true
section_organization = true
tag_management = true
```

### **Advanced Configuration**
```toml
[ace.advanced]
# Multi-epoch adaptation
enable_multi_epoch = true
epoch_learning_rate = 0.1
epoch_memory_decay = 0.9

# Context evolution
enable_context_evolution = true
evolution_threshold = 0.05
evolution_frequency = 100

# Performance optimization
enable_performance_tracking = true
track_insight_quality = true
track_context_effectiveness = true

# Memory management
context_retention_days = 30
max_context_size = 10000
compression_enabled = true
```

### **Component-Specific Configuration**
```toml
[ace.generator]
# Trajectory generation
max_trajectory_length = 2000
context_awareness = 0.8
feedback_sensitivity = 0.7

[ace.reflector]
# Reflection settings
max_refinement_rounds = 3
insight_quality_threshold = 0.6
pattern_detection_sensitivity = 0.8

[ace.curator]
# Curation settings
deduplication_threshold = 0.8
merge_strategy = "weighted_average"
organization_strategy = "semantic_clustering"
```

---

## 🚀 **Usage**

### **Python API**
```python
from openhands.metasop.ace import ACEFramework
from openhands.metasop.ace.models import ContextPlaybook, Query

# Initialize ACE framework
ace_framework = ACEFramework(
    max_bullets=1000,
    similarity_threshold=0.7,
    max_refinement_rounds=3
)

# Create or load context playbook
context = ContextPlaybook(max_bullets=1000)

# Process a query
query = Query(
    text="How to implement user authentication in a web application?",
    context_type="software_development",
    priority="high"
)

result = await ace_framework.process_query(query, context)

if result.success:
    print("Query processed successfully!")
    print(f"New bullets added: {result.curation_result.new_bullets}")
    print(f"Updated bullets: {result.curation_result.updated_bullets}")
    print(f"Context size: {len(context.bullets)}")
else:
    print(f"Query processing failed: {result.error}")
```

### **MetaSOP Integration**
```python
from openhands.metasop import MetaSOPOrchestrator

# Initialize MetaSOP with ACE
orchestrator = MetaSOPOrchestrator("feature_delivery")
orchestrator.ace_framework = ACEFramework()

# Execute task with ACE
task = Task(
    title="Implement user authentication",
    description="Add login/logout functionality",
    priority="high"
)

result = await orchestrator.execute_task(task)

# ACE automatically processes the task and updates context
print(f"ACE processed task: {result.ace_result.success}")
print(f"Context updated: {result.ace_result.context_updated}")
```

### **CodeAct Integration**
```python
from openhands.agenthub.codeact_agent import CodeActAgent

# Initialize CodeAct with ACE
agent = CodeActAgent(
    config=AgentConfig(
        enable_ace=True,
        ace_max_bullets=1000
    )
)

# Use agent with ACE context
response = await agent.run(
    "Create a user authentication system with JWT tokens"
)

# ACE automatically updates context based on execution
print(f"Response generated: {response.success}")
print(f"Context bullets: {len(agent.ace_framework.context.bullets)}")
```

---

## 📊 **Monitoring**

### **Context Playbook Metrics**
```python
# Get context playbook statistics
stats = context.get_statistics()

print("=== Context Playbook Statistics ===")
print(f"Total bullets: {stats['total_bullets']}")
print(f"Helpful bullets: {stats['helpful_bullets']}")
print(f"Harmful bullets: {stats['harmful_bullets']}")
print(f"Average helpfulness: {stats['avg_helpfulness']:.3f}")
print(f"Last updated: {stats['last_updated']}")
print(f"Memory usage: {stats['memory_usage']:.2f} MB")
```

### **ACE Performance Metrics**
```python
# Get ACE framework performance
performance = ace_framework.get_performance_metrics()

print("=== ACE Performance Metrics ===")
print(f"Queries processed: {performance['queries_processed']}")
print(f"Success rate: {performance['success_rate']:.3f}")
print(f"Average processing time: {performance['avg_processing_time']:.3f}s")
print(f"Context updates: {performance['context_updates']}")
print(f"Insights generated: {performance['insights_generated']}")
```

### **Component-Specific Metrics**
```python
# Generator metrics
generator_metrics = ace_framework.generator.get_metrics()
print(f"Trajectories generated: {generator_metrics['trajectories_generated']}")
print(f"Feedback collected: {generator_metrics['feedback_collected']}")

# Reflector metrics
reflector_metrics = ace_framework.reflector.get_metrics()
print(f"Insights extracted: {reflector_metrics['insights_extracted']}")
print(f"Refinement rounds: {reflector_metrics['refinement_rounds']}")

# Curator metrics
curator_metrics = ace_framework.curator.get_metrics()
print(f"Bullets created: {curator_metrics['bullets_created']}")
print(f"Bullets updated: {curator_metrics['bullets_updated']}")
print(f"Deduplication operations: {curator_metrics['deduplication_ops']}")
```

---

## 🎯 **Advanced Features**

### **Multi-Epoch Adaptation**
```python
# Enable multi-epoch adaptation
ace_framework.enable_multi_epoch(
    num_epochs=5,
    learning_rate=0.1,
    memory_decay=0.9
)

# Process query with multiple epochs
result = await ace_framework.process_query_multi_epoch(
    query, context, num_epochs=5
)

print(f"Epochs completed: {result.epochs_completed}")
print(f"Final improvement: {result.final_improvement:.3f}")
```

### **Context Evolution**
```python
# Enable context evolution
ace_framework.enable_context_evolution(
    threshold=0.05,
    frequency=100
)

# Monitor evolution
evolution_stats = ace_framework.get_evolution_stats()
print(f"Evolution cycles: {evolution_stats['cycles']}")
print(f"Context growth: {evolution_stats['growth_rate']:.3f}")
print(f"Quality improvement: {evolution_stats['quality_improvement']:.3f}")
```

### **Custom Insight Types**
```python
from openhands.metasop.ace.models import Insight, InsightType

# Create custom insight type
class CustomInsight(Insight):
    insight_type = InsightType.CUSTOM
    custom_field: str = ""

# Register custom insight handler
def handle_custom_insight(insight: CustomInsight) -> ContextBullet:
    return ContextBullet(
        content=f"Custom insight: {insight.custom_field}",
        section="custom",
        tags=["custom", "insight"]
    )

ace_framework.curator.register_insight_handler(
    InsightType.CUSTOM, handle_custom_insight
)
```

### **Context Export/Import**
```python
# Export context playbook
context_data = context.export_to_dict()
with open("context_backup.json", "w") as f:
    json.dump(context_data, f, indent=2)

# Import context playbook
with open("context_backup.json", "r") as f:
    context_data = json.load(f)
    context = ContextPlaybook.from_dict(context_data)
```

---

## 📚 **API Reference**

### **ACEFramework**

#### **Methods**

##### `__init__(max_bullets=1000, similarity_threshold=0.7, max_refinement_rounds=3)`
Initialize the ACE framework.

**Parameters:**
- `max_bullets`: Maximum number of bullets in context
- `similarity_threshold`: Threshold for bullet similarity
- `max_refinement_rounds`: Maximum refinement rounds

##### `async process_query(query: Query, context: ContextPlaybook) -> ACEResult`
Process a query through the ACE framework.

**Parameters:**
- `query`: Query object to process
- `context`: Context playbook to update

**Returns:**
- `ACEResult`: Result of ACE processing

##### `enable_multi_epoch(num_epochs=5, learning_rate=0.1, memory_decay=0.9)`
Enable multi-epoch adaptation.

##### `enable_context_evolution(threshold=0.05, frequency=100)`
Enable context evolution.

##### `get_performance_metrics() -> Dict[str, Any]`
Get ACE framework performance metrics.

### **ContextPlaybook**

#### **Methods**

##### `add_bullet(bullet: ContextBullet) -> str`
Add a new bullet to the playbook.

##### `update_bullet(bullet_id: str, updates: Dict[str, Any]) -> bool`
Update an existing bullet.

##### `get_statistics() -> Dict[str, Any]`
Get playbook statistics.

##### `export_to_dict() -> Dict[str, Any]`
Export playbook to dictionary.

##### `from_dict(data: Dict[str, Any]) -> ContextPlaybook`
Create playbook from dictionary.

### **ContextBullet**

#### **Properties**
- `id: str`: Unique bullet identifier
- `content: str`: Bullet content
- `section: str`: Section category
- `tags: List[str]`: Associated tags
- `helpful_count: int`: Number of helpful marks
- `harmful_count: int`: Number of harmful marks
- `created_at: datetime`: Creation timestamp
- `updated_at: datetime`: Last update timestamp

---

## 🎯 **Examples**

### **Example 1: Basic ACE Usage**
```python
import asyncio
from openhands.metasop.ace import ACEFramework
from openhands.metasop.ace.models import Query, ContextPlaybook

async def basic_ace_example():
    # Initialize ACE framework
    ace = ACEFramework(max_bullets=500)
    
    # Create context playbook
    context = ContextPlaybook(max_bullets=500)
    
    # Process multiple queries
    queries = [
        "How to implement user authentication?",
        "What are best practices for API design?",
        "How to handle database migrations?",
        "What security measures should I implement?"
    ]
    
    for query_text in queries:
        query = Query(
            text=query_text,
            context_type="software_development",
            priority="medium"
        )
        
        result = await ace.process_query(query, context)
        print(f"Processed: {query_text}")
        print(f"Success: {result.success}")
        print(f"Context size: {len(context.bullets)}")
        print()

asyncio.run(basic_ace_example())
```

### **Example 2: Advanced Context Management**
```python
async def advanced_context_example():
    # Initialize with advanced configuration
    ace = ACEFramework(
        max_bullets=2000,
        similarity_threshold=0.8,
        max_refinement_rounds=5
    )
    
    # Enable advanced features
    ace.enable_multi_epoch(num_epochs=3)
    ace.enable_context_evolution(threshold=0.03)
    
    context = ContextPlaybook(max_bullets=2000)
    
    # Process complex query
    query = Query(
        text="Design a microservices architecture for an e-commerce platform",
        context_type="system_design",
        priority="high"
    )
    
    result = await ace.process_query(query, context)
    
    # Analyze results
    print("=== ACE Processing Results ===")
    print(f"Success: {result.success}")
    print(f"Trajectory length: {len(result.trajectory_result.trajectory)}")
    print(f"Insights generated: {len(result.reflection_result.insights)}")
    print(f"New bullets: {result.curation_result.new_bullets}")
    print(f"Updated bullets: {result.curation_result.updated_bullets}")
    
    # Get context statistics
    stats = context.get_statistics()
    print(f"\n=== Context Statistics ===")
    print(f"Total bullets: {stats['total_bullets']}")
    print(f"Helpful bullets: {stats['helpful_bullets']}")
    print(f"Average helpfulness: {stats['avg_helpfulness']:.3f}")
```

### **Example 3: Integration with MetaSOP**
```python
async def metasop_integration_example():
    from openhands.metasop import MetaSOPOrchestrator
    from openhands.metasop.models import Task
    
    # Initialize MetaSOP with ACE
    orchestrator = MetaSOPOrchestrator("feature_delivery")
    
    # Create complex task
    task = Task(
        title="Implement user authentication system",
        description="Create a complete authentication system with JWT tokens, password hashing, and role-based access control",
        priority="high",
        requirements=["security", "scalability", "user_experience"]
    )
    
    # Execute with ACE
    result = await orchestrator.execute_task(task)
    
    # Check ACE results
    if result.ace_result:
        print("=== ACE Integration Results ===")
        print(f"ACE success: {result.ace_result.success}")
        print(f"Context updated: {result.ace_result.context_updated}")
        print(f"New insights: {len(result.ace_result.reflection_result.insights)}")
        
        # Get updated context
        context = orchestrator.ace_framework.context
        stats = context.get_statistics()
        print(f"Context bullets: {stats['total_bullets']}")
        print(f"Helpful bullets: {stats['helpful_bullets']}")
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Context Playbook Full**
```python
# Check context size
stats = context.get_statistics()
if stats['total_bullets'] >= context.max_bullets:
    # Enable de-duplication
    ace_framework.curator.enable_aggressive_deduplication()
    
    # Or increase max bullets
    context.max_bullets = 2000
```

#### **Low Insight Quality**
```python
# Check insight quality
reflector_metrics = ace_framework.reflector.get_metrics()
if reflector_metrics['avg_insight_quality'] < 0.6:
    # Adjust quality threshold
    ace_framework.reflector.insight_quality_threshold = 0.5
    
    # Increase refinement rounds
    ace_framework.reflector.max_refinement_rounds = 5
```

#### **Memory Usage Issues**
```python
# Monitor memory usage
stats = context.get_statistics()
if stats['memory_usage'] > 100:  # MB
    # Enable compression
    context.enable_compression()
    
    # Clean old bullets
    context.clean_old_bullets(days=30)
```

### **Performance Optimization**

#### **Optimize Similarity Calculation**
```python
# Use cached embeddings
ace_framework.generator.enable_embedding_cache()

# Adjust similarity threshold
ace_framework.similarity_threshold = 0.8  # Higher = more selective
```

#### **Optimize Context Updates**
```python
# Batch context updates
ace_framework.curator.enable_batch_updates(batch_size=10)

# Enable lazy de-duplication
ace_framework.curator.enable_lazy_deduplication()
```

---

## 📈 **Best Practices**

### **Context Design**
1. **Start Small**: Begin with a focused context and let it grow
2. **Use Clear Sections**: Organize bullets by logical sections
3. **Tag Appropriately**: Use meaningful tags for easy retrieval
4. **Regular Cleanup**: Periodically clean up outdated bullets

### **Query Processing**
1. **Provide Context**: Include relevant context in queries
2. **Use Appropriate Priority**: Set realistic priority levels
3. **Monitor Quality**: Track insight quality and adjust thresholds
4. **Handle Failures**: Implement proper error handling

### **System Configuration**
1. **Tune Thresholds**: Adjust similarity and quality thresholds
2. **Monitor Performance**: Track processing time and memory usage
3. **Enable Features Gradually**: Start with basic features and add advanced ones
4. **Regular Maintenance**: Clean up old data and optimize performance

---

**Agentic Context Engineering - The future of intelligent context management.** 🧠
