# Advanced Features

This document covers advanced features and technical capabilities that provide deeper insights into Forge's agentic workflow.

## Beta Launch: Temporarily Disabled UI Features

For the beta launch, several advanced UI features have been **disabled but preserved** for easy post-beta re-activation. This ensures a clean, focused user experience while maintaining all the advanced functionality for future use.

### Disabled Features

The following features are **disabled in the UI only** - all backend functionality and components remain intact:

#### 1. Technical Details Toggle
- **What it does**: Shows/hides detailed technical information about agent actions (terminal commands, file operations)
- **Status**: Hardcoded to `false` in `chat-interface.tsx`
- **Component**: Fully functional, just not rendered
- **Re-enable**: Change `const showTechnicalDetails = false;` back to state hook

#### 2. Keyboard Shortcuts Panel (`Ctrl+?`)
- **What it does**: Displays all available keyboard shortcuts
- **Status**: Component and rendering disabled
- **Files**: `keyboard-shortcuts-panel.tsx` (preserved)
- **Re-enable**: Uncomment imports and rendering in `chat-interface.tsx`

#### 3. Conversation Bookmarks (`Ctrl+B`)
- **What it does**: Allows users to bookmark important messages for quick reference
- **Status**: Component and rendering disabled
- **Files**: `conversation-bookmarks.tsx` (preserved)
- **Re-enable**: Uncomment imports, hooks, and rendering in `chat-interface.tsx`

#### 4. MetaSOP Orchestration Diagram Panel
- **What it does**: Visualizes multi-agent orchestration workflows in real-time
- **Status**: Panel rendering disabled, orchestration still works
- **Files**: `orchestration-diagram-panel.tsx` (preserved)
- **Re-enable**: Change `const showOrchestrationPanel = false;` back to state hook

### What's Still Active

✅ **Conversation Search** (`Ctrl+K`) - Kept as it's essential for beta users

### Post-Beta Re-Activation Guide

To re-enable all advanced features after beta:

**File to modify**: `frontend/src/components/features/chat/chat-interface.tsx`

#### Step 1: Uncomment Imports (Lines ~25-38)

```typescript
// Change from:
// Beta launch: Keyboard shortcuts disabled
// import { KeyboardShortcutsPanel, useKeyboardShortcuts } from "./keyboard-shortcuts-panel";

// Beta launch: Bookmarks disabled
// import { ConversationBookmarks, useConversationBookmarks } from "./conversation-bookmarks";

// Beta launch: Orchestration disabled
// import { OrchestrationDiagramPanel } from "../orchestration/orchestration-diagram-panel";

// To:
import { KeyboardShortcutsPanel, useKeyboardShortcuts } from "./keyboard-shortcuts-panel";
import { ConversationBookmarks, useConversationBookmarks } from "./conversation-bookmarks";
import { OrchestrationDiagramPanel } from "../orchestration/orchestration-diagram-panel";
```

#### Step 2: Re-enable State Hooks (Lines ~111-156)

```typescript
// Change from:
// Advanced features disabled for beta launch
// const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
// const bookmarksHook = useConversationBookmarks();

// Keyboard shortcuts disabled for beta
// useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

// Orchestration panel disabled for beta
const showOrchestrationPanel = false;

// Technical details hardcoded to false for beta launch
const showTechnicalDetails = false;

// To:
const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
const bookmarksHook = useConversationBookmarks();

useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

const [showOrchestrationPanel, setShowOrchestrationPanel] = React.useState(false);

const [showTechnicalDetails, setShowTechnicalDetails] = React.useState<boolean>(() => {
  try {
    return localStorage.getItem("Forge.showTechnicalDetails") === "true";
  } catch {
    return false;
  }
});

React.useEffect(() => {
  try {
    localStorage.setItem("Forge.showTechnicalDetails", showTechnicalDetails ? "true" : "false");
  } catch {
    /* ignore */
  }
}, [showTechnicalDetails]);
```

#### Step 3: Re-enable Keyboard Shortcuts (Lines ~121-143)

```typescript
// Change from:
// Beta launch: Only search keyboard shortcut enabled
React.useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Cmd/Ctrl + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      setIsSearchOpen(true);
    }
    
    // Escape to close search
    if (e.key === 'Escape') {
      if (isSearchOpen) setIsSearchOpen(false);
    }
  };

  if (!isInputFocused) {
    window.addEventListener('keydown', handleKeyDown);
  }
  
  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}, [isInputFocused, isSearchOpen]);

// To:
React.useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Cmd/Ctrl + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      setIsSearchOpen(true);
    }
    
    // Cmd/Ctrl + B for bookmarks
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      bookmarksHook.setIsOpen(true);
    }
    
    // Escape to close panels
    if (e.key === 'Escape') {
      if (isSearchOpen) setIsSearchOpen(false);
      if (bookmarksHook.isOpen) bookmarksHook.setIsOpen(false);
      if (showShortcutsPanel) setShowShortcutsPanel(false);
    }
  };

  if (!isInputFocused) {
    window.addEventListener('keydown', handleKeyDown);
  }
  
  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}, [isInputFocused, isSearchOpen, bookmarksHook, showShortcutsPanel]);

// Also uncomment this line (around line 175):
useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);
```

