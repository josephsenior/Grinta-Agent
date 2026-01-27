import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  MessageSquare,
  HelpCircle,
  Settings,
} from "lucide-react";
import { cn } from "#/utils/utils";
import { I18nKey } from "#/i18n/declaration";

interface NavItem {
  to: string;
  labelKey: I18nKey;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavGroup {
  titleKey: I18nKey;
  items: NavItem[];
}

export function AppNavigation() {
  const location = useLocation();
  const { t } = useTranslation();

  // Simplified navigation - all settings consolidated under single entry
  const navGroups: NavGroup[] = [
    {
      titleKey: I18nKey.NAVIGATION$GROUP_MAIN,
      items: [
        {
          to: "/conversations",
          labelKey: I18nKey.NAVIGATION$ITEM_CONVERSATIONS,
          icon: MessageSquare,
        },
      ],
    },
    {
      titleKey: I18nKey.SETTINGS$TITLE,
      items: [
        {
          to: "/settings/app",
          labelKey: I18nKey.SETTINGS$TITLE,
          icon: Settings,
        },
      ],
    },
  ];

  return (
    <div className="space-y-8">
      {navGroups.map((group) => (
        <div key={group.titleKey} className="space-y-3">
          <h3 className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-white/50">
            {t(group.titleKey)}
          </h3>
          <nav className="space-y-1">
            {group.items.map(({ to, labelKey, icon: Icon }) => {
              const isActive =
                location.pathname === to ||
                (to !== "/" && location.pathname.startsWith(to));
              return (
                <NavLink
                  key={to}
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-white/10 border border-white/20 text-white"
                      : "text-white/70 hover:text-white hover:bg-white/5",
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-white/50" />
                  <span>{t(labelKey)}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      ))}
    </div>
  );
}
