import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Settings, Command, PanelLeft } from "lucide-react";
import { cn } from "#/utils/utils";
import { CommandPalette } from "#/components/features/command-palette/command-palette";

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

// Helper Components (defined before main component)
function StatusBar() {
  const location = useLocation();
  const isConversationPage = location.pathname.startsWith("/conversations/");

  return (
    <div className="h-6 bg-[#007acc] text-white flex items-center justify-between px-3 text-[11px] font-medium flex-shrink-0 select-none">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white ml-1" />
          <span className="opacity-90">Forge Ready</span>
        </div>
        {isConversationPage && (
          <>
            <span className="opacity-60">|</span>
            <span className="opacity-90 font-mono">
              Session: {location.pathname.split("/").pop()?.slice(0, 8) || "N/A"}
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1 opacity-80 hover:opacity-100 cursor-pointer">
          <span>UTF-8</span>
        </div>
        <div className="flex items-center gap-1 opacity-80 hover:opacity-100 cursor-pointer">
          <span>TypeScript React</span>
        </div>
        <div className="flex items-center gap-1 opacity-80 hover:opacity-100 cursor-pointer">
          <span>Prettier</span>
        </div>
        <div className="opacity-80 hover:opacity-100 cursor-pointer ml-2">
          Forge Core v1.0
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
              "bg-(--bg-tertiary) text-[var(--text-accent)]",
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

      {/* Main Content Area - Edge to Edge */}
      <div className="flex-1 flex min-h-0 overflow-hidden bg-[var(--bg-primary)]">
        {/* Left Sidebar */}
        {leftSidebarOpen && (
          <div className="w-[260px] flex-shrink-0 bg-[var(--bg-elevated)] border-r border-[var(--border-primary)] h-full overflow-hidden">
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

        {/* Center Content */}
        <div className="flex-1 min-w-0 flex flex-col bg-[var(--bg-primary)] overflow-hidden">
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