#### Step 4: Re-enable UI Buttons (Lines ~488-586)

Find the comment `{/* Advanced features removed for beta launch */}` and add back the button code:

```typescript
{/* Technical Details Toggle */}
<Button
  type="button"
  variant="ghost"
  size="icon"
  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
  className={cn(
    "h-8 w-8 p-1 rounded-lg transition-all duration-200",
    showTechnicalDetails
      ? "bg-brand-500/20 text-violet-500 hover:bg-brand-500/30"
      : "hover:bg-violet-500/10 text-foreground-secondary"
  )}
  title={showTechnicalDetails ? "Hide technical details" : "Show technical details"}
>
  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  </svg>
</Button>

{/* Keyboard Shortcuts Button */}
<Button
  type="button"
  variant="ghost"
  size="icon"
  onClick={() => setShowShortcutsPanel(true)}
  className="h-8 w-8 p-1 rounded-lg hover:bg-violet-500/10 transition-all duration-200"
  title="Keyboard shortcuts (Ctrl+?)"
>
  <Keyboard className="h-3.5 w-3.5 text-foreground-secondary" />
</Button>

{/* Bookmarks Button */}
<Button
  type="button"
  variant="ghost"
  size="icon"
  onClick={() => bookmarksHook.setIsOpen(true)}
  className="h-8 w-8 p-1 rounded-lg hover:bg-violet-500/10 transition-all duration-200 relative"
  title="Bookmarked messages"
>
  <Bookmark className="h-3.5 w-3.5 text-foreground-secondary" />
  {bookmarksHook.bookmarks.length > 0 && (
    <span className="absolute -top-0.5 -right-0.5 h-3 w-3 bg-brand-500 rounded-full text-white text-[8px] font-bold flex items-center justify-center">
      {bookmarksHook.bookmarks.length}
    </span>
  )}
</Button>

{/* Orchestration Diagrams Button (when SOP is enabled) */}
{useSop && (
  <Button
    type="button"
    variant="ghost"
    size="icon"
    onClick={() => setShowOrchestrationPanel(!showOrchestrationPanel)}
    className={cn(
      "h-8 w-8 p-1 rounded-lg transition-all duration-200 relative",
      showOrchestrationPanel
        ? "bg-brand-500 text-white"
        : "hover:bg-violet-500/10 text-foreground-secondary",
      (isOrchestrating || optimisticSopStarting) &&
        "animate-pulse bg-warning-500 text-white",
    )}
    title={
      (isOrchestrating || optimisticSopStarting)
        ? "MetaSOP orchestration in progress"
        : "Orchestration Diagrams"
    }
  >
    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
    {(isOrchestrating || optimisticSopStarting) && (
      <div className="absolute -top-1 -right-1 h-3 w-3 bg-orange-500 rounded-full animate-ping" />
    )}
  </Button>
)}
```

#### Step 5: Re-enable Component Rendering (Lines ~644-674)

```typescript
// Change from:
{/* Orchestration Diagram Panel - Disabled for beta launch */}

{/* Beta launch: Advanced features disabled, only search enabled */}

// To:
{/* Orchestration Diagram Panel (sliding side panel) */}
{showOrchestrationPanel && useSop && (
  <div className="w-full md:w-96 lg:w-[500px] border-l border-border dark:border-border animate-slide-in-right overflow-hidden">
    <OrchestrationDiagramPanel
      onClose={() => setShowOrchestrationPanel(false)}
    />
  </div>
)}

{/* Keyboard Shortcuts Panel */}
<KeyboardShortcutsPanel
  isOpen={showShortcutsPanel}
  onClose={() => setShowShortcutsPanel(false)}
/>

{/* Conversation Bookmarks */}
<ConversationBookmarks
  isOpen={bookmarksHook.isOpen}
  onClose={() => bookmarksHook.setIsOpen(false)}
  bookmarks={bookmarksHook.bookmarks}
  onSelectBookmark={(index) => {
    console.log("Navigate to bookmarked message:", index);
  }}
  onRemoveBookmark={bookmarksHook.removeBookmark}
/>
```

#### Step 6: Re-add Icon Imports (Line ~6)

