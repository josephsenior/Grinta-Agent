/**
 * Centralized settings navigation metadata consumed by the sidebar, hub, search, and breadcrumbs.
 * Add new items here and update docs/REFACTORED_NAVIGATION.md when categories change.
 */
import {
  Bot,
  Settings as SettingsIcon,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";

export type SettingsNavMode = "oss" | "saas";

export interface SettingsNavContext {
  mode: SettingsNavMode;
}

export interface SettingsNavSubItem {
  id: string;
  label: string;
  path: string;
}

export interface SettingsNavItem {
  id: string;
  path: string;
  labelKey: I18nKey;
  icon: LucideIcon;
  description: string;
  subItems?: SettingsNavSubItem[];
}

export interface SettingsCategory {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
  items: SettingsNavItem[];
}

interface CategoryItemRef {
  itemId: SettingsNavItem["id"];
}

interface SettingsCategoryDefinition extends Omit<SettingsCategory, "items"> {
  items: CategoryItemRef[];
}

const SETTINGS_ITEM_DEFINITIONS: SettingsNavItem[] = [
  {
    id: "llm",
    path: "/settings/llm",
    labelKey: I18nKey.SETTINGS$NAV_LLM,
    icon: Bot,
    description: "Configure AI models and providers",
  },
  {
    id: "mcp",
    path: "/settings/mcp",
    labelKey: I18nKey.SETTINGS$NAV_MCP,
    icon: Workflow,
    description: "Manage Model Context Protocol servers",
    subItems: [
      {
        id: "mcp-my-servers",
        label: "My Servers",
        path: "/settings/mcp?tab=my-servers",
      },
      {
        id: "mcp-marketplace",
        label: "Marketplace",
        path: "/settings/mcp?tab=marketplace",
      },
    ],
  },
  {
    id: "app",
    path: "/settings/app",
    labelKey: I18nKey.SETTINGS$NAV_APPLICATION,
    icon: SettingsIcon,
    description: "Application preferences and language",
  },
];

const SETTINGS_ITEM_MAP: Record<string, SettingsNavItem> =
  SETTINGS_ITEM_DEFINITIONS.reduce(
    (acc, item) => {
      acc[item.id] = item;
      return acc;
    },
    {} as Record<string, SettingsNavItem>,
  );

const SETTINGS_CATEGORY_DEFINITIONS: SettingsCategoryDefinition[] = [
  {
    id: "ai-models",
    title: "AI & Models",
    description: "Configure AI models and MCP servers",
    icon: Bot,
    items: [
      { itemId: "llm" },
      { itemId: "mcp" },
    ],
  },
  {
    id: "account",
    title: "Account",
    description: "Manage your workspace preferences",
    icon: SettingsIcon,
    items: [
      { itemId: "app" },
    ],
  },
];

export const SETTINGS_PATH_LABEL_MAP: Record<string, I18nKey> =
  SETTINGS_ITEM_DEFINITIONS.reduce(
    (acc, item) => {
      acc[item.path] = item.labelKey;
      return acc;
    },
    {} as Record<string, I18nKey>,
  );

export function getAllSettingsNavItems(): SettingsNavItem[] {
  const items = SETTINGS_ITEM_DEFINITIONS;
  const uniqueByPath = new Map<string, SettingsNavItem>();
  items.forEach((item) => {
    if (!uniqueByPath.has(item.path)) {
      uniqueByPath.set(item.path, item);
    }
  });
  return Array.from(uniqueByPath.values());
}

export function getSettingsCategories(
  _context: SettingsNavContext,
): SettingsCategory[] {
  return SETTINGS_CATEGORY_DEFINITIONS.map((category) => {
    const items = category.items
      .map((ref) => SETTINGS_ITEM_MAP[ref.itemId]);

    return {
      id: category.id,
      title: category.title,
      description: category.description,
      icon: category.icon,
      items,
    };
  });
}
