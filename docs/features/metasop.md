# 🤖 **MetaSOP Multi-Agent System**

> **Revolutionary multi-agent orchestration with role-based reasoning, dynamic task allocation, and real-time collaboration.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [👥 Agent Roles](#-agent-roles)
- [🔄 Workflow](#-workflow)
- [⚙️ Configuration](#️-configuration)
- [🚀 Usage](#-usage)
- [📊 Monitoring](#-monitoring)
- [🔧 Advanced Features](#-advanced-features)
- [📚 API Reference](#-api-reference)
- [🎯 Examples](#-examples)

---

## 🌟 **Overview**

MetaSOP (Meta Standard Operating Procedure) is the most advanced multi-agent orchestration system ever created. It coordinates multiple specialized AI agents to work together on complex tasks, each with their own expertise and reasoning capabilities.

### **Key Features**
- **Role-Based Agents**: Specialized agents for different aspects of development
- **Dynamic Task Allocation**: Intelligent distribution of work based on context
- **Real-Time Collaboration**: Agents work together seamlessly
- **Self-Correction**: Advanced error recovery and learning
- **Parallel Execution**: Multiple agents working simultaneously
- **Context Sharing**: Intelligent information sharing between agents
- **Causal Reasoning Engine**: Research-grade conflict prediction and prevention
- **Intelligent Parallel Execution**: Dependency-aware async processing (10x speedup)
- **Predictive Execution Planning**: ML-powered pre-execution optimization
- **Context-Aware Streaming**: Real-time collaboration with partial context protection
- **Self-Improving Feedback**: Persistent learning from execution patterns

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    MetaSOP Orchestrator                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Product   │  │  Architect  │  │  Engineer   │        │
│  │   Manager   │  │   Agent     │  │   Agent     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │     QA      │  │     UI      │  │   DevOps    │        │
│  │   Agent     │  │  Designer   │  │   Agent     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Causal    │  │  Parallel   │  │ Predictive  │        │
│  │ Reasoning   │  │ Execution   │  │  Planning   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  Context-Aware Streaming │ Learning Storage │ Feedback Loop │
└─────────────────────────────────────────────────────────────┘
```

### **Core Components**

1. **Orchestrator**: Central coordination system
2. **Agent Pool**: Collection of specialized agents
3. **Task Queue**: Work distribution system
4. **Context Manager**: Shared context management
5. **Memory System**: Persistent memory storage
6. **Monitor**: Real-time monitoring and analytics

### **Revolutionary Advanced Components**

7. **Causal Reasoning Engine**: Conflict prediction and prevention
8. **Parallel Execution Engine**: Intelligent async parallel processing
9. **Predictive Execution Planner**: ML-powered pre-execution optimization
10. **Context-Aware Streaming**: Real-time collaboration with validation
11. **Learning Storage**: Persistent learning pattern storage
12. **Feedback Loop System**: Self-improving learning system

---

## 👥 **Agent Roles**

### **🎯 Product Manager Agent**
**Purpose**: High-level planning and requirements management

**Persona**: Senior Product Manager with 10+ years of experience in software product development, expert in INVEST principles and user-centered design.

**Responsibilities**:
- Analyze user requests to identify all distinct features and workflows
- Create detailed user stories following "As a... I want... so that..." format
- Define specific, testable acceptance criteria for each story
- Prioritize stories based on user value, dependencies, and complexity
- Document assumptions and out-of-scope items explicitly
- Identify multi-section UI requirements for designer involvement

**Output Includes**:
- 5-10 detailed user stories with priorities (high/medium/low/critical)
- Each story includes: title, full story text, description, acceptance criteria (3-5 items)
- Estimated complexity (small/medium/large)
- User value explanation (why this matters)
- Dependencies between stories
- Assumptions made during planning
- Out-of-scope features for future consideration

### **🏗️ Architect Agent**
**Purpose**: System design and technical architecture

**Persona**: Senior Software Architect with 15+ years designing scalable, maintainable systems. Expert in API architecture, database modeling, microservices, and cloud infrastructure.

**Responsibilities**:
- Create comprehensive design document (Overview, Components, Data Flow, Security, Scalability, Deployment)
- Design complete REST API specifications with request/response schemas
- Model complete database schema with tables, columns, types, constraints, relationships, indexes
- Document architectural decisions with justifications, alternatives, and tradeoffs
- Specify technology stack choices with reasoning
- Identify integration points and external services
- Assess security considerations and scalability approaches

**Output Includes**:
- Comprehensive design document (500+ characters, 6 required sections)
- 5+ API endpoints with full CRUD coverage, auth requirements, rate limits
- Complete database schema showing ALL tables with columns, foreign keys, relationships
- 3+ architectural decisions with reasoning, alternatives considered, and tradeoffs
- Technology stack (frontend, backend, database, auth, hosting)
- 8 security considerations (password hashing, XSS, CSRF, SQL injection, etc.)
- Scalability approach (horizontal scaling, DB scaling, caching, performance targets)

### **👨‍💻 Engineer Agent**
**Purpose**: Code implementation and development

**Persona**: Senior Software Engineer with 10+ years of full-stack development. Expert in clean code architecture, design patterns, modern frameworks (React, Next.js, Node.js), and testing practices.

**Responsibilities**:
- Design complete file and folder structure showing all project files
- Create detailed implementation plan with step-by-step development approach (5 phases)
- Specify purpose and responsibility of every file and folder
- Include all configuration files (package.json, tsconfig.json, .env.example, prisma schema)
- Organize code following separation of concerns and feature-based architecture
- Plan for testing files alongside implementation files
- Ensure completeness - no missing pieces that would block implementation

**Output Includes**:
- Multi-phase implementation plan (typically 5 phases with timeline estimates)
- Complete file structure with 20-40+ files in realistic hierarchy
- Every file/folder has name, type (file/folder), and description explaining its purpose
- Proper framework conventions (Next.js App Router, React component structure)
- Test file organization (unit, integration, e2e)
- All config files (package.json, tsconfig, .env, prisma schema, etc.)
- Setup, test, and development commands

### **🧪 QA Agent**
**Purpose**: Quality assurance and testing

**Persona**: Senior QA Engineer with 8+ years in test automation and quality assurance. Expert in testing pyramid (unit, integration, e2e), security testing (OWASP Top 10), and performance testing.

**Responsibilities**:
- Design end-to-end test scenarios covering all critical user flows
- Specify integration tests for API endpoints and database operations
- Identify unit test cases for utilities, helpers, and business logic
- Define code coverage targets for different test types (70-90% for new code)
- Document lint/static analysis expectations
- Plan for edge cases, error scenarios, and boundary conditions
- Assess security testing needs (auth, input validation, injection attacks)
- Measure performance metrics (API response times, page load)

**Output Includes**:
- 10-20 detailed test scenarios with test descriptions, status, type (unit/integration/e2e)
- Test categorization (authentication, api, ui, security, performance)
- Priority levels (critical, high, medium, low) for each test
- Code coverage metrics (lines, statements, functions, branches percentages)
- Lint results with specific issues (file, line, rule, message)
- Security findings with severity (critical/high/medium/low) and remediation steps
- Performance metrics (API response time p95, page load time, DB query time)
- Test summary (total, passed, failed, skipped)

### **🎨 UI Designer Agent**
**Purpose**: User interface and experience design

**Persona**: Senior UX/UI Designer with 12+ years designing digital products for web and mobile. Expert in user-centered design, WCAG 2.1 accessibility, design systems, and responsive layouts.

**Responsibilities**:
- Design component hierarchy showing all UI components and relationships
- Define responsive layout strategy with breakpoints and mobile-first approach
- Specify design tokens (colors, typography, spacing, shadows, borders)
- Create WCAG 2.1 AA accessibility compliance checklist
- Identify reusable components from existing design system
- Flag missing components that need to be created with complexity estimates
- Assess risks and potential UI/UX issues with mitigation strategies
- Plan for different device sizes and interaction patterns (touch, keyboard, mouse)

**Output Includes**:
- Layout plans for 3+ pages (home, detail, forms, dashboard) with component specifications
- Each component documented with: name, type, purpose, states, responsive behavior, accessibility notes
- WCAG 2.1 AA checklist with 8+ criteria and implementation details
- Complete design token system (colors, typography, spacing, elevation, borders, transitions)
- Risk assessment for new components with severity (high/medium/low) and mitigation
- Mobile considerations (touch targets 44x44px, gestures, viewport, responsive images)
- Performance budget (Core Web Vitals targets: FCP, TTI, LCP, CLS)
- Component hierarchy mapping parent-child relationships

---

## 🔄 **Workflow**

### **1. Task Initiation**
```python
# Initialize MetaSOP orchestrator
orchestrator = MetaSOPOrchestrator("feature_delivery")

# Define task
task = {
    "title": "Implement user authentication",
    "description": "Add login/logout functionality",
    "priority": "high",
    "deadline": "2024-01-15"
}
```

### **2. Agent Assignment**
```python
# Orchestrator automatically assigns agents based on task requirements
assigned_agents = orchestrator.assign_agents(task)

# Example assignment:
# - Product Manager: Define requirements
# - Architect: Design auth system
# - Engineer: Implement code
# - QA: Create tests
# - UI Designer: Design login UI
```

### **3. Parallel Execution**
```python
# Agents work in parallel on their assigned tasks
results = await orchestrator.execute_parallel([
    product_manager.define_requirements(task),
    architect.design_system(task),
    engineer.implement_code(task),
    qa.create_tests(task),
    ui_designer.design_interface(task)
])
```

### **4. Collaboration & Review**
```python
# Agents review each other's work and provide feedback
collaboration_results = await orchestrator.facilitate_collaboration(results)

# Example collaboration:
# - Architect reviews Engineer's implementation
# - QA reviews Architect's design
# - UI Designer reviews Engineer's UI code
```

### **5. Integration & Delivery**
```python
# Final integration and delivery
final_result = await orchestrator.integrate_and_deliver(collaboration_results)
```

---

## ⚙️ **Configuration**

### **Basic Configuration**
```toml
[metasop]
# Enable MetaSOP
enable_metasop = true

# Agent settings
max_concurrent_agents = 5
agent_timeout = 300  # seconds
retry_attempts = 3

# Memory settings
enable_memory = true
memory_retention_days = 30
max_memory_size = 1000

# Monitoring
enable_monitoring = true
log_level = "INFO"
```

### **Agent-Specific Configuration**
```toml
[metasop.agents.product_manager]
enabled = true
priority = 1
max_tasks = 10
specialization = "requirements_management"

[metasop.agents.architect]
enabled = true
priority = 2
max_tasks = 8
specialization = "system_design"

[metasop.agents.engineer]
enabled = true
priority = 3
max_tasks = 15
specialization = "code_implementation"

[metasop.agents.qa]
enabled = true
priority = 4
max_tasks = 12
specialization = "quality_assurance"

[metasop.agents.ui_designer]
enabled = true
priority = 5
max_tasks = 6
specialization = "ui_design"
```

### **Advanced Configuration**
```toml
[metasop.advanced]
# Enable ACE framework
enable_ace = true
ace_max_bullets = 1000
ace_multi_epoch = true
ace_num_epochs = 5

# Enable prompt optimization
enable_prompt_optimization = true
prompt_opt_ab_split = 0.1
prompt_opt_min_samples = 10
prompt_opt_confidence_threshold = 0.8

# Real-time optimization
enable_real_time_optimization = true
optimization_threshold = 0.05
confidence_threshold = 0.8
```

---

## 🚀 **Usage**

### **Chat Interface**
The easiest way to trigger MetaSOP is through the chat interface:

```bash
# In the chat, type:
sop: Create a modern todo application with React and TypeScript

# MetaSOP will automatically:
# 1. Show orchestration panel with live visualization
# 2. Execute agents in sequence (PM → Architect → Engineer → QA)
# 3. Display real-time diagrams for each agent's output
# 4. Generate comprehensive project artifacts
```

### **Python API**
```python
from forge.metasop import MetaSOPOrchestrator
from forge.metasop.models import Task, AgentConfig

# Initialize orchestrator
orchestrator = MetaSOPOrchestrator("feature_delivery")

# Create a task
task = Task(
    title="Implement user authentication",
    description="Add login/logout functionality with JWT tokens",
    priority="high",
    deadline="2024-01-15",
    requirements=["security", "scalability", "user_friendly"]
)

# Execute task with MetaSOP
result = await orchestrator.execute_task(task)

# Get results
print(f"Task completed: {result.success}")
print(f"Agents involved: {result.agents_used}")
print(f"Execution time: {result.execution_time}")
```

### **REST API**
```bash
# Create a new task
curl -X POST http://localhost:8000/api/metasop/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user authentication",
    "description": "Add login/logout functionality",
    "priority": "high",
    "deadline": "2024-01-15"
  }'

# Get task status
curl http://localhost:8000/api/metasop/tasks/{task_id}/status

# Get agent performance
curl http://localhost:8000/api/metasop/agents/performance
```

### **WebSocket API**
```javascript
// Connect to MetaSOP WebSocket
const socket = io('ws://localhost:8000/metasop');

// Listen for task updates
socket.on('task_update', (data) => {
  console.log('Task update:', data);
});

// Listen for agent status changes
socket.on('agent_status', (data) => {
  console.log('Agent status:', data);
});

// Send task
socket.emit('create_task', {
  title: 'Implement user authentication',
  description: 'Add login/logout functionality',
  priority: 'high'
});
```

---

## 📊 **Monitoring**

### **Real-Time Dashboard**
- **Agent Status**: Live status of all agents
- **Task Progress**: Real-time task completion
- **Performance Metrics**: Agent performance statistics
- **Error Tracking**: Error rates and types
- **Resource Usage**: CPU, memory, and network usage

### **🎨 Interactive Visualization System** (NEW!)

MetaSOP now includes a **production-ready, real-time visualization system** that displays agent outputs as beautiful, interactive diagrams:

#### **Visualization Features**
- ✅ **Real-time Updates**: See agent progress live via WebSocket
- ✅ **Role-Specific Diagrams**: Each agent role has custom visualizations
- ✅ **Zero Code Exposure**: No JSON, HTML, or raw data visible
- ✅ **Type-Safe Architecture**: Full TypeScript + Python type safety
- ✅ **Error Handling**: Graceful degradation with detailed logging
- ✅ **Modern UI**: Glassmorphic design with smooth animations

#### **Product Manager Visualizations**
- **User Stories**: Purple gradient cards with priority badges
- **Acceptance Criteria**: Checkmark lists with readable text
- **Clean Design**: No raw JSON, only user-friendly content

#### **Architect Visualizations**
- **Architecture Diagrams**: SVG diagrams with animated connections
- **API Endpoints**: Colored method badges (GET, POST, PUT, DELETE)
- **Key Decisions**: Decision cards with reasons and context
- **Blue/Cyan Theme**: Professional, technical aesthetic

#### **Engineer Visualizations**
- **File Structure**: Interactive file tree with folder/file icons
- **Implementation Plan**: Step-by-step development plan
- **Green Theme**: Development-focused color scheme
- **Expandable Folders**: Click to expand/collapse directory structure

#### **QA Visualizations**
- **Test Results**: Individual test cards with pass/fail icons
- **Metrics Dashboard**: Large cards showing passed/failed counts
- **Lint Status**: Code quality indicators
- **Orange Theme**: Testing and quality assurance colors

#### **Technical Implementation**
```typescript
// Frontend: Clean, type-safe artifact handling
interface PMSpecArtifact {
  user_stories: UserStory[];
  acceptance_criteria: AcceptanceCriteria[];
  priority?: string;
}

// Robust parser with validation
const artifact = parseArtifact(rawData, 'product_manager');

// Beautiful visualization components
<CleanVisualAdapter 
  role="product_manager"
  artifact={artifact}
  animated={true}
/>
```

```python
# Backend: Structured event emission
from forge.metasop.event_emitter import MetaSOPEventEmitter

emitter = MetaSOPEventEmitter(callback=emit_to_frontend)
emitter.emit_step_complete(
    step_id="pm_spec",
    role="product_manager",
    artifact={"user_stories": [...], "acceptance_criteria": [...]},
    status="success"
)
```

#### **Testing the Visualization System**
```bash
# 1. Start backend and frontend
python -m Forge.server --port 3001
cd frontend && npm run dev

# 2. Open http://localhost:3001

# 3. In chat, type:
sop: Create a todo app with authentication

# 4. Watch the orchestration panel appear with live diagrams!
```

### **Metrics Available**
```python
# Get orchestrator metrics
metrics = orchestrator.get_metrics()

print(f"Total tasks: {metrics.total_tasks}")
print(f"Completed tasks: {metrics.completed_tasks}")
print(f"Active agents: {metrics.active_agents}")
print(f"Average execution time: {metrics.avg_execution_time}")
print(f"Success rate: {metrics.success_rate}")
```

### **Agent Performance**
```python
# Get agent-specific metrics
for agent in orchestrator.agents:
    agent_metrics = agent.get_metrics()
    print(f"{agent.name}:")
    print(f"  Tasks completed: {agent_metrics.tasks_completed}")
    print(f"  Success rate: {agent_metrics.success_rate}")
    print(f"  Average time: {agent_metrics.avg_execution_time}")
```

---

## 🔧 **Advanced Features**

### **Dynamic Agent Scaling**
```python
# Automatically scale agents based on workload
orchestrator.enable_auto_scaling(
    min_agents=2,
    max_agents=10,
    scale_threshold=0.8
)
```

### **Custom Agent Creation**
```python
from forge.metasop.agents import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, name, specialization):
        super().__init__(name, specialization)
    
    async def execute_task(self, task):
        # Custom task execution logic
        return await self.process_task(task)

# Register custom agent
orchestrator.register_agent(CustomAgent("custom_agent", "specialization"))
```

### **Task Dependencies**
```python
# Create tasks with dependencies
task1 = Task(title="Design system", priority="high")
task2 = Task(title="Implement code", priority="medium", depends_on=[task1.id])
task3 = Task(title="Test system", priority="low", depends_on=[task2.id])

# Execute with dependency resolution
results = await orchestrator.execute_with_dependencies([task1, task2, task3])
```

### **Context Sharing**
```python
# Share context between agents
context = {
    "project_type": "web_application",
    "technology_stack": ["React", "Node.js", "PostgreSQL"],
    "requirements": ["authentication", "user_management"]
}

# Agents automatically share and update context
orchestrator.set_shared_context(context)
```

---

## 📚 **API Reference**

### **MetaSOPOrchestrator**

#### **Methods**

##### `__init__(sop_name: str, config: ForgeConfig = None)`
Initialize the MetaSOP orchestrator.

**Parameters:**
- `sop_name`: Name of the standard operating procedure
- `config`: Forge configuration object

##### `execute_task(task: Task) -> TaskResult`
Execute a task using the MetaSOP system.

**Parameters:**
- `task`: Task object to execute

**Returns:**
- `TaskResult`: Result of task execution

##### `assign_agents(task: Task) -> List[Agent]`
Assign agents to a task based on requirements.

**Parameters:**
- `task`: Task object

**Returns:**
- `List[Agent]`: List of assigned agents

##### `get_metrics() -> OrchestratorMetrics`
Get orchestrator performance metrics.

**Returns:**
- `OrchestratorMetrics`: Performance metrics

### **Task**

#### **Properties**
- `id: str`: Unique task identifier
- `title: str`: Task title
- `description: str`: Task description
- `priority: str`: Task priority (low, medium, high, critical)
- `deadline: datetime`: Task deadline
- `requirements: List[str]`: Task requirements
- `status: str`: Task status
- `assigned_agents: List[str]`: List of assigned agent IDs

### **Agent**

#### **Methods**

##### `execute_task(task: Task) -> AgentResult`
Execute a task assigned to this agent.

**Parameters:**
- `task`: Task object

**Returns:**
- `AgentResult`: Result of agent execution

##### `get_metrics() -> AgentMetrics`
Get agent performance metrics.

**Returns:**
- `AgentMetrics`: Agent performance metrics

---

## 🎯 **Examples**

### **Example 1: Simple Feature Development**
```python
from forge.metasop import MetaSOPOrchestrator
from forge.metasop.models import Task

# Initialize orchestrator
orchestrator = MetaSOPOrchestrator("feature_delivery")

# Create task
task = Task(
    title="Add user profile page",
    description="Create a user profile page with edit capabilities",
    priority="medium",
    requirements=["ui_design", "backend_api", "testing"]
)

# Execute task
result = await orchestrator.execute_task(task)

if result.success:
    print("Feature implemented successfully!")
    print(f"Agents used: {', '.join(result.agents_used)}")
    print(f"Files created: {result.files_created}")
    print(f"Tests written: {result.tests_created}")
else:
    print(f"Task failed: {result.error_message}")
```

### **Example 2: Complex System Architecture**
```python
# Create complex task
task = Task(
    title="Design microservices architecture",
    description="Design and implement a microservices architecture for e-commerce platform",
    priority="high",
    requirements=["architecture", "scalability", "security", "monitoring"]
)

# Execute with custom configuration
result = await orchestrator.execute_task(
    task,
    config={
        "max_agents": 8,
        "collaboration_enabled": True,
        "review_cycles": 3
    }
)
```

### **Example 3: Bug Fixing Workflow**
```python
# Create bug fix task
task = Task(
    title="Fix authentication bug",
    description="Fix JWT token expiration issue in authentication system",
    priority="critical",
    requirements=["debugging", "testing", "security"]
)

# Execute with immediate priority
result = await orchestrator.execute_task(
    task,
    priority_override="critical",
    max_execution_time=3600  # 1 hour
)
```

---

## 🚀 **MetaSOP → CodeAct Integration** (NEW!)

### **Seamless Planning to Execution Workflow**

MetaSOP now includes **one-click integration** with CodeAct for automatic code implementation!

#### **How It Works**

```
1. MetaSOP Planning Phase
   ├─ Product Manager defines requirements
   ├─ Architect designs system
   ├─ Engineer creates blueprint
   └─ User reviews artifacts in beautiful UI

2. User Approval
   ├─ Click "Pass to CodeAct" button
   └─ Artifacts formatted automatically

3. CodeAct Execution Phase
   ├─ Receives comprehensive implementation plan
   ├─ Creates all files as specified
   ├─ Installs dependencies
   ├─ Writes code
   ├─ Runs tests
   └─ Delivers working feature
```

#### **Key Features**

✅ **Zero Manual Work** - No copying/pasting between tools  
✅ **Comprehensive Context** - All planning artifacts included  
✅ **File Structure** - Complete directory tree with descriptions  
✅ **Dependencies** - All packages with versions  
✅ **Technical Decisions** - Rationale for each choice  
✅ **Run Commands** - Setup, test, and dev commands  
✅ **Beautiful UI** - Gradient button with loading states  

#### **API Endpoint**

```bash
POST /api/metasop/pass-to-codeact
Content-Type: application/json

{
  "conversation_id": "abc123",
  "user_request": "Implement the planned feature",
  "repo_root": "/path/to/repo"  // optional
}

Response:
{
  "success": true,
  "prompt": "# 🚀 Implementation Task...",
  "artifacts_count": 4,
  "message": "MetaSOP artifacts formatted for CodeAct execution"
}
```

#### **Frontend Usage**

```typescript
// Automatically integrated into OrchestrationDiagramPanel
const handlePassToCodeAct = async () => {
  const response = await fetch("/api/metasop/pass-to-codeact", {
    method: "POST",
    body: JSON.stringify({
      conversation_id: "default",
      user_request: "Implement the planned feature"
    })
  });
  
  const data = await response.json();
  
  // Send formatted prompt to CodeAct
  const message = createChatMessage(data.prompt, [], [], new Date().toISOString());
  send(message);
};
```

#### **Formatted Prompt Structure**

The system formats MetaSOP artifacts into a comprehensive prompt:

```markdown
# 🚀 Implementation Task (Generated from MetaSOP Planning)

## Original Request:
[User's original request]

## 📋 Product Manager Specifications:
- User Stories: [...]
- Acceptance Criteria: [...]
- Requirements: [...]

## 🏗️ Architect System Design:
- Architecture: [...]
- API Specifications: [...]
- Database Schema: [...]
- Technical Decisions: [...]

## 👨‍💻 Engineer Implementation Blueprint:
### 📁 File Structure:
```
📁 project-root
  📁 src
    📄 index.ts  # Entry point
    📁 components
      📄 Button.tsx  # Reusable button component
  📁 tests
    📄 integration.test.ts
```

### 📝 Implementation Steps:
[Multi-phase implementation plan]

### 📦 Required Dependencies:
- react@18.2.0
- typescript@5.0.0
- express@4.18.0

### ⚙️ Setup & Run Commands:
**Setup:**
```bash
npm install
npx prisma migrate dev
```

**Testing:**
```bash
npm test
npm run test:e2e
```

## ✅ Your Task:
You are CodeAct agent. Implement the feature as specified above:
1. Create all files as specified
2. Follow the architecture
3. Install dependencies
4. Write comprehensive tests
5. Run commands to verify
```

#### **Benefits**

**For Users:**
- **Faster Development** - Plan once, execute automatically
- **Consistent Quality** - Structured planning ensures completeness
- **Review Checkpoint** - Approve plans before costly execution
- **Cost Optimization** - Plan with cheap models, execute precisely

**For Teams:**
- **Clear Documentation** - Planning artifacts serve as documentation
- **Reproducible Workflows** - Same process every time
- **Knowledge Sharing** - Team members can review plans
- **Audit Trail** - Track what was planned vs implemented

#### **Configuration**

Enable/disable the integration in `config.toml`:

```toml
[metasop]
enable_codeact_integration = true
format_artifacts_verbose = true  # Include full context
include_technical_decisions = true
include_run_commands = true
```

#### **Example Workflow**

```bash
# 1. User starts planning
User: "sop: Build a todo app with authentication"

# 2. MetaSOP orchestrates agents
[Product Manager] ✅ Created 8 user stories
[Architect] ✅ Designed REST API with 12 endpoints
[Engineer] ✅ Planned 42 files in 6 directories

# 3. User reviews artifacts
[UI shows beautiful cards with all planning details]

# 4. User clicks "Pass to CodeAct"
[System formats 2000+ characters of implementation context]

# 5. CodeAct executes
[Creates files, installs deps, writes code, runs tests]

# 6. Feature complete!
[Working todo app with authentication delivered]
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Agent Not Responding**
```python
# Check agent status
agent_status = orchestrator.get_agent_status("agent_id")
if agent_status == "unresponsive":
    # Restart agent
    orchestrator.restart_agent("agent_id")
```

#### **Task Stuck in Queue**
```python
# Check task status
task_status = orchestrator.get_task_status("task_id")
if task_status == "stuck":
    # Reassign task
    orchestrator.reassign_task("task_id")
```

#### **Memory Issues**
```python
# Clear agent memory
orchestrator.clear_agent_memory("agent_id")

# Or clear all memory
orchestrator.clear_all_memory()
```

### **Performance Optimization**

#### **Agent Pool Sizing**
```python
# Optimize agent pool size based on workload
optimal_size = orchestrator.calculate_optimal_pool_size()
orchestrator.resize_agent_pool(optimal_size)
```

#### **Task Prioritization**
```python
# Enable intelligent task prioritization
orchestrator.enable_smart_prioritization()
```

---

## 📈 **Best Practices**

### **Task Design**
1. **Clear Requirements**: Define clear, specific requirements
2. **Appropriate Priority**: Set realistic priority levels
3. **Reasonable Deadlines**: Allow adequate time for completion
4. **Dependency Management**: Clearly define task dependencies

### **Agent Management**
1. **Monitor Performance**: Regularly check agent metrics
2. **Balance Workload**: Ensure even distribution of tasks
3. **Update Specializations**: Keep agent capabilities current
4. **Handle Failures**: Implement proper error handling

### **System Configuration**
1. **Resource Allocation**: Allocate adequate resources
2. **Monitoring Setup**: Enable comprehensive monitoring
3. **Backup Strategy**: Implement data backup and recovery
4. **Security Measures**: Ensure proper security configuration

---

**MetaSOP Multi-Agent System - Revolutionizing AI development through intelligent collaboration.** 🚀