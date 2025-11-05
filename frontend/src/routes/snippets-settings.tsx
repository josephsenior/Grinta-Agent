/**
 * Code Snippet Library Settings Page
 */

import React, { useState, useMemo } from "react";
import {
  Plus,
  Search,
  Filter,
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
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  const [showMenu, setShowMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(snippet.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    setShowMenu(false);
  };

  return (
    <div className="bg-black border border-violet-500/20 rounded-lg p-4 hover:border-border-active transition-colors">
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
                <Heart className="w-4 h-4 text-red-500 fill-red-500 flex-shrink-0" />
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
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 top-8 z-20 w-48 bg-black border border-violet-500/20 rounded-lg shadow-lg py-1">
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
                    className={`w-4 h-4 ${snippet.is_favorite ? "fill-red-500 text-red-500" : ""}`}
                  />
                  {snippet.is_favorite ? "Remove Favorite" : "Add Favorite"}
                </button>
                <div className="border-t border-violet-500/20 my-1" />
                <button
                  type="button"
                  onClick={() => {
                    onDelete(snippet.id);
                    setShowMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-500 hover:bg-background flex items-center gap-2"
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
            className="px-2 py-1 bg-black border border-violet-500/20 rounded text-xs text-foreground hover:bg-background flex items-center gap-1"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-green-500" />
                <span className="text-green-500">Copied!</span>
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
      <div className="flex items-center justify-between pt-3 border-t border-violet-500/20">
        <div className="text-xs text-foreground-secondary">
          Used {snippet.usage_count} times
        </div>
        <button
          type="button"
          onClick={() => onUse(snippet)}
          className="px-3 py-1.5 bg-primary text-white text-sm font-medium rounded hover:bg-primary-dark transition-colors"
        >
          Use Snippet
        </button>
      </div>
    </div>
  );
}

// Snippet Form Modal Component
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
  const { t } = useTranslation();
  const [title, setTitle] = useState(initialData?.title || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [language, setLanguage] = useState<SnippetLanguage>(
    initialData?.language || SnippetLanguage.PLAINTEXT,
  );
  const [category, setCategory] = useState<SnippetCategory>(
    initialData?.category || SnippetCategory.CUSTOM,
  );
  const [code, setCode] = useState(initialData?.code || "");
  const [tags, setTags] = useState<string[]>(initialData?.tags || []);
  const [tagInput, setTagInput] = useState("");
  const [isFavorite, setIsFavorite] = useState(initialData?.is_favorite || false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      title,
      description: description || undefined,
      language,
      category,
      code,
      tags,
      is_favorite: isFavorite,
    });
    if (!initialData) {
      setTitle("");
      setDescription("");
      setLanguage(SnippetLanguage.PLAINTEXT);
      setCategory(SnippetCategory.CUSTOM);
      setCode("");
      setTags([]);
      setIsFavorite(false);
    }
    onClose();
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-black border border-violet-500/20 rounded-lg w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-violet-500/20">
          <h2 className="text-xl font-semibold text-foreground">
            {initialData ? "Edit Snippet" : "Create Snippet"}
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
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active resize-none"
              />
            </div>

            {/* Language & Category */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as SnippetLanguage)}
                  className="w-full px-3 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
                >
                  {Object.entries(SNIPPET_LANGUAGE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as SnippetCategory)}
                  className="w-full px-3 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
                >
                  {Object.entries(SNIPPET_CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Code */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Code <span className="text-red-500">*</span>
              </label>
              <div className="border border-violet-500/20 rounded overflow-hidden">
                <textarea
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
                  Preview with {SNIPPET_LANGUAGE_LABELS[language]} syntax highlighting
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
              <label className="block text-sm font-medium text-foreground mb-2">
                Tags
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
                  placeholder="Add a tag..."
                  className="flex-1 px-3 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
                />
                <button
                  type="button"
                  onClick={addTag}
                  className="px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark"
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
                className="w-4 h-4 text-primary focus:ring-primary"
              />
              <label htmlFor="favorite" className="text-sm text-foreground">
                Mark as favorite
              </label>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-violet-500/20">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-foreground-secondary hover:text-foreground"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            disabled={!title.trim() || !code.trim()}
          >
            {initialData ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Main Settings Screen
function SnippetsSettingsScreen() {
  const { t } = useTranslation();
  const toast = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSnippet, setEditingSnippet] = useState<CodeSnippet | undefined>();
  const [selectedLanguage, setSelectedLanguage] = useState<SnippetLanguage | "all">("all");
  const [selectedCategory, setSelectedCategory] = useState<SnippetCategory | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

  const { data: snippets, isLoading } = useSnippets({
    language: selectedLanguage !== "all" ? selectedLanguage : undefined,
    category: selectedCategory !== "all" ? selectedCategory : undefined,
    is_favorite: showFavoritesOnly || undefined,
  });
  const { data: stats } = useSnippetStats();

  const createMutation = useCreateSnippet();
  const updateMutation = useUpdateSnippet();
  const deleteMutation = useDeleteSnippet();
  const exportMutation = useExportSnippets();
  const importMutation = useImportSnippets();
  const trackUsageMutation = useTrackSnippetUsage();

  const handleCreate = (data: CreateSnippetRequest) => {
    createMutation.mutate(data, {
      onSuccess: () => toast.success("Snippet created successfully!"),
      onError: () => toast.error("Failed to create snippet"),
    });
  };

  const handleEdit = (snippet: CodeSnippet) => {
    setEditingSnippet(snippet);
    setIsModalOpen(true);
  };

  const handleUpdate = (data: CreateSnippetRequest) => {
    if (editingSnippet) {
      updateMutation.mutate(
        { snippetId: editingSnippet.id, data },
        {
          onSuccess: () => toast.success("Snippet updated successfully!"),
          onError: () => toast.error("Failed to update snippet"),
        },
      );
    }
  };

  const handleDelete = (snippetId: string) => {
    if (confirm("Are you sure you want to delete this snippet?")) {
      deleteMutation.mutate(snippetId, {
        onSuccess: () => toast.success("Snippet deleted"),
        onError: () => toast.error("Failed to delete snippet"),
      });
    }
  };

  const handleUse = (snippet: CodeSnippet) => {
    navigator.clipboard.writeText(snippet.code);
    trackUsageMutation.mutate(snippet.id);
    toast.success("Code copied to clipboard!");
  };

  const handleToggleFavorite = (snippetId: string, isFavorite: boolean) => {
    updateMutation.mutate({ snippetId, data: { is_favorite: isFavorite } });
  };

  const handleExport = async () => {
    try {
      const result = await exportMutation.mutateAsync({
        language: selectedLanguage !== "all" ? selectedLanguage : undefined,
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        is_favorite: showFavoritesOnly || undefined,
      });

      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `snippets_export_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success(`Exported ${result.snippets.length} snippets!`);
    } catch (error) {
      toast.error("Failed to export snippets");
    }
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const collection = JSON.parse(text);
        const result = await importMutation.mutateAsync(collection);
        toast.success(
          `Imported ${result.imported} new and updated ${result.updated} snippets!`,
        );
      } catch (error) {
        toast.error("Failed to import snippets. Please check the file format.");
        console.error("Import error:", error);
      }
    };
    input.click();
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingSnippet(undefined);
  };

  const filteredSnippets = useMemo(() => {
    if (!snippets || !Array.isArray(snippets)) return [];

    if (!searchQuery.trim()) return snippets;

    const query = searchQuery.toLowerCase();
    return snippets.filter(
      (s) =>
        s.title.toLowerCase().includes(query) ||
        s.description?.toLowerCase().includes(query) ||
        s.code.toLowerCase().includes(query) ||
        s.tags.some((tag) => tag.toLowerCase().includes(query)),
    );
  }, [snippets, searchQuery]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + N to create new snippet
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        setIsModalOpen(true);
      }
      
      // Ctrl/Cmd + K to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('input[placeholder="Search snippets..."]')?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
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
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-violet-500/20 rounded hover:bg-background"
            disabled={exportMutation.isPending}
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            type="button"
            onClick={handleImport}
            className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-violet-500/20 rounded hover:bg-background"
            disabled={importMutation.isPending}
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
          >
            <Plus className="w-4 h-4" />
            New Snippet
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                Total Snippets
              </span>
              <TrendingUp className="w-4 h-4 text-primary" />
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {stats.total_snippets}
            </p>
          </div>

          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                Favorites
              </span>
              <Star className="w-4 h-4 text-yellow-500" />
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {stats.total_favorites}
            </p>
          </div>

          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                Languages
              </span>
              <Code2 className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {Object.keys(stats.snippets_by_language).length}
            </p>
          </div>

          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                Total Tags
              </span>
              <span className="text-green-500 text-xs">#{stats.total_tags}</span>
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {stats.total_tags}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search snippets..."
            className="w-full pl-10 pr-4 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
          />
        </div>

        {/* Language filter */}
        <select
          value={selectedLanguage}
          onChange={(e) =>
            setSelectedLanguage(e.target.value as SnippetLanguage | "all")
          }
          className="px-4 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
        >
          <option value="all">All Languages</option>
          {Object.entries(SNIPPET_LANGUAGE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        {/* Category filter */}
        <select
          value={selectedCategory}
          onChange={(e) =>
            setSelectedCategory(e.target.value as SnippetCategory | "all")
          }
          className="px-4 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
        >
          <option value="all">All Categories</option>
          {Object.entries(SNIPPET_CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        {/* Favorites filter */}
        <button
          type="button"
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          className={`flex items-center gap-2 px-4 py-2 border rounded transition-colors ${
            showFavoritesOnly
              ? "bg-primary text-white border-primary"
              : "bg-background text-foreground-secondary border-violet-500/20 hover:bg-black"
          }`}
        >
          <Star
            className={`w-4 h-4 ${showFavoritesOnly ? "fill-white" : ""}`}
          />
          Favorites Only
        </button>
      </div>

      {/* Snippets grid */}
      {isLoading ? (
        <CardSkeletonGrid count={6} />
      ) : filteredSnippets.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-foreground-secondary mb-4">
            {searchQuery || showFavoritesOnly || selectedLanguage !== "all" || selectedCategory !== "all"
              ? "No snippets found matching your criteria"
              : "You don't have any snippets yet. Create your first snippet to get started!"}
          </p>
          {!searchQuery && !showFavoritesOnly && selectedLanguage === "all" && selectedCategory === "all" && (
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            >
              Create Your First Snippet
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSnippets.map((snippet) => (
            <SnippetCard
              key={snippet.id}
              snippet={snippet}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onUse={handleUse}
              onToggleFavorite={handleToggleFavorite}
            />
          ))}
        </div>
      )}

      {/* Modal */}
      <SnippetFormModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={editingSnippet ? handleUpdate : handleCreate}
        initialData={editingSnippet}
      />

      {/* Toast notifications */}
      <ToastContainer toasts={toast.toasts} onRemove={toast.removeToast} />
    </div>
  );
}

export default SnippetsSettingsScreen;

