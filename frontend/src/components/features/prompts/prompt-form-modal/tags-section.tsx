import React from "react";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";

interface TagsSectionProps {
  tags: string[];
  tagInput: string;
  onTagInputChange: (value: string) => void;
  onAddTag: () => void;
  onRemoveTag: (tag: string) => void;
}

export function TagsSection({
  tags,
  tagInput,
  onTagInputChange,
  onAddTag,
  onRemoveTag,
}: TagsSectionProps) {
  const { t } = useTranslation();

  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        {t("PROMPTS$TAGS")}
      </label>
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={tagInput}
          onChange={(e) => onTagInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAddTag();
            }
          }}
          placeholder={t("PROMPTS$ADD_TAG_PLACEHOLDER")}
          className="flex-1 px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active"
        />
        <button
          type="button"
          onClick={onAddTag}
          className="px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark"
        >
          {t("PROMPTS$ADD")}
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-1 bg-background rounded text-sm text-foreground flex items-center gap-1"
          >
            #{tag}
            <button
              type="button"
              onClick={() => onRemoveTag(tag)}
              className="text-foreground-secondary hover:text-foreground"
              aria-label={`Remove ${tag}`}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
