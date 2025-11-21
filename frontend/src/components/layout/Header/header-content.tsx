import React from "react";
import { Link } from "react-router-dom";
import {
  MessageCircle,
  User,
  Plus,
  Menu,
  Info,
  DollarSign,
  Bell,
  PanelLeft,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { cn } from "#/utils/utils";
import { UserProfileDropdown } from "#/components/features/user/user-profile-dropdown";
import { NotificationsCenter } from "#/components/features/notifications/notifications-center";
import { GlobalSearch } from "#/components/features/search/global-search";

const logo = "/forge-logo.png";

interface HeaderContentProps {
  isLandingRoute: boolean;
  isConversationRoute: boolean;
  scrollY: number;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  isPending: boolean;
  isCreatingConversationElsewhere: boolean;
  handleCreateConversation: () => void;
}

export function HeaderContent({
  isLandingRoute,
  isConversationRoute,
  scrollY,
  mobileOpen,
  setMobileOpen,
  sidebarCollapsed,
  setSidebarCollapsed,
  isPending,
  isCreatingConversationElsewhere,
  handleCreateConversation,
}: HeaderContentProps) {
  const { t } = useTranslation();
  const navigate = (path: string) => {
    window.location.href = path;
  };

  const navLinks = React.useMemo(
    () => [
      {
        to: "/dashboard",
        label: t("COMMON$DASHBOARD", { defaultValue: "Dashboard" }),
        icon: MessageCircle,
      },
      {
        to: "/profile",
        label: t("COMMON$PROFILE", { defaultValue: "Profile" }),
        icon: User,
      },
      {
        to: "/notifications",
        label: t("COMMON$NOTIFICATIONS", { defaultValue: "Notifications" }),
        icon: Bell,
      },
      {
        to: "/help",
        label: t("COMMON$HELP", { defaultValue: "Help" }),
        icon: Info,
      },
      {
        to: "/pricing",
        label: t("PRICING", { defaultValue: "Pricing" }),
        icon: DollarSign,
      },
    ],
    [t],
  );

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border transition-all duration-500",
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

      <div className="relative flex items-center gap-4 px-4 sm:px-6 py-3 sm:py-4">
        {/* Logo (left) */}
        <div
          className="flex items-center space-x-3 select-none group cursor-pointer flex-shrink-0"
          onClick={() => navigate("/")}
        >
          <img
            src={logo}
            alt="Forge"
            className="h-7 sm:h-8 w-auto transition-all duration-300 group-hover:opacity-90 drop-shadow-[0_0_8px_rgba(139,92,246,0.3)]"
            draggable={false}
          />
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1 flex-1">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                "text-white/70 hover:text-white hover:bg-white/10",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right side actions */}
        <div className="flex items-center gap-2 ml-auto">
          {isConversationRoute && (
            <button
              type="button"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className={cn(
                "p-2 rounded-lg transition-all duration-200",
                "text-white/70 hover:text-white hover:bg-white/10",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
              )}
              aria-label={t("COMMON$TOGGLE_SIDEBAR", {
                defaultValue: "Toggle sidebar",
              })}
            >
              <PanelLeft className="h-5 w-5" />
            </button>
          )}

          <GlobalSearch />

          <NotificationsCenter />

          <ThemeToggle />

          <button
            type="button"
            onClick={handleCreateConversation}
            disabled={isPending || isCreatingConversationElsewhere}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              "bg-brand-500 text-white hover:bg-brand-600",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50",
            )}
          >
            <Plus className="h-4 w-4 inline-block mr-2" />
            {t("COMMON$NEW_CONVERSATION", { defaultValue: "New Conversation" })}
          </button>

          <UserProfileDropdown />

          {/* Mobile menu button */}
          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className={cn(
              "md:hidden p-2 rounded-lg transition-all duration-200",
              "text-white/70 hover:text-white hover:bg-white/10",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50",
            )}
            aria-label={t("COMMON$MENU", { defaultValue: "Menu" })}
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 px-4 py-3">
          <nav className="flex flex-col gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    "text-white/70 hover:text-white hover:bg-white/10",
                    "flex items-center gap-2",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </div>
  );
}
