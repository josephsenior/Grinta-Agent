import React, { useState } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { Command } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { useDeleteConversation } from "#/hooks/mutation/use-delete-conversation";
import { downloadTrajectory } from "#/utils/download-trajectory";
import { useWsStatus } from "#/context/ws-client-provider";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { AgentState } from "#/types/agent-state";
import { useAgentState } from "#/hooks/use-agent-state";
import { useGetTrajectory } from "#/hooks/mutation/use-get-trajectory";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import Forge from "#/api/forge";

export interface CommandPaletteProps {
  onClose: () => void;
  onSelect: (command: string) => void;
  leftSidebarOpen: boolean;
  setLeftSidebarOpen: (open: boolean) => void;
}

export function CommandPalette({
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
  const { send } = useWsStatus();
  const curAgentState = useAgentState();

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
        className="w-[600px] bg-[var(--bg-elevated)] border border-(--border-primary) rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-3 border-b border-(--border-primary)">
          <div className="flex items-center gap-2">
            <Command className="w-4 h-4 text-(--text-tertiary)" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 bg-(--bg-input) border border-(--border-primary) rounded px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
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
