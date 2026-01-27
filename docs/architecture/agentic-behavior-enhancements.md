# Agentic Behavior Enhancements

## Current State Assessment

### ✅ **Strengths**
- Tooling breadth (tree-sitter editing, bash, browser)
- Modular architecture (Planner, Executor, MemoryManager, SafetyManager)
- Middleware pipeline (plan → verify → execute → observe)
- Anti-hallucination system (always enabled)
- Safety validation in pipeline

### ❌ **Gaps**
1. **No High-Level Planning**: Agent loop is still classic ReAct with no task decomposition
2. **No Self-Reflection**: No verification/assertion phase before executing edits
3. **Static Iteration Limits**: Default 100 iterations, no dynamic pacing based on task complexity
4. **Task Tracker Opt-In**: `enable_plan_mode = False` means no automatic task decomposition
5. **"Think Forever or Bail Early"**: No dynamic iteration management based on progress

---

## Enhancement Plan

### **Phase 1: High-Level Planning Stage** 🎯

**Goal**: Add automatic task decomposition before agent execution.

**Implementation**:

1. **Task Complexity Analyzer**
   - Analyze user message to detect complexity
   - Multi-step tasks: "build X with Y and Z"
   - Single-step tasks: "add a comment to line 5"
   - Threshold: 3+ distinct requirements → complex

2. **Automatic Task Decomposition**
   - For complex tasks, auto-invoke task tracker tool
   - Decompose into sub-tasks before first agent step
   - Store task list in state for agent to reference

3. **Planning Middleware**
   - New `PlanningMiddleware` in tool pipeline
   - Runs before agent.step() if no task plan exists
   - Uses LLM to decompose task if needed

**Files to Create**:
- `forge/agenthub/codeact_agent/task_complexity.py` - Complexity analysis
- `forge/controller/tool_pipeline.py` - Add PlanningMiddleware
- `forge/agenthub/codeact_agent/planner.py` - Add planning methods

**Configuration**:
```python
# forge/core/config/agent_config.py
enable_auto_planning: bool = Field(
    default=True,  # ← Enable by default!
    description="Automatically decompose complex tasks before execution"
)
planning_complexity_threshold: int = Field(
    default=3,
    description="Minimum number of distinct requirements to trigger planning"
)
```

---

### **Phase 2: Self-Reflection/Verification Stage** 🔍

**Goal**: Add verification phase where agent reviews actions before execution.

**Implementation**:

1. **Reflection Middleware**
   - New `ReflectionMiddleware` in tool pipeline
   - Runs in `verify` stage before execution
   - Uses LLM to verify action correctness

2. **Action Verification**
   - For file edits: verify syntax, check for common errors
   - For commands: verify safety, check for destructive operations
   - For complex actions: verify logic and correctness

3. **Self-Correction**
   - If verification fails, agent can self-correct
   - Re-generate action with fixes
   - Max 2 self-correction attempts to prevent loops

**Files to Create**:
- `forge/controller/tool_pipeline.py` - Add ReflectionMiddleware
- `forge/agenthub/codeact_agent/reflection.py` - Reflection logic
- `forge/agenthub/codeact_agent/verification.py` - Action verification

**Configuration**:
```python
enable_reflection: bool = Field(
    default=True,  # ← Enable by default!
    description="Enable self-reflection before executing actions"
)
reflection_max_attempts: int = Field(
    default=2,
    description="Maximum self-correction attempts"
)
```

---

### **Phase 3: Dynamic Iteration Management** 📊

**Goal**: Adjust max_iterations based on task complexity and progress.

**Implementation**:

1. **Task Complexity Scoring**
   - Score: 1-10 based on task complexity
   - Factors: number of files, lines of code, dependencies
   - Initial estimate from planning stage

2. **Progress Tracking**
   - Track completed sub-tasks
   - Track iterations per sub-task
   - Detect stuck conditions early

3. **Dynamic Adjustment**
   - Increase iterations for complex tasks (up to 500)
   - Decrease iterations for simple tasks (min 20)
   - Adjust based on progress rate

**Files to Modify**:
- `forge/controller/state/control_flags.py` - Add dynamic iteration logic
- `forge/controller/state/state_tracker.py` - Add progress tracking
- `forge/agenthub/codeact_agent/task_complexity.py` - Add scoring

