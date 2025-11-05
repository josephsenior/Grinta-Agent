import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Settings,
  MessageCircle,
  User,
  Plus,
  Menu,
  Info,
  Mail,
  FileText,
  Shield,
} from "lucide-react";
import { BRAND } from "#/config/brand";
// Use public logo instead of bundled asset
const logoImage = "/forge-logo.png";

import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";

export function Header() {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();
  const isConversationRoute = pathname.startsWith("/conversations/");

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
            // ignore
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  };

  const handleOpenMessages = () => {
    const event = new CustomEvent("openhands:open-conversation-panel");
    window.dispatchEvent(event);
  };

  const handleOpenUserSettings = () => navigate("/settings/user");
  const handleOpenAppSettings = () => navigate("/settings/app");

  const isPlaywrightRun = (() => {
    interface WindowWithE2E extends Window {
      __OPENHANDS_PLAYWRIGHT?: boolean;
    }
    const win =
      typeof window !== "undefined"
        ? (window as unknown as WindowWithE2E)
        : undefined;
    return win?.__OPENHANDS_PLAYWRIGHT === true;
  })();

  return (
    <header
      className={`fixed top-0 left-0 right-0 glass border-b border-border h-14 safe-area-top ${
        isPlaywrightRun ? "z-[9999] pointer-events-auto" : "z-50"
      }`}
      style={{
        paddingTop: 'max(0.875rem, env(safe-area-inset-top))',
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-full">
        <div className="flex items-center justify-between gap-4 h-full">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3 select-none min-w-0">
            <img
              src={logoImage}
              alt="CodePilot Pro Logo"
              className="w-8 h-8 object-contain"
            />
            <span className="text-xl font-bold text-gradient-brand tracking-tight truncate">
              {BRAND.name}
            </span>
            <span className="hidden lg:inline text-xs text-foreground-tertiary font-medium tracking-wide">
              {BRAND.tagline}
            </span>
          </div>

          {/* All Icons - Unified */}
          <div className="flex items-center gap-3">
            {/* Navigation Links */}
            <a
              href="/about"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors px-3 py-2 rounded-lg hover:bg-background-tertiary/50 text-sm font-medium"
              title="About"
            >
              <Info className="w-4 h-4" />
              <span>About</span>
            </a>
            <a
              href="/contact"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors px-3 py-2 rounded-lg hover:bg-background-tertiary/50 text-sm font-medium"
              title="Contact"
            >
              <Mail className="w-4 h-4" />
              <span>Contact</span>
            </a>
            <a
              href="/terms"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors px-3 py-2 rounded-lg hover:bg-background-tertiary/50 text-sm font-medium"
              title="Terms of Service"
            >
              <FileText className="w-4 h-4" />
              <span>Terms</span>
            </a>
            <a
              href="/privacy"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors px-3 py-2 rounded-lg hover:bg-background-tertiary/50 text-sm font-medium"
              title="Privacy Policy"
            >
              <Shield className="w-4 h-4" />
              <span>Privacy</span>
            </a>

            {/* Separator */}
            <div className="h-6 w-px bg-border/50 mx-1" />

            {/* Action Buttons */}
            {!isConversationRoute && (
              <>
                <button
                  data-testid="header-launch-button"
                  type="button"
                  onClick={handleCreateConversation}
                  disabled={isPending || isCreatingConversationElsewhere}
                  aria-label="New conversation"
                  className="gradient-brand hover:opacity-90 transition-all h-10 px-6 rounded-lg flex items-center gap-2 text-sm font-semibold text-white disabled:opacity-60 shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <Plus className="w-4 h-4" />
                  <span>New Chat</span>
                </button>

                <button
                  type="button"
                  onClick={handleOpenMessages}
                  aria-label="Open conversations"
                  title="Conversations"
                  className="text-foreground-secondary hover:text-foreground transition-colors h-10 px-3 flex items-center gap-2 rounded-lg hover:bg-background-tertiary text-sm font-medium"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">Chats</span>
                </button>

                <button
                  type="button"
                  onClick={handleOpenUserSettings}
                  aria-label="User settings"
                  title="User Settings"
                  className="text-foreground-secondary hover:text-foreground transition-colors h-10 px-3 flex items-center gap-2 rounded-lg hover:bg-background-tertiary text-sm font-medium"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">Profile</span>
                </button>

                <button
                  type="button"
                  onClick={handleOpenAppSettings}
                  aria-label="CodePilot Pro settings"
                  title="App Settings"
                  className="text-foreground-secondary hover:text-foreground transition-colors h-10 px-3 flex items-center gap-2 rounded-lg hover:bg-background-tertiary text-sm font-medium"
                >
                  <Settings className="w-4 h-4" />
                  <span className="hidden sm:inline">Settings</span>
                </button>
              </>
            )}

            {/* Mobile menu button - hidden since nav is always visible */}
            <button
              type="button"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Toggle navigation"
              aria-expanded={mobileOpen}
              className="hidden text-foreground-secondary hover:text-foreground transition-colors h-9 w-9 flex items-center justify-center rounded-lg hover:bg-background-tertiary"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Mobile menu with Icons */}
        {mobileOpen && (
          <div className="md:hidden absolute top-full left-0 right-0 mt-1 mx-4 rounded-xl border border-border glass p-4 space-y-2 animate-slide-up shadow-xl">
            <a
              href="/about"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors py-2 px-3 rounded-lg hover:bg-background-tertiary"
              onClick={() => setMobileOpen(false)}
            >
              <Info className="w-4 h-4" />
              About
            </a>
            <a
              href="/contact"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors py-2 px-3 rounded-lg hover:bg-background-tertiary"
              onClick={() => setMobileOpen(false)}
            >
              <Mail className="w-4 h-4" />
              Contact
            </a>
            <a
              href="/terms"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors py-2 px-3 rounded-lg hover:bg-background-tertiary"
              onClick={() => setMobileOpen(false)}
            >
              <FileText className="w-4 h-4" />
              Terms
            </a>
            <a
              href="/privacy"
              className="flex items-center gap-2 text-foreground-secondary hover:text-foreground transition-colors py-2 px-3 rounded-lg hover:bg-background-tertiary"
              onClick={() => setMobileOpen(false)}
            >
              <Shield className="w-4 h-4" />
              Privacy
            </a>
          </div>
        )}
      </div>
    </header>
  );
}
