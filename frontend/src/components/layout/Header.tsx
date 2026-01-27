import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MessageCircle, Menu, PanelLeft, User } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSidebar } from "#/contexts/sidebar-context";
import { useScrollY } from "#/hooks/use-scroll-reveal";
import { cn } from "#/utils/utils";
import { useHeaderHandlers } from "./Header/use-header-handlers";
import { useHeaderNavigation } from "./Header/use-header-navigation";
import { usePlaywrightDetection } from "./Header/use-playwright-detection";
import { NotificationsCenter } from "#/components/features/notifications/notifications-center";
import { SettingsDrawer } from "#/components/settings/SettingsDrawer";
// HelpCenter moved to sidebar - removed from header
// Use public logo instead of bundled asset
const logo = "/forge-logo.png";

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [settingsDrawerOpen, setSettingsDrawerOpen] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const isConversationRoute = pathname.startsWith("/conversations/");
  const isLandingRoute = pathname === "/";
  const scrollY = useScrollY(16);
  const { t } = useTranslation();
  const { sidebarCollapsed, setSidebarCollapsed } = useSidebar();
  const { handleOpenMessages } = useHeaderHandlers();
  const navLinks = useHeaderNavigation();
  const isPlaywrightRun = usePlaywrightDetection();

  const openSettingsDrawer = () => setSettingsDrawerOpen(true);
  const closeSettingsDrawer = () => setSettingsDrawerOpen(false);

  return (
    <>
      <header
        className={cn(
          "fixed top-0 left-0 right-0 transition-all duration-500 gpu-accelerated h-auto",
          isPlaywrightRun ? "z-[9999] pointer-events-auto" : "z-50",
        )}
      >
        <div className="w-full px-4 sm:px-6 lg:px-8 pt-4 pb-4 pointer-events-none">
          <div
            className={cn(
              "relative overflow-hidden rounded-2xl border transition-all duration-500 animate-fade-in-up pointer-events-auto max-w-5xl mx-auto",
              "border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 shadow-[0_20px_60px_rgba(0,0,0,0.3)] backdrop-blur-xl",
            )}
            style={
              isLandingRoute
                ? {
                    backdropFilter: `blur(${Math.min(scrollY / 8, 24)}px) saturate(180%)`,
                  }
                : {
                    backdropFilter: "blur(24px) saturate(180%)",
                  }
            }
          >
            {/* Gradient overlay */}
            <div aria-hidden className="pointer-events-none absolute inset-0">
              <div className="absolute inset-y-0 left-1/2 w-1/2 rounded-r-2xl bg-gradient-to-r from-brand-500/10 via-accent-500/5 to-transparent blur-2xl" />
              <div className="absolute -top-12 right-4 h-32 w-32 rounded-full bg-brand-500/20 blur-[100px]" />
            </div>

            <div className="relative flex items-center gap-4 px-4 sm:px-6 py-2.5">
              {/* Logo (left) */}
              <div
                className="flex items-center space-x-3 select-none group cursor-pointer flex-shrink-0"
                onClick={() => navigate("/conversations")}
              >
                <img
                  src={logo}
                  alt="Forge"
                  className="h-7 sm:h-8 w-auto transition-all duration-300 group-hover:opacity-90 drop-shadow-[0_0_8px_rgba(139,92,246,0.3)]"
                  draggable={false}
                />
              </div>

              {/* Navigation (hidden on mobile, shown when no search) */}
              {isConversationRoute && (
                <nav className="hidden md:flex items-center gap-1 flex-1">
                  {navLinks.map(({ to, label, icon: Icon }) => (
                    <Link
                      key={to}
                      to={to}
                      aria-label={label}
                      className={cn(
                        "relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
                        "text-white/80 hover:text-white hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
                        pathname === to && "text-white bg-white/10",
                      )}
                      title={label}
                    >
                      <Icon className="h-3.5 w-3.5 text-white/60" />
                      <span>{label}</span>
                    </Link>
                  ))}
                </nav>
              )}

              {/* Action buttons (right) */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {!isConversationRoute && (
                  <div className="flex items-center gap-1.5">
                    {/* Sidebar Toggle Button - Always visible in header */}
                    <button
                      type="button"
                      onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                      aria-label={
                        sidebarCollapsed ? "Show sidebar" : "Hide sidebar"
                      }
                      title={
                        sidebarCollapsed
                          ? "Show sidebar (Ctrl/Cmd + B)"
                          : "Hide sidebar (Ctrl/Cmd + B)"
                      }
                      className="relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10"
                    >
                      <PanelLeft className="w-4 h-4" />
                    </button>
                    {/* <ThemeToggle variant="icon" /> */}
                    <button
                      type="button"
                      onClick={handleOpenMessages}
                      aria-label={t("COMMON$OPEN_CONVERSATIONS", {
                        defaultValue: "Open conversations",
                      })}
                      className="relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10"
                    >
                      <MessageCircle className="w-4 h-4" />
                    </button>
                    <NotificationsCenter />
                    <button
                      type="button"
                      onClick={openSettingsDrawer}
                      aria-label={t("COMMON$SETTINGS", {
                        defaultValue: "Settings",
                      })}
                      className="relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10"
                    >
                      <User className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Mobile menu toggle - Always visible on mobile */}
                <button
                  type="button"
                  onClick={() => setMobileOpen((o) => !o)}
                  aria-label={t("COMMON$TOGGLE_NAVIGATION", {
                    defaultValue: "Toggle navigation",
                  })}
                  aria-expanded={mobileOpen}
                  className="md:hidden relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10 z-50"
                >
                  <Menu className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Mobile menu */}
            {mobileOpen && (
              <div className="md:hidden border-t border-white/10 px-4 sm:px-6 py-4 space-y-1">
                {navLinks.map(({ to, label, icon: Icon }) => (
                  <Link
                    key={to}
                    to={to}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm transition-all duration-200",
                      "text-white/80 hover:text-white hover:bg-white/10",
                      pathname === to && "text-white bg-white/10",
                    )}
                    onClick={() => setMobileOpen(false)}
                  >
                    <Icon className="h-4 w-4 text-white/60" />
                    {label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      <SettingsDrawer
        isOpen={settingsDrawerOpen}
        onClose={closeSettingsDrawer}
      />
    </>
  );
}
