import {
  Trash,
  Power,
  Pencil,
  Download,
  Wallet,
  Wrench,
  Bot,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { useClickOutsideElement } from "#/hooks/use-click-outside-element";
import { cn } from "#/utils/utils";
import { ContextMenu } from "../context-menu/context-menu";
import { ContextMenuListItem } from "../context-menu/context-menu-list-item";
import { ContextMenuSeparator } from "../context-menu/context-menu-separator";
import { I18nKey } from "#/i18n/declaration";
import { ContextMenuIconText } from "../context-menu/context-menu-icon-text";

interface ConversationCardContextMenuProps {
  onClose: () => void;
  onDelete?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onStop?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onEdit?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onDisplayCost?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onShowAgentTools?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onShowMicroagents?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onDownloadViaVSCode?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  position?: "top" | "bottom";
}

type MenuItemConfig = {
  testId: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  i18nKey: I18nKey;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
};

type MenuSection = MenuItemConfig[];

export function ConversationCardContextMenu({
  onClose,
  onDelete,
  onStop,
  onEdit,
  onDisplayCost,
  onShowAgentTools,
  onShowMicroagents,
  onDownloadViaVSCode,
  position = "bottom",
}: ConversationCardContextMenuProps) {
  const { t } = useTranslation();
  const ref = useClickOutsideElement<HTMLUListElement>(onClose);

  const sections = useMemo<MenuSection[]>(
    () =>
      buildMenuSections({
        onEdit,
        onDownloadViaVSCode,
        onShowAgentTools,
        onShowMicroagents,
        onDisplayCost,
        onStop,
        onDelete,
      }),
    [
      onEdit,
      onDownloadViaVSCode,
      onShowAgentTools,
      onShowMicroagents,
      onDisplayCost,
      onStop,
      onDelete,
    ],
  );

  return (
    <ContextMenu
      ref={ref}
      testId="context-menu"
      className={cn(
        "right-0 absolute mt-3",
        position === "top" && "bottom-full",
        position === "bottom" && "top-full",
      )}
    >
      {sections.map((section, sectionIndex) => (
        <MenuSectionRenderer
          key={getSectionKey(section, sectionIndex)}
          section={section}
          sectionIndex={sectionIndex}
          translator={t}
        />
      ))}
    </ContextMenu>
  );
}

function MenuSectionRenderer({
  section,
  sectionIndex,
  translator,
}: {
  section: MenuSection;
  sectionIndex: number;
  translator: ReturnType<typeof useTranslation>["t"];
}) {
  if (section.length === 0) {
    return null;
  }

  return (
    <>
      {sectionIndex > 0 && <ContextMenuSeparator />}
      {section.map((item) => (
        <ContextMenuListItem key={item.testId} testId={item.testId} onClick={item.onClick}>
          <ContextMenuIconText icon={item.icon} text={translator(item.i18nKey)} />
        </ContextMenuListItem>
      ))}
    </>
  );
}

function buildMenuSections(handlers: {
  onEdit?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onDownloadViaVSCode?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onShowAgentTools?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onShowMicroagents?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onDisplayCost?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onStop?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onDelete?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}): MenuSection[] {
  const sections: MenuSection[] = [];

  sections.push(
    createMenuSection([
      handlers.onEdit && {
        testId: "edit-button",
        icon: Pencil,
        i18nKey: I18nKey.BUTTON$EDIT_TITLE,
        onClick: handlers.onEdit,
      },
    ]),
  );

  sections.push(
    createMenuSection([
      handlers.onDownloadViaVSCode && {
        testId: "download-vscode-button",
        icon: Download,
        i18nKey: I18nKey.BUTTON$DOWNLOAD_VIA_VSCODE,
        onClick: handlers.onDownloadViaVSCode,
      },
    ]),
  );

  sections.push(
    createMenuSection([
      handlers.onShowAgentTools && {
        testId: "show-agent-tools-button",
        icon: Wrench,
        i18nKey: I18nKey.BUTTON$SHOW_AGENT_TOOLS_AND_METADATA,
        onClick: handlers.onShowAgentTools,
      },
      handlers.onShowMicroagents && {
        testId: "show-microagents-button",
        icon: Bot,
        i18nKey: I18nKey.CONVERSATION$SHOW_MICROAGENTS,
        onClick: handlers.onShowMicroagents,
      },
    ]),
  );

  sections.push(
    createMenuSection([
      handlers.onDisplayCost && {
        testId: "display-cost-button",
        icon: Wallet,
        i18nKey: I18nKey.BUTTON$DISPLAY_COST,
        onClick: handlers.onDisplayCost,
      },
    ]),
  );

  sections.push(
    createMenuSection([
      handlers.onStop && {
        testId: "stop-button",
        icon: Power,
        i18nKey: I18nKey.BUTTON$PAUSE,
        onClick: handlers.onStop,
      },
      handlers.onDelete && {
        testId: "delete-button",
        icon: Trash,
        i18nKey: I18nKey.BUTTON$DELETE,
        onClick: handlers.onDelete,
      },
    ]),
  );

  return sections.filter((section) => section.length > 0);
}

function createMenuSection(items: Array<MenuItemConfig | false | undefined>): MenuSection {
  return items.filter(Boolean) as MenuSection;
}

function getSectionKey(section: MenuSection, index: number) {
  if (section.length === 0) {
    return `section-empty-${index}`;
  }
  return section.map((item) => item.testId).join(":");
}
