/**
 * PromptFormModal component for creating/editing prompts
 */

import React from "react";
import { X, Plus, Trash2, HelpCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import type {
  CreatePromptRequest,
  PromptTemplate,
  PromptVariable,
} from "#/types/prompt";
import { PromptCategory, PROMPT_CATEGORY_LABELS } from "#/types/prompt";

interface PromptFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreatePromptRequest) => void;
  initialData?: PromptTemplate;
}

export function PromptFormModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: PromptFormModalProps) {
  const { t } = useTranslation();
  const [title, setTitle] = React.useState(initialData?.title || "");
  const [description, setDescription] = React.useState(
    initialData?.description || "",
  );
  const [category, setCategory] = React.useState<PromptCategory>(
    initialData?.category || PromptCategory.CUSTOM,
  );
  const [content, setContent] = React.useState(initialData?.content || "");
  const [variables, setVariables] = React.useState<PromptVariable[]>(
    initialData?.variables || [],
  );
  const [tags, setTags] = React.useState<string[]>(initialData?.tags || []);
  const [tagInput, setTagInput] = React.useState("");
  const [isFavorite, setIsFavorite] = React.useState(
    initialData?.is_favorite || false,
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    onSubmit({
      title,
      description: description || undefined,
      category,
      content,
      variables,
      tags,
      is_favorite: isFavorite,
    });

    // Reset form if creating new prompt
    if (!initialData) {
      setTitle("");
      setDescription("");
      setCategory(PromptCategory.CUSTOM);
      setContent("");
      setVariables([]);
      setTags([]);
      setIsFavorite(false);
    }

    onClose();
  };

  const addVariable = () => {
    setVariables([
      ...variables,
      { name: "", description: "", default_value: "", required: true },
    ]);
  };

  const updateVariable = (index: number, field: keyof PromptVariable, value: string | boolean) => {
    const updated = [...variables];
    updated[index] = { ...updated[index], [field]: value };
    setVariables(updated);
  };

  const removeVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const addTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput("");
    }
  };

  const removeTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const insertVariable = (varName: string) => {
    setContent(content + `{{${varName}}}`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-background-secondary border border-border rounded-lg w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-foreground">
            {initialData ? t("PROMPTS$EDIT_PROMPT") : t("PROMPTS$CREATE_PROMPT")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 hover:bg-background rounded text-foreground-secondary hover:text-foreground"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Title */}
            <div>
              <label
                htmlFor="title"
                className="block text-sm font-medium text-foreground mb-2"
              >
                {t("PROMPTS$TITLE")} <span className="text-red-500">*</span>
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-foreground mb-2"
              >
                {t("PROMPTS$DESCRIPTION")}
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active resize-none"
              />
            </div>

            {/* Category */}
            <div>
              <label
                htmlFor="category"
                className="block text-sm font-medium text-foreground mb-2"
              >
                {t("PROMPTS$CATEGORY")}
              </label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value as PromptCategory)}
                className="w-full px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active"
              >
                {Object.entries(PROMPT_CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Content */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="content"
                  className="block text-sm font-medium text-foreground"
                >
                  {t("PROMPTS$CONTENT")} <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center gap-1 text-xs text-foreground-secondary">
                  <HelpCircle className="w-3 h-3" />
                  {t("PROMPTS$USE_VARIABLES_HINT")}
                </div>
              </div>
              <textarea
                id="content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                className="w-full px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active resize-none font-mono text-sm"
                required
                placeholder={t("PROMPTS$CONTENT_PLACEHOLDER")}
              />
            </div>

            {/* Variables */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-foreground">
                  {t("PROMPTS$VARIABLES")}
                </label>
                <button
                  type="button"
                  onClick={addVariable}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-primary hover:text-primary-dark"
                >
                  <Plus className="w-3 h-3" />
                  {t("PROMPTS$ADD_VARIABLE")}
                </button>
              </div>

              <div className="space-y-3">
                {variables.map((variable, index) => (
                  <div
                    key={index}
                    className="p-3 bg-background border border-border rounded"
                  >
                    <div className="grid grid-cols-2 gap-3 mb-2">
                      <input
                        type="text"
                        value={variable.name}
                        onChange={(e) =>
                          updateVariable(index, "name", e.target.value)
                        }
                        placeholder={t("PROMPTS$VARIABLE_NAME")}
                        className="px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active"
                      />
                      <input
                        type="text"
                        value={variable.default_value || ""}
                        onChange={(e) =>
                          updateVariable(index, "default_value", e.target.value)
                        }
                        placeholder={t("PROMPTS$DEFAULT_VALUE")}
                        className="px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <input
                        type="text"
                        value={variable.description || ""}
                        onChange={(e) =>
                          updateVariable(index, "description", e.target.value)
                        }
                        placeholder={t("PROMPTS$VARIABLE_DESCRIPTION")}
                        className="flex-1 px-2 py-1 bg-background-secondary border border-border rounded text-sm text-foreground focus:outline-none focus:border-border-active mr-2"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => insertVariable(variable.name)}
                          className="px-2 py-1 text-xs text-primary hover:text-primary-dark"
                          disabled={!variable.name}
                        >
                          {t("PROMPTS$INSERT")}
                        </button>
                        <button
                          type="button"
                          onClick={() => removeVariable(index)}
                          className="p-1 text-red-500 hover:text-red-600"
                          aria-label="Remove variable"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t("PROMPTS$TAGS")}
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  placeholder={t("PROMPTS$ADD_TAG_PLACEHOLDER")}
                  className="flex-1 px-3 py-2 bg-background border border-border rounded text-foreground focus:outline-none focus:border-border-active"
                />
                <button
                  type="button"
                  onClick={addTag}
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
                      onClick={() => removeTag(tag)}
                      className="text-foreground-secondary hover:text-foreground"
                      aria-label={`Remove ${tag}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Favorite */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="favorite"
                checked={isFavorite}
                onChange={(e) => setIsFavorite(e.target.checked)}
                className="w-4 h-4 text-primary focus:ring-primary"
              />
              <label htmlFor="favorite" className="text-sm text-foreground">
                {t("PROMPTS$MARK_AS_FAVORITE")}
              </label>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-foreground-secondary hover:text-foreground"
          >
            {t("PROMPTS$CANCEL")}
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            disabled={!title.trim() || !content.trim()}
          >
            {initialData ? t("PROMPTS$UPDATE") : t("PROMPTS$CREATE")}
          </button>
        </div>
      </div>
    </div>
  );
}

