import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronRight, Home } from "lucide-react";

// Map of settings paths to their display labels
const SETTINGS_PATH_MAP: Record<string, string> = {
  "/settings": "Settings",
  "/settings/user": "SETTINGS$NAV_USER",
  "/settings/billing": "SETTINGS$NAV_CREDITS",
  "/settings/app": "SETTINGS$NAV_APPLICATION",
  "/settings/llm": "SETTINGS$NAV_LLM",
  "/settings/mcp": "SETTINGS$NAV_MCP",
  "/settings/prompts": "SETTINGS$NAV_PROMPTS",
  "/settings/memory": "SETTINGS$NAV_MEMORY",
  "/settings/integrations": "SETTINGS$NAV_INTEGRATIONS",
  "/settings/slack": "SETTINGS$NAV_SLACK",
  "/settings/databases": "SETTINGS$NAV_DATABASES",
  "/settings/knowledge-base": "Knowledge Base",
  "/settings/backup": "SETTINGS$NAV_BACKUP",
  "/settings/snippets": "SETTINGS$NAV_SNIPPETS",
  "/settings/secrets": "SETTINGS$NAV_SECRETS",
  "/settings/api-keys": "SETTINGS$NAV_API_KEYS",
  "/settings/analytics": "SETTINGS$NAV_ANALYTICS",
};

export function SettingsBreadcrumbs() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleBreadcrumbClick = (path: string) => {
    navigate(path);
  };

  // Get the current page label
  const currentPageLabel = React.useMemo(() => {
    const currentPath = location.pathname;
    const label =
      SETTINGS_PATH_MAP[currentPath] ||
      currentPath.split("/").pop() ||
      "Settings";
    return label && label.startsWith("SETTINGS$") ? t(label) : label;
  }, [location.pathname, t]);

  // Don't show breadcrumbs on the hub page
  if (location.pathname === "/settings") {
    return null;
  }

  return (
    <nav
      className="flex items-center gap-2 text-sm mb-4"
      aria-label="Breadcrumb"
    >
      <ol className="flex items-center gap-2 flex-wrap">
        {/* Settings (Home) */}
        <li className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleBreadcrumbClick("/settings")}
            className="flex items-center gap-1.5 transition-colors hover:text-white text-white/70"
          >
            <Home className="w-4 h-4" />
            <span>Settings</span>
          </button>
        </li>

        {/* Current Page */}
        <li className="flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-white/30 flex-shrink-0" />
          <span className="font-medium text-white">{currentPageLabel}</span>
        </li>
      </ol>
    </nav>
  );
}
