import { useMemo, useState } from "react";
import { NavLink, Outlet, redirect } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Keyboard, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "#/utils/utils";
import { KeyboardShortcutsPanel } from "#/components/features/chat/keyboard-shortcuts-panel";
import { useConfig } from "#/hooks/query/use-config";
import { Route } from "./+types/settings";
import Forge from "#/api/forge";
import { queryClient } from "#/query-client-config";
import { GetConfigResponse } from "#/api/forge.types";
import { I18nKey } from "#/i18n/declaration";
import {
  getSettingsCategories,
  type SettingsNavContext,
} from "#/config/settings-nav";

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

  // Redirect /settings to /settings/app
  if (pathname === "/settings") {
    return redirect("/settings/app");
  }

  return null;
};

function SettingsSidebarLink({
  item,
  collapsed,
}: {
  item: {
    path: string;
    labelKey: I18nKey;
    icon: React.ComponentType<{ className?: string }>;
  };
  collapsed: boolean;
}) {
  const { t } = useTranslation();
  const Icon = item.icon;
  const label = t(item.labelKey);

  return (
    <NavLink
      to={item.path}
      end
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium",
          "transition-all duration-200",
          collapsed && "justify-center",
          isActive
            ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
            : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
        )
      }
    >
      <Icon className="h-4 w-4 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </NavLink>
  );
}

function SettingsSidebar({
  navGroups,
  onOpenShortcuts,
  collapsed,
  onToggleCollapse,
}: {
  navGroups: ReturnType<typeof getSettingsCategories>;
  onOpenShortcuts?: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div
      className={cn(
        "flex-shrink-0 transition-all duration-300 ease-in-out border-r border-[var(--border-primary)]",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="h-full flex flex-col bg-[var(--bg-elevated)]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 pb-4 border-b border-[var(--border-primary)]">
          {!collapsed && (
            <div>
              <h1 className="text-xl font-bold text-[var(--text-primary)] mb-1">
                {t(I18nKey.SETTINGS$TITLE)}
              </h1>
              <p className="text-xs text-[var(--text-tertiary)]">
                {t("settings.description", "Configure your preferences")}
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={onToggleCollapse}
            className={cn(
              "p-2 rounded-lg transition-all duration-200",
              "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
              collapsed && "mx-auto",
            )}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Scrollable Navigation */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden space-y-6 p-4 pt-4">
          {navGroups.map((group) => (
            <div key={group.id} className="space-y-2">
              {!collapsed && (
                <div className="flex items-center gap-2 px-3 mb-2">
                  <group.icon className="h-4 w-4 text-[var(--text-tertiary)]" />
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                    {group.title}
                  </h2>
                </div>
              )}
              {collapsed && (
                <div className="flex justify-center mb-2">
                  <group.icon className="h-4 w-4 text-[var(--text-tertiary)]" />
                </div>
              )}
              <div className="space-y-1">
                {group.items.map((item) => {
                  return (
                    <SettingsSidebarLink
                      key={item.path}
                      item={item}
                      collapsed={collapsed}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer */}
        {onOpenShortcuts && (
          <div className="p-4 pt-4 border-t border-[var(--border-primary)]">
            <button
              type="button"
              onClick={onOpenShortcuts}
              title={
                collapsed
                  ? t("chat.keyboardShortcuts", "Keyboard Shortcuts")
                  : undefined
              }
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium",
                "transition-all duration-200 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]",
                collapsed && "justify-center",
              )}
            >
              <Keyboard className="h-4 w-4 flex-shrink-0" />
              {!collapsed && (
                <span>{t("chat.keyboardShortcuts", "Keyboard Shortcuts")}</span>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SettingsScreen() {
  const { data: config } = useConfig();
  const [showShortcutsPanel, setShowShortcutsPanel] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const navContext = useMemo<SettingsNavContext>(
    () => ({
      mode: "oss",
    }),
    [],
  );

  const navGroups = useMemo(
    () => getSettingsCategories(navContext),
    [navContext],
  );

  return (
    <div className="h-screen w-full bg-[var(--bg-primary)] flex flex-col overflow-hidden">
      <div className="flex-1 flex overflow-hidden">
        <SettingsSidebar
          navGroups={navGroups}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onOpenShortcuts={() => setShowShortcutsPanel(true)}
        />
        <div className="flex-1 min-w-0 overflow-y-auto p-6">
          <div className="max-w-[1400px] mx-auto">
            <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-2xl p-6">
              <Outlet />
            </div>
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Panel */}
      <KeyboardShortcutsPanel
        isOpen={showShortcutsPanel}
        onClose={() => setShowShortcutsPanel(false)}
      />
    </div>
  );
}

export default SettingsScreen;