```typescript
// Change from:
import { ChevronLeft, Menu, X, Search } from "lucide-react";

// To:
import { ChevronLeft, Menu, X, Keyboard, Search, Bookmark } from "lucide-react";
```

#### Step 7: Rebuild and Deploy

```bash
cd frontend
npm run build
docker-compose up -d --force-recreate forge
```

### Why These Features Were Disabled for Beta

1. **Simplified UX**: Focus beta testers on core functionality
2. **Prevent Console Manipulation**: Advanced users couldn't access features via browser console (credibility issue)
3. **Cleaner First Impression**: Reduce UI complexity for new users
4. **Easy Re-enable**: All components preserved, just imports/rendering disabled

### Estimated Re-enable Time

**~5-10 minutes** - Just uncomment code blocks and rebuild

### Testing Post-Re-enable

After re-enabling, test:
- `Ctrl+?` opens keyboard shortcuts panel
- `Ctrl+B` opens bookmarks panel
- `Ctrl+K` still works for search
- Technical details toggle shows/hides terminal commands
- MetaSOP orchestration diagram appears when orchestration is active
- All state persists in localStorage as expected

## Error Handling and Recovery

Forge implements sophisticated error handling mechanisms to ensure reliable operation across complex multi-agent scenarios.

### Retry Policies

The system uses configurable retry policies with exponential backoff:

```toml
[metasop]
# Retry settings for orchestration steps
max_attempts = 10
initial_delay = 1.0  # seconds
backoff_factor = 2.0
max_delay = 60.0     # seconds
```

**Features:**
- **Exponential backoff**: Delays increase progressively to avoid overwhelming systems
- **Maximum attempts**: Prevents infinite retry loops
- **Configurable delays**: Fine-tune for different environments

### Timeout Management

Dedicated timeout executors handle long-running operations:

- **TimeoutStepExecutor**: Manages orchestration step timeouts
- **TimeoutQAExecutor**: Handles QA and validation timeouts
- **Stuck thread detection**: Identifies and handles unresponsive threads

```toml
[metasop]
# Timeout settings
step_timeout = 300    # 5 minutes per step
qa_timeout = 120      # 2 minutes for QA
stuck_thread_timeout = 600  # 10 minutes
```

### Failure Classification and Remediation

The system automatically classifies failures and suggests remediation:

- **DefaultFailureClassifier**: Categorizes errors by type and severity
- **Remediation planning**: Generates actionable recovery steps
- **Error taxonomy**: Structured error categorization for better diagnostics

**Common failure types:**
- Network timeouts
- Resource exhaustion
- Agent conflicts
- Execution errors
- Validation failures

### Recovery Strategies

Multiple recovery strategies are available:

- **Automatic retry**: For transient failures
- **Alternative paths**: Route around failed components
- **Graceful degradation**: Reduce functionality to maintain operation
- **Manual intervention**: Allow user-guided recovery

### Fallback Mechanisms

Layered fallback systems ensure continuity:

- **LLM fallbacks**: Switch to heuristic methods when LLM unavailable
- **Memory fallbacks**: Vector search → lexical search → basic matching
- **Runtime fallbacks**: Docker → Local → CLI execution
- **Agent fallbacks**: Full orchestration → simplified execution

## Causal Reasoning Engine

The causal reasoning engine predicts conflicts, side effects, and opportunities in multi-agent workflows.

### Conflict Prediction

Uses LLM-powered analysis to identify potential issues:

- **Agent conflicts**: When multiple agents modify the same resources
- **Side effects**: Unintended consequences of actions
- **Resource contention**: Competition for system resources
- **Dependency issues**: Broken chains of operations

### Confidence Scoring

Each prediction includes confidence levels:

- **High confidence**: >80% - Strong likelihood of issue
- **Medium confidence**: 50-80% - Potential concern
- **Low confidence**: <50% - Minor consideration

### Learning from Execution

The engine improves over time by:

- **Outcome analysis**: Comparing predictions to actual results
- **Pattern recognition**: Identifying recurring conflict types
- **Strategy adaptation**: Adjusting prediction algorithms

### Configuration

```toml
[metasop.causal_reasoning]
enabled = true
confidence_threshold = 0.7
learning_enabled = true
fallback_to_heuristics = true
```

## Tree-sitter Integration

Structure-aware code editing using Tree-sitter parsers.

### Supported Languages

40+ programming languages with AST-based editing:

- **Major languages**: Python, JavaScript, TypeScript, Java, C++, Go, Rust
- **Web technologies**: HTML, CSS, JSON, YAML
- **Data formats**: SQL, GraphQL, Docker
- **Configuration**: TOML, INI, Properties

