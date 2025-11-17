// Snippets settings — typed via `#/types/snippet`
/**
 * Code Snippet Library Settings Page
 */
/* eslint-disable i18next/no-literal-string */

import React, { useState, useMemo, useEffect, useCallback } from "react";
import {
  Plus,
  Search,
  Download,
  Upload,
  Star,
  Code2,
  Copy,
  Edit,
  Trash2,
  MoreVertical,
  X,
  Heart,
  TrendingUp,
  Check,
} from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useToast, ToastContainer } from "#/components/shared/toast";
import { CardSkeletonGrid } from "#/components/shared/card-skeleton";
import {
  useSnippets,
  useSnippetStats,
  useCreateSnippet,
  useUpdateSnippet,
  useDeleteSnippet,
  useExportSnippets,
  useImportSnippets,
  useTrackSnippetUsage,
} from "#/hooks/query/use-snippets";
import type {
  CodeSnippet,
  CreateSnippetRequest,
  SnippetStats,
} from "#/types/snippet";
import {
  SnippetLanguage,
  SnippetCategory,
  SNIPPET_LANGUAGE_LABELS,
  SNIPPET_CATEGORY_LABELS,
} from "#/types/snippet";

// Snippet Card Component
function SnippetCard({
  snippet,
  onEdit,
  onDelete,
  onUse,
  onToggleFavorite,
}: {
  snippet: CodeSnippet;
  onEdit: (snippet: CodeSnippet) => void;
  onDelete: (id: string) => void;
  onUse: (snippet: CodeSnippet) => void;
  onToggleFavorite: (id: string, isFavorite: boolean) => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(snippet.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    setShowMenu(false);
  };

  return (
    <div
      className="bg-black/60 border border-white/10 rounded-2xl p-4 hover:border-white/20 transition-colors"
      data-testid={`snippet-card-${snippet.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="p-2 bg-background rounded-md text-foreground-secondary flex-shrink-0">
            <Code2 className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-base font-semibold text-foreground truncate">
                {snippet.title}
              </h3>
              {snippet.is_favorite && (
                <Heart className="w-4 h-4 text-foreground-tertiary fill-foreground-tertiary flex-shrink-0" />
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-foreground-secondary">
              <span>{SNIPPET_LANGUAGE_LABELS[snippet.language]}</span>
              <span>•</span>
              <span>{SNIPPET_CATEGORY_LABELS[snippet.category]}</span>
            </div>
          </div>
        </div>

        {/* Actions menu */}
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 hover:bg-background rounded text-foreground-secondary hover:text-foreground"
            aria-label="Snippet actions"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 top-8 z-20 w-48 bg-black/90 border border-white/10 rounded-xl shadow-lg py-1 backdrop-blur-xl">
                <button
                  type="button"
                  onClick={() => {
                    onEdit(snippet);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy Code
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onToggleFavorite(snippet.id, !snippet.is_favorite);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-background flex items-center gap-2"
                >
                  <Heart
                    className={`w-4 h-4 ${snippet.is_favorite ? "fill-foreground-tertiary text-foreground-tertiary" : ""}`}
                  />
                  {snippet.is_favorite ? "Remove Favorite" : "Add Favorite"}
                </button>
                <div className="border-t border-white/10 my-1" />
                <button
                  type="button"
                  onClick={() => {
                    onDelete(snippet.id);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-foreground-secondary hover:bg-white/5 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Description */}
      {snippet.description && (
        <p className="text-sm text-foreground-secondary mb-3 line-clamp-2">
          {snippet.description}
        </p>
      )}

      {/* Code preview with syntax highlighting */}
      <div className="mb-3 rounded overflow-hidden relative group">
        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={handleCopy}
            className="px-2 py-1 bg-black/60 border border-white/10 rounded-xl text-xs text-foreground hover:bg-white/5 flex items-center gap-1"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-foreground-secondary" />
                <span className="text-foreground-secondary">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
        <div className="max-h-32 overflow-hidden">
          <SyntaxHighlighter
            language={snippet.language}
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              fontSize: "0.75rem",
              borderRadius: "0.375rem",
            }}
            showLineNumbers={false}
          >
            {snippet.code}
          </SyntaxHighlighter>
        </div>
        {snippet.code.split("\n").length > 8 && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[#1e1e1e] to-transparent pointer-events-none" />
        )}
      </div>

      {/* Tags */}
      {snippet.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {snippet.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 bg-background rounded text-xs text-foreground-secondary"
            >
              #{tag}
            </span>
          ))}
          {snippet.tags.length > 3 && (
            <span className="px-2 py-1 text-xs text-foreground-secondary">
              +{snippet.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-white/10">
        <div className="text-xs text-foreground-secondary">
          Used {snippet.usage_count} times
        </div>
        <button
          type="button"
          onClick={() => onUse(snippet)}
          className="px-4 py-2 bg-white text-black text-sm font-semibold rounded-xl hover:bg-white/90 transition-colors"
        >
          Use Snippet
        </button>
      </div>
    </div>
  );
}

// Snippet Form Modal Component
const useSnippetForm = ({
  initialData,
  onSubmit,
  onClose,
}: {
  initialData?: CodeSnippet;
  onSubmit: (data: CreateSnippetRequest) => void;
  onClose: () => void;
}) => {
  const isEditing = Boolean(initialData);
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [description, setDescription] = useState(
    initialData?.description ?? "",
  );
  const [language, setLanguage] = useState<SnippetLanguage>(
    initialData?.language ?? SnippetLanguage.PLAINTEXT,
  );
  const [category, setCategory] = useState<SnippetCategory>(
    initialData?.category ?? SnippetCategory.CUSTOM,
  );
  const [code, setCode] = useState(initialData?.code ?? "");
  const [tags, setTags] = useState<string[]>(initialData?.tags ?? []);
  const [tagInput, setTagInput] = useState("");
  const [isFavorite, setIsFavorite] = useState(
    initialData?.is_favorite ?? false,
  );

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setLanguage(SnippetLanguage.PLAINTEXT);
    setCategory(SnippetCategory.CUSTOM);
    setCode("");
    setTags([]);
    setIsFavorite(false);
  }, []);

  const submitForm = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      onSubmit({
        title,
        description: description || undefined,
        language,
        category,
        code,
        tags,
        is_favorite: isFavorite,
      });

      if (!isEditing) {
        resetForm();
      }

      onClose();
    },
    [
      category,
      code,
      description,
      isEditing,
      isFavorite,
      language,
      onClose,
      onSubmit,
      resetForm,
      tags,
      title,
    ],
  );

  const addTag = useCallback(() => {
    const trimmed = tagInput.trim();
    if (!trimmed) {
      return;
    }

    setTags((prevTags) => {
      if (prevTags.includes(trimmed)) {
        return prevTags;
      }

      return [...prevTags, trimmed];
    });
    setTagInput("");
  }, [tagInput]);

  const removeTag = useCallback((tag: string) => {
    setTags((prevTags) =>
      prevTags.filter((existingTag) => existingTag !== tag),
    );
  }, []);

  const handleTagKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key !== "Enter") {
        return;
      }

      event.preventDefault();
      addTag();
    },
    [addTag],
  );

  const isSubmitDisabled = !title.trim() || !code.trim();

  return {
    state: {
      title,
      description,
      language,
      category,
      code,
      tags,
      tagInput,
      isFavorite,
      isEditing,
    },
    actions: {
      setTitle,
      setDescription,
      setLanguage,
      setCategory,
      setCode,
      setTagInput,
      setIsFavorite,
      addTag,
      removeTag,
      submitForm,
      handleTagKeyDown,
    },
    isSubmitDisabled,
  };
};

function SnippetFormModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateSnippetRequest) => void;
  initialData?: CodeSnippet;
}) {
  const {
    state: {
      title,
      description,
      language,
      category,
      code,
      tags,
      tagInput,
      isFavorite,
      isEditing,
    },
    actions: {
      setTitle,
      setDescription,
      setLanguage,
      setCategory,
      setCode,
      setTagInput,
      setIsFavorite,
      addTag,
      removeTag,
      submitForm,
      handleTagKeyDown,
    },
    isSubmitDisabled,
  } = useSnippetForm({ initialData, onSubmit, onClose });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-black/90 border border-white/10 rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col backdrop-blur-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <h2 className="text-xl font-semibold text-foreground">
            {isEditing ? "Edit Snippet" : "Create Snippet"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 hover:bg-background rounded text-foreground-secondary hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form
          onSubmit={submitForm}
          className="flex-1 overflow-y-auto p-6"
          data-testid="snippet-form"
        >
          <div className="space-y-6">
            {/* Title */}
            <div>
              <label
                htmlFor="snippet-title"
                className="block text-sm font-medium text-foreground mb-2"
              >
                Title <span className="text-foreground-tertiary">*</span>
              </label>
              <input
                id="snippet-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="snippet-description"
                className="block text-sm font-medium text-foreground mb-2"
              >
                Description
              </label>
              <textarea
                id="snippet-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20 resize-none"
              />
            </div>

            {/* Language & Category */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="snippet-language"
                  className="block text-sm font-medium text-foreground mb-2"
                >
                  Language
                </label>
                <select
                  id="snippet-language"
                  value={language}
                  onChange={(e) =>
                    setLanguage(e.target.value as SnippetLanguage)
                  }
                  className="w-full px-3 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
                >
                  {Object.entries(SNIPPET_LANGUAGE_LABELS).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                </select>
              </div>
              <div>
                <label
                  htmlFor="snippet-category"
                  className="block text-sm font-medium text-foreground mb-2"
                >
                  Category
                </label>
                <select
                  id="snippet-category"
                  value={category}
                  onChange={(e) =>
                    setCategory(e.target.value as SnippetCategory)
                  }
                  className="w-full px-3 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
                >
                  {Object.entries(SNIPPET_CATEGORY_LABELS).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                </select>
              </div>
            </div>

            {/* Code */}
            <div>
              <label
                htmlFor="snippet-code"
                className="block text-sm font-medium text-foreground mb-2"
              >
                Code <span className="text-foreground-tertiary">*</span>
              </label>
              <div className="border border-white/10 rounded-xl overflow-hidden">
                <textarea
                  id="snippet-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  rows={12}
                  className="w-full px-3 py-2 bg-background text-foreground focus:outline-none resize-none font-mono text-sm"
                  required
                  placeholder="Paste your code here..."
                  spellCheck={false}
                />
              </div>
              {code && (
                <div className="mt-2 text-xs text-foreground-secondary">
                  Preview with {SNIPPET_LANGUAGE_LABELS[language]} syntax
                  highlighting
                </div>
              )}
              {code && (
                <div className="mt-2 rounded overflow-hidden max-h-64 overflow-y-auto">
                  <SyntaxHighlighter
                    language={language}
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      fontSize: "0.75rem",
                    }}
                    showLineNumbers
                  >
                    {code}
                  </SyntaxHighlighter>
                </div>
              )}
            </div>

            {/* Tags */}
            <div>
              <label
                htmlFor="snippet-tags"
                className="block text-sm font-medium text-foreground mb-2"
              >
                Tags
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  id="snippet-tags"
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  placeholder="Add a tag..."
                  className="flex-1 px-3 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
                />
                <button
                  type="button"
                  onClick={addTag}
                  className="px-4 py-2 bg-white text-black text-sm font-semibold rounded-xl hover:bg-white/90"
                >
                  Add
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
                className="w-4 h-4 text-foreground-tertiary"
              />
              <label htmlFor="favorite" className="text-sm text-foreground">
                Mark as favorite
              </label>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-foreground-secondary hover:text-foreground border border-white/10 rounded-xl hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={submitForm}
            className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90"
            disabled={isSubmitDisabled}
          >
            {isEditing ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

function SnippetsHeader({
  onExport,
  onImport,
  onCreate,
  exportPending,
  importPending,
}: {
  onExport: () => void;
  onImport: () => void;
  onCreate: () => void;
  exportPending: boolean;
  importPending: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Code Snippet Library
        </h1>
        <p className="text-foreground-secondary mt-1">
          Save and reuse code snippets across your projects
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onExport}
          className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-white/10 rounded-xl hover:bg-white/5"
          disabled={exportPending}
        >
          <Download className="w-4 h-4" />
          Export
        </button>
        <button
          type="button"
          onClick={onImport}
          className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-white/10 rounded-xl hover:bg-white/5"
          disabled={importPending}
        >
          <Upload className="w-4 h-4" />
          Import
        </button>
        <button
          type="button"
          onClick={onCreate}
          className="flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90"
        >
          <Plus className="w-4 h-4" />
          New Snippet
        </button>
      </div>
    </div>
  );
}

function StatsTile({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="p-3 bg-black/60 border border-white/10 rounded-lg">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-foreground-secondary">{label}</span>
        {icon}
      </div>
      <p className="text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

function SnippetsStats({ stats }: { stats: SnippetStats | undefined }) {
  if (!stats) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <StatsTile
        label="Total Snippets"
        value={stats.total_snippets}
        icon={<TrendingUp className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsTile
        label="Favorites"
        value={stats.total_favorites}
        icon={<Star className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsTile
        label="Languages"
        value={Object.keys(stats.snippets_by_language).length}
        icon={<Code2 className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsTile
        label="Total Tags"
        value={stats.total_tags}
        icon={
          <span className="text-foreground-tertiary text-xs">
            #{stats.total_tags}
          </span>
        }
      />
    </div>
  );
}

function SnippetsFilters({
  searchQuery,
  onSearchChange,
  selectedLanguage,
  onLanguageChange,
  selectedCategory,
  onCategoryChange,
  showFavoritesOnly,
  onToggleFavorites,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedLanguage: SnippetLanguage | "all";
  onLanguageChange: (value: SnippetLanguage | "all") => void;
  selectedCategory: SnippetCategory | "all";
  onCategoryChange: (value: SnippetCategory | "all") => void;
  showFavoritesOnly: boolean;
  onToggleFavorites: () => void;
}) {
  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search snippets..."
          data-snippets-search
          className="w-full pl-10 pr-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
        />
      </div>

      <select
        value={selectedLanguage}
        onChange={(event) =>
          onLanguageChange(event.target.value as SnippetLanguage | "all")
        }
        className="px-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
      >
        <option value="all">All Languages</option>
        {Object.entries(SNIPPET_LANGUAGE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <select
        value={selectedCategory}
        onChange={(event) =>
          onCategoryChange(event.target.value as SnippetCategory | "all")
        }
        className="px-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
      >
        <option value="all">All Categories</option>
        {Object.entries(SNIPPET_CATEGORY_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={onToggleFavorites}
        className={`flex items-center gap-2 px-4 py-2 border rounded-xl transition-colors ${
          showFavoritesOnly
            ? "bg-white text-black border-white"
            : "bg-black/60 text-foreground-secondary border-white/10 hover:bg-white/5"
        }`}
      >
        <Star className={`w-4 h-4 ${showFavoritesOnly ? "fill-white" : ""}`} />
        Favorites Only
      </button>
    </div>
  );
}

function SnippetsGrid({
  isLoading,
  filteredSnippets,
  searchQuery,
  showFavoritesOnly,
  selectedLanguage,
  selectedCategory,
  onCreateFirst,
  onEdit,
  onDelete,
  onUse,
  onToggleFavorite,
}: {
  isLoading: boolean;
  filteredSnippets: CodeSnippet[];
  searchQuery: string;
  showFavoritesOnly: boolean;
  selectedLanguage: SnippetLanguage | "all";
  selectedCategory: SnippetCategory | "all";
  onCreateFirst: () => void;
  onEdit: (snippet: CodeSnippet) => void;
  onDelete: (snippetId: string) => void;
  onUse: (snippet: CodeSnippet) => void;
  onToggleFavorite: (snippetId: string, isFavorite: boolean) => void;
}) {
  if (isLoading) {
    return <CardSkeletonGrid count={6} />;
  }

  if (filteredSnippets.length === 0) {
    const hasActiveFilters = Boolean(
      searchQuery ||
        showFavoritesOnly ||
        selectedLanguage !== "all" ||
        selectedCategory !== "all",
    );

    return (
      <div className="text-center py-12">
        <p className="text-foreground-secondary mb-4">
          {hasActiveFilters
            ? "No snippets found matching your criteria"
            : "You don't have any snippets yet. Create your first snippet to get started!"}
        </p>
        {!hasActiveFilters && (
          <button
            type="button"
            onClick={onCreateFirst}
            className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90"
          >
            Create Your First Snippet
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
      {filteredSnippets.map((snippet) => (
        <SnippetCard
          key={snippet.id}
          snippet={snippet}
          onEdit={onEdit}
          onDelete={onDelete}
          onUse={onUse}
          onToggleFavorite={onToggleFavorite}
        />
      ))}
    </div>
  );
}

function useSnippetsSettingsController() {
  const toast = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSnippet, setEditingSnippet] = useState<
    CodeSnippet | undefined
  >();
  const [selectedLanguage, setSelectedLanguage] = useState<
    SnippetLanguage | "all"
  >("all");
  const [selectedCategory, setSelectedCategory] = useState<
    SnippetCategory | "all"
  >("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

  const snippetsQuery = useSnippets({
    language: selectedLanguage !== "all" ? selectedLanguage : undefined,
    category: selectedCategory !== "all" ? selectedCategory : undefined,
    is_favorite: showFavoritesOnly || undefined,
  });
  const statsQuery = useSnippetStats();

  const createMutation = useCreateSnippet();
  const updateMutation = useUpdateSnippet();
  const deleteMutation = useDeleteSnippet();
  const exportMutation = useExportSnippets();
  const importMutation = useImportSnippets();
  const trackUsageMutation = useTrackSnippetUsage();

  const openCreateModal = useCallback(() => {
    setEditingSnippet(undefined);
    setIsModalOpen(true);
  }, []);

  const handleCreate = useCallback(
    (data: CreateSnippetRequest) => {
      createMutation.mutate(data, {
        onSuccess: () => toast.success("Snippet created successfully!"),
        onError: () => toast.error("Failed to create snippet"),
      });
    },
    [createMutation, toast],
  );

  const handleEdit = useCallback((snippet: CodeSnippet) => {
    setEditingSnippet(snippet);
    setIsModalOpen(true);
  }, []);

  const handleUpdate = useCallback(
    (data: CreateSnippetRequest) => {
      if (!editingSnippet) {
        return;
      }

      updateMutation.mutate(
        { snippetId: editingSnippet.id, data },
        {
          onSuccess: () => toast.success("Snippet updated successfully!"),
          onError: () => toast.error("Failed to update snippet"),
        },
      );
    },
    [editingSnippet, updateMutation, toast],
  );

  const handleDelete = useCallback(
    (snippetId: string) => {
      // eslint-disable-next-line no-alert
      const shouldDelete = window.confirm(
        "Are you sure you want to delete this snippet?",
      );
      if (shouldDelete) {
        deleteMutation.mutate(snippetId, {
          onSuccess: () => toast.success("Snippet deleted"),
          onError: () => toast.error("Failed to delete snippet"),
        });
      }
    },
    [deleteMutation, toast],
  );

  const handleUse = useCallback(
    (snippet: CodeSnippet) => {
      navigator.clipboard.writeText(snippet.code);
      trackUsageMutation.mutate(snippet.id);
      toast.success("Code copied to clipboard!");
    },
    [trackUsageMutation, toast],
  );

  const handleToggleFavorite = useCallback(
    (snippetId: string, isFavorite: boolean) => {
      updateMutation.mutate({ snippetId, data: { is_favorite: isFavorite } });
    },
    [updateMutation],
  );

  const handleExport = useCallback(async () => {
    try {
      const result = await exportMutation.mutateAsync({
        language: selectedLanguage !== "all" ? selectedLanguage : undefined,
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        is_favorite: showFavoritesOnly || undefined,
      });

      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const anchor = document.createElement("a");
      anchor.href = URL.createObjectURL(blob);
      anchor.download = `snippets_export_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(URL.createObjectURL(blob));

      toast.success(`Exported ${result.snippets.length} snippets!`);
    } catch (error) {
      toast.error("Failed to export snippets");
    }
  }, [
    exportMutation,
    selectedLanguage,
    selectedCategory,
    showFavoritesOnly,
    toast,
  ]);

  const handleImport = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) {
        return;
      }

      try {
        const text = await file.text();
        const collection = JSON.parse(text);
        const result = await importMutation.mutateAsync(collection);
        toast.success(
          `Imported ${result.imported} new and updated ${result.updated} snippets!`,
        );
      } catch (error) {
        toast.error("Failed to import snippets. Please check the file format.");
        // eslint-disable-next-line no-console
        console.error("Import error:", error);
      }
    };
    input.click();
  }, [importMutation, toast]);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setEditingSnippet(undefined);
  }, []);

  const filteredSnippets = useMemo(() => {
    const { data } = snippetsQuery;
    if (!data || !Array.isArray(data)) {
      return [] as CodeSnippet[];
    }

    if (!searchQuery.trim()) {
      return data;
    }

    const query = searchQuery.toLowerCase();
    return data.filter(
      (snippet) =>
        snippet.title.toLowerCase().includes(query) ||
        snippet.description?.toLowerCase().includes(query) ||
        snippet.code.toLowerCase().includes(query) ||
        snippet.tags.some((tag) => tag.toLowerCase().includes(query)),
    );
  }, [snippetsQuery.data, searchQuery]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "n") {
        event.preventDefault();
        openCreateModal();
      }

      if ((event.ctrlKey || event.metaKey) && event.key === "k") {
        event.preventDefault();
        document
          .querySelector<HTMLInputElement>("input[data-snippets-search]")
          ?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [openCreateModal]);

  const toggleFavoritesOnly = useCallback(() => {
    setShowFavoritesOnly((previous) => !previous);
  }, []);

  return {
    toast,
    isModalOpen,
    openCreateModal,
    handleCloseModal,
    editingSnippet,
    handleCreate,
    handleUpdate,
    handleEdit,
    handleDelete,
    handleUse,
    handleToggleFavorite,
    handleExport,
    handleImport,
    exportPending: exportMutation.isPending,
    importPending: importMutation.isPending,
    stats: statsQuery.data,
    isLoading: snippetsQuery.isLoading,
    filteredSnippets,
    selectedLanguage,
    setSelectedLanguage,
    selectedCategory,
    setSelectedCategory,
    searchQuery,
    setSearchQuery,
    showFavoritesOnly,
    toggleFavoritesOnly,
  } as const;
}

