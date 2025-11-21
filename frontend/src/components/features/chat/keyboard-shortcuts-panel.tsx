import React from "react";
import { useTranslation } from "react-i18next";
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
  LayoutDashboard,
  Search as SearchIcon,
  Database,
  User,
  Settings,
  HelpCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "#/components/ui/dialog";
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
  // Navigation shortcuts - Global
  {
    id: "nav-dashboard",
    keys: ["⌘", "1"],
    description: "Go to Dashboard",
    category: "navigation",
    icon: <LayoutDashboard className="h-3 w-3" />,
  },
  {
    id: "nav-conversations",
    keys: ["⌘", "2"],
    description: "Go to Conversations",
    category: "navigation",
    icon: <MessageSquare className="h-3 w-3" />,
  },
  {
    id: "nav-search",
    keys: ["⌘", "3"],
    description: "Go to Search",
    category: "navigation",
    icon: <SearchIcon className="h-3 w-3" />,
  },
  {
    id: "nav-database",
    keys: ["⌘", "4"],
    description: "Go to Database Browser",
    category: "navigation",
    icon: <Database className="h-3 w-3" />,
  },
  {
    id: "nav-profile",
    keys: ["⌘", "5"],
    description: "Go to Profile",
    category: "navigation",
    icon: <User className="h-3 w-3" />,
  },
  {
    id: "nav-settings",
    keys: ["⌘", ","],
    description: "Go to Settings",
    category: "navigation",
    icon: <Settings className="h-3 w-3" />,
  },
  {
    id: "nav-help",
    keys: ["⌘", "H"],
    description: "Go to Help",
    category: "navigation",
    icon: <HelpCircle className="h-3 w-3" />,
  },
  {
    id: "toggle-sidebar",
    keys: ["⌘", "B"],
    description: "Toggle sidebar",
    category: "navigation",
  },
  {
    id: "search-conversation",
    keys: ["⌘", "K"],
    description: "Search conversation",
    category: "navigation",
    icon: <Search className="h-3 w-3" />,
  },
  {
    id: "quick-search",
    keys: ["Ctrl", "P"],
    description: "Quick search (coming soon)",
    category: "navigation",
    icon: <Search className="h-3 w-3" />,
  },

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
    category: "editing",
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
      className="px-2 py-0.5 font-mono text-xs bg-[var(--bg-elevated)] border-[var(--border-primary)] text-[var(--text-primary)]"
    >
      {displayKey}
    </Badge>
  );
}

function ShortcutRow({ shortcut }: { shortcut: KeyboardShortcut }) {
  return (
    <div className="flex items-center justify-between py-2 group hover:bg-white/5 px-2 rounded-lg transition-colors">
      <div className="flex items-center gap-3 flex-1">
        {shortcut.icon && (
          <div className="flex-shrink-0 text-[#8b5cf6]">{shortcut.icon}</div>
        )}
        <span className="text-sm text-[var(--text-primary)]">
          {shortcut.description}
        </span>
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        {shortcut.keys.map((key, index) => (
          <React.Fragment key={index}>
            {index > 0 && (
              <span className="text-xs text-[var(--text-tertiary)] mx-1">
                +
              </span>
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
  const { t } = useTranslation();
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
    navigation: "Navigation",
    editing: "Message Editing",
    code: "Code Actions",
    actions: "General Actions",
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col bg-[var(--bg-primary)] border-[var(--border-primary)]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[var(--text-primary)]">
            <Keyboard className="h-5 w-5" />
            {t("chat.keyboardShortcuts", "Keyboard Shortcuts")}
          </DialogTitle>
        </DialogHeader>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-tertiary)]" />
          <input
            type="text"
            placeholder="Search shortcuts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              "w-full pl-10 pr-4 py-2 rounded-lg",
              "bg-[var(--bg-input)] border border-[var(--border-primary)]",
              "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]",
              "focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] focus:border-[var(--border-accent)]",
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
                <h3 className="text-sm font-semibold text-white/70 mb-2 px-2">
                  {categoryTitles[category]}
                </h3>
                <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-lg p-2">
                  <div className="space-y-0.5">
                    {shortcuts.map((shortcut) => (
                      <ShortcutRow key={shortcut.id} shortcut={shortcut} />
                    ))}
                  </div>
                </div>
              </div>
            );
          })}

          {filteredShortcuts.length === 0 && (
            <div className="text-center py-8 text-[var(--text-tertiary)]">
              <Keyboard className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>
                {t(
                  "chat.noShortcutsFound",
                  'No shortcuts found matching "{{query}}"',
                  {
                    query: searchQuery,
                  },
                )}
              </p>
            </div>
          )}
        </div>

        {/* Footer tip */}
        <div className="border-t border-[var(--border-primary)] pt-3 text-xs text-[var(--text-tertiary)] text-center">
          {t("chat.pressEscToClose", "Press")} <KeyBadge keyName="Esc" />{" "}
          {t("chat.toCloseDialog", "to close this dialog")}
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
    const handleKeyDown = (e: KeyboardEvent): void => {
      // Ctrl/Cmd + ? to show shortcuts
      if ((e.ctrlKey || e.metaKey) && e.key === "?") {
        e.preventDefault();
        onShowPanel();
        return;
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
