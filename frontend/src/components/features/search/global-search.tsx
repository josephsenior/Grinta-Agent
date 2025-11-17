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

interface SearchResult {
  id: string;
  type: "conversation" | "settings" | "action";
  title: string;
  description?: string;
  path: string;
  icon: React.ElementType;
}

export function GlobalSearch() {
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
          title: "New Conversation",
          description: "Start a new AI conversation",
          path: "/conversations/new",
          icon: MessageSquare,
        },
        {
          id: "conversations",
          type: "settings",
          title: "All Conversations",
          description: "View all conversations",
          path: "/conversations",
          icon: MessageSquare,
        },
        {
          id: "settings",
          type: "settings",
          title: "Settings",
          description: "Manage your settings",
          path: "/settings",
          icon: Settings,
        },
        {
          id: "analytics",
          type: "settings",
          title: "Analytics",
          description: "View usage analytics",
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
            conv.updated_at
              ? new Date(conv.updated_at).toLocaleDateString()
              : "recent"
          }`,
          path: `/conversations/${conv.conversation_id}`,
          icon: MessageSquare,
        });
      });

    // Search settings pages
    const settingsPages = [
      { id: "settings", title: "Settings", path: "/settings" },
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

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Cmd+K or Ctrl+K to open global search (only when not in conversation)
      // Conversation search uses Cmd+K within conversations, so we check the pathname
      const isInConversation =
        window.location.pathname.startsWith("/conversations/");

      if (
        (event.metaKey || event.ctrlKey) &&
        event.key === "k" &&
        !isInConversation
      ) {
        // Check if we're in an input/textarea to avoid conflicts
        const target = event.target as HTMLElement;
        if (
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable
        ) {
          return; // Let the input handle it
        }

        event.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 0);
      }

      // Escape to close
      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
        setQuery("");
        setSelectedIndex(0);
      }

      // Arrow keys to navigate
      if (isOpen && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
        event.preventDefault();
        setSelectedIndex((prev) => {
          if (event.key === "ArrowDown") {
            return prev < results.length - 1 ? prev + 1 : 0;
          }
          return prev > 0 ? prev - 1 : results.length - 1;
        });
      }

      // Enter to select
      if (isOpen && event.key === "Enter" && results[selectedIndex]) {
        event.preventDefault();
        handleSelectResult(results[selectedIndex]);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, results, selectedIndex]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleSelectResult = (result: SearchResult) => {
    navigate(result.path);
    setIsOpen(false);
    setQuery("");
    setSelectedIndex(0);
  };

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
