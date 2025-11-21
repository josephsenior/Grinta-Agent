import { ChevronLeft, Home } from "lucide-react";
import { useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();

  return (
    <aside
      id="main-sidebar"
      className="fixed left-0 bottom-0 border-r-2 border-white/20 overflow-hidden shadow-2xl transition-all duration-300 ease-in-out"
      style={{
        backgroundColor: "#000000",
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
          <div className="flex items-center justify-between px-4 pt-0 pb-2.5 border-b border-white/10 flex-shrink-0">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-all text-sm font-medium"
              aria-label="Go to homepage"
            >
              <Home className="w-4 h-4" />
              <span>Home</span>
            </button>
            <button
              type="button"
              onClick={onToggle}
              className="p-2 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-all"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
        )}

        {!sidebarCollapsed && (
          <div className="flex-1 overflow-y-auto px-6 pb-6 pt-4">
            <AppNavigation />
          </div>
        )}
      </div>
    </aside>
  );
}
