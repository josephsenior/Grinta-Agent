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

// To:
import { KeyboardShortcutsPanel, useKeyboardShortcuts } from "./keyboard-shortcuts-panel";
import { ConversationBookmarks, useConversationBookmarks } from "./conversation-bookmarks";
```

#### Step 2: Re-enable State Hooks (Lines ~111-156)

```typescript
// Change from:
// Advanced features disabled for beta launch
// const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
// const bookmarksHook = useConversationBookmarks();

// Keyboard shortcuts disabled for beta
// useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

// Technical details hardcoded to false for beta launch
const showTechnicalDetails = false;

// To:
const [showShortcutsPanel, setShowShortcutsPanel] = React.useState(false);
const bookmarksHook = useConversationBookmarks();

useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

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

{/* Advanced features removed for beta launch */}
```

#### Step 5: Re-enable Component Rendering (Lines ~644-674)

```typescript
// Change from:
{/* Beta launch: Advanced features disabled, only search enabled */}

// To:
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
pnpm run build
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
- All state persists in localStorage as expected

## Error Handling and Recovery

Forge implements sophisticated error handling mechanisms to ensure reliable operation across complex agentic scenarios.

### Retry Policies

The system uses configurable retry policies with exponential backoff:

```toml
[core]
# Retry settings for agent actions
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

- **TimeoutStepExecutor**: Manages agent step timeouts
- **TimeoutQAExecutor**: Handles validation timeouts
- **Stuck thread detection**: Identifies and handles unresponsive threads

```toml
[core]
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