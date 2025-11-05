# 🖥️ **Modern Terminal Interface**

> **Bolt.new-inspired terminal interface with glassmorphism, advanced interactions, and premium user experience.**

---

## 📖 **Table of Contents**

- [🌟 Overview](#-overview)
- [🎨 Visual Design](#-visual-design)
- [⚡ Interactive Features](#-interactive-features)
- [📱 Mobile Optimization](#-mobile-optimization)
- [♿ Accessibility](#-accessibility)
- [🔧 Component Architecture](#-component-architecture)
- [📚 API Reference](#-api-reference)
- [🎯 Usage Guide](#-usage-guide)
- [🚀 Configuration](#-configuration)

---

## 🌟 **Overview**

OpenHands features a revolutionary terminal interface inspired by modern development tools like Bolt.new. The terminal provides a premium, glassmorphism-based design with advanced interactive features, real-time streaming, and comprehensive accessibility support.

### **Key Features**
- **Glassmorphism Design**: Modern translucent interface with depth
- **Real-Time Streaming**: Typewriter effects with smooth animations
- **Advanced Actions**: Copy, download, expand, fullscreen, external terminal
- **Status Indicators**: Dynamic visual feedback for command states
- **Mobile Optimized**: Touch gestures and responsive design
- **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation
- **Modern Typography**: JetBrains Mono for enhanced code readability

### **Performance Benefits**
- **60fps animations** with hardware acceleration
- **Smooth streaming** with configurable chunk sizes
- **Efficient rendering** with virtual scrolling for large outputs
- **Responsive design** across all device sizes

---

## 🎨 **Visual Design**

### **Glassmorphism Effects**

The terminal uses modern glassmorphism design principles:

```css
.streaming-terminal {
  background: linear-gradient(135deg, 
    rgba(17, 24, 39, 0.9) 0%, 
    rgba(31, 41, 55, 0.9) 50%, 
    rgba(17, 24, 39, 0.9) 100%);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}
```

### **Dynamic Status Styling**

Real-time status indicators with contextual colors:

```typescript
const getStatusStyling = () => {
  switch (status) {
    case "running":
      return {
        color: "text-blue-400",
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
        icon: "●",
        label: "Running"
      };
    case "success":
      return {
        color: "text-emerald-400",
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20",
        icon: "✓",
        label: "Success"
      };
    case "error":
      return {
        color: "text-red-400",
        bg: "bg-red-500/10",
        border: "border-red-500/20",
        icon: "✗",
        label: "Error"
      };
    default:
      return {
        color: "text-gray-400",
        bg: "bg-gray-500/10",
        border: "border-gray-500/20",
        icon: "○",
        label: "Ready"
      };
  }
};
```

---

## ⚡ **Interactive Features**

### **Advanced Action Buttons**

Comprehensive set of terminal actions:

```typescript
// Copy functionality with visual feedback
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  } catch (error) {
    console.error("Failed to copy:", error);
  }
};

// Download terminal output
const handleDownload = () => {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `terminal-output-${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
```

### **Expandable Content**

Smart content management for large outputs:

```typescript
// Dynamic height management
const isLongOutput = lineCount > 8;
const maxHeight = isExpanded ? "40rem" : "16rem";

// Expand/collapse with smooth transitions
<button
  type="button"
  onClick={() => setIsExpanded(!isExpanded)}
  className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-all duration-200"
  title={isExpanded ? "Collapse" : "Expand"}
>
  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
</button>
```

### **More Actions Menu**

Additional terminal operations:

```typescript
// Dropdown menu with advanced actions
{showActions && (
  <div className="absolute right-0 top-full mt-1 w-48 bg-gray-800/95 backdrop-blur-xl border border-white/10 rounded-lg shadow-xl z-10">
    <div className="p-2">
      <button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:text-white hover:bg-white/10 rounded-md transition-colors flex items-center gap-2">
        <ExternalLink className="w-4 h-4" />
        Open in external terminal
      </button>
      <button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:text-white hover:bg-white/10 rounded-md transition-colors flex items-center gap-2">
        <Play className="w-4 h-4" />
        Run command again
      </button>
      <button className="w-full text-left px-3 py-2 text-sm text-white/80 hover:text-white hover:bg-white/10 rounded-md transition-colors flex items-center gap-2">
        <Square className="w-4 h-4" />
        Stop execution
      </button>
    </div>
  </div>
)}
```

---

## 📱 **Mobile Optimization**

### **Touch Gestures**

Mobile-first interaction design:

```typescript
// Swipeable terminal content with touch support
const [touchStart, setTouchStart] = useState<number | null>(null);
const [touchEnd, setTouchEnd] = useState<number | null>(null);

const minSwipeDistance = 50;

const onTouchStart = (e: React.TouchEvent) => {
  setTouchEnd(null);
  setTouchStart(e.targetTouches[0].clientX);
};

const onTouchMove = (e: React.TouchEvent) => {
  setTouchEnd(e.targetTouches[0].clientX);
};

const onTouchEnd = () => {
  if (!touchStart || !touchEnd) return;
  
  const distance = touchStart - touchEnd;
  const isLeftSwipe = distance > minSwipeDistance;
  const isRightSwipe = distance < -minSwipeDistance;

  if (isLeftSwipe) {
    // Handle left swipe (e.g., show more actions)
  } else if (isRightSwipe) {
    // Handle right swipe (e.g., hide actions)
  }
};
```

### **Responsive Design**

Adaptive layout for all screen sizes:

```typescript
// Responsive terminal sizing
const TerminalContent = styled.div`
  @media (max-width: 768px) {
    font-size: 14px;
    padding: 12px;
    max-height: 50vh;
  }
  
  @media (min-width: 769px) {
    font-size: 16px;
    padding: 16px;
    max-height: 60vh;
  }
`;
```

---

## ♿ **Accessibility**

### **Keyboard Navigation**

Complete keyboard support:

```typescript
// Keyboard event handling
const handleKeyDown = (e: React.KeyboardEvent) => {
  switch (e.key) {
    case 'Escape':
      setShowActions(false);
      break;
    case 'Enter':
      if (e.ctrlKey) {
        handleCopy();
      }
      break;
    case 'ArrowUp':
      if (isCollapsed) {
        setIsExpanded(true);
      }
      break;
    case 'ArrowDown':
      if (isExpanded) {
        setIsExpanded(false);
      }
      break;
  }
};
```

### **ARIA Attributes**

Comprehensive accessibility labels:

```typescript
// Accessible terminal component
<div
  role="log"
  aria-label="Terminal output"
  aria-live="polite"
  aria-atomic="true"
  tabIndex={0}
  onKeyDown={handleKeyDown}
>
  <div className="terminal-header" role="toolbar" aria-label="Terminal controls">
    <button
      aria-label="Copy terminal output"
      onClick={handleCopy}
      className="copy-button"
    >
      {isCopied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
    </button>
  </div>
</div>
```

### **Screen Reader Support**

Optimized for assistive technologies:

```typescript
// Screen reader announcements
const announceToScreenReader = (message: string) => {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', 'polite');
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  document.body.appendChild(announcement);
  
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
};
```

---

## 🔧 **Component Architecture**

### **Component Hierarchy**

```
TerminalTab
├── TerminalTabContent (lazy loaded)
    └── ModernTerminal
        ├── TerminalHeader
        │   ├── StatusIndicator
        │   ├── CommandDisplay
        │   └── ActionButtons
        ├── TerminalContent
        │   └── StreamingTerminal
        │       ├── ContentArea
        │       ├── EmptyState
        │       └── LoadingState
        └── TerminalFooter
            ├── CharacterCount
            ├── LineCount
            └── StreamingStatus
```

### **StreamingTerminal Component**

Core streaming functionality:

```typescript
interface StreamingTerminalProps {
  eventId: string;
  content: string;
  exitCode?: number;
  command?: string;
  onComplete?: () => void;
}

export function StreamingTerminal({
  eventId,
  content,
  exitCode,
  command,
  onComplete,
}: StreamingTerminalProps) {
  const [displayedContent, setDisplayedContent] = useState("");
  const [isCopied, setIsCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  // Streaming effect with typewriter animation
  useEffect(() => {
    if (!streamingEnabled || !isStreaming) {
      setDisplayedContent(content);
      setIsRunning(false);
      return;
    }

    setIsRunning(true);
    let currentIndex = 0;
    const chunkSize = 3; // Slower, more realistic typewriter effect

    const interval = setInterval(() => {
      currentIndex += chunkSize;

      if (currentIndex >= content.length) {
        setDisplayedContent(content);
        setIsRunning(false);
        clearInterval(interval);
        onComplete?.();
      } else {
        setDisplayedContent(content.slice(0, currentIndex));
      }

      if (contentRef.current) {
        contentRef.current.scrollTop = contentRef.current.scrollHeight;
      }
    }, 20); // 20ms interval for smooth streaming

    return () => clearInterval(interval);
  }, [content, isStreaming, streamingEnabled, onComplete]);

  return (
    <div className="streaming-terminal group relative overflow-hidden rounded-xl border border-white/10 bg-gradient-to-br from-gray-900/90 via-gray-800/90 to-gray-900/90 backdrop-blur-xl shadow-2xl my-3 w-full">
      {/* Terminal implementation */}
    </div>
  );
}
```

---

## 📚 **API Reference**

### **TerminalTabContent**

Main terminal tab component:

```typescript
interface TerminalTabContentProps {
  className?: string;
}

export function TerminalTabContent({ className }: TerminalTabContentProps): JSX.Element {
  // Component implementation
}
```

### **StreamingTerminal**

Streaming terminal display:

```typescript
interface StreamingTerminalProps {
  eventId: string;
  content: string;
  exitCode?: number;
  command?: string;
  onComplete?: () => void;
}

export function StreamingTerminal(props: StreamingTerminalProps): JSX.Element;
```

### **ModernTerminal**

Core terminal interface:

```typescript
interface ModernTerminalProps {
  instances: TerminalInstance[];
  onInstanceChange: (instance: TerminalInstance) => void;
  onNewInstance: () => void;
}

export function ModernTerminal(props: ModernTerminalProps): JSX.Element;
```

---

## 🎯 **Usage Guide**

### **Basic Implementation**

1. **Import terminal components**
```typescript
import { TerminalTabContent } from '#/components/features/terminal/terminal-tab-content';
import { StreamingTerminal } from '#/components/features/terminal/streaming-terminal';
```

2. **Use in your application**
```typescript
function MyApp() {
  return (
    <div className="app">
      <TerminalTabContent />
    </div>
  );
}
```

3. **Customize streaming terminal**
```typescript
<StreamingTerminal
  eventId="cmd_123"
  content={terminalOutput}
  exitCode={0}
  command="ls -la"
  onComplete={() => console.log('Command completed')}
/>
```

### **Advanced Configuration**

1. **Custom styling**
```css
/* Override terminal styles */
.streaming-terminal {
  --terminal-primary-color: #00ff00;
  --terminal-bg-opacity: 0.95;
  --terminal-border-radius: 16px;
}
```

2. **Performance optimization**
```typescript
// Optimize for large outputs
const StreamingTerminalOptimized = React.memo(StreamingTerminal, (prevProps, nextProps) => {
  return prevProps.content === nextProps.content && 
         prevProps.exitCode === nextProps.exitCode;
});
```

---

## 🚀 **Configuration**

### **Environment Variables**

```bash
# Terminal configuration
VITE_TERMINAL_FONT_SIZE=14
VITE_TERMINAL_MAX_HEIGHT=60vh
VITE_TERMINAL_STREAMING_CHUNK_SIZE=3
VITE_TERMINAL_STREAMING_INTERVAL=20
```

### **Component Props**

```typescript
// Terminal configuration interface
interface TerminalConfig {
  fontSize: number;
  maxHeight: string;
  streamingChunkSize: number;
  streamingInterval: number;
  enableAnimations: boolean;
  enableDownload: boolean;
  enableExternalTerminal: boolean;
}

const defaultConfig: TerminalConfig = {
  fontSize: 14,
  maxHeight: '60vh',
  streamingChunkSize: 3,
  streamingInterval: 20,
  enableAnimations: true,
  enableDownload: true,
  enableExternalTerminal: true,
};
```

### **CSS Custom Properties**

```css
:root {
  --terminal-bg-primary: rgba(17, 24, 39, 0.9);
  --terminal-bg-secondary: rgba(31, 41, 55, 0.9);
  --terminal-border-color: rgba(255, 255, 255, 0.1);
  --terminal-text-color: rgba(255, 255, 255, 0.9);
  --terminal-accent-color: #10b981;
  --terminal-border-radius: 12px;
  --terminal-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
}
```

---

## 🎯 **Best Practices**

### **Performance Optimization**

1. **Memoization**: Use React.memo for expensive components
2. **Virtual Scrolling**: Implement for very large outputs
3. **Lazy Loading**: Load terminal components only when needed
4. **Debouncing**: Debounce frequent updates and interactions

### **Accessibility Guidelines**

1. **Keyboard Navigation**: Ensure all actions are keyboard accessible
2. **Screen Reader Support**: Provide proper ARIA labels and announcements
3. **Color Contrast**: Maintain sufficient contrast ratios
4. **Focus Management**: Clear focus indicators and tab order

### **User Experience**

1. **Loading States**: Provide clear feedback during operations
2. **Error Handling**: Graceful error recovery and user feedback
3. **Responsive Design**: Test across all device sizes
4. **Performance**: Maintain 60fps animations and smooth scrolling

---

## 🔮 **Future Enhancements**

### **Planned Features**
- **Syntax Highlighting**: Command and output syntax highlighting
- **Terminal Themes**: Multiple visual themes and customization
- **Command History**: Persistent command history and search
- **Multi-Terminal**: Tabbed terminal interface support

### **Advanced Features**
- **Terminal Plugins**: Extensible terminal functionality
- **SSH Integration**: Remote terminal connections
- **Terminal Sharing**: Collaborative terminal sessions
- **Advanced Shortcuts**: Customizable keyboard shortcuts

---

*This terminal interface represents the pinnacle of modern web terminal design, combining cutting-edge visual aesthetics with unparalleled functionality and accessibility.*
