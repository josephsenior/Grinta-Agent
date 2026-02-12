import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { FileCode, Terminal, Globe } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";
import { TabContent } from "#/components/layout/tab-content";
import { useConversationId } from "#/hooks/use-conversation-id";
import { cn } from "#/utils/utils";

interface TabButtonProps {
  to: string;
  basePath: string;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ to, basePath, icon, label }: TabButtonProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isActive =
    location.pathname === `${basePath}${to ? `/${to}` : ""}` ||
    (to === "" && location.pathname === basePath);

  return (
    <button
      type="button"
      onClick={() => navigate(`${basePath}${to ? `/${to}` : ""}`)}
      className={cn(
        "h-full px-4 flex items-center gap-2 text-xs border-r border-[var(--border-primary)] transition-colors",
        isActive
          ? "bg-[var(--bg-primary)] text-[var(--text-primary)]"
          : "bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]",
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function ConversationTabs() {
  const { conversationId } = useConversationId();

  const { t } = useTranslation();

  const basePath = `/conversations/${conversationId}`;

  return (
    <div className="h-full w-full flex flex-col bg-[var(--bg-primary)]">
      {/* Desktop-style tabs */}
      <div className="h-9 bg-[var(--bg-tertiary)] border-b border-[var(--border-primary)] flex items-center px-2 flex-shrink-0">
        <TabButton
          to=""
          basePath={basePath}
          icon={<FileCode className="w-4 h-4" />}
          label="Workspace"
        />
        <TabButton
          to="terminal"
          basePath={basePath}
          icon={<Terminal className="w-4 h-4" />}
          label={t(I18nKey.WORKSPACE$TERMINAL_TAB_LABEL)}
        />
        <TabButton
          to="browser"
          basePath={basePath}
          icon={<Globe className="w-4 h-4" />}
          label="Browser"
        />
      </div>
      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <TabContent conversationPath={basePath} />
      </div>
    </div>
  );
}
