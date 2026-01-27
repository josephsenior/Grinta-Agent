import { Menu } from "lucide-react";
import { AppNavigation } from "#/components/layout/AppNavigation";

interface MobileSidebarProps {
  mobileDrawerOpen: boolean;
  onClose: () => void;
}

export function MobileSidebar({
  mobileDrawerOpen,
  onClose,
}: MobileSidebarProps) {
  return (
    <>
      {/* Mobile Drawer Overlay */}
      {mobileDrawerOpen && (
        <div
          className="fixed inset-0 bg-[var(--bg-primary)]/60 backdrop-blur-sm"
          onClick={onClose}
          style={{ zIndex: 9998, display: "block" }}
          data-mobile-overlay
        >
          <style>{`
            @media (min-width: 768px) {
              div[data-mobile-overlay] {
                display: none !important;
              }
            }
          `}</style>
        </div>
      )}

      {/* Mobile Drawer Sidebar */}
      <aside
        className="fixed left-0 top-0 bottom-0 w-64 border-r border-[var(--border-primary)] overflow-y-auto shadow-2xl transition-transform duration-300 ease-in-out"
        style={{
          backgroundColor: "var(--bg-secondary)",
          zIndex: 9999,
          transform: mobileDrawerOpen ? "translateX(0)" : "translateX(-100%)",
          display: "block",
        }}
        data-mobile-drawer
      >
        <style>{`
          @media (min-width: 768px) {
            aside[data-mobile-drawer] {
              display: none !important;
            }
          }
        `}</style>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <img
              src="/forge-logo.png"
              alt="Forge"
              className="h-8 w-auto"
              draggable={false}
            />
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
              aria-label="Close drawer"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <AppNavigation />
        </div>
      </aside>

      {/* Mobile Menu Button */}
      <button
        type="button"
        onClick={onClose}
        className="fixed bottom-4 left-4 p-3 rounded-full bg-[var(--bg-elevated)] border border-[var(--border-primary)] shadow-lg text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-all flex items-center justify-center"
        style={{ zIndex: 10000, display: "block" }}
        data-mobile-button
        aria-label="Open navigation menu"
      >
        <style>{`
          @media (min-width: 768px) {
            button[data-mobile-button] {
              display: none !important;
            }
          }
        `}</style>
        <Menu className="w-6 h-6" />
      </button>
    </>
  );
}
