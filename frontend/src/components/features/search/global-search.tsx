import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  Search,
  Command,
  ArrowRight,
  FileText,
  Settings,
  MessageSquare,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { useSearchKeyboardShortcuts } from "#/hooks/use-search-keyboard-shortcuts";

interface SearchResult {
  id: string;
  type: "conversation" | "settings" | "action";
  title: string;
  description?: string;
  path: string;
  icon: React.ElementType;
}

interface GlobalSearchProps {
  variant?: "button" | "inline";
}

export function GlobalSearch({ variant = "button" }: GlobalSearchProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { data: conversationsData } = usePaginatedConversations(50);

  const conversations = useMemo(
    () => conversationsData?.pages.flatMap((p) => p.results) ?? [],
    [conversationsData],
  );

  // Search results
  const results = useMemo<SearchResult[]>(() => {
    if (!query.trim()) {
      return [
        {
          id: "new-conversation",
          type: "action",
          title: t("search.newConversation", "New Conversation"),
          description: t(
            "search.startNewConversation",
            "Start a new AI conversation",
          ),
          path: "/conversations/new",
          icon: MessageSquare,
        },
        {
          id: "conversations",
          type: "settings",
          title: t("search.allConversations", "All Conversations"),
          description: t(
            "search.viewAllConversations",
            "View all conversations",
          ),
          path: "/conversations",
          icon: MessageSquare,
        },
        {
          id: "settings",
          type: "settings",
          title: t("search.settings", "Settings"),
          description: t("search.manageSettings", "Manage your settings"),
          path: "/settings/app",
          icon: Settings,
        },
        {
          id: "analytics",
          type: "settings",
          title: t("search.analytics", "Analytics"),
          description: t("search.viewAnalytics", "View usage analytics"),
          path: "/settings/analytics",
          icon: FileText,
        },
      ];
    }

    const lowerQuery = query.toLowerCase();
    const searchResults: SearchResult[] = [];

    // Search conversations
    conversations
      .filter(
        (conv) =>
          conv.title?.toLowerCase().includes(lowerQuery) ||
          conv.conversation_id.toLowerCase().includes(lowerQuery),
      )
      .slice(0, 5)
      .forEach((conv) => {
        searchResults.push({
          id: conv.conversation_id,
          type: "conversation",
          title: conv.title || "Untitled Conversation",
          description: `Conversation from ${
            conv.last_updated_at
              ? new Date(conv.last_updated_at).toLocaleDateString()
              : "recent"
          }`,
          path: `/conversations/${conv.conversation_id}`,
          icon: MessageSquare,
        });
      });

    // Search settings pages
    const settingsPages = [
      { id: "settings", title: "Settings", path: "/settings/app" },
      { id: "user-settings", title: "User Settings", path: "/settings/user" },
      { id: "app-settings", title: "App Settings", path: "/settings/app" },
      { id: "billing", title: "Billing", path: "/settings/billing" },
      { id: "analytics", title: "Analytics", path: "/settings/analytics" },
      { id: "api-keys", title: "API Keys", path: "/settings/api-keys" },
    ];

    settingsPages
      .filter((page) => page.title.toLowerCase().includes(lowerQuery))
      .forEach((page) => {
        searchResults.push({
          id: page.id,
          type: "settings",
          title: page.title,
          description: "Settings page",
          path: page.path,
          icon: Settings,
        });
      });

    return searchResults.slice(0, 8);
  }, [query, conversations]);

  const handleSelectResult = React.useCallback(
    (result: SearchResult) => {
      navigate(result.path);
      setIsOpen(false);
      setQuery("");
      setSelectedIndex(0);
    },
    [navigate],
  );

  const handleSelectByIndex = React.useCallback(
    (index: number) => {
      if (results[index]) {
        handleSelectResult(results[index]);
      }
    },
    [results, handleSelectResult],
  );

  const handleClose = React.useCallback(() => {
    if (variant === "button") {
      setQuery("");
    }
    setSelectedIndex(0);
  }, [variant]);

  // Use shared keyboard shortcuts hook
  useSearchKeyboardShortcuts({
    isOpen,
    setIsOpen,
    inputRef,
    selectedIndex,
    setSelectedIndex,
    results,
    onSelect: handleSelectByIndex,
    onClose: handleClose,
    shouldOpen: (event) => {
      // Only open when not in conversation
      // Use event to check if it's a keyboard shortcut and handle Escape key
      if (event instanceof KeyboardEvent && event.key === "Escape") {
        return false;
      }
      return !window.location.pathname.startsWith("/conversations/");
    },
    variant,
  });

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  // Close dropdown when clicking outside (for inline mode)
  useEffect(() => {
    if (variant === "inline" && isOpen) {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          dropdownRef.current &&
          !dropdownRef.current.contains(event.target as Node) &&
          inputRef.current &&
          !inputRef.current.contains(event.target as Node)
        ) {
          setIsOpen(false);
        }
      };
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
    return undefined;
  }, [isOpen, variant]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Inline mode: always show search input in header center
  if (variant === "inline") {
    return (
      <div className="relative w-full">
        <div className="relative flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-white/60 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search conversations, settings..."
            className="w-full pl-10 pr-10 py-2 rounded-lg border border-white/10 bg-black/60 text-white placeholder:text-white/40 hover:border-white/20 focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] focus:border-[#8b5cf6] transition-all duration-200 text-sm"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setIsOpen(false);
              }}
              className="absolute right-3 text-white/40 hover:text-white/60 transition-colors"
            >
              <span className="text-xs">✕</span>
            </button>
          )}
          <kbd className="absolute right-3 hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-xs font-mono text-white/40">
            <Command className="w-3 h-3" />K
          </kbd>
        </div>

        {/* Dropdown results */}
        {isOpen && query && (
          <div
            ref={dropdownRef}
            className="absolute top-full left-0 right-0 mt-2 rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl overflow-hidden z-50"
          >
            <div className="max-h-96 overflow-y-auto">
              {results.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <Search className="h-8 w-8 text-white/20 mx-auto mb-2" />
                  <p className="text-sm text-white/60">No results found</p>
                </div>
              ) : (
                <div className="py-2">
                  {results.map((result, index) => {
                    const Icon = result.icon;
                    return (
                      <button
                        key={result.id}
                        type="button"
                        onClick={() => handleSelectResult(result)}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors",
                          index === selectedIndex && "bg-white/10",
                        )}
                      >
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
                          <Icon className="w-4 h-4 text-white/60" />
                        </div>
                        <div className="flex-1 min-w-0 text-left">
                          <p className="text-sm font-medium text-white truncate">
                            {result.title}
                          </p>
                          {result.description && (
                            <p className="text-xs text-white/50 truncate">
                              {result.description}
                            </p>
                          )}
                        </div>
                        <ArrowRight className="w-4 h-4 text-white/40 flex-shrink-0" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Button mode: button that opens modal
  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-black/60 text-white/60 hover:text-white hover:border-white/20 hover:bg-white/5 transition-all duration-200 text-sm"
      >
        <Search className="w-4 h-4" />
        <span className="hidden lg:inline">Search...</span>
        <kbd className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-xs font-mono">
          <Command className="w-3 h-3" />K
        </kbd>
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-black/60 text-white/60 hover:text-white hover:border-white/20 hover:bg-white/5 transition-all duration-200 text-sm"
      >
        <Search className="w-4 h-4" />
        <span className="hidden lg:inline">Search...</span>
        <kbd className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-xs font-mono">
          <Command className="w-3 h-3" />K
        </kbd>
      </button>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-20 px-4 pointer-events-none">
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm pointer-events-auto"
            onClick={() => {
              setIsOpen(false);
              setQuery("");
            }}
          />
          <div
            ref={dropdownRef}
            className="relative w-full max-w-2xl rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl overflow-hidden pointer-events-auto"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
              <Search className="w-5 h-5 text-white/60" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search conversations, settings..."
                className="flex-1 bg-transparent text-white placeholder:text-white/40 outline-none text-sm"
              />
              <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded border border-white/10 bg-white/5 text-xs font-mono text-white/60">
                Esc
              </kbd>
            </div>

            {/* Results */}
            <div className="max-h-96 overflow-y-auto">
              {results.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <Search className="h-8 w-8 text-white/20 mx-auto mb-2" />
                  <p className="text-sm text-white/60">No results found</p>
                </div>
              ) : (
                <div className="py-2">
                  {results.map((result, index) => {
                    const Icon = result.icon;
                    return (
                      <button
                        key={result.id}
                        type="button"
                        onClick={() => handleSelectResult(result)}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors",
                          index === selectedIndex && "bg-white/10",
                        )}
                      >
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
                          <Icon className="w-4 h-4 text-white/60" />
                        </div>
                        <div className="flex-1 min-w-0 text-left">
                          <p className="text-sm font-medium text-white truncate">
                            {result.title}
                          </p>
                          {result.description && (
                            <p className="text-xs text-white/50 truncate">
                              {result.description}
                            </p>
                          )}
                        </div>
                        <ArrowRight className="w-4 h-4 text-white/40 flex-shrink-0" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
