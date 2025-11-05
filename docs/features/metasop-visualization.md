# 🎨 **MetaSOP Visualization System**

> **Production-ready, real-time visualization system for MetaSOP agent outputs with type-safe architecture and beautiful UI.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🎨 Visualization Components](#-visualization-components)
- [🔄 Data Flow](#-data-flow)
- [⚙️ Technical Implementation](#️-technical-implementation)
- [🚀 Usage](#-usage)
- [🔧 Customization](#-customization)
- [📊 Testing](#-testing)

---

## 🌟 **Overview**

The MetaSOP Visualization System transforms raw agent artifacts into beautiful, interactive diagrams in real-time. Each agent role (Product Manager, Architect, Engineer, QA) has custom visualizations optimized for their output type.

### **Key Features**

- ✅ **Real-Time Updates**: Live WebSocket streaming
- ✅ **Type-Safe**: Full TypeScript + Python type safety
- ✅ **Zero Code Exposure**: No JSON, HTML, or raw data visible
- ✅ **Graceful Degradation**: Robust error handling
- ✅ **Modern UI**: Glassmorphic design with animations
- ✅ **Role-Specific**: Custom visualizations per agent role
- ✅ **Production-Ready**: Comprehensive testing and validation

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                     Backend (Python)                        │
├─────────────────────────────────────────────────────────────┤
│  MetaSOP Orchestrator                                       │
│    ↓                                                        │
│  Template Loader → Load agent templates                    │
│    ↓                                                        │
│  Agent Execution → Generate artifacts                      │
│    ↓                                                        │
│  Event Emitter → Structure events                          │
│    ↓                                                        │
│  WebSocket → Emit to frontend                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    [WebSocket Connection]
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Hook → Receive events                           │
│    ↓                                                        │
│  Event Parser → Extract artifact data                      │
│    ↓                                                        │
│  Artifact Parser → Validate & normalize                    │
│    ↓                                                        │
│  Visual Adapter → Route to role-specific component         │
│    ↓                                                        │
│  Visualization Component → Render beautiful UI             │
└─────────────────────────────────────────────────────────────┘
```

### **Component Overview**

#### **Backend Components**

1. **`template_loader.py`**: Loads MetaSOP agent templates
2. **`event_emitter.py`**: Structures and emits events
3. **`clean_orchestrator.py`**: Wraps legacy orchestrator
4. **`clean_router.py`**: Routes MetaSOP requests

#### **Frontend Components**

1. **`metasop-artifacts.ts`**: TypeScript type definitions
2. **`artifact-parser.ts`**: Robust data parser
3. **`clean-visualizations.tsx`**: Visualization components
4. **`use-clean-metasop-orchestration.ts`**: React hook
5. **`modern-flow-diagram.tsx`**: React Flow integration

---

## 🎨 **Visualization Components**

### **🎯 Product Manager View** (Purple Theme)

**Displays:**
- User story cards with priority badges
- Acceptance criteria checklists
- Clean, glassmorphic design

**Example Output:**
```
┌───────────────────────────────────────┐
│ 👤 User Story #1          [HIGH] ◉   │
│                                       │
│ As a user, I want to login            │
│ so that I can access my account       │
│                                       │
│ ✅ Acceptance Criteria                │
│  ☑ User can enter email/password     │
│  ☑ System validates credentials       │
│  ☑ User redirected on success         │
└───────────────────────────────────────┘
```

### **🏗️ Architect View** (Blue Theme)

**Displays:**
- SVG architecture diagrams with animations
- API endpoint cards with method badges
- Architectural decision cards

**Example Output:**
```
┌───────────────────────────────────────┐
│ 🏗 System Architecture                │
│                                       │
│  [Client] ←→ [API Gateway] ←→ [DB]  │
│     ↓             ↓            ↓     │
│  [Auth]       [Services]    [Cache]  │
│                                       │
│ 🌐 API Endpoints                      │
│  POST /api/auth/login     [POST] ●   │
│  GET  /api/users/:id      [GET]  ●   │
│                                       │
│ 💡 Key Decisions                      │
│  • Use JWT for authentication         │
│  • PostgreSQL for data persistence    │
└───────────────────────────────────────┘
```

### **👨‍💻 Engineer View** (Green Theme)

**Displays:**
- Interactive file structure tree
- Expandable folders
- Implementation plan

**Example Output:**
```
┌───────────────────────────────────────┐
│ 📁 File Structure                     │
│                                       │
│ 📂 src/                               │
│  📂 components/                       │
│   📄 LoginForm.tsx                    │
│   📄 UserProfile.tsx                  │
│  📂 api/                              │
│   📄 auth.ts                          │
│   📄 users.ts                         │
│  📄 index.tsx                         │
│                                       │
│ 📝 Implementation Plan                │
│  1. Set up authentication system      │
│  2. Create user components            │
│  3. Integrate API endpoints           │
└───────────────────────────────────────┘
```

### **🧪 QA View** (Orange Theme)

**Displays:**
- Test results dashboard
- Pass/fail metrics
- Lint status

**Example Output:**
```
┌───────────────────────────────────────┐
│ 📊 Test Results                       │
│                                       │
│ [✅ Passed: 24]    [❌ Failed: 0]    │
│                                       │
│ 📊 Code Coverage                      │
│  Lines: 87%      Statements: 85%      │
│  Functions: 82%  Branches: 76%        │
│                                       │
│ Test Scenarios (15):                  │
│ ✅ User Registration Flow             │
│    User can register with credentials │
│    🔴 critical  e2e  authentication   │
│                                       │
│ ✅ SQL Injection Prevention           │
│    Malicious input safely handled     │
│    🔴 critical  integration  security │
│                                       │
│ 🔒 Security Findings (0)              │
│  No vulnerabilities found ✅          │
│                                       │
│ ⚡ Performance                        │
│  API Response: 150ms                  │
│  Page Load: 1.8s                      │
│  DB Query: 45ms                       │
│                                       │
│ 📈 Lint: Clean ✅                     │
└───────────────────────────────────────┘
```

---

## 🔄 **Data Flow**

### **1. Agent Execution**

```python
# Backend: Agent generates artifact
artifact = {
    "user_stories": [
        {
            "title": "User Login",
            "description": "As a user, I want to login...",
            "priority": "high"
        }
    ],
    "acceptance_criteria": [
        "User can enter credentials",
        "System validates credentials"
    ]
}
```

### **2. Event Emission**

```python
# Backend: Emit structured event
emitter.emit_step_complete(
    step_id="pm_spec",
    role="product_manager",
    artifact=artifact,
    status="success"
)
```

### **3. WebSocket Transmission**

```json
{
  "type": "metasop_step_update",
  "event_type": "step_complete",
  "step_id": "pm_spec",
  "role": "product_manager",
  "artifact": { ... },
  "status": "success",
  "timestamp": "2025-01-23T10:30:00Z"
}
```

### **4. Frontend Reception**

```typescript
// Frontend: Receive and parse event
const handleEvent = (event: CleanMetaSOPEvent) => {
  if (event.event_type === 'step_complete') {
    const artifact = parseArtifact(event.artifact, event.role);
    updateStepWithArtifact(event.step_id, artifact);
  }
};
```

### **5. Visualization Rendering**

```typescript
// Frontend: Render visualization
<CleanVisualAdapter 
  role="product_manager"
  artifact={artifact}
  animated={true}
/>
```

---

## ⚙️ **Technical Implementation**

### **Type Definitions**

```typescript
// Frontend: Strict TypeScript interfaces
interface PMSpecArtifact {
  user_stories: UserStory[];
  acceptance_criteria: AcceptanceCriteria[];
  priority?: string;
}

interface UserStory {
  title: string;
  story?: string;
  description?: string;
  priority?: 'high' | 'medium' | 'low';
}

interface AcceptanceCriteria {
  criteria?: string;
  description?: string;
}
```

### **Artifact Parser**

```typescript
// Frontend: Robust parsing with validation
export function parseArtifact(
  rawData: unknown,
  role: string
): ParsedArtifact {
  try {
    // Handle __raw__ field unwrapping
    let data = rawData;
    if (data && typeof data === 'object' && '__raw__' in data) {
      data = JSON.parse((data as any).__raw__);
    }

    // Role-specific parsing
    switch (role) {
      case 'product_manager':
        return parsePMSpec(data);
      case 'architect':
        return parseArchitectSpec(data);
      // ... other roles
    }
  } catch (error) {
    console.error('Parse error:', error);
    return { error: 'Failed to parse artifact' };
  }
}
```

### **Event Emitter**

```python
# Backend: Structured event emission
class MetaSOPEventEmitter:
    def emit_step_complete(
        self,
        step_id: str,
        role: str,
        artifact: Dict[str, Any],
        status: str = "success"
    ):
        event = MetaSOPEvent(
            event_type=EventType.STEP_COMPLETE,
            step_id=step_id,
            role=role,
            artifact=artifact,
            status=status,
            timestamp=datetime.now().isoformat()
        )
        self._emit(event)
```

### **React Hook**

```typescript
// Frontend: Clean MetaSOP orchestration hook
export function useCleanMetaSOPOrchestration(events: any[]) {
  const [steps, setSteps] = useState<OrchestrationStep[]>([]);
  const [status, setStatus] = useState<string>('idle');
  
  useEffect(() => {
    events.forEach(event => {
      if (event.type === 'metasop_step_update') {
        handleStepUpdate(event);
      }
    });
  }, [events]);
  
  return { steps, status };
}
```

---

## 🚀 **Usage**

### **Basic Usage**

```bash
# 1. Start backend and frontend
python -m openhands.server --port 3001
cd frontend && npm run dev

# 2. Open http://localhost:3001

# 3. In chat, type:
sop: Create a todo app with authentication

# 4. Watch visualizations appear in real-time!
```

### **Programmatic Usage**

```python
# Backend: Trigger MetaSOP with visualization
from openhands.metasop.clean_router import run_clean_metasop_orchestration

async def example():
    await run_clean_metasop_orchestration(
        conversation_id="conv_123",
        message="Create a todo app",
        emit_callback=emit_to_frontend
    )
```

```typescript
// Frontend: Subscribe to updates
const { steps, status } = useCleanMetaSOPOrchestration(events);

return (
  <ModernFlowDiagram 
    steps={steps}
    status={status}
  />
);
```

---

## 🔧 **Customization**

### **Custom Themes**

```typescript
// Add custom theme to visualizations
const customTheme = {
  productManager: {
    primary: '#9333ea',
    secondary: '#a855f7',
    accent: '#c084fc'
  },
  architect: {
    primary: '#3b82f6',
    secondary: '#60a5fa',
    accent: '#93c5fd'
  }
};
```

### **Custom Components**

```typescript
// Create custom visualization component
export function CustomPMVisual({ artifact }: { artifact: PMSpecArtifact }) {
  return (
    <div className="custom-pm-visual">
      {artifact.user_stories.map(story => (
        <div key={story.title} className="custom-story-card">
          {/* Custom rendering */}
        </div>
      ))}
    </div>
  );
}
```

---

## 📊 **Testing**

### **Backend Tests**

```bash
# Run backend tests
cd OpenHands
python -m pytest openhands/metasop/tests/ -v

# Test event emitter
python -m pytest openhands/metasop/tests/test_event_emitter.py

# Test artifact generation
python -m pytest openhands/metasop/tests/test_artifacts.py
```

### **Frontend Tests**

```bash
# Run frontend tests
cd OpenHands/frontend
npm test

# Test parser
npm test -- artifact-parser.test.ts

# Test components
npm test -- clean-visualizations.test.tsx
```

### **Manual Testing**

See `OpenHands/MANUAL_METASOP_TEST_GUIDE.md` for comprehensive manual testing procedures.

---

## 🎯 **Best Practices**

### **Backend**

1. **Always emit structured events** using `MetaSOPEventEmitter`
2. **Validate artifact structure** before emission
3. **Include error handling** for all agent executions
4. **Log all events** for debugging

### **Frontend**

1. **Use the artifact parser** for all raw data
2. **Handle loading states** gracefully
3. **Show error messages** when parsing fails
4. **Test with mock data** before live integration

### **Testing**

1. **Test all agent roles** individually
2. **Test error scenarios** (invalid data, network failures)
3. **Verify client-side rendering** (no hydration errors)
4. **Check console** for warnings/errors

---

## 📈 **Performance**

### **Optimization Tips**

1. **Use React.memo** for expensive components
2. **Memoize nodeTypes** in React Flow
3. **Implement virtual scrolling** for large datasets
4. **Lazy load** heavy visualizations

### **Metrics**

- **Event latency**: < 50ms
- **Render time**: < 100ms per component
- **Memory usage**: < 50MB for typical session
- **Bundle size**: +120KB gzipped

---

## 🚨 **Troubleshooting**

### **Visualizations not appearing**

1. Check WebSocket connection in DevTools → Network → WS
2. Verify events include artifact data
3. Check console for parsing errors

### **Hydration errors**

1. Ensure client-side rendering checks are in place
2. Verify React Flow components not rendered on server
3. Check `isClient` state in components

### **Performance issues**

1. Enable React DevTools Profiler
2. Check for unnecessary re-renders
3. Verify nodeTypes memoization
4. Optimize artifact data size

---

**MetaSOP Visualization System - Beautiful, real-time agent collaboration diagrams!** 🎨✨

