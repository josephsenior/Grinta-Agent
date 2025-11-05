import React from "react";
import {
  Keyboard,
  Search,
  ArrowUp,
  CornerDownLeft,
  Copy,
  Play,
  Save,
  MessageSquare,
  X,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "#/components/ui/dialog";
import { Card } from "#/components/ui/card";
import { Badge } from "#/components/ui/badge";
import { cn } from "#/utils/utils";

interface KeyboardShortcut {
  id: string;
  keys: string[];
  description: string;
  category: "editing" | "navigation" | "actions" | "code";
  icon?: React.ReactNode;
}

interface KeyboardShortcutsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS: KeyboardShortcut[] = [
  // Editing shortcuts
  {
    id: "edit-last",
    keys: ["↑"],
    description: "Edit last message (when input is empty)",
    category: "editing",
    icon: <ArrowUp className="h-3 w-3" />,
  },
  {
    id: "send-message",
    keys: ["Enter"],
    description: "Send message",
    category: "editing",
    icon: <CornerDownLeft className="h-3 w-3" />,
  },
  {
    id: "new-line",
    keys: ["Shift", "Enter"],
    description: "New line in message",
    category: "editing",
  },
  {
    id: "focus-input",
    keys: ["/"],
    description: "Focus message input",
    category: "navigation",
  },

  // Code actions
  {
    id: "copy-code",
    keys: ["Hover", "Copy"],
    description: "Copy code block (hover over code)",
    category: "code",
    icon: <Copy className="h-3 w-3" />,
  },
  {
    id: "run-code",
    keys: ["Hover", "Run"],
    description: "Execute code block",
    category: "code",
    icon: <Play className="h-3 w-3" />,
  },
  {
    id: "save-code",
    keys: ["Hover", "Save"],
    description: "Download code as file",
    category: "code",
    icon: <Save className="h-3 w-3" />,
  },
  {
    id: "ask-code",
    keys: ["Hover", "Ask"],
    description: "Ask about code",
    category: "code",
    icon: <MessageSquare className="h-3 w-3" />,
  },

  // Navigation shortcuts
  {
    id: "search-conversation",
    keys: ["⌘", "K"],
    description: "Search conversation",
    category: "navigation",
    icon: <Search className="h-3 w-3" />,
  },
  {
    id: "bookmarks",
    keys: ["⌘", "B"],
    description: "Open bookmarks",
    category: "navigation",
  },
  {
    id: "quick-search",
    keys: ["Ctrl", "P"],
    description: "Quick search (coming soon)",
    category: "navigation",
    icon: <Search className="h-3 w-3" />,
  },

  // General actions
  {
    id: "show-shortcuts",
    keys: ["?"],
    description: "Show keyboard shortcuts",
    category: "actions",
    icon: <Keyboard className="h-3 w-3" />,
  },
  {
    id: "close-panel",
    keys: ["Esc"],
    description: "Close panels/modals",
    category: "navigation",
    icon: <X className="h-3 w-3" />,
  },
];

function KeyBadge({ keyName }: { keyName: string }) {
  const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
  const displayKey = keyName === "Ctrl" && isMac ? "⌘" : keyName;

  return (
    <Badge
      variant="outline"
      className="px-2 py-0.5 font-mono text-xs bg-background-surface border-border-glass"
    >
      {displayKey}
    </Badge>
  );
}

function ShortcutRow({ shortcut }: { shortcut: KeyboardShortcut }) {
  return (
    <div className="flex items-center justify-between py-2 group hover:bg-primary-500/5 px-2 rounded-lg transition-colors">
      <div className="flex items-center gap-3 flex-1">
        {shortcut.icon && (
          <div className="flex-shrink-0 text-primary-500">{shortcut.icon}</div>
        )}
        <span className="text-sm text-text-primary">
          {shortcut.description}
        </span>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {shortcut.keys.map((key, index) => (
          <React.Fragment key={index}>
            {index > 0 && (
              <span className="text-xs text-text-foreground-secondary mx-1">+</span>
            )}
            <KeyBadge keyName={key} />
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export function KeyboardShortcutsPanel({
  isOpen,
  onClose,
}: KeyboardShortcutsPanelProps) {
  const [searchQuery, setSearchQuery] = React.useState("");

  React.useEffect(() => {
    if (isOpen) {
      setSearchQuery("");
    }
  }, [isOpen]);

  const filteredShortcuts = React.useMemo(() => {
    if (!searchQuery) return SHORTCUTS;
    const query = searchQuery.toLowerCase();
    return SHORTCUTS.filter(
      (s) =>
        s.description.toLowerCase().includes(query) ||
        s.keys.some((k) => k.toLowerCase().includes(query)),
    );
  }, [searchQuery]);

  const groupedShortcuts = React.useMemo(() => {
    const groups: Record<string, KeyboardShortcut[]> = {
      editing: [],
      navigation: [],
      code: [],
      actions: [],
    };

    filteredShortcuts.forEach((shortcut) => {
      groups[shortcut.category].push(shortcut);
    });

    return groups;
  }, [filteredShortcuts]);

  const categoryTitles: Record<string, string> = {
    editing: "Message Editing",
    navigation: "Navigation",
    code: "Code Actions",
    actions: "General Actions",
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
        </DialogHeader>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-foreground-secondary" />
          <input
            type="text"
            placeholder="Search shortcuts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              "w-full pl-10 pr-4 py-2 rounded-lg",
              "bg-background-surface border border-border-glass",
              "text-text-primary placeholder:text-text-foreground-secondary",
              "focus:outline-none focus:ring-2 focus:ring-primary-500/50",
              "text-sm",
            )}
          />
        </div>

        {/* Shortcuts List */}
        <div className="flex-1 overflow-y-auto space-y-6 py-2">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => {
            if (shortcuts.length === 0) return null;

            return (
              <div key={category}>
                <h3 className="text-sm font-semibold text-text-secondary mb-2 px-2">
                  {categoryTitles[category]}
                </h3>
                <Card className="bg-background-surface/50 border-border-glass p-2">
                  <div className="space-y-0.5">
                    {shortcuts.map((shortcut) => (
                      <ShortcutRow key={shortcut.id} shortcut={shortcut} />
                    ))}
                  </div>
                </Card>
              </div>
            );
          })}

          {filteredShortcuts.length === 0 && (
            <div className="text-center py-8 text-text-foreground-secondary">
              <Keyboard className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No shortcuts found matching "{searchQuery}"</p>
            </div>
          )}
        </div>

        {/* Footer tip */}
        <div className="border-t border-border-glass pt-3 text-xs text-text-foreground-secondary text-center">
          Press <KeyBadge keyName="Esc" /> to close this dialog
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Global shortcut hook
export function useKeyboardShortcuts(
  onShowPanel: () => void,
  isInputFocused: boolean,
) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + ? to show shortcuts
      if ((e.ctrlKey || e.metaKey) && e.key === "?") {
        e.preventDefault();
        onShowPanel();
      }

      // / to focus input (when not already focused)
      if (e.key === "/" && !isInputFocused) {
        const target = e.target as HTMLElement;
        if (
          target.tagName !== "INPUT" &&
          target.tagName !== "TEXTAREA" &&
          !target.isContentEditable
        ) {
          e.preventDefault();
          // Focus the input - this will be handled by parent component
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onShowPanel, isInputFocused]);
}