### Structural Operations

Beyond text editing, Tree-sitter enables:

- **Node-level modifications**: Change function signatures, class structures
- **Scope-aware insertions**: Add imports, methods in correct locations
- **Syntax validation**: Ensure edits maintain valid code structure
- **Refactoring support**: Rename variables, extract methods with context

### Performance Benefits

- **Faster parsing**: Incremental updates to AST
- **Accurate modifications**: Context-aware changes
- **Language agnostic**: Consistent editing across languages
- **Error prevention**: Structural validation before execution

## ACE Framework (Agentic Context Engineering)

Self-improving agents through accumulated experience and playbooks.

### Playbook System

Learned strategies stored in playbooks:

- **Task-specific patterns**: Successful approaches for common tasks
- **Context accumulation**: Building knowledge from past executions
- **Strategy evolution**: Adapting based on outcomes

### Learning Mechanisms

ACE learns through:

- **Execution analysis**: Reviewing successful and failed attempts
- **Pattern extraction**: Identifying effective strategies
- **Context enrichment**: Adding domain knowledge over time

### Integration Points

ACE enhances multiple components:

- **MetaSOP orchestration**: Improved planning based on learned patterns
- **CodeAct execution**: Better code generation from accumulated knowledge
- **Error recovery**: Learned remediation strategies

### Configuration

```toml
[metasop.ace]
enabled = true
playbook_persistence_path = "~/.Forge/ace_playbooks"
learning_rate = 0.1
max_playbook_size = 1000
context_window = 50
```

## Advanced Orchestration Features

Beyond basic multi-agent coordination.

### Real-time Event Processing

WebSocket-based event streaming:

- **Step progress**: Live updates on orchestration progress
- **Artifact generation**: Real-time artifact creation and updates
- **Conflict detection**: Immediate notification of issues
- **Status changes**: Agent state and orchestration status

### Parallel Execution

Concurrent agent operations:

- **Dependency management**: Ensuring correct execution order
- **Resource allocation**: Balancing load across agents
- **Synchronization**: Coordinating shared resources
- **Scalability**: Handling multiple concurrent workflows

### Artifact Management

Structured data exchange between agents:

- **Artifact types**: Code, documentation, test cases, designs
- **Version control**: Tracking artifact evolution
- **Handoff protocols**: Seamless transfer between agents
- **Quality assurance**: Validation and review processes

### Performance Optimization

Advanced optimization techniques:

- **Predictive execution**: Anticipating next steps
- **Caching strategies**: Reusing successful patterns
- **Load balancing**: Distributing work efficiently
- **Resource monitoring**: Tracking and optimizing usage

## Configuration Examples

### Production Setup

```toml
[metasop]
enabled = true
default_sop = "feature_delivery"
enable_failure_taxonomy = true

[metasop.causal_reasoning]
enabled = true
confidence_threshold = 0.8
learning_enabled = true

[metasop.ace]
enabled = true
playbook_persistence_path = "/data/ace_playbooks"
learning_rate = 0.2

[metasop.performance]
parallel_execution = true
max_concurrent_agents = 5
resource_monitoring = true
```

### Development Setup

```toml
[metasop]
enabled = true
default_sop = "code_generation"

[metasop.causal_reasoning]
enabled = true
confidence_threshold = 0.6
learning_enabled = false  # Disable learning in dev

[metasop.ace]
enabled = false  # Start simple in development

[metasop.debug]
verbose_logging = true
trace_events = true
```

## Monitoring and Debugging

### Metrics Collection

Track advanced feature performance:

- **Retry success rates**: Effectiveness of retry policies
- **Causal prediction accuracy**: How often predictions are correct
- **ACE learning progress**: Improvement over time
- **Orchestration efficiency**: Time and resource usage

### Debugging Tools

Advanced debugging capabilities:

- **Event tracing**: Detailed logs of orchestration events
- **Artifact inspection**: Examine intermediate results
- **Conflict visualization**: See predicted and actual conflicts
- **Performance profiling**: Identify bottlenecks

## Best Practices

### Error Handling

- Start with conservative retry settings and increase as needed
- Monitor failure patterns to improve classification
- Use remediation suggestions to enhance recovery strategies

### Causal Reasoning

- Set appropriate confidence thresholds for your use case
- Enable learning in production for continuous improvement
- Review predictions regularly to validate accuracy

### ACE Framework

- Allow time for playbook accumulation before expecting major improvements
- Backup playbooks regularly for disaster recovery
- Monitor learning progress and adjust parameters as needed

### Performance

- Scale parallel execution gradually based on resource availability
- Use caching and optimization features for high-throughput scenarios
- Monitor resource usage to prevent system overload