**Configuration**:
```python
enable_dynamic_iterations: bool = Field(
    default=True,  # ← Enable by default!
    description="Dynamically adjust max_iterations based on task complexity"
)
min_iterations: int = Field(
    default=20,
    description="Minimum iterations for simple tasks"
)
max_iterations: int = Field(
    default=500,  # ← Increase from 100!
    description="Maximum iterations for complex tasks"
)
complexity_iteration_multiplier: float = Field(
    default=50.0,
    description="Iterations = complexity_score * multiplier (capped at max)"
)
```

---

### **Phase 4: Enable Task Tracker by Default** 📋

**Goal**: Make task tracker available without manual configuration.

**Implementation**:

1. **Always Enable Task Tracker**
   - Remove `enable_plan_mode` requirement
   - Always include task tracker tool
   - Agent decides when to use it

2. **Proactive Task Management**
   - Agent uses task tracker for complex tasks
   - Agent updates task status automatically
   - Task tracker integrated into planning stage

**Files to Modify**:
- `forge/agenthub/codeact_agent/planner.py` - Always include task tracker
- `forge/core/config/agent_config.py` - Remove enable_plan_mode requirement

**Configuration**:
```python
# Remove enable_plan_mode - task tracker always available
# Agent decides when to use it based on task complexity
```

---

## Implementation Priority

### **High Priority** (Immediate Impact)
1. ✅ **Enable Task Tracker by Default** - Easy win, big impact
2. ✅ **Dynamic Iteration Management** - Fix "think forever or bail early"

### **Medium Priority** (Next Sprint)
3. ✅ **High-Level Planning Stage** - Task decomposition
4. ✅ **Self-Reflection/Verification** - Action verification

---

## Expected Outcomes

### **Before Enhancements**
- ❌ Classic ReAct loop
- ❌ No task decomposition
- ❌ Static 100 iterations
- ❌ Task tracker opt-in
- ❌ "Think forever or bail early" problem

### **After Enhancements**
- ✅ High-level planning stage
- ✅ Automatic task decomposition
- ✅ Dynamic iteration management (20-500)
- ✅ Task tracker always available
- ✅ Self-reflection before execution
- ✅ Progress-aware iteration limits

---

## Testing Strategy

### **Unit Tests**
- Task complexity analysis
- Planning middleware
- Reflection middleware
- Dynamic iteration calculation

### **Integration Tests**
- End-to-end planning → execution → reflection
- Dynamic iteration adjustment
- Task tracker integration

### **Performance Tests**
- Planning overhead (should be < 1s)
- Reflection overhead (should be < 0.5s)
- Dynamic iteration impact on execution time

---

## Migration Path

### **Phase 1: Enable by Default** (Week 1)
- Enable task tracker by default
- Increase max_iterations to 500

### **Phase 2: Add Planning** (Week 2)
- Implement task complexity analysis
- Add planning middleware
- Integrate with task tracker

### **Phase 3: Add Reflection** (Week 3)
- Implement reflection middleware
- Add action verification
- Integrate with safety pipeline

### **Phase 4: Dynamic Iterations** (Week 4)
- Implement dynamic iteration management
- Add progress tracking
- Integrate with planning stage

---

## Configuration Migration

### **Old Configuration**
```python
enable_plan_mode = False  # Task tracker opt-in
max_iterations = 100  # Static limit
```

### **New Configuration**
```python
enable_auto_planning = True  # Auto-decompose complex tasks
enable_reflection = True  # Self-reflection before execution
enable_dynamic_iterations = True  # Dynamic iteration management
min_iterations = 20  # Minimum for simple tasks
max_iterations = 500  # Maximum for complex tasks
```

---

## Success Metrics

### **Agentic Behavior Score**
- **Before**: 6.5/10 (classic ReAct)
- **Target**: 8.5/10 (enhanced agentic behavior)

### **Key Metrics**
- Task completion rate: +15%
- Average iterations per task: -20% (better planning)
- Self-correction rate: +10% (reflection)
- User satisfaction: +20%

---

## Next Steps

1. **Review and approve** this enhancement plan
2. **Prioritize** enhancements based on impact
3. **Implement** Phase 1 (Enable by Default)
4. **Test** and iterate
5. **Deploy** to production

---

## References

- [CodeAct Agent Architecture](../features/codeact-agent.md)
- [Task Tracker Tool](../features/tool-integration.md)
- [Middleware Pipeline](../architecture.md#middleware-pipeline)
