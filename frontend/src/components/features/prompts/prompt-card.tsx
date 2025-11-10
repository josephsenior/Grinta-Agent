/**
 * PromptCard component for displaying a single prompt template
 */

import React from "react";
import {
  BookOpen,
  Code,
  Edit,
  FileText,
  Heart,
  MoreVertical,
  Star,
  Trash2,
  Copy,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { PromptTemplate } from "#/types/prompt";
import { PROMPT_CATEGORY_LABELS } from "#/types/prompt";

interface PromptCardProps {
  prompt: PromptTemplate;
  onEdit: (prompt: PromptTemplate) => void;
  onDelete: (promptId: string) => void;
  onUse: (prompt: PromptTemplate) => void;
  onToggleFavorite: (promptId: string, isFavorite: boolean) => void;
}

const getCategoryIcon = (category: string) => {
  switch (category) {
    case "coding":
    case "debugging":
    case "refactoring":
    case "testing":
    case "code_review":
      return <Code className="w-4 h-4" />;
    case "documentation":
    case "writing":
      return <FileText className="w-4 h-4" />;
    case "analysis":
    case "summarization":
      return <BookOpen className="w-4 h-4" />;
    default:
      return <Star className="w-4 h-4" />;
  }
};

export function PromptCard({
  prompt,
  onEdit,
  onDelete,
  onUse,
  onToggleFavorite,
}: PromptCardProps) {
  const { t } = useTranslation();
  const [showMenu, setShowMenu] = React.useState(false);

  const handleCopyContent = () => {
    navigator.clipboard.writeText(prompt.content);
    // TODO: Show toast notification
    setShowMenu(false);
  };

  return (
    <div className="bg-background-secondary border border-border rounded-lg p-4 hover:border-border-active transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="p-2 bg-background rounded-md text-foreground-secondary">
            {getCategoryIcon(prompt.category)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-base font-semibold text-foreground truncate">
                {prompt.title}
              </h3>
              {prompt.is_favorite && (
                <Heart className="w-4 h-4 text-red-500 fill-red-500 flex-shrink-0" />
              )}
            </div>
            <span className="text-xs text-foreground-secondary">
              {PROMPT_CATEGORY_LABELS[prompt.category]}
            </span>
          </div>
        </div>

        {/* Actions menu */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 hover:bg-background rounded text-foreground-secondary hover:text-foreground"
            aria-label="More options"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
                onKeyDown={(e) => e.key === "Escape" && setShowMenu(false)}
                role="button"
                tabIndex={0}
                aria-label="Close menu"
              />
              <div className="absolute right-0 top-8 z-20 w-48 bg-background-secondary border border-border rounded-lg shadow-lg py-1">
                <button
                  type="button"
                  onClick={() => {
                    onEdit(prompt);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  {t("PROMPTS$EDIT")}
                </button>
                <button
                  type="button"
                  onClick={handleCopyContent}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  {t("PROMPTS$COPY")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onToggleFavorite(prompt.id, !prompt.is_favorite);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Heart
                    className={`w-4 h-4 ${prompt.is_favorite ? "fill-red-500 text-red-500" : ""}`}
                  />
                  {prompt.is_favorite
                    ? t("PROMPTS$REMOVE_FAVORITE")
                    : t("PROMPTS$ADD_FAVORITE")}
                </button>
                <div className="border-t border-border my-1" />
                <button
                  type="button"
                  onClick={() => {
                    onDelete(prompt.id);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-500 hover:bg-background flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  {t("PROMPTS$DELETE")}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Description */}
      {prompt.description && (
        <p className="text-sm text-foreground-secondary mb-3 line-clamp-2">
          {prompt.description}
        </p>
      )}

      {/* Content preview */}
      <div className="mb-3 p-3 bg-background rounded text-xs font-mono text-foreground-secondary line-clamp-3">
        {prompt.content}
      </div>

      {/* Tags */}
      {prompt.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {prompt.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 bg-background rounded text-xs text-foreground-secondary"
            >
              #{tag}
            </span>
          ))}
          {prompt.tags.length > 3 && (
            <span className="px-2 py-1 text-xs text-foreground-secondary">
              +{prompt.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="text-xs text-foreground-secondary">
          {t("PROMPTS$USED_COUNT", { count: prompt.usage_count })}
        </div>
        <button
          type="button"
          onClick={() => onUse(prompt)}
          className="px-3 py-1.5 bg-primary text-white text-sm font-medium rounded hover:bg-primary-dark transition-colors"
        >
          {t("PROMPTS$USE_PROMPT")}
        </button>
      </div>
    </div>
  );
}
