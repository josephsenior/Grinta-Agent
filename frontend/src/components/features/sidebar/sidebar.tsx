import React, { useState, useEffect } from "react";
import { Menu } from "lucide-react";
import { useLogout } from "#/hooks/mutation/use-logout";
import { useGitUser } from "#/hooks/query/use-git-user";
import { useSidebar } from "#/contexts/sidebar-context";
import { ConversationPanel } from "../conversation-panel/conversation-panel";
import { ConversationPanelWrapper } from "../conversation-panel/conversation-panel-wrapper";
import { SettingsModal } from "#/components/shared/modals/settings/settings-modal";
import { useSidebarVisibility } from "./hooks/use-sidebar-visibility";
import { useSidebarKeyboardShortcuts } from "./hooks/use-sidebar-keyboard-shortcuts";
import { useConversationPanel } from "./hooks/use-conversation-panel";
import { useSidebarSettings } from "./hooks/use-sidebar-settings";
import { DesktopSidebar } from "./components/desktop-sidebar";
import { MobileSidebar } from "./components/mobile-sidebar";

export function Sidebar() {
  useGitUser();
  useLogout();

  const { sidebarCollapsed, setSidebarCollapsed } = useSidebar();
  const { showSidebar, hasHeader } = useSidebarVisibility();
  const { conversationPanelIsOpen, setConversationPanelIsOpen } =
    useConversationPanel();
  const { settingsModalIsOpen, setSettingsModalIsOpen, settings } =
    useSidebarSettings();

  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  useSidebarKeyboardShortcuts(sidebarCollapsed, setSidebarCollapsed);

  // Listen for external toggle events
  useEffect(() => {
    const handleToggle = () => {
      setSidebarCollapsed(!sidebarCollapsed);
    };
    window.addEventListener("Forge:toggle-sidebar", handleToggle);
    return () =>
      window.removeEventListener("Forge:toggle-sidebar", handleToggle);
  }, [sidebarCollapsed, setSidebarCollapsed]);

  if (!showSidebar) {
    return null;
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  interface WindowWithE2E extends Window {
    __Forge_PLAYWRIGHT?: boolean;
  }
  const win =
    typeof window !== "undefined"
      ? (window as unknown as WindowWithE2E)
      : undefined;
  const isPlaywrightRun = win?.__Forge_PLAYWRIGHT === true;

  return (
    <>
      <DesktopSidebar
        sidebarCollapsed={sidebarCollapsed}
        hasHeader={hasHeader}
        onToggle={toggleSidebar}
      />

      {sidebarCollapsed && (
        <button
          type="button"
          onClick={toggleSidebar}
          className="fixed left-0 top-1/2 -translate-y-1/2 p-3 rounded-r-lg bg-black/80 border-r border-y border-white/20 text-white/70 hover:text-white hover:bg-black/90 transition-all z-[10001] flex items-center justify-center backdrop-blur-sm shadow-lg"
          aria-label="Expand sidebar (or press Ctrl/Cmd + B)"
          data-sidebar-toggle
          title="Show sidebar (Ctrl/Cmd + B)"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      <MobileSidebar
        mobileDrawerOpen={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(!mobileDrawerOpen)}
      />

      {conversationPanelIsOpen && !isPlaywrightRun && (
        <ConversationPanelWrapper isOpen={conversationPanelIsOpen}>
          <div className="animate-slide-up">
            <ConversationPanel
              onClose={() => setConversationPanelIsOpen(false)}
            />
          </div>
        </ConversationPanelWrapper>
      )}

      {settingsModalIsOpen && (
        <div className="animate-scale-in">
          <SettingsModal
            settings={settings}
            onClose={() => setSettingsModalIsOpen(false)}
          />
        </div>
      )}
    </>
  );
}
