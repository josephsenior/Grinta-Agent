import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronUp, BookOpen } from "lucide-react";

interface GuidesPanelHeaderProps {
  isExpanded: boolean;
  onToggle: () => void;
  repositoryName: string;
}

export function GuidesPanelHeader({
  isExpanded,
  onToggle,
  repositoryName,
}: GuidesPanelHeaderProps) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full px-4 py-3 flex items-center justify-between hover:bg-violet-500/5 transition-colors"
    >
      <div className="flex items-center gap-2">
        <BookOpen className="h-4 w-4 text-violet-400" />
        <span className="text-sm font-medium text-foreground-secondary">
          {t("chat.guides.repositoryGuides", "Repository Guides")}
        </span>
        <span className="text-xs text-foreground-tertiary">
          ({repositoryName})
        </span>
      </div>
      {isExpanded ? (
        <ChevronUp className="h-4 w-4 text-foreground-tertiary" />
      ) : (
        <ChevronDown className="h-4 w-4 text-foreground-tertiary" />
      )}
    </button>
  );
}
