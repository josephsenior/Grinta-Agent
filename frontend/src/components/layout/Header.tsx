import React, { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  MessageCircle,
  User,
  Plus,
  Menu,
  Info,
  DollarSign,
  Bell,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { useScrollY } from "#/hooks/use-scroll-reveal";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";
import { cn } from "#/utils/utils";
import { UserProfileDropdown } from "#/components/features/user/user-profile-dropdown";
import { NotificationsCenter } from "#/components/features/notifications/notifications-center";
import { GlobalSearch } from "#/components/features/search/global-search";
import { HelpCenter } from "#/components/features/help/help-center";
// Use public logo instead of bundled asset
const logo = "/forge-logo.png";

export function Header() {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();
  const isConversationRoute = pathname.startsWith("/conversations/");
  const isLandingRoute = pathname === "/";
  const scrollY = useScrollY(16);
  const { t } = useTranslation();
  const navLinks = useMemo(
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

  const handleCreateConversation = () => {
    if (isPending) {
      return;
    }
    createConversation(
      {},
      {
        onSuccess: (data) => {
          try {
            localStorage.setItem(
              "RECENT_CONVERSATION_ID",
              data.conversation_id,
            );
          } catch (e) {
            // ignore errors when persisting recent conversation id (e.g., storage disabled)
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  const handleOpenMessages = () => {
    // Request opening the conversation overlay panel via a custom event
    const event = new CustomEvent("Forge:open-conversation-panel");
    window.dispatchEvent(event);
  };
  // Detect Playwright test runs; test harness sets __Forge_PLAYWRIGHT on window
  type WindowWithE2E = Window & { __Forge_PLAYWRIGHT?: boolean };
  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 transition-all duration-500 gpu-accelerated",
        isPlaywrightRun ? "z-[9999] pointer-events-auto" : "z-50",
      )}
    >
      <div className="w-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-5">
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

          <div className="relative flex items-center justify-between gap-4 px-4 sm:px-6 py-3 sm:py-4">
            {/* Logo */}
            <div
              className="flex items-center space-x-3 select-none group cursor-pointer"
              onClick={() => navigate("/")}
            >
              <img
                src={logo}
                alt="Forge"
                className="h-7 sm:h-8 w-auto transition-all duration-300 group-hover:opacity-90 drop-shadow-[0_0_8px_rgba(139,92,246,0.3)]"
                draggable={false}
              />
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1">
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

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {!isConversationRoute && (
                <>
                  <div className="flex items-center gap-1.5">
                    <ThemeToggle variant="icon" />
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
                    <GlobalSearch />
                    <HelpCenter />
                    <UserProfileDropdown />
                  </div>

                  <button
                    data-testid="header-launch-button"
                    type="button"
                    onClick={handleCreateConversation}
                    disabled={isPending || isCreatingConversationElsewhere}
                    aria-label={t("COMMON$NEW_CONVERSATION", {
                      defaultValue: "New conversation",
                    })}
                    className={cn(
                      "relative flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed",
                      "bg-white text-black hover:bg-white/90 shadow-lg shadow-black/20",
                    )}
                  >
                    <Plus className="w-4 h-4" />
                    <span className="hidden sm:inline">
                      {t(I18nKey.CONVERSATION$START_NEW, {
                        defaultValue: "Start new",
                      })}
                    </span>
                  </button>
                </>
              )}

              {/* Mobile menu toggle */}
              <button
                type="button"
                onClick={() => setMobileOpen((o) => !o)}
                aria-label={t("COMMON$TOGGLE_NAVIGATION", {
                  defaultValue: "Toggle navigation",
                })}
                aria-expanded={mobileOpen}
                className="md:hidden relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10"
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
  );
}
