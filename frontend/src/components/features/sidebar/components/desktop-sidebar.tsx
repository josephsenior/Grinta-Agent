import { ChevronLeft } from "lucide-react";
import { AppNavigation } from "#/components/layout/AppNavigation";

interface DesktopSidebarProps {
  sidebarCollapsed: boolean;
  hasHeader: boolean;
  onToggle: () => void;
}

export function DesktopSidebar({
  sidebarCollapsed,
  hasHeader,
  onToggle,
}: DesktopSidebarProps) {
  return (
    <aside
      id="main-sidebar"
      className="fixed left-0 bottom-0 border-r border-[var(--border-primary)] overflow-hidden shadow-2xl transition-all duration-300 ease-in-out"
      style={{
        backgroundColor: "var(--bg-elevated)",
        top: hasHeader ? "88px" : "0px",
        minHeight: hasHeader ? "calc(100vh - 88px)" : "100vh",
        maxHeight: hasHeader ? "calc(100vh - 88px)" : "100vh",
        width: sidebarCollapsed ? "0px" : "256px",
        zIndex: 1000,
        display: "none",
      }}
      data-desktop-sidebar
      data-sidebar-collapsed={sidebarCollapsed}
    >
      <style>{`
        @media (min-width: 768px) {
          aside[data-desktop-sidebar] {
            display: block !important;
          }
        }
      `}</style>
      <div className="h-full flex flex-col">
        {!sidebarCollapsed && (
          <div className="flex items-center justify-end px-4 pt-4 pb-2.5 border-b border-[var(--border-primary)] flex-shrink-0">
            <button
              type="button"
              onClick={onToggle}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-all"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
        )}

        {!sidebarCollapsed && (
          <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4 custom-scrollbar">
            <AppNavigation />
          </div>
        )}
      </div>
    </aside>
  );
}
