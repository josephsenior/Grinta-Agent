import React, { useState, useRef, useEffect, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Search, ArrowRight } from "lucide-react";
import { cn } from "#/utils/utils";
import { useSearchKeyboardShortcuts } from "#/hooks/use-search-keyboard-shortcuts";

interface SettingsSearchItem {
  path: string;
  label: string;
  category: string;
  description?: string;
  saasOnly?: boolean;
}

// All settings paths with their metadata
const ALL_SETTINGS_ITEMS: SettingsSearchItem[] = [
  // AI & Models
  {
    path: "/settings/llm",
    label: "LLM Settings",
    category: "AI & Models",
    description: "Configure AI models and providers",
  },
  {
    path: "/settings/mcp",
    label: "MCP",
    category: "AI & Models",
    description: "Model Context Protocol servers",
  },
  {
    path: "/settings/prompts",
    label: "Prompts",
    category: "AI & Models",
    description: "Manage prompt templates",
  },
  {
    path: "/settings/memory",
    label: "Memory",
    category: "AI & Models",
    description: "Configure memory settings",
  },
  // Account
  {
    path: "/settings/user",
    label: "User Settings",
    category: "Account",
    description: "Manage your profile",
    saasOnly: true,
  },
  {
    path: "/settings/billing",
    label: "Billing",
    category: "Account",
    description: "Manage billing and credits",
    saasOnly: true,
  },
  {
    path: "/settings/app",
    label: "Application",
    category: "Account",
    description: "Application settings",
  },
  {
    path: "/settings/api-keys",
    label: "API Keys",
    category: "Account",
    description: "Manage API keys",
  },
  // Integrations
  {
    path: "/settings/integrations",
    label: "Git Integration",
    category: "Integrations",
    description: "Connect Git repositories",
  },
  {
    path: "/settings/slack",
    label: "Slack",
    category: "Integrations",
    description: "Slack integration",
  },
  // Data & Storage
  {
    path: "/settings/databases",
    label: "Databases",
    category: "Data & Storage",
    description: "Manage databases",
  },
  {
    path: "/settings/knowledge-base",
    label: "Knowledge Base",
    category: "Data & Storage",
    description: "Knowledge base settings",
  },
  {
    path: "/settings/backup",
    label: "Backup & Restore",
    category: "Data & Storage",
    description: "Backup and restore data",
  },
  // Development
  {
    path: "/settings/snippets",
    label: "Code Snippets",
    category: "Development",
    description: "Manage code snippets",
  },
  {
    path: "/settings/secrets",
    label: "Secrets",
    category: "Development",
    description: "Manage secrets",
  },
  // Analytics
  {
    path: "/settings/analytics",
    label: "Analytics",
    category: "Analytics",
    description: "Usage statistics and metrics",
  },
];

interface SettingsSearchProps {
  variant?: "inline" | "button";
  onNavigate?: () => void;
}

export function SettingsSearch({
  variant = "inline",
  onNavigate,
}: SettingsSearchProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Filter settings based on query
  const filteredItems = useMemo(() => {
    if (!query.trim()) {
      return ALL_SETTINGS_ITEMS.slice(0, 8); // Show top 8 when no query
    }

    const lowerQuery = query.toLowerCase();
    // Use t for translation context (even if not directly used in filter)
    const translatedQuery = t("search.query", query).toLowerCase();
    return ALL_SETTINGS_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(lowerQuery) ||
        item.category.toLowerCase().includes(lowerQuery) ||
        item.description?.toLowerCase().includes(lowerQuery) ||
        translatedQuery.includes(lowerQuery),
    );
  }, [query, t]);

  const handleSelectItem = React.useCallback(
    (item: SettingsSearchItem) => {
      navigate(item.path);
      setIsOpen(false);
      setQuery("");
      setSelectedIndex(0);
      onNavigate?.();
    },
    [navigate, onNavigate],
  );

  const handleSelectByIndex = React.useCallback(
    (index: number) => {
      if (filteredItems[index]) {
        handleSelectItem(filteredItems[index]);
      }
    },
    [filteredItems, handleSelectItem],
  );

  const handleClose = React.useCallback(() => {
    setQuery("");
    setSelectedIndex(0);
  }, []);

  // Use shared keyboard shortcuts hook
  useSearchKeyboardShortcuts({
    isOpen,
    setIsOpen,
    inputRef,
    selectedIndex,
    setSelectedIndex,
    results: filteredItems,
    onSelect: handleSelectByIndex,
    onClose: handleClose,
    shouldOpen: () => location.pathname === "/settings",
    variant,
  });

  // Focus input when opened
  useEffect(() => {
    if (isOpen && variant === "button") {
      inputRef.current?.focus();
    }
  }, [isOpen, variant]);

  if (variant === "button") {
    return (
      <>
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-black/60 text-white/70 hover:text-white hover:bg-white/5 transition-all text-sm"
        >
          <Search className="w-4 h-4" />
          <span>Search settings...</span>
          <kbd className="ml-auto px-1.5 py-0.5 text-xs bg-white/10 rounded">
            ⌘K
          </kbd>
        </button>

        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
              onClick={() => setIsOpen(false)}
            />
            <div
              ref={dropdownRef}
              className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 bg-black/95 border border-white/10 rounded-xl shadow-2xl overflow-hidden"
            >
              <div className="p-4 border-b border-white/10">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Search settings..."
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setSelectedIndex(0);
                    }}
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                  />
                </div>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {filteredItems.length > 0 ? (
                  filteredItems.map((item, index) => (
                    <button
                      type="button"
                      key={item.path}
                      onClick={() => handleSelectItem(item)}
                      className={cn(
                        "w-full flex items-start gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left",
                        index === selectedIndex && "bg-white/5",
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white">
                          {item.label}
                        </div>
                        <div className="text-xs text-white/50 mt-0.5">
                          {item.category}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-white/30 flex-shrink-0 mt-0.5" />
                    </button>
                  ))
                ) : (
                  <div className="px-4 py-8 text-center text-white/50 text-sm">
                    No settings found matching "{query}"
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </>
    );
  }

  // Inline variant
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40" />
      <input
        ref={inputRef}
        type="text"
        placeholder="Search settings... (⌘K)"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setSelectedIndex(0);
        }}
        onFocus={() => setIsOpen(true)}
        className="w-full pl-10 pr-4 py-2.5 bg-black/60 border border-white/10 rounded-xl text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all"
      />

      {isOpen && query && filteredItems.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-2 bg-black/95 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 max-h-96 overflow-y-auto"
        >
          {filteredItems.map((item, index) => (
            <button
              type="button"
              key={item.path}
              onClick={() => handleSelectItem(item)}
              className={cn(
                "w-full flex items-start gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left",
                index === selectedIndex && "bg-white/5",
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white">
                  {item.label}
                </div>
                <div className="text-xs text-white/50 mt-0.5">
                  {item.category}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-white/30 flex-shrink-0 mt-0.5" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
