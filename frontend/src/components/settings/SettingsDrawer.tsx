import { useEffect, useRef, useMemo } from "react";
import {
  X,
  MessageSquare,
  Settings,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useTranslation } from "react-i18next";
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

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsDrawer({ isOpen, onClose }: SettingsDrawerProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const firstItemRef = useRef<HTMLButtonElement>(null);
  const { t } = useTranslation();

  const navGroups: NavGroup[] = useMemo(
    () => [
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
    ],
    [],
  );

  useEffect(() => {
    if (isOpen) {
      firstItemRef.current?.focus();
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleNavigate = (path: string) => {
    if (path === "#") {
      // Handle keyboard shortcuts or other special actions
      return;
    }
    if (location.pathname !== path) {
      navigate(path);
    }
    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex justify-end"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        aria-label={t("common.close", "Close")}
        onClick={onClose}
      />
      <div
        className="relative h-full w-full max-w-[380px] bg-black border-l border-white/10 shadow-2xl overflow-y-auto z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <p className="text-sm font-semibold text-white">
            {t("common.navigation", "Navigation")}
          </p>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-full hover:bg-white/10 transition"
            aria-label="Close navigation drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="p-4 space-y-6">
          {navGroups.map((group, groupIdx) => (
            <div key={group.titleKey} className="space-y-2">
              <p className="text-xs uppercase tracking-[0.25em] text-white/40">
                {t(group.titleKey)}
              </p>
              <div className="space-y-1">
                {group.items.map((item, itemIdx) => {
                  const Icon = item.icon;
                  const isActive =
                    location.pathname === item.to ||
                    (item.to !== "/" && location.pathname.startsWith(item.to));

                  return (
                    <button
                      key={item.to}
                      ref={
                        groupIdx === 0 && itemIdx === 0
                          ? firstItemRef
                          : undefined
                      }
                      type="button"
                      onClick={() => handleNavigate(item.to)}
                      className={cn(
                        "w-full flex items-center gap-3 text-left rounded-xl px-3 py-2.5 text-sm font-medium transition",
                        isActive
                          ? "bg-white/10 text-white"
                          : "text-white/70 hover:bg-white/10 hover:text-white",
                      )}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      {t(item.labelKey)}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>
    </div>
  );
}
