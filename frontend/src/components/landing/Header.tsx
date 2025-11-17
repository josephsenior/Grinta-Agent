import React, { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Settings,
  MessageCircle,
  User,
  Plus,
  Menu,
  Info,
  FileText,
  Shield,
  DollarSign,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { ThemeToggle } from "#/components/ui/theme-toggle";
import { useScrollY } from "#/hooks/use-scroll-reveal";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";
import { cn } from "#/utils/utils";
// Use public logo instead of bundled asset
const logo = "/forge-logo.png";

export default function Header(): React.ReactElement {
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
        to: "/about",
        label: t(I18nKey.LANDING$START_HELP, { defaultValue: "About" }),
        icon: Info,
      },
      {
        to: "/pricing",
        label: t("PRICING", { defaultValue: "Pricing" }),
        icon: DollarSign,
      },
      {
        to: "/contact",
        label: t(I18nKey.COMMON$HERE, { defaultValue: "Contact" }),
        icon: MessageCircle,
      },
      {
        to: "/terms",
        label: t(I18nKey.TOS$TERMS, { defaultValue: "Terms" }),
        icon: FileText,
      },
      {
        to: "/privacy",
        label: t(I18nKey.COMMON$PRIVACY_POLICY, { defaultValue: "Privacy" }),
        icon: Shield,
      },
    ],
    [t],
  );

  // Calculate blur amount based on scroll (0-20px)
  const blurAmount = Math.min(scrollY / 10, 20);
  // Calculate opacity for background (0.8-0.95)
  const bgOpacity = Math.min(0.8 + scrollY / 500, 0.95);
  // Calculate shadow intensity
  const shadowOpacity = Math.min(scrollY / 500, 0.3);

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

  const handleOpenUserSettings = () => navigate("/settings/user");
  const handleOpenAppSettings = () => navigate("/settings/app");
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
      <div className="mx-auto max-w-6xl px-6 pt-6">
        <div
          className={cn(
            "relative overflow-hidden rounded-[24px] border transition-all duration-500",
            isLandingRoute
              ? "border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 shadow-[0_20px_60px_rgba(0,0,0,0.3)] backdrop-blur-xl"
              : "border-white/5 bg-black/60 backdrop-blur-md",
          )}
          style={
            isLandingRoute
              ? {
                  backdropFilter: `blur(${Math.min(scrollY / 8, 24)}px) saturate(180%)`,
                }
              : undefined
          }
        >
          {/* Gradient overlay for landing route */}
          {isLandingRoute && (
            <div aria-hidden className="pointer-events-none absolute inset-0">
              <div className="absolute inset-y-0 left-1/2 w-1/2 rounded-r-[24px] bg-gradient-to-r from-brand-500/10 via-accent-500/5 to-transparent blur-2xl" />
              <div className="absolute -top-12 right-4 h-32 w-32 rounded-full bg-brand-500/20 blur-[100px]" />
            </div>
          )}

          <div className="relative flex items-center justify-between gap-4 px-6 py-4">
            {/* Logo */}
            <div
              className="flex items-center space-x-3 select-none group cursor-pointer"
              onClick={() => navigate("/")}
            >
              <img
                src={logo}
                alt="Forge"
                className={cn(
                  "h-8 w-auto transition-all duration-300",
                  isLandingRoute
                    ? "group-hover:opacity-90 drop-shadow-[0_0_8px_rgba(139,92,246,0.3)]"
                    : "group-hover:opacity-80",
                )}
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
                    "relative flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2",
                    isLandingRoute
                      ? "text-white/90 hover:text-white hover:bg-white/10 focus-visible:ring-white/50"
                      : "text-foreground-secondary hover:text-foreground hover:bg-white/5 focus-visible:ring-brand-500/40",
                  )}
                  title={label}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4 transition-transform duration-300",
                      isLandingRoute
                        ? "text-white/70"
                        : "text-foreground-tertiary",
                    )}
                  />
                  <span>{label}</span>
                </Link>
              ))}
            </nav>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {!isConversationRoute && (
                <>
                  <ThemeToggle variant="icon" />

                  <button
                    data-testid="header-launch-button"
                    type="button"
                    onClick={handleCreateConversation}
                    disabled={isPending || isCreatingConversationElsewhere}
                    aria-label={t("COMMON$NEW_CONVERSATION", {
                      defaultValue: "New conversation",
                    })}
                    className={cn(
                      "relative flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed overflow-hidden",
                      isLandingRoute
                        ? "bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/40 hover:shadow-xl hover:shadow-brand-500/50 hover:scale-[1.02]"
                        : "bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-md shadow-brand-500/30 hover:shadow-lg",
                    )}
                  >
                    <Plus className="w-4 h-4" />
                    <span>
                      {t(I18nKey.CONVERSATION$START_NEW, {
                        defaultValue: "Start new",
                      })}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenMessages}
                    aria-label={t("COMMON$OPEN_CONVERSATIONS", {
                      defaultValue: "Open conversations",
                    })}
                    className={cn(
                      "relative p-2.5 rounded-xl transition-all duration-300",
                      isLandingRoute
                        ? "text-white/80 hover:text-white hover:bg-white/10"
                        : "text-foreground-secondary hover:text-brand-400 hover:bg-white/5",
                    )}
                  >
                    <MessageCircle className="w-5 h-5" />
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenUserSettings}
                    aria-label={t("COMMON$USER_SETTINGS", {
                      defaultValue: "User settings",
                    })}
                    className={cn(
                      "relative p-2.5 rounded-xl transition-all duration-300",
                      isLandingRoute
                        ? "text-white/80 hover:text-white hover:bg-white/10"
                        : "text-foreground-secondary hover:text-brand-400 hover:bg-white/5",
                    )}
                  >
                    <User className="w-5 h-5" />
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenAppSettings}
                    aria-label={t(I18nKey.USER$ACCOUNT_SETTINGS, {
                      defaultValue: "Forge Pro settings",
                    })}
                    className={cn(
                      "relative p-2.5 rounded-xl transition-all duration-300",
                      isLandingRoute
                        ? "text-white/80 hover:text-white hover:bg-white/10"
                        : "text-foreground-secondary hover:text-brand-400 hover:bg-white/5",
                    )}
                  >
                    <Settings className="w-5 h-5" />
                    <span className="sr-only">
                      {t(I18nKey.USER$ACCOUNT_SETTINGS, {
                        defaultValue: "Forge Pro settings",
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
                className={cn(
                  "md:hidden relative p-2.5 rounded-xl transition-all duration-300",
                  isLandingRoute
                    ? "text-white/80 hover:text-white hover:bg-white/10"
                    : "text-foreground-secondary hover:text-brand-400 hover:bg-white/5",
                )}
              >
                <Menu className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Mobile menu */}
          {mobileOpen && (
            <div
              className={cn(
                "md:hidden border-t px-6 py-4 space-y-2",
                isLandingRoute ? "border-white/10" : "border-white/5",
              )}
            >
              {navLinks.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-4 py-3 text-sm transition-all duration-300",
                    isLandingRoute
                      ? "text-white/90 hover:text-white hover:bg-white/10"
                      : "text-foreground-secondary hover:text-foreground hover:bg-white/5",
                  )}
                  onClick={() => setMobileOpen(false)}
                >
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      isLandingRoute
                        ? "text-white/70"
                        : "text-foreground-tertiary",
                    )}
                  />
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
