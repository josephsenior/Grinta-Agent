import React, { useMemo, useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  Workflow,
  FileText,
  Brain,
  User,
  CreditCard,
  Key,
  Settings,
  Plug,
  GitBranch,
  MessageCircle,
  Database,
  BookOpen,
  Download,
  Code,
  Lock,
  BarChart3,
  Search,
  ArrowRight,
  Keyboard,
} from "lucide-react";
import { gsap } from "gsap";
import { useConfig } from "#/hooks/query/use-config";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { KeyboardShortcutsPanel } from "#/components/features/chat/keyboard-shortcuts-panel";
import {
  useGSAPFadeIn,
  useGSAPHover,
  useGSAPScale,
} from "#/hooks/use-gsap-animations";

interface SettingsItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  requiresPro?: boolean;
  saasOnly?: boolean;
  ossOnly?: boolean;
  action?: () => void;
}

interface SettingsCategory {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  items: SettingsItem[];
}

// Settings Category Card Component with GSAP animations
function SettingsCategoryCard({
  category,
  onItemClick,
}: {
  category: SettingsCategory;
  onItemClick: (item: SettingsItem) => void;
}) {
  const Icon = category.icon;
  const cardRef = useGSAPHover<HTMLDivElement>({
    scale: 1.02,
    y: -4,
    duration: 0.3,
  });

  return (
    <div
      ref={cardRef}
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 backdrop-blur-xl p-6 shadow-[0_40px_120px_rgba(0,0,0,0.45)] hover:border-brand-500/30 transition-all duration-300"
    >
      {/* Background gradient effect */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
      >
        <div className="absolute inset-y-0 left-1/2 w-1/2 bg-gradient-to-r from-brand-500/5 via-accent-500/3 to-transparent blur-2xl" />
      </div>

      <div className="relative z-[1] space-y-4">
        {/* Category Header */}
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-white/5 border border-white/10 group-hover:bg-brand-500/10 group-hover:border-brand-500/30 transition-all">
            <Icon className="h-5 w-5 text-white/70 group-hover:text-brand-400 transition-colors" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-white mb-1">
              {category.title}
            </h2>
            <p className="text-xs text-white/50 leading-relaxed">
              {category.description}
            </p>
          </div>
        </div>

        {/* Category Items */}
        <div className="space-y-1.5">
          {category.items.map((item) => {
            const ItemIcon = item.icon;
            return (
              <button
                key={item.to}
                type="button"
                onClick={() => onItemClick(item)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-white/70 hover:text-white hover:bg-white/5 transition-all duration-200 group/item"
              >
                <ItemIcon className="h-4 w-4 flex-shrink-0 text-white/50 group-hover/item:text-brand-400 transition-colors" />
                <span className="flex-1 text-left">{item.label}</span>
                <ArrowRight className="h-4 w-4 opacity-0 group-hover/item:opacity-100 transition-opacity text-white/40" />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function SettingsHub() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const [searchQuery, setSearchQuery] = useState("");
  const [showShortcutsPanel, setShowShortcutsPanel] = useState(false);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // GSAP animation refs
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.1,
    duration: 0.6,
  });
  const cardsContainerRef = useRef<HTMLDivElement>(null);
  const emptyStateRef = useGSAPScale<HTMLDivElement>({
    delay: 0.1,
    duration: 0.5,
    autoPlay: false,
  });

  const isSaas = config?.APP_MODE === "saas";
  const hasPro = subscriptionAccess?.status === "ACTIVE";

  const allCategories: SettingsCategory[] = useMemo(
    () => [
      {
        id: "ai-models",
        title: "AI & Models",
        description: "Configure AI models, MCP servers, prompts, and memory",
        icon: Bot,
        items: [
          {
            to: "/settings/llm",
            label: "LLM Settings",
            icon: Bot,
            requiresPro: false,
          },
          { to: "/settings/mcp", label: "MCP", icon: Workflow },
          { to: "/settings/prompts", label: "Prompts", icon: FileText },
          { to: "/settings/memory", label: "Memory", icon: Brain },
        ],
      },
      {
        id: "account",
        title: "Account",
        description: "Manage your profile, billing, and account settings",
        icon: User,
        items: [
          {
            to: "/settings/user",
            label: "User Settings",
            icon: User,
            saasOnly: true,
          },
          {
            to: "/settings/billing",
            label: "Billing",
            icon: CreditCard,
            saasOnly: true,
          },
          {
            to: "/settings/api-keys",
            label: "API Keys",
            icon: Key,
            saasOnly: true,
          },
          {
            to: "/settings/app",
            label: "Application",
            icon: Settings,
          },
        ],
      },
      {
        id: "integrations",
        title: "Integrations",
        description: "Connect external services and tools",
        icon: Plug,
        items: [
          {
            to: "/settings/integrations",
            label: "Git Integration",
            icon: GitBranch,
          },
          { to: "/settings/slack", label: "Slack", icon: MessageCircle },
        ],
      },
      {
        id: "data-storage",
        title: "Data & Storage",
        description: "Manage databases, knowledge base, and backups",
        icon: Database,
        items: [
          { to: "/settings/databases", label: "Databases", icon: Database },
          {
            to: "/settings/knowledge-base",
            label: "Knowledge Base",
            icon: BookOpen,
          },
          {
            to: "/settings/backup",
            label: "Backup & Restore",
            icon: Download,
          },
        ],
      },
      {
        id: "development",
        title: "Development",
        description: "Code snippets, secrets, and development tools",
        icon: Code,
        items: [
          { to: "/settings/snippets", label: "Code Snippets", icon: Code },
          { to: "/settings/secrets", label: "Secrets", icon: Lock },
          {
            to: "/settings/api-keys",
            label: "API Keys",
            icon: Key,
            ossOnly: true,
          },
        ],
      },
      {
        id: "analytics",
        title: "Analytics",
        description: "Usage statistics, costs, and performance metrics",
        icon: BarChart3,
        items: [
          { to: "/settings/analytics", label: "Analytics", icon: BarChart3 },
        ],
      },
      {
        id: "keyboard-shortcuts",
        title: "Keyboard Shortcuts",
        description: "View and learn all available keyboard shortcuts",
        icon: Keyboard,
        items: [
          {
            to: "#",
            label: "View Shortcuts",
            icon: Keyboard,
            action: () => setShowShortcutsPanel(true),
          },
        ],
      },
    ],
    [],
  );

  // Filter categories and items based on mode and access
  const filteredCategories = useMemo(
    () =>
      allCategories
        .map((category) => ({
          ...category,
          items: category.items.filter((item) => {
            // Filter by SaaS/OSS mode
            if (item.saasOnly && !isSaas) return false;
            if (item.ossOnly && isSaas) return false;

            // Filter by Pro access
            if (item.requiresPro && !hasPro) return false;

            // Filter by search query
            if (searchQuery) {
              const query = searchQuery.toLowerCase();
              return (
                item.label.toLowerCase().includes(query) ||
                category.title.toLowerCase().includes(query) ||
                category.description.toLowerCase().includes(query)
              );
            }

            return true;
          }),
        }))
        .filter((category) => category.items.length > 0),
    [allCategories, isSaas, hasPro, searchQuery],
  );

  // Animate cards on mount and when search results change
  useEffect(() => {
    if (!cardsContainerRef.current) return;

    const cards = Array.from(
      cardsContainerRef.current.children,
    ) as HTMLElement[];
    if (cards.length === 0) {
      // Show empty state animation
      if (emptyStateRef.current) {
        gsap.fromTo(
          emptyStateRef.current,
          { opacity: 0, scale: 0.9 },
          { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.2)" },
        );
      }
      return;
    }

    // Hide empty state
    if (emptyStateRef.current) {
      gsap.set(emptyStateRef.current, { opacity: 0, scale: 0.9 });
    }

    // Animate cards with stagger
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      gsap.set(cards, { opacity: 1, y: 0 });
      return;
    }

    gsap.set(cards, { opacity: 0, y: 30 });
    gsap.to(cards, {
      opacity: 1,
      y: 0,
      duration: 0.6,
      stagger: 0.08,
      ease: "power3.out",
      delay: 0.1,
    });
  }, [filteredCategories, searchQuery, emptyStateRef]);

  const handleItemClick = (item: SettingsItem) => {
    if (item.action) {
      item.action();
    } else {
      navigate(item.to);
    }
  };

  // Keyboard shortcut to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        const target = e.target as HTMLElement;
        if (
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable
        ) {
          return;
        }
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="p-6 sm:p-8 lg:p-10">
      <div className="mx-auto max-w-7xl w-full space-y-8">
        {/* Header */}
        <div ref={headerRef} className="space-y-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              {t("settings.title", "Settings")}
            </h1>
            <p className="text-white/60 text-sm">
              {t(
                "settings.description",
                "Manage your account, preferences, and integrations",
              )}
            </p>
          </div>

          {/* Search Bar */}
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder={t(
                "settings.searchPlaceholder",
                "Search settings... (⌘K)",
              )}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-black/60 border border-white/10 rounded-xl text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all"
            />
          </div>
        </div>

        {/* Settings Categories Grid */}
        <div
          ref={cardsContainerRef}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {filteredCategories.map((category) => (
            <SettingsCategoryCard
              key={category.id}
              category={category}
              onItemClick={handleItemClick}
            />
          ))}
        </div>

        {/* Empty State */}
        {filteredCategories.length === 0 && (
          <div ref={emptyStateRef} className="text-center py-12">
            <Search className="h-12 w-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 text-sm">
              {t(
                "settings.noSettingsFound",
                'No settings found matching "{{query}}"',
                {
                  query: searchQuery,
                },
              )}
            </p>
          </div>
        )}
      </div>

      {/* Keyboard Shortcuts Panel */}
      <KeyboardShortcutsPanel
        isOpen={showShortcutsPanel}
        onClose={() => setShowShortcutsPanel(false)}
      />
    </div>
  );
}
