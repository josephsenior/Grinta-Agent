import React, { useState } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { Settings, Command, X, PanelLeft, Home } from "lucide-react";
import { useSelector } from "react-redux";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { useDeleteConversation } from "#/hooks/mutation/use-delete-conversation";
import { downloadTrajectory } from "#/utils/download-trajectory";
import { useWsClient } from "#/context/ws-client-provider";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { AgentState } from "#/types/agent-state";
import { RootState } from "#/store";
import { useGetTrajectory } from "#/hooks/mutation/use-get-trajectory";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import Forge from "#/api/forge";

const ConversationsSidebar = React.lazy(() =>
  import("#/components/features/conversations/conversations-sidebar").then(
    (m) => ({
      default: m.ConversationsSidebar,
    }),
  ),
);

interface DesktopLayoutProps {
  children?: React.ReactNode;
}

interface CommandPaletteProps {
  onClose: () => void;
  onSelect: (command: string) => void;
  leftSidebarOpen: boolean;
  setLeftSidebarOpen: (open: boolean) => void;
}

// Helper Components (defined before main component)
function StatusBar() {
  const location = useLocation();

  const isConversationPage = location.pathname.startsWith("/conversations/");

  return (
    <div className="h-7 bg-[var(--bg-elevated)] flex items-center justify-between px-3 text-[10px] font-bold uppercase tracking-widest flex-shrink-0 border border-[var(--border-primary)] rounded-lg shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 group">
          <div
            className="w-1.5 h-1.5 rounded-full transition-all duration-300 bg-[var(--text-success)] shadow-[0_0_8px_var(--text-success)]"
          />
          <span className="text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)] transition-colors">
            Stable
          </span>
        </div>
        {isConversationPage && (
          <>
            <div className="w-px h-3 bg-[var(--border-secondary)]" />
            <span className="text-[var(--text-tertiary)]">
              Session:{" "}
              {location.pathname.split("/").pop()?.slice(0, 8) || "N/A"}
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[var(--text-muted)] hover:text-[var(--text-tertiary)] transition-colors cursor-default">
          Forge Core
        </span>
      </div>
    </div>
  );
}

function CommandPalette({
  onClose,
  onSelect,
  leftSidebarOpen,
  setLeftSidebarOpen,
}: CommandPaletteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ conversationId?: string }>();
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Hooks for conversation operations
  const deleteConversation = useDeleteConversation();
  const { mutateAsync: getTrajectory } = useGetTrajectory();
  const { conversationId } = params;
  const isConversationPage = location.pathname.startsWith("/conversations/");

  // Hooks for agent control
  const { send } = useWsClient();
  const { curAgentState } = useSelector((state: RootState) => state.agent);

  // Keyboard shortcut helper
  const getShortcut = (keys: string) => {
    const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
    return keys.replace(/Ctrl/g, isMac ? "Cmd" : "Ctrl");
  };

  const commands = React.useMemo(() => {
    const cmds: Array<{
      id: string;
      label: string;
      category: string;
      shortcut?: string;
      action: () => void;
      disabled?: boolean;
    }> = [
      // === CONVERSATION ===
      {
        id: "new-conversation",
        label: "New Conversation",
        category: "Conversation",
        shortcut: "Ctrl+N",
        action: () => {
          navigate("/conversations");
        },
      },
      {
        id: "open-conversations",
        label: "Open Conversations",
        category: "Conversation",
        action: () => navigate("/conversations"),
      },
      {
        id: "delete-conversation",
        label: "Delete Conversation",
        category: "Conversation",
        action: () => {
          if (conversationId) {
            // eslint-disable-next-line no-alert
            if (
              window.confirm(
                t("Are you sure you want to delete this conversation?") ||
                  "Are you sure you want to delete this conversation?",
              )
            ) {
              deleteConversation.mutate(
                { conversationId },
                {
                  onSuccess: () => {
                    navigate("/conversations");
                    displaySuccessToast(
                      t("Conversation deleted") || "Conversation deleted",
                    );
                    onClose();
                  },
                  onError: (error) => {
                    displayErrorToast(error);
                  },
                },
              );
            }
          } else {
            displayErrorToast(
              t("No conversation selected") || "No conversation selected",
            );
          }
        },
        disabled: !isConversationPage || !conversationId,
      },
      {
        id: "export-trajectory",
        label: "Export Trajectory",
        category: "Conversation",
        action: async () => {
          if (conversationId) {
            try {
              const trajectoryData = await getTrajectory(conversationId);
              await downloadTrajectory(
                conversationId,
                trajectoryData.trajectory,
              );
              displaySuccessToast(
                t("Trajectory exported successfully") ||
                  "Trajectory exported successfully",
              );
              onClose();
            } catch (error) {
              displayErrorToast(error);
            }
          } else {
            displayErrorToast(
              t("No conversation selected") || "No conversation selected",
            );
          }
        },
        disabled: !isConversationPage || !conversationId,
      },

      // === FILE OPERATIONS ===
      {
        id: "download-workspace",
        label: "Download Workspace",
        category: "File",
        action: async () => {
          if (conversationId) {
            try {
              const blob = await Forge.getWorkspaceZip(conversationId);
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `workspace-${conversationId}.zip`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
              displaySuccessToast(
                t("Workspace downloaded successfully") ||
                  "Workspace downloaded successfully",
              );
              onClose();
            } catch (error) {
              displayErrorToast(error);
            }
          } else {
            displayErrorToast(
              t("No conversation selected") || "No conversation selected",
            );
          }
        },
        disabled: !isConversationPage || !conversationId,
      },

      // === WORKSPACE ===
      {
        id: "reload-window",
        label: "Reload Window",
        category: "Workspace",
        shortcut: "Ctrl+R",
        action: () => {
          window.location.reload();
        },
      },
      {
        id: "focus-chat",
        label: "Focus Chat Input",
        category: "Workspace",
        shortcut: "Ctrl+L",
        action: () => {
          window.dispatchEvent(new CustomEvent("Forge:focus-chat-input"));
          onClose();
        },
      },

      // === AGENT CONTROL ===
      {
        id: "pause-agent",
        label: "Pause Agent",
        category: "Agent",
        shortcut: "Ctrl+Shift+P",
        action: () => {
          if (curAgentState === AgentState.RUNNING) {
            send(generateAgentStateChangeEvent(AgentState.PAUSED));
            displaySuccessToast(t("Agent paused") || "Agent paused");
            onClose();
          }
        },
        disabled: curAgentState !== AgentState.RUNNING,
      },
      {
        id: "resume-agent",
        label: "Resume Agent",
        category: "Agent",
        action: () => {
          if (curAgentState === AgentState.PAUSED) {
            send(generateAgentStateChangeEvent(AgentState.RUNNING));
            displaySuccessToast(t("Agent resumed") || "Agent resumed");
            onClose();
          }
        },
        disabled: curAgentState !== AgentState.PAUSED,
      },

      // === SEARCH ===
      {
        id: "search-conversation",
        label: "Search in Conversation",
        category: "Search",
        shortcut: "Ctrl+K",
        action: () => {
          if (isConversationPage) {
            window.dispatchEvent(
              new CustomEvent("Forge:open-conversation-search"),
            );
            onClose();
          } else {
            displayErrorToast(
              t("Open a conversation to search") ||
                "Open a conversation to search",
            );
          }
        },
        disabled: !isConversationPage,
      },

      // === VIEW ===
      {
        id: "toggle-sidebar",
        label: "Toggle Sidebar",
        category: "View",
        shortcut: "Ctrl+B",
        action: () => {
          setLeftSidebarOpen(!leftSidebarOpen);
          onClose();
        },
      },
      {
        id: "toggle-file-explorer",
        label: "Toggle File Explorer",
        category: "View",
        action: () => {
          setLeftSidebarOpen(!leftSidebarOpen);
          onClose();
        },
      },
      {
        id: "toggle-terminal",
        label: "Toggle Terminal",
        category: "View",
        shortcut: "Ctrl+`",
        action: () => {
          window.dispatchEvent(new CustomEvent("Forge:toggle-terminal"));
          onClose();
        },
      },
      {
        id: "command-palette",
        label: "Show Command Palette",
        category: "View",
        shortcut: "Ctrl+P",
        action: () => {},
      },

      // === SETTINGS ===
      {
        id: "open-settings",
        label: "Open Settings",
        category: "Settings",
        shortcut: "Ctrl+,",
        action: () => {
          navigate("/settings");
          onClose();
        },
      },
    ];

    // Filter out disabled commands
    return cmds.filter((cmd) => !cmd.disabled);
  }, [
    navigate,
    location.pathname,
    conversationId,
    isConversationPage,
    deleteConversation,
    getTrajectory,
    curAgentState,
    send,
    leftSidebarOpen,
    setLeftSidebarOpen,
    t,
    onClose,
  ]);

  const filteredCommands = React.useMemo(() => {
    if (!search.trim()) return commands;
    const query = search.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(query) ||
        cmd.category.toLowerCase().includes(query) ||
        (cmd.shortcut && cmd.shortcut.toLowerCase().includes(query)),
    );
  }, [search, commands]);

  React.useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  const handleKeyDown = React.useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredCommands.length - 1,
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
          onSelect(filteredCommands[selectedIndex].id);
        }
      }
    },
    [filteredCommands, selectedIndex, onSelect],
  );

  React.useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  type CommandType = (typeof commands)[number];

  const groupedCommands = React.useMemo(() => {
    const groups: Record<string, CommandType[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) {
        groups[cmd.category] = [];
      }
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-32 z-50"
      onClick={onClose}
    >
      <div
        className="w-[600px] bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-3 border-b border-[var(--border-primary)]">
          <div className="flex items-center gap-2">
            <Command className="w-4 h-4 text-[var(--text-tertiary)]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 bg-[var(--bg-input)] border border-[var(--border-primary)] rounded px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
            />
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {Object.entries(groupedCommands).map(([category, cmds]) => (
            <div key={category}>
              <div className="px-3 py-1.5 text-xs text-[var(--text-tertiary)] uppercase tracking-wide bg-[var(--bg-primary)] border-b border-[var(--border-primary)]">
                {category}
              </div>
              {cmds.map((cmd: CommandType) => {
                const globalIndex = filteredCommands.indexOf(cmd);
                const isSelected =
                  globalIndex === selectedIndex || globalIndex === hoveredIndex;
                return (
                  <button
                    type="button"
                    key={cmd.id}
                    onClick={() => {
                      cmd.action();
                      onSelect(cmd.id);
                    }}
                    onMouseEnter={() => setHoveredIndex(globalIndex)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className={cn(
                      "w-full text-left px-3 py-2 text-sm flex items-center justify-between transition-colors",
                      isSelected
                        ? "bg-[var(--bg-elevated)] text-[var(--text-primary)]"
                        : "text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
                    )}
                  >
                    <span>{cmd.label}</span>
                    {cmd.shortcut && (
                      <span className="text-xs text-[var(--text-tertiary)] font-mono">
                        {getShortcut(cmd.shortcut)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          {filteredCommands.length === 0 && (
            <div className="px-3 py-8 text-center text-sm text-[var(--text-tertiary)]">
              No commands found
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Desktop-style layout similar to Cursor/Windsurf
 * Features:
 * - Left sidebar: File explorer, search, etc.
 * - Center: Main content (chat/editor)
 * - Right sidebar: Optional panels (settings, etc.)
 * - Top bar: Tabs, command palette
 * - Bottom: Status bar
 */
export function DesktopLayout({ children }: DesktopLayoutProps) {
  const navigate = useNavigate();
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true); // Open by default for better UX
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + P for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "p") {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
      // Cmd/Ctrl + B to toggle left sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault();
        setLeftSidebarOpen(!leftSidebarOpen);
      }
      // Escape to close command palette
      if (e.key === "Escape" && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandPaletteOpen, leftSidebarOpen]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-hidden p-3 gap-3">
      {/* Top Bar - Sidebar Toggle and Command Palette - Floating Style */}
      <div className="h-11 bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl flex items-center flex-shrink-0 px-2 shadow-sm z-50">
        {/* Left sidebar toggle */}
        <button
          type="button"
          onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
          className={cn(
            "p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] flex items-center justify-center transition-all duration-200 active:scale-95",
            leftSidebarOpen &&
              "bg-[var(--bg-tertiary)] text-[var(--text-accent)]",
          )}
          title="Toggle Sidebar (Ctrl+B)"
        >
          <PanelLeft
            className={cn(
              "w-4 h-4 transition-transform",
              !leftSidebarOpen && "rotate-180",
            )}
          />
        </button>

        <div className="w-px h-6 bg-[var(--border-primary)] mx-2" />

        {/* Command Palette Button */}
        <button
          type="button"
          onClick={() => setCommandPaletteOpen(true)}
          className="px-3 h-full hover:bg-[var(--bg-tertiary)] flex items-center gap-2 text-xs text-[var(--text-tertiary)] transition-colors"
          title="Command Palette (Ctrl+P)"
        >
          <Command className="w-3 h-3" />
          <span className="hidden sm:inline font-mono opacity-60">Ctrl+P</span>
        </button>

        {/* Settings Button */}
        <button
          type="button"
          onClick={() => navigate("/settings/app")}
          className="px-3 h-full hover:bg-[var(--bg-tertiary)] flex items-center gap-2 text-xs text-[var(--text-tertiary)] transition-colors"
          title="Settings"
        >
          <Settings className="w-3 h-3" />
          <span className="hidden sm:inline">Settings</span>
        </button>

        {/* Spacer */}
        <div className="flex-1" />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden gap-3">
        {/* Left Sidebar - Floating Dock Style */}
        {leftSidebarOpen && (
          <div className="w-[260px] flex-shrink-0 bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl h-full overflow-hidden shadow-sm">
            <React.Suspense
              fallback={
                <div className="px-2 py-4 text-xs text-[var(--text-tertiary)] italic text-center">
                  Loading...
                </div>
              }
            >
              <ConversationsSidebar />
            </React.Suspense>
          </div>
        )}

        {/* Center Content - Floating Dock Style */}
        <div className="flex-1 min-w-0 flex flex-col bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl shadow-sm overflow-hidden">
          <div className="h-full w-full">{children}</div>
        </div>


      </div>

      {/* Status Bar */}
      <StatusBar />

      {/* Command Palette Modal */}
      {commandPaletteOpen && (
        <CommandPalette
          onClose={() => setCommandPaletteOpen(false)}
          onSelect={() => {
            // Handle command selection
            setCommandPaletteOpen(false);
          }}
          leftSidebarOpen={leftSidebarOpen}
          setLeftSidebarOpen={setLeftSidebarOpen}
        />
      )}
    </div>
  );
}
