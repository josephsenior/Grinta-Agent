import { Edit, Trash2, Clock, Hash, Tag } from "lucide-react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import type { Memory } from "#/types/memory";

interface MemoryCardProps {
  memory: Memory;
  onEdit: (memory: Memory) => void;
  onDelete: (memoryId: string) => void;
}

export function MemoryCard({ memory, onEdit, onDelete }: MemoryCardProps) {
  const { t } = useTranslation();

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "technical":
        return "💡";
      case "preference":
        return "🎨";
      case "project":
        return "🏗️";
      case "fact":
        return "📚";
      default:
        return "📌";
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "technical":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "preference":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      case "project":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "fact":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      default:
        return "bg-foreground-secondary/10 text-foreground-secondary border-border";
    }
  };

  const getImportanceColor = (importance: string) => {
    switch (importance) {
      case "high":
        return "bg-error-500/10 text-error-500 border-error-500/20";
      case "medium":
        return "bg-warning-500/10 text-warning-500 border-warning-500/20";
      default:
        return "bg-foreground-secondary/10 text-foreground-secondary border-border";
    }
  };

  const getRelativeTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return t(I18nKey.MEMORY$RELATIVE_TIME_JUST_NOW);
    if (diffMins < 60)
      return t(I18nKey.MEMORY$RELATIVE_TIME_MINUTES_AGO, {
        count: diffMins,
        plural: diffMins > 1 ? "s" : "",
      });
    if (diffHours < 24)
      return t(I18nKey.MEMORY$RELATIVE_TIME_HOURS_AGO, {
        count: diffHours,
        plural: diffHours > 1 ? "s" : "",
      });
    return t(I18nKey.MEMORY$RELATIVE_TIME_DAYS_AGO, {
      count: diffDays,
      plural: diffDays > 1 ? "s" : "",
    });
  };

  return (
    <div className="p-4 bg-background-secondary border border-border rounded-lg hover:border-brand-500 transition-colors group">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <span className="text-2xl flex-shrink-0">
            {getCategoryIcon(memory.category)}
          </span>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-foreground text-base mb-1 truncate">
              {memory.title}
            </h3>
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`px-2 py-0.5 text-xs font-medium rounded border ${getCategoryColor(memory.category)}`}
              >
                {memory.category.charAt(0).toUpperCase() +
                  memory.category.slice(1)}
              </span>
              <span
                className={`px-2 py-0.5 text-xs font-medium rounded border ${getImportanceColor(memory.importance)}`}
              >
                {memory.importance.charAt(0).toUpperCase() +
                  memory.importance.slice(1)}
              </span>
              {memory.source === "ai-suggested" && (
                <span className="px-2 py-0.5 text-xs font-medium rounded border bg-brand-500/10 text-violet-500 border-brand-500/20">
                  AI
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={() => onEdit(memory)}
            className="p-2 text-foreground-secondary hover:text-foreground hover:bg-background-tertiary rounded-md transition-colors"
            title={t(I18nKey.MEMORY$BUTTON_EDIT)}
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(memory.id)}
            className="p-2 text-foreground-secondary hover:text-error-500 hover:bg-error-500/10 rounded-md transition-colors"
            title={t(I18nKey.MEMORY$BUTTON_DELETE)}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <p className="text-sm text-foreground-secondary mb-3 line-clamp-2">
        {memory.content}
      </p>

      {/* Tags */}
      {memory.tags.length > 0 && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          {memory.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-background-tertiary border border-border rounded text-foreground-secondary flex items-center gap-1"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center gap-4 text-xs text-foreground-secondary">
        <div className="flex items-center gap-1">
          <Hash className="w-3 h-3" />
          <span>
            {t(I18nKey.MEMORY$USED_COUNT, { count: memory.usageCount })}
          </span>
        </div>
        {memory.lastUsed && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>
              {t(I18nKey.MEMORY$LAST_USED, {
                time: getRelativeTime(memory.lastUsed),
              })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
