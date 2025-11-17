import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  User,
  Bell,
  HelpCircle,
  BarChart3,
  CreditCard,
  Key,
  Database,
  Brain,
  Code,
  FileText,
  Workflow,
  Bot,
  Plug,
  Download,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { useConfig } from "#/hooks/query/use-config";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  requiresPro?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export function AppNavigation() {
  const location = useLocation();
  const { data: config } = useConfig();
  const { data: subscriptionAccess } = useSubscriptionAccess();

  const isSaas = config?.APP_MODE === "saas";
  const hasPro = subscriptionAccess?.status === "ACTIVE";

  const navGroups: NavGroup[] = [
    {
      title: "Main",
      items: [
        { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { to: "/conversations", label: "Conversations", icon: MessageSquare },
        { to: "/profile", label: "Profile", icon: User },
        { to: "/notifications", label: "Notifications", icon: Bell },
        { to: "/help", label: "Help & Support", icon: HelpCircle },
      ],
    },
    {
      title: "Settings",
      items: [
        {
          to: "/settings",
          label: "LLM Settings",
          icon: Bot,
          requiresPro: true,
        },
        { to: "/settings/mcp", label: "MCP", icon: Workflow },
        { to: "/settings/prompts", label: "Prompts", icon: FileText },
        { to: "/settings/memory", label: "Memory", icon: Brain },
        { to: "/settings/analytics", label: "Analytics", icon: BarChart3 },
      ],
    },
    ...(isSaas
      ? [
          {
            title: "Account",
            items: [
              { to: "/settings/user", label: "User Settings", icon: User },
              { to: "/settings/billing", label: "Billing", icon: CreditCard },
              { to: "/settings/api-keys", label: "API Keys", icon: Key },
            ],
          } as NavGroup,
        ]
      : []),
    {
      title: "Data & Tools",
      items: [
        { to: "/settings/databases", label: "Databases", icon: Database },
        { to: "/settings/snippets", label: "Code Snippets", icon: Code },
        { to: "/settings/integrations", label: "Integrations", icon: Plug },
        { to: "/settings/backup", label: "Backup & Restore", icon: Download },
      ],
    },
  ];

  // Filter out pro-only items if user doesn't have pro
  const filteredGroups = navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.requiresPro || hasPro),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <div className="sticky top-28 space-y-8">
      {filteredGroups.map((group) => (
        <div key={group.title} className="space-y-3">
          <h3 className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-foreground-tertiary">
            {group.title}
          </h3>
          <nav className="space-y-1">
            {group.items.map(({ to, label, icon: Icon }) => {
              const isActive =
                location.pathname === to ||
                (to !== "/dashboard" && location.pathname.startsWith(to));
              return (
                <NavLink
                  key={to}
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-white/10 border border-white/20 text-foreground"
                      : "text-foreground-secondary hover:text-foreground hover:bg-white/5",
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-foreground-tertiary" />
                  <span>{label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      ))}
    </div>
  );
}
