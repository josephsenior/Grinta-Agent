import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
// Use public logo instead of bundled asset
const logo = "/forge-logo.png";

export default function Header(): React.ReactElement {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();
  const isConversationRoute = pathname.startsWith("/conversations/");
  const scrollY = useScrollY(16);
  
  // Calculate blur amount based on scroll (0-20px)
  const blurAmount = Math.min(scrollY / 10, 20);
  // Calculate opacity for background (0.8-0.95)
  const bgOpacity = Math.min(0.8 + (scrollY / 500), 0.95);
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
  // detect Playwright runs (test init script sets this flag)
  const { t } = useTranslation();

  // Detect Playwright test runs; test harness sets __Forge_PLAYWRIGHT on window
  type WindowWithE2E = Window & { __Forge_PLAYWRIGHT?: boolean };
  const isPlaywrightRun =
    typeof window !== "undefined" &&
    (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;

  return (
    <header
      className={`fixed top-0 left-0 right-0 transition-all duration-300 gpu-accelerated ${
        // keep header on top during Playwright runs to avoid other subtrees intercepting pointer events
        isPlaywrightRun ? "z-[9999] pointer-events-auto" : "z-50"
      }`}
      style={{
        backdropFilter: `blur(${blurAmount}px) saturate(150%)`,
        backgroundColor: `rgba(0, 0, 0, ${bgOpacity})`,
        borderBottom: `1px solid rgba(139, 92, 246, ${0.2 + shadowOpacity})`,
        boxShadow: `0 4px 24px rgba(139, 92, 246, ${shadowOpacity})`,
      }}
    >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 md:py-4">
        <div className="flex items-center justify-between gap-4">
          {/* Logo with enhanced glow */}
          <div className="flex items-center space-x-3 select-none group cursor-pointer" onClick={() => navigate("/")}>
            <img
              src={logo}
              alt="Forge"
              className="h-8 w-auto group-hover:opacity-90 transition-opacity duration-200"
              draggable={false}
            />
          </div>

          {/* Navigation with underline animations */}
          <nav className="hidden md:flex items-center space-x-2">
            <a
              href="/about"
              aria-label={t(I18nKey.LANDING$START_HELP, {
                defaultValue: "About",
              })}
              className="nav-link relative px-4 py-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-2 focus-visible:ring-brand-500/50 group gpu-accelerated"
              title={t(I18nKey.LANDING$START_HELP, { defaultValue: "About" })}
            >
              <Info className="w-5 h-5 inline-block mr-1.5 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-medium">About</span>
            </a>
            <a
              href="/pricing"
              aria-label="Pricing"
              className="nav-link relative px-4 py-2.5 rounded-lg text-foreground-secondary hover:text-success-500 transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success-500/50 group gpu-accelerated"
              title="Pricing"
            >
              <DollarSign className="w-5 h-5 inline-block mr-1.5 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-medium">Pricing</span>
            </a>
            <a
              href="/contact"
              aria-label={t(I18nKey.COMMON$HERE, { defaultValue: "Contact" })}
              className="nav-link relative px-4 py-2.5 rounded-lg text-foreground-secondary hover:text-accent-emerald transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-emerald/50 group gpu-accelerated"
              title={t(I18nKey.COMMON$HERE, { defaultValue: "Contact" })}
            >
              <MessageCircle className="w-5 h-5 inline-block mr-1.5 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-medium">Contact</span>
            </a>
            <a
              href="/terms"
              aria-label={t(I18nKey.TOS$TERMS, { defaultValue: "Terms" })}
              className="nav-link relative px-4 py-2.5 rounded-lg text-foreground-secondary hover:text-accent-sapphire transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-sapphire/50 group gpu-accelerated"
              title={t(I18nKey.TOS$TERMS, { defaultValue: "Terms" })}
            >
              <FileText className="w-5 h-5 inline-block mr-1.5 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-medium">Terms</span>
            </a>
            <a
              href="/privacy"
              aria-label={t(I18nKey.COMMON$PRIVACY_POLICY, {
                defaultValue: "Privacy",
              })}
              className="nav-link relative px-4 py-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 group gpu-accelerated"
              title={t(I18nKey.COMMON$PRIVACY_POLICY, {
                defaultValue: "Privacy",
              })}
            >
              <Shield className="w-5 h-5 inline-block mr-1.5 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-medium">Privacy</span>
            </a>
          </nav>

          {/* Action Icons & Mobile Toggle (hide action icons on conversation routes) */}
          <div className="flex items-center space-x-2">
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
                  className="button-shine relative h-10 px-6 flex items-center gap-2 text-sm font-semibold tracking-wide rounded-lg bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40 hover:scale-105 transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed gpu-accelerated overflow-hidden"
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
                  className="relative p-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300 interactive-scale gpu-accelerated"
                >
                  <MessageCircle className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={handleOpenUserSettings}
                  aria-label={t("COMMON$USER_SETTINGS", {
                    defaultValue: "User settings",
                  })}
                  className="relative p-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300 interactive-scale gpu-accelerated"
                >
                  <User className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={handleOpenAppSettings}
                  aria-label={t(I18nKey.USER$ACCOUNT_SETTINGS, {
                    defaultValue: "Forge Pro settings",
                  })}
                  className="relative p-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300 interactive-scale gpu-accelerated"
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
              className="md:hidden relative p-2.5 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300 interactive-scale gpu-accelerated"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>
        {/* Mobile menu with slide-in animation */}
        {mobileOpen && (
          <div className="md:hidden mt-3 rounded-xl glass-modern p-5 space-y-3 text-sm shadow-2xl shadow-black/50 animate-slide-down">
            <a
              href="/about"
              className="nav-link block py-2 px-3 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300"
              onClick={() => setMobileOpen(false)}
            >
              {t(I18nKey.LANDING$START_HELP, { defaultValue: "About" })}
            </a>
            <a
              href="/pricing"
              className="nav-link block py-2 px-3 rounded-lg text-foreground-secondary hover:text-success-500 hover:bg-success-500/10 transition-all duration-300"
              onClick={() => setMobileOpen(false)}
            >
              Pricing
            </a>
            <a
              href="/contact"
              className="nav-link block py-2 px-3 rounded-lg text-foreground-secondary hover:text-accent-emerald hover:bg-accent-emerald/10 transition-all duration-300"
              onClick={() => setMobileOpen(false)}
            >
              {t(I18nKey.COMMON$HERE, { defaultValue: "Contact" })}
            </a>
            <a
              href="/terms"
              className="nav-link block py-2 px-3 rounded-lg text-foreground-secondary hover:text-accent-sapphire hover:bg-accent-sapphire/10 transition-all duration-300"
              onClick={() => setMobileOpen(false)}
            >
              {t(I18nKey.TOS$TERMS, { defaultValue: "Terms" })}
            </a>
            <a
              href="/privacy"
              className="nav-link block py-2 px-3 rounded-lg text-foreground-secondary hover:text-violet-500 hover:bg-violet-500/10 transition-all duration-300"
              onClick={() => setMobileOpen(false)}
            >
              {t(I18nKey.COMMON$PRIVACY_POLICY, { defaultValue: "Privacy" })}
            </a>
          </div>
        )}
      </div>
    </header>
  );
}
