import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Menu, ArrowLeft } from "lucide-react";
import { Button } from "#/components/ui/button";
import { AppNavigation } from "./AppNavigation";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Don't show navigation on landing page or conversation pages
  const isLandingRoute = location.pathname === "/";
  const isConversationRoute = location.pathname.startsWith("/conversations/");
  const showNavigation = !isLandingRoute && !isConversationRoute;

  return (
    <div className="relative z-[1] mx-auto max-w-7xl px-6 py-6">
      <div className="flex gap-8">
        {/* Desktop Sidebar - Always visible on desktop */}
        {showNavigation && (
          <aside className="hidden md:block w-[280px] flex-shrink-0">
            <AppNavigation />
          </aside>
        )}

        {/* Mobile Sidebar - Toggleable */}
        {showNavigation && mobileSidebarOpen && (
          <>
            {/* Overlay */}
            <div
              className="fixed inset-0 bg-black/50 z-40 md:hidden"
              onClick={() => setMobileSidebarOpen(false)}
            />
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 z-50 w-[280px] bg-black/95 backdrop-blur-xl border-r border-white/10 overflow-y-auto md:hidden">
              <div className="p-4">
                <AppNavigation />
              </div>
            </aside>
          </>
        )}

        {/* Content Area */}
        <div className="flex-1 min-w-0">
          {/* Header - Always visible */}
          {showNavigation && (
            <div className="mb-4 flex items-center gap-3">
              <button
                onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
                className="md:hidden rounded-xl border border-white/10 bg-black/60 p-2 text-foreground-secondary hover:bg-white/5 hover:text-foreground transition-all"
                aria-label="Toggle sidebar"
              >
                <Menu className="h-4 w-4" />
              </button>
              <Button
                variant="outline"
                onClick={() => navigate("/")}
                className="ml-auto border border-white/20 bg-transparent text-foreground hover:bg-white/10 text-xs h-8 px-3"
              >
                <ArrowLeft className="mr-1.5 h-3 w-3" />
                Back
              </Button>
            </div>
          )}

          {/* Page Content */}
          {children}
        </div>
      </div>
    </div>
  );
}
