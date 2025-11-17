import React, { useState, useRef, useEffect } from "react";
import {
  HelpCircle,
  Book,
  MessageCircle,
  ExternalLink,
  X,
  Keyboard,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { BRAND } from "#/config/brand";
import { KeyboardShortcutsPanel } from "#/components/features/chat/keyboard-shortcuts-panel";

export function HelpCenter() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [activeTab, setActiveTab] = useState<"shortcuts" | "docs" | "support">(
    "shortcuts",
  );
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Cmd+/ or Ctrl+/ to open help
      if ((event.metaKey || event.ctrlKey) && event.key === "/") {
        event.preventDefault();
        setIsOpen(true);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10"
        aria-label="Help"
      >
        <HelpCircle className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />
          <div
            ref={dropdownRef}
            className="relative w-full max-w-2xl max-h-[80vh] rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h2 className="text-xl font-semibold text-white">Help Center</h2>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-white/60" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 px-6 py-3 border-b border-white/10">
              <button
                type="button"
                onClick={() => setActiveTab("shortcuts")}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "shortcuts"
                    ? "bg-white/10 text-white"
                    : "text-white/60 hover:text-white hover:bg-white/5",
                )}
              >
                <Keyboard className="w-4 h-4 inline mr-2" />
                Shortcuts
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("docs")}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "docs"
                    ? "bg-white/10 text-white"
                    : "text-white/60 hover:text-white hover:bg-white/5",
                )}
              >
                <Book className="w-4 h-4 inline mr-2" />
                Documentation
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("support")}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "support"
                    ? "bg-white/10 text-white"
                    : "text-white/60 hover:text-white hover:bg-white/5",
                )}
              >
                <MessageCircle className="w-4 h-4 inline mr-2" />
                Support
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {activeTab === "shortcuts" && (
                <div className="space-y-4">
                  <div className="text-center py-4">
                    <p className="text-sm text-white/60 mb-4">
                      View all keyboard shortcuts and commands
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setShowShortcuts(true);
                        setIsOpen(false);
                      }}
                      className="px-6 py-3 rounded-xl border border-white/20 bg-white/10 hover:bg-white/15 text-white font-semibold transition-all"
                    >
                      Open Keyboard Shortcuts
                    </button>
                  </div>
                  <div className="pt-4 border-t border-white/10">
                    <p className="text-xs text-white/50 text-center">
                      Press{" "}
                      <kbd className="px-2 py-1 rounded border border-white/10 bg-white/5 text-xs font-mono">
                        ?
                      </kbd>{" "}
                      anywhere to show shortcuts
                    </p>
                  </div>
                </div>
              )}

              {activeTab === "docs" && (
                <div className="space-y-4">
                  <div className="space-y-3">
                    <a
                      href={BRAND.urls.docs}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-black/60 hover:border-white/20 hover:bg-white/5 transition-all group"
                    >
                      <div>
                        <h3 className="text-sm font-semibold text-white mb-1">
                          Documentation
                        </h3>
                        <p className="text-xs text-white/60">
                          Complete guides and API reference
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-white/40 group-hover:text-white/60" />
                    </a>

                    <a
                      href={BRAND.urls.github}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-black/60 hover:border-white/20 hover:bg-white/5 transition-all group"
                    >
                      <div>
                        <h3 className="text-sm font-semibold text-white mb-1">
                          GitHub Repository
                        </h3>
                        <p className="text-xs text-white/60">
                          Source code and contributions
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-white/40 group-hover:text-white/60" />
                    </a>
                  </div>
                </div>
              )}

              {activeTab === "support" && (
                <div className="space-y-4">
                  <div className="space-y-3">
                    <a
                      href={BRAND.urls.support}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-black/60 hover:border-white/20 hover:bg-white/5 transition-all group"
                    >
                      <div>
                        <h3 className="text-sm font-semibold text-white mb-1">
                          Get Support
                        </h3>
                        <p className="text-xs text-white/60">
                          Contact our support team
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-white/40 group-hover:text-white/60" />
                    </a>

                    <button
                      type="button"
                      onClick={() => {
                        navigate("/contact");
                        setIsOpen(false);
                      }}
                      className="w-full flex items-center justify-between p-4 rounded-xl border border-white/10 bg-black/60 hover:border-white/20 hover:bg-white/5 transition-all group text-left"
                    >
                      <div>
                        <h3 className="text-sm font-semibold text-white mb-1">
                          Contact Us
                        </h3>
                        <p className="text-xs text-white/60">
                          Send us a message
                        </p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-white/40 group-hover:text-white/60" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Use existing KeyboardShortcutsPanel */}
      <KeyboardShortcutsPanel
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </>
  );
}
