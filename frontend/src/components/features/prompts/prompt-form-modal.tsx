/**
 * PromptFormModal component for creating/editing prompts
 */

import React from "react";
import { X, HelpCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { CreatePromptRequest } from "#/types/prompt";
import { PromptCategory, PROMPT_CATEGORY_LABELS } from "#/types/prompt";
import { usePromptFormState } from "./prompt-form-modal/use-prompt-form-state";
import { useVariableManagement } from "./prompt-form-modal/use-variable-management";
import { useTagManagement } from "./prompt-form-modal/use-tag-management";
import { VariablesSection } from "./prompt-form-modal/variables-section";
import { TagsSection } from "./prompt-form-modal/tags-section";

interface PromptFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreatePromptRequest) => void;
  initialData?: import("#/types/prompt").PromptTemplate;
}

export function PromptFormModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: PromptFormModalProps) {
  const { t } = useTranslation();
  const formState = usePromptFormState(initialData);
  const {
    title,
    setTitle,
    description,
    setDescription,
    category,
    setCategory,
    content,
    setContent,
    variables,
    setVariables,
    tags,
    setTags,
    tagInput,
    setTagInput,
    isFavorite,
    setIsFavorite,
    resetForm,
  } = formState;

  const { addVariable, updateVariable, removeVariable, insertVariable } =
    useVariableManagement(variables, setVariables, content, setContent);

  const { addTag, removeTag } = useTagManagement(
    tags,
    setTags,
    tagInput,
    setTagInput,
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

    if (!initialData) {
      resetForm();
    }

    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-background-secondary border border-border rounded-lg w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-foreground">
            {initialData
              ? t("PROMPTS$EDIT_PROMPT")
              : t("PROMPTS$CREATE_PROMPT")}
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

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
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
                {Object.entries(PROMPT_CATEGORY_LABELS).map(
                  ([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ),
                )}
              </select>
            </div>

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

            <VariablesSection
              variables={variables}
              onAddVariable={addVariable}
              onUpdateVariable={updateVariable}
              onRemoveVariable={removeVariable}
              onInsertVariable={insertVariable}
            />

            <TagsSection
              tags={tags}
              tagInput={tagInput}
              onTagInputChange={setTagInput}
              onAddTag={addTag}
              onRemoveTag={removeTag}
            />

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
