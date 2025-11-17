import { useMemo, useState } from "react";
import { NavLink, Outlet, redirect, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  User,
  Plug,
  Database,
  Brain,
  BarChart3,
  FileText,
  Code,
  MessageSquare,
  Download,
  Settings,
  CreditCard,
  Key,
  Workflow,
  Bot,
  Menu,
  ArrowLeft,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { useConfig } from "#/hooks/query/use-config";
import { Route } from "./+types/settings";
import Forge from "#/api/forge";
import { queryClient } from "#/query-client-config";
import { GetConfigResponse } from "#/api/forge.types";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";
import { Button } from "#/components/ui/button";
import AnimatedBackground from "#/components/landing/AnimatedBackground";

const SAAS_ONLY_PATHS = [
  "/settings/user",
  "/settings/billing",
  "/settings/credits",
  "/settings/api-keys",
];

const SAAS_NAV_GROUPS = [
  {
    title: "Account",
    items: [
      { to: "/settings/user", text: "SETTINGS$NAV_USER", icon: User },
      {
        to: "/settings/billing",
        text: "SETTINGS$NAV_CREDITS",
        icon: CreditCard,
      },
      { to: "/settings/app", text: "SETTINGS$NAV_APPLICATION", icon: Settings },
    ],
  },
  {
    title: "AI & Models",
    items: [
      {
        to: "/settings",
        text: "SETTINGS$NAV_LLM",
        icon: Bot,
        requiresPro: true,
      },
      { to: "/settings/mcp", text: "SETTINGS$NAV_MCP", icon: Workflow },
      { to: "/settings/prompts", text: "SETTINGS$NAV_PROMPTS", icon: FileText },
      { to: "/settings/memory", text: "SETTINGS$NAV_MEMORY", icon: Brain },
    ],
  },
  {
    title: "Integrations",
    items: [
      {
        to: "/settings/integrations",
        text: "SETTINGS$NAV_INTEGRATIONS",
        icon: Plug,
      },
      {
        to: "/settings/slack",
        text: "SETTINGS$NAV_SLACK",
        icon: MessageSquare,
      },
    ],
  },
  {
    title: "Data & Storage",
    items: [
      {
        to: "/settings/databases",
        text: "SETTINGS$NAV_DATABASES",
        icon: Database,
      },
      { to: "/settings/knowledge-base", text: "Knowledge Base", icon: Brain },
      { to: "/settings/backup", text: "SETTINGS$NAV_BACKUP", icon: Download },
    ],
  },
  {
    title: "Development",
    items: [
      { to: "/settings/snippets", text: "SETTINGS$NAV_SNIPPETS", icon: Code },
      { to: "/settings/secrets", text: "SETTINGS$NAV_SECRETS", icon: Key },
      { to: "/settings/api-keys", text: "SETTINGS$NAV_API_KEYS", icon: Key },
    ],
  },
  {
    title: "Analytics",
    items: [
      {
        to: "/settings/analytics",
        text: "SETTINGS$NAV_ANALYTICS",
        icon: BarChart3,
      },
    ],
  },
];

const OSS_NAV_GROUPS = [
  {
    title: "AI & Models",
    items: [
      { to: "/settings", text: "SETTINGS$NAV_LLM", icon: Bot },
      { to: "/settings/mcp", text: "SETTINGS$NAV_MCP", icon: Workflow },
      { to: "/settings/prompts", text: "SETTINGS$NAV_PROMPTS", icon: FileText },
      { to: "/settings/memory", text: "SETTINGS$NAV_MEMORY", icon: Brain },
    ],
  },
  {
    title: "Integrations",
    items: [
      {
        to: "/settings/integrations",
        text: "SETTINGS$NAV_INTEGRATIONS",
        icon: Plug,
      },
    ],
  },
  {
    title: "Data & Storage",
    items: [
      {
        to: "/settings/databases",
        text: "SETTINGS$NAV_DATABASES",
        icon: Database,
      },
      {
        to: "/settings/knowledge-base",
        text: "Knowledge Base",
        icon: Database,
      },
      { to: "/settings/backup", text: "SETTINGS$NAV_BACKUP", icon: Download },
    ],
  },
  {
    title: "Development",
    items: [
      { to: "/settings/snippets", text: "SETTINGS$NAV_SNIPPETS", icon: Code },
      { to: "/settings/secrets", text: "SETTINGS$NAV_SECRETS", icon: Key },
    ],
  },
  {
    title: "System",
    items: [
      { to: "/settings/app", text: "SETTINGS$NAV_APPLICATION", icon: Settings },
      {
        to: "/settings/analytics",
        text: "SETTINGS$NAV_ANALYTICS",
        icon: BarChart3,
      },
    ],
  },
];

export const clientLoader = async (args: Route.ClientLoaderArgs) => {
  if (!args || !args.request) {
    return null;
  }
  const url = new URL(args.request.url);
  const { pathname } = url;

  let config = queryClient.getQueryData<GetConfigResponse>(["config"]);
  if (!config) {
    config = await Forge.getConfig();
    queryClient.setQueryData<GetConfigResponse>(["config"], config);
  }

  const isSaas = config?.APP_MODE === "saas";

  if (isSaas && pathname === "/settings") {
    return redirect("/settings/user");
  }

  if (!isSaas && SAAS_ONLY_PATHS.includes(pathname)) {
    return redirect("/settings");
  }

  return null;
};

interface NavItem {
  to: string;
  text: string;
  icon: React.ComponentType<{ className?: string }>;
  requiresPro?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

function SettingsSidebar({ groups }: { groups: NavGroup[] }) {
  const { t } = useTranslation();

  return (
    <aside className="w-[280px] flex-shrink-0">
      <div className="sticky top-28 space-y-8">
        {groups.map((group) => (
          <div key={group.title} className="space-y-3">
            <h3 className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-foreground-tertiary">
              {group.title}
            </h3>
            <nav className="space-y-1">
              {group.items.map(({ to, text, icon: Icon }) => (
                <NavLink
                  end
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-gradient-to-r from-brand-500/20 to-brand-600/20 border border-brand-500/30 text-foreground shadow-lg shadow-brand-500/10"
                        : "text-foreground-secondary hover:text-foreground hover:bg-white/5",
                    )
                  }
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-foreground-tertiary" />
                  <span>{t(text)}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        ))}
      </div>
    </aside>
  );
}

function MobileNavigation({ groups }: { groups: NavGroup[] }) {
  const { t } = useTranslation();

  return (
    <div className="mb-6 md:hidden">
      <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/60 p-4 backdrop-blur-xl">
        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.title} className="space-y-2">
              <h3 className="px-2 text-xs font-semibold uppercase tracking-[0.2em] text-foreground-tertiary">
                {group.title}
              </h3>
              <div className="flex flex-wrap gap-2">
                {group.items.map(({ to, text, icon: Icon }) => (
                  <NavLink
                    end
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      cn(
                        "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200",
                        isActive
                          ? "bg-white text-black"
                          : "border border-white/10 bg-white/5 text-foreground-secondary hover:text-foreground hover:bg-white/10",
                      )
                    }
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{t(text)}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SettingsScreen() {
  const { t } = useTranslation();
  const { data: config } = useConfig();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const isSaas = config?.APP_MODE === "saas";
  const navGroups = useMemo(() => {
    const groups = (isSaas ? SAAS_NAV_GROUPS : OSS_NAV_GROUPS) as NavGroup[];
    return groups
      .map((group) => ({
        ...group,
        items: group.items.filter(
          (item) => !item.requiresPro || subscriptionAccess,
        ),
      }))
      .filter((group) => group.items.length > 0);
  }, [isSaas, subscriptionAccess]);

  return (
    <main
      data-testid="settings-screen"
      className="relative min-h-screen overflow-hidden bg-black text-foreground"
    >
      <div aria-hidden className="pointer-events-none">
        <AnimatedBackground />
      </div>
      {/* Main Content */}
      <div className="relative z-[1] mx-auto max-w-7xl px-6 py-6">
        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          {/* Desktop Sidebar - Always visible on desktop */}
          <aside className="hidden md:block w-[280px] flex-shrink-0">
            <SettingsSidebar groups={navGroups} />
          </aside>

          {/* Mobile Sidebar - Toggleable */}
          {sidebarOpen && (
            <aside className="md:hidden fixed inset-y-0 left-0 z-50 w-[280px] bg-black/95 backdrop-blur-xl border-r border-white/10 overflow-y-auto">
              <SettingsSidebar groups={navGroups} />
            </aside>
          )}

          {/* Content Area */}
          <div className="flex-1 min-w-0">
            {/* Header - Always visible */}
            <div className="mb-4 flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="rounded-xl border border-white/10 bg-black/60 p-2 text-foreground-secondary hover:bg-white/5 hover:text-foreground transition-all"
                aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
              >
                <Menu className="h-4 w-4" />
              </button>
              <Button
                variant="outline"
                onClick={() => navigate("/")}
                className="ml-auto border border-white/20 bg-transparent text-foreground hover:bg-white/10 text-xs h-8 px-3"
              >
                <ArrowLeft className="mr-1.5 h-3 w-3" />
                Back
              </Button>
            </div>

            {/* Mobile Navigation - Hidden on desktop, shown when sidebar is hidden */}
            {!sidebarOpen && (
              <div className="mb-6 md:hidden">
                <MobileNavigation groups={navGroups} />
              </div>
            )}

            {/* Settings Content */}
            <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl">
              <Outlet />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default SettingsScreen;
