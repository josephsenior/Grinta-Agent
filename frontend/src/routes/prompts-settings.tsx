/**
 * Prompt Library Settings Page
 */

import React from "react";
import {
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  Star,
  TrendingUp,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useToast, ToastContainer } from "#/components/shared/toast";
import { CardSkeletonGrid } from "#/components/shared/card-skeleton";
import { PromptCard } from "#/components/features/prompts/prompt-card";
import { PromptFormModal } from "#/components/features/prompts/prompt-form-modal";
import {
  usePrompts,
  usePromptStats,
  useCreatePrompt,
  useUpdatePrompt,
  useDeletePrompt,
  useExportPrompts,
  useImportPrompts,
} from "#/hooks/query/use-prompts";
import type {
  CreatePromptRequest,
  PromptTemplate,
} from "#/types/prompt";
import { PromptCategory, PROMPT_CATEGORY_LABELS } from "#/types/prompt";
import { useDebounce } from "#/hooks/use-debounce";

function PromptsSettingsScreen() {
  const { t } = useTranslation();
  const toast = useToast();

  // State
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [editingPrompt, setEditingPrompt] = React.useState<
    PromptTemplate | undefined
  >();
  const [selectedCategory, setSelectedCategory] = React.useState<
    PromptCategory | "all"
  >("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [showFavoritesOnly, setShowFavoritesOnly] = React.useState(false);

  // Debounce search query for performance (waits 300ms after user stops typing)
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Queries
  const { data: prompts, isLoading } = usePrompts({
    category:
      selectedCategory !== "all" ? selectedCategory : undefined,
    is_favorite: showFavoritesOnly || undefined,
  });
  const { data: stats } = usePromptStats();

  // Mutations
  const createMutation = useCreatePrompt();
  const updateMutation = useUpdatePrompt();
  const deleteMutation = useDeletePrompt();
  const exportMutation = useExportPrompts();
  const importMutation = useImportPrompts();

  // Handlers
  const handleCreate = (data: CreatePromptRequest) => {
    createMutation.mutate(data, {
      onSuccess: () => toast.success("Prompt created successfully!"),
      onError: () => toast.error("Failed to create prompt"),
    });
  };

  const handleEdit = (prompt: PromptTemplate) => {
    setEditingPrompt(prompt);
    setIsModalOpen(true);
  };

  const handleUpdate = (data: CreatePromptRequest) => {
    if (editingPrompt) {
      updateMutation.mutate(
        {
          promptId: editingPrompt.id,
          data,
        },
        {
          onSuccess: () => toast.success("Prompt updated successfully!"),
          onError: () => toast.error("Failed to update prompt"),
        },
      );
    }
  };

  const handleDelete = (promptId: string) => {
    if (confirm(t("PROMPTS$DELETE_CONFIRM"))) {
      deleteMutation.mutate(promptId, {
        onSuccess: () => toast.success("Prompt deleted"),
        onError: () => toast.error("Failed to delete prompt"),
      });
    }
  };

  const handleUse = (prompt: PromptTemplate) => {
    navigator.clipboard.writeText(prompt.content);
    toast.success(t("PROMPTS$COPIED_TO_CLIPBOARD"));
  };

  const handleToggleFavorite = (promptId: string, isFavorite: boolean) => {
    updateMutation.mutate({
      promptId,
      data: { is_favorite: isFavorite },
    });
  };

  const handleExport = async () => {
    try {
      const result = await exportMutation.mutateAsync({
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        is_favorite: showFavoritesOnly || undefined,
      });

      const blob = new Blob([JSON.stringify(result, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `prompts_export_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success(`Exported ${result.prompts.length} prompts!`);
    } catch (error) {
      toast.error("Failed to export prompts");
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
          t("PROMPTS$IMPORT_SUCCESS", {
            imported: result.imported,
            updated: result.updated,
          }),
        );
      } catch (error) {
        toast.error(t("PROMPTS$IMPORT_ERROR"));
        console.error("Import error:", error);
      }
    };
    input.click();
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingPrompt(undefined);
  };

  // Filter prompts by search query
  // Use debounced search query for filtering (performance optimization)
  const filteredPrompts = React.useMemo(() => {
    if (!prompts || !Array.isArray(prompts)) return [];

    if (!debouncedSearchQuery.trim()) return prompts;

    const query = debouncedSearchQuery.toLowerCase();
    return prompts.filter(
      (p) =>
        p.title.toLowerCase().includes(query) ||
        p.description?.toLowerCase().includes(query) ||
        p.content.toLowerCase().includes(query) ||
        p.tags.some((tag) => tag.toLowerCase().includes(query)),
    );
  }, [prompts, debouncedSearchQuery]);

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {t("PROMPTS$TITLE")}
          </h1>
          <p className="text-foreground-secondary mt-1">
            {t("PROMPTS$SUBTITLE")}
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
            {t("PROMPTS$EXPORT")}
          </button>
          <button
            type="button"
            onClick={handleImport}
            className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-violet-500/20 rounded hover:bg-background"
            disabled={importMutation.isPending}
          >
            <Upload className="w-4 h-4" />
            {t("PROMPTS$IMPORT")}
          </button>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
          >
            <Plus className="w-4 h-4" />
            {t("PROMPTS$NEW_PROMPT")}
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                {t("PROMPTS$TOTAL_PROMPTS")}
              </span>
              <TrendingUp className="w-4 h-4 text-primary" />
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {stats.total_prompts}
            </p>
          </div>

          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                {t("PROMPTS$FAVORITES")}
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
                {t("PROMPTS$CATEGORIES")}
              </span>
              <Filter className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-semibold text-foreground mt-2">
              {Object.keys(stats.prompts_by_category).length}
            </p>
          </div>

          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-foreground-secondary text-sm">
                {t("PROMPTS$TOTAL_TAGS")}
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
            placeholder={t("PROMPTS$SEARCH_PLACEHOLDER")}
            className="w-full pl-10 pr-4 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
          />
        </div>

        {/* Category filter */}
        <select
          value={selectedCategory}
          onChange={(e) =>
            setSelectedCategory(e.target.value as PromptCategory | "all")
          }
          className="px-4 py-2 bg-background border border-violet-500/20 rounded text-foreground focus:outline-none focus:border-border-active"
        >
          <option value="all">{t("PROMPTS$ALL_CATEGORIES")}</option>
          {Object.entries(PROMPT_CATEGORY_LABELS).map(([value, label]) => (
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
          {t("PROMPTS$FAVORITES_ONLY")}
        </button>
      </div>

      {/* Prompts grid */}
      {isLoading ? (
        <CardSkeletonGrid count={6} />
      ) : filteredPrompts.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-foreground-secondary mb-4">
            {searchQuery || showFavoritesOnly || selectedCategory !== "all"
              ? t("PROMPTS$NO_RESULTS")
              : t("PROMPTS$EMPTY_STATE")}
          </p>
          {!searchQuery && !showFavoritesOnly && selectedCategory === "all" && (
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            >
              {t("PROMPTS$CREATE_FIRST")}
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPrompts.map((prompt) => (
            <PromptCard
              key={prompt.id}
              prompt={prompt}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onUse={handleUse}
              onToggleFavorite={handleToggleFavorite}
            />
          ))}
        </div>
      )}

      {/* Modal */}
      <PromptFormModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={editingPrompt ? handleUpdate : handleCreate}
        initialData={editingPrompt}
      />

      {/* Toast notifications */}
      <ToastContainer toasts={toast.toasts} onRemove={toast.removeToast} />
    </div>
  );
}

export default PromptsSettingsScreen;