// Main Settings Screen
function SnippetsSettingsScreen() {
  const controller = useSnippetsSettingsController();

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <SnippetsHeader
          onExport={controller.handleExport}
          onImport={controller.handleImport}
          onCreate={controller.openCreateModal}
          exportPending={controller.exportPending}
          importPending={controller.importPending}
        />

        <SnippetsStats stats={controller.stats} />

        <SnippetsFilters
          searchQuery={controller.searchQuery}
          onSearchChange={controller.setSearchQuery}
          selectedLanguage={controller.selectedLanguage}
          onLanguageChange={controller.setSelectedLanguage}
          selectedCategory={controller.selectedCategory}
          onCategoryChange={controller.setSelectedCategory}
          showFavoritesOnly={controller.showFavoritesOnly}
          onToggleFavorites={controller.toggleFavoritesOnly}
        />

        <SnippetsGrid
          isLoading={controller.isLoading}
          filteredSnippets={controller.filteredSnippets}
          searchQuery={controller.searchQuery}
          showFavoritesOnly={controller.showFavoritesOnly}
          selectedLanguage={controller.selectedLanguage}
          selectedCategory={controller.selectedCategory}
          onCreateFirst={controller.openCreateModal}
          onEdit={controller.handleEdit}
          onDelete={controller.handleDelete}
          onUse={controller.handleUse}
          onToggleFavorite={controller.handleToggleFavorite}
        />

        <SnippetFormModal
          isOpen={controller.isModalOpen}
          onClose={controller.handleCloseModal}
          onSubmit={
            controller.editingSnippet
              ? controller.handleUpdate
              : controller.handleCreate
          }
          initialData={controller.editingSnippet}
        />

        <ToastContainer
          toasts={controller.toast.toasts}
          onRemove={controller.toast.removeToast}
        />
      </div>
    </div>
  );
}

export default SnippetsSettingsScreen;
