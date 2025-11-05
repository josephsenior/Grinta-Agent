import { useMemo } from "react";
import { NavLink, Outlet, redirect, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronLeft } from "#/assets/chevron-left";
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
} from "lucide-react";
import { cn } from "#/utils/utils";
import { useConfig } from "#/hooks/query/use-config";
import { I18nKey } from "#/i18n/declaration";
import { Route } from "./+types/settings";
import OpenHands from "#/api/open-hands";
import { queryClient } from "#/query-client-config";
import { GetConfigResponse } from "#/api/open-hands.types";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";

const SAAS_ONLY_PATHS = [
  "/settings/user",
  "/settings/billing",
  "/settings/credits",
  "/settings/api-keys",
];

const SAAS_NAV_ITEMS = [
  { to: "/settings/user", text: "SETTINGS$NAV_USER", icon: User },
  { to: "/settings/integrations", text: "SETTINGS$NAV_INTEGRATIONS", icon: Plug },
  { to: "/settings/databases", text: "SETTINGS$NAV_DATABASES", icon: Database },
  { to: "/settings/knowledge-base", text: "Knowledge Base", icon: Brain },
  { to: "/settings/memory", text: "SETTINGS$NAV_MEMORY", icon: Brain },
  { to: "/settings/analytics", text: "SETTINGS$NAV_ANALYTICS", icon: BarChart3 },
  { to: "/settings/prompts", text: "SETTINGS$NAV_PROMPTS", icon: FileText },
  { to: "/settings/snippets", text: "SETTINGS$NAV_SNIPPETS", icon: Code },
  { to: "/settings/slack", text: "SETTINGS$NAV_SLACK", icon: MessageSquare },
  { to: "/settings/backup", text: "SETTINGS$NAV_BACKUP", icon: Download },
  { to: "/settings/app", text: "SETTINGS$NAV_APPLICATION", icon: Settings },
  { to: "/settings/billing", text: "SETTINGS$NAV_CREDITS", icon: CreditCard },
  { to: "/settings/secrets", text: "SETTINGS$NAV_SECRETS", icon: Key },
  { to: "/settings/api-keys", text: "SETTINGS$NAV_API_KEYS", icon: Key },
  { to: "/settings/mcp", text: "SETTINGS$NAV_MCP", icon: Workflow },
];

const OSS_NAV_ITEMS = [
  { to: "/settings", text: "SETTINGS$NAV_LLM", icon: Bot },
  { to: "/settings/mcp", text: "SETTINGS$NAV_MCP", icon: Workflow },
  { to: "/settings/integrations", text: "SETTINGS$NAV_INTEGRATIONS", icon: Plug },
  { to: "/settings/databases", text: "SETTINGS$NAV_DATABASES", icon: Database },
  { to: "/settings/knowledge-base", text: "Knowledge Base", icon: Database },
  { to: "/settings/memory", text: "SETTINGS$NAV_MEMORY", icon: Brain },
  { to: "/settings/analytics", text: "SETTINGS$NAV_ANALYTICS", icon: BarChart3 },
  { to: "/settings/prompts", text: "SETTINGS$NAV_PROMPTS", icon: FileText },
  { to: "/settings/snippets", text: "SETTINGS$NAV_SNIPPETS", icon: Code },
  { to: "/settings/backup", text: "SETTINGS$NAV_BACKUP", icon: Download },
  { to: "/settings/app", text: "SETTINGS$NAV_APPLICATION", icon: Settings },
  { to: "/settings/secrets", text: "SETTINGS$NAV_SECRETS", icon: Key },
];

export const clientLoader = async (args: Route.ClientLoaderArgs) => {
  if (!args || !args.request) {
    return null;
  }
  const url = new URL(args.request.url);
  const { pathname } = url;

  let config = queryClient.getQueryData<GetConfigResponse>(["config"]);
  if (!config) {
    config = await OpenHands.getConfig();
    queryClient.setQueryData<GetConfigResponse>(["config"], config);
  }

  const isSaas = config?.APP_MODE === "saas";

  if (isSaas && pathname === "/settings") {
    // no llm settings in saas mode, so redirect to user settings
    return redirect("/settings/user");
  }

  if (!isSaas && SAAS_ONLY_PATHS.includes(pathname)) {
    // if in OSS mode, do not allow access to saas-only paths
    return redirect("/settings");
  }

  return null;
};

function SettingsScreen() {
  const { t } = useTranslation();
  const { data: config } = useConfig();
  const { data: subscriptionAccess } = useSubscriptionAccess();
  const navigate = useNavigate();

  const isSaas = config?.APP_MODE === "saas";
  // this is used to determine which settings are available in the UI
  const navItems = useMemo(() => {
    const items = [];
    if (isSaas) {
      if (subscriptionAccess) {
        items.push({ to: "/settings", text: "SETTINGS$NAV_LLM", icon: Bot });
      }
      items.push(...SAAS_NAV_ITEMS);
    } else {
      items.push(...OSS_NAV_ITEMS);
    }
    return items;
  }, [isSaas, !!subscriptionAccess]);

  return (
    <main
      data-testid="settings-screen"
      className="flex flex-col h-full bg-background-primary"
    >
      {/* Fixed header with proper spacing */}
      <div className="flex-shrink-0 px-6 pt-6 pb-4 bg-background-primary border-b border-border">
        <div className="flex items-center gap-4">
          <button
            type="button"
            aria-label="Go back to home"
            onClick={() => navigate("/")}
            className="p-2 rounded-lg hover:bg-background-tertiary transition-colors duration-200"
          >
            <ChevronLeft width={18} height={18} />
          </button>
          <h1
            data-testid="page-title"
            className="text-xl font-semibold text-foreground"
          >
            {t(I18nKey.SETTINGS$TITLE)}
          </h1>
        </div>

        {/* Settings navigation tabs */}
        <div className="mt-6">
          <nav className="flex items-center gap-1 overflow-x-auto">
            {navItems.map(({ to, text, icon: Icon }) => (
              <NavLink
                end
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap flex items-center gap-2",
                    isActive 
                      ? "bg-brand-500 text-white shadow-sm" 
                      : "text-foreground-secondary hover:text-foreground hover:bg-background-tertiary"
                  )
                }
              >
                {Icon && <Icon className="w-4 h-4" />}
                {t(text)}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-auto">
        <Outlet />
      </div>
    </main>
  );
}

export default SettingsScreen;
