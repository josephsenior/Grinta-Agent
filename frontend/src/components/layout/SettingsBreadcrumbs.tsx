import React, { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronRight, Home } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import {
  SETTINGS_PATH_LABEL_MAP,
  getSettingsCategories,
  type SettingsNavContext,
} from "#/config/settings-nav";
import { useConfig } from "#/hooks/query/use-config";
import { useSubscriptionAccess } from "#/hooks/query/use-subscription-access";

const SETTINGS_PATH_MAP: Record<string, I18nKey> = {
  "/settings/app": I18nKey.SETTINGS$TITLE,
  ...SETTINGS_PATH_LABEL_MAP,
};

export function SettingsBreadcrumbs() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: config } = useConfig();
  const { data: subscriptionAccess } = useSubscriptionAccess();

  const navContext = useMemo<SettingsNavContext>(
    () => ({
      mode: config?.APP_MODE === "saas" ? "saas" : "oss",
      hasPro: subscriptionAccess?.status === "ACTIVE",
    }),
    [config?.APP_MODE, subscriptionAccess?.status],
  );

  const categoryByPath = useMemo(() => {
    const map = new Map<string, string>();
    getSettingsCategories(navContext).forEach((category) => {
      category.items.forEach((item) => map.set(item.path, category.title));
    });
    return map;
  }, [navContext]);

  const handleBreadcrumbClick = (path: string) => {
    navigate(path);
  };

  const currentPath = location.pathname;
  const categoryLabel = categoryByPath.get(currentPath);

  // Get the current page label
  const currentPageLabel = useMemo(() => {
    const labelKey = SETTINGS_PATH_MAP[currentPath];
    if (labelKey) {
      return t(labelKey);
    }

    const fallbackLabel = currentPath.split("/").pop();
    return fallbackLabel || t(I18nKey.SETTINGS$TITLE);
  }, [currentPath, t]);

  return (
    <nav
      className="flex items-center gap-2 text-sm mb-4"
      aria-label="Breadcrumb"
    >
      <ol className="flex items-center gap-2 flex-wrap">
        {/* Home */}
        <li className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleBreadcrumbClick("/")}
            className="flex items-center gap-1.5 transition-colors hover:text-white text-white/70"
          >
            <Home className="w-4 h-4" />
            <span>{t("common.home", "Home")}</span>
          </button>
        </li>

        {/* Category Crumb */}
        {categoryLabel && (
          <li className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4 text-white/30 flex-shrink-0" />
            <span className="text-white/70">{categoryLabel}</span>
          </li>
        )}

        {/* Current Page */}
        <li className="flex items-center gap-2">
          <ChevronRight className="w-4 h-4 text-white/30 flex-shrink-0" />
          <span className="font-medium text-white">{currentPageLabel}</span>
        </li>
      </ol>
    </nav>
  );
}
