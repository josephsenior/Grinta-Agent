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
import type { CreatePromptRequest, PromptTemplate } from "#/types/prompt";
import { PromptCategory, PROMPT_CATEGORY_LABELS } from "#/types/prompt";
import { useDebounce } from "#/hooks/use-debounce";
import { logger } from "#/utils/logger";

function usePromptsSettingsController() {
  const { t } = useTranslation();
  const toast = useToast();
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [editingPrompt, setEditingPrompt] = React.useState<
    PromptTemplate | undefined
  >();
  const [selectedCategory, setSelectedCategory] = React.useState<
    PromptCategory | "all"
  >("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [showFavoritesOnly, setShowFavoritesOnly] = React.useState(false);

  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const promptsQuery = usePrompts({
    category: selectedCategory !== "all" ? selectedCategory : undefined,
    is_favorite: showFavoritesOnly || undefined,
  });
  const statsQuery = usePromptStats();

  const createMutation = useCreatePrompt();
  const updateMutation = useUpdatePrompt();
  const deleteMutation = useDeletePrompt();
  const exportMutation = useExportPrompts();
  const importMutation = useImportPrompts();

  const filteredPrompts = React.useMemo(() => {
    const prompts = promptsQuery.data;
    if (!prompts || !Array.isArray(prompts)) {
      return [];
    }
    if (!debouncedSearchQuery.trim()) {
      return prompts;
    }
    const query = debouncedSearchQuery.toLowerCase();
    return prompts.filter(
      (prompt) =>
        prompt.title.toLowerCase().includes(query) ||
        prompt.description?.toLowerCase().includes(query) ||
        prompt.content.toLowerCase().includes(query) ||
        prompt.tags.some((tag) => tag.toLowerCase().includes(query)),
    );
  }, [promptsQuery.data, debouncedSearchQuery]);

  const handleCreatePrompt = React.useCallback(
    (data: CreatePromptRequest) => {
      createMutation.mutate(data, {
        onSuccess: () => toast.success("Prompt created successfully!"),
        onError: () => toast.error("Failed to create prompt"),
      });
    },
    [createMutation, toast],
  );

  const handleEditPrompt = React.useCallback((prompt: PromptTemplate) => {
    setEditingPrompt(prompt);
    setIsModalOpen(true);
  }, []);

  const handleUpdatePrompt = React.useCallback(
    (data: CreatePromptRequest) => {
      if (!editingPrompt) {
        return;
      }
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
    },
    [editingPrompt, toast, updateMutation],
  );

  const handleDeletePrompt = React.useCallback(
    (promptId: string) => {
      // eslint-disable-next-line no-alert
      const shouldDelete = window.confirm(t("PROMPTS$DELETE_CONFIRM"));
      if (!shouldDelete) {
        return;
      }
      deleteMutation.mutate(promptId, {
        onSuccess: () => toast.success("Prompt deleted"),
        onError: () => toast.error("Failed to delete prompt"),
      });
    },
    [deleteMutation, toast, t],
  );

  const handleUsePrompt = React.useCallback(
    (prompt: PromptTemplate) => {
      navigator.clipboard.writeText(prompt.content);
      toast.success(t("PROMPTS$COPIED_TO_CLIPBOARD"));
    },
    [toast, t],
  );

  const handleToggleFavorite = React.useCallback(
    (promptId: string, isFavorite: boolean) => {
      updateMutation.mutate({
        promptId,
        data: { is_favorite: isFavorite },
      });
    },
    [updateMutation],
  );

  const handleExport = React.useCallback(async () => {
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
  }, [exportMutation, selectedCategory, showFavoritesOnly, toast]);

  const handleImport = React.useCallback(() => {
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
          t("PROMPTS$IMPORT_SUCCESS", {
            imported: result.imported,
            updated: result.updated,
          }),
        );
      } catch (error) {
        toast.error(t("PROMPTS$IMPORT_ERROR"));
        logger.error("Import error:", error);
      }
    };
    input.click();
  }, [importMutation, t, toast]);

  const openCreateModal = React.useCallback(() => {
    setEditingPrompt(undefined);
    setIsModalOpen(true);
  }, []);

  const closeModal = React.useCallback(() => {
    setIsModalOpen(false);
    setEditingPrompt(undefined);
  }, []);

  const toggleFavoritesOnly = React.useCallback(() => {
    setShowFavoritesOnly((prev) => !prev);
  }, []);

  return {
    t,
    stats: statsQuery.data,
    isLoading: promptsQuery.isLoading,
    filteredPrompts,
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    showFavoritesOnly,
    toggleFavoritesOnly,
    handleExport,
    handleImport,
    handleCreatePrompt,
    handleUpdatePrompt,
    handleEditPrompt,
    handleDeletePrompt,
    handleUsePrompt,
    handleToggleFavorite,
    isModalOpen,
    openCreateModal,
    closeModal,
    editingPrompt,
    toast,
    exportIsPending: exportMutation.isPending,
    importIsPending: importMutation.isPending,
  } as const;
}

function PromptsHeader({
  t,
  onExport,
  onImport,
  onCreate,
  exportDisabled,
  importDisabled,
}: {
  t: ReturnType<typeof useTranslation>["t"];
  onExport: () => void;
  onImport: () => void;
  onCreate: () => void;
  exportDisabled: boolean;
  importDisabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between w-full">
      <div className="w-full">
        <h1 className="text-2xl font-semibold text-foreground w-full">
          {t("PROMPTS$TITLE")}
        </h1>
        <p className="text-foreground-secondary mt-1 w-full">
          {t("PROMPTS$SUBTITLE")}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onExport}
          className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-white/10 rounded-xl hover:bg-white/5"
          disabled={exportDisabled}
        >
          <Download className="w-4 h-4" />
          {t("PROMPTS$EXPORT")}
        </button>
        <button
          type="button"
          onClick={onImport}
          className="flex items-center gap-2 px-4 py-2 text-foreground-secondary hover:text-foreground border border-white/10 rounded-xl hover:bg-white/5"
          disabled={importDisabled}
        >
          <Upload className="w-4 h-4" />
          {t("PROMPTS$IMPORT")}
        </button>
        <button
          type="button"
          onClick={onCreate}
          className="flex items-center gap-2 px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90"
        >
          <Plus className="w-4 h-4" />
          {t("PROMPTS$NEW_PROMPT")}
        </button>
      </div>
    </div>
  );
}

function StatsCard({
  title,
  value,
  icon,
  badge,
}: {
  title: string;
  value: number;
  icon?: React.ReactNode;
  badge?: string;
}) {
  return (
    <div className="p-3 bg-black/60 border border-white/10 rounded-lg">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-foreground-secondary">{title}</span>
        {badge ? (
          <span className="text-xs text-foreground-tertiary">{badge}</span>
        ) : (
          icon
        )}
      </div>
      <p className="text-lg font-semibold text-foreground w-full">{value}</p>
    </div>
  );
}

function PromptsStatsSection({
  stats,
  t,
}: {
  stats: NonNullable<ReturnType<typeof usePromptStats>["data"]>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <StatsCard
        title={t("PROMPTS$TOTAL_PROMPTS")}
        value={stats.total_prompts}
        icon={<TrendingUp className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsCard
        title={t("PROMPTS$FAVORITES")}
        value={stats.total_favorites}
        icon={<Star className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsCard
        title={t("PROMPTS$CATEGORIES")}
        value={Object.keys(stats.prompts_by_category).length}
        icon={<Filter className="w-3 h-3 text-foreground-tertiary" />}
      />
      <StatsCard
        title={t("PROMPTS$TOTAL_TAGS")}
        value={stats.total_tags}
        badge={`#${stats.total_tags}`}
      />
    </div>
  );
}

function PromptsFilters({
  t,
  searchQuery,
  onSearchChange,
  selectedCategory,
  onCategoryChange,
  showFavoritesOnly,
  toggleFavoritesOnly,
}: {
  t: ReturnType<typeof useTranslation>["t"];
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedCategory: PromptCategory | "all";
  onCategoryChange: (value: PromptCategory | "all") => void;
  showFavoritesOnly: boolean;
  toggleFavoritesOnly: () => void;
}) {
  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("PROMPTS$SEARCH_PLACEHOLDER")}
          className="w-full pl-10 pr-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
        />
      </div>

      <select
        value={selectedCategory}
        onChange={(event) =>
          onCategoryChange(event.target.value as PromptCategory | "all")
        }
        className="px-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-white/20"
      >
        <option value="all">{t("PROMPTS$ALL_CATEGORIES")}</option>
        {Object.entries(PROMPT_CATEGORY_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={toggleFavoritesOnly}
        className={`flex items-center gap-2 px-4 py-2 border rounded transition-colors ${
          showFavoritesOnly
            ? "bg-white text-black border-white"
            : "bg-black/60 text-foreground-secondary border-white/10 hover:bg-white/5"
        }`}
      >
        <Star className={`w-4 h-4 ${showFavoritesOnly ? "fill-white" : ""}`} />
        {t("PROMPTS$FAVORITES_ONLY")}
      </button>
    </div>
  );
}

function PromptsGridSection({
  isLoading,
  filteredPrompts,
  searchQuery,
  showFavoritesOnly,
  selectedCategory,
  onCreate,
  onEdit,
  onDelete,
  onUse,
  onToggleFavorite,
  t,
}: {
  isLoading: boolean;
  filteredPrompts: PromptTemplate[];
  searchQuery: string;
  showFavoritesOnly: boolean;
  selectedCategory: PromptCategory | "all";
  onCreate: () => void;
  onEdit: (prompt: PromptTemplate) => void;
  onDelete: (promptId: string) => void;
  onUse: (prompt: PromptTemplate) => void;
  onToggleFavorite: (promptId: string, isFavorite: boolean) => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (isLoading) {
    return <CardSkeletonGrid count={6} />;
  }

  if (filteredPrompts.length === 0) {
    const isFiltered = Boolean(
      searchQuery || showFavoritesOnly || selectedCategory !== "all",
    );

    return (
      <div className="text-center py-12">
        <p className="text-foreground-secondary mb-4">
          {isFiltered ? t("PROMPTS$NO_RESULTS") : t("PROMPTS$EMPTY_STATE")}
        </p>
        {!isFiltered && (
          <button
            type="button"
            onClick={onCreate}
            className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90"
          >
            {t("PROMPTS$CREATE_FIRST")}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {filteredPrompts.map((prompt) => (
        <PromptCard
          key={prompt.id}
          prompt={prompt}
          onEdit={onEdit}
          onDelete={onDelete}
          onUse={onUse}
          onToggleFavorite={onToggleFavorite}
        />
      ))}
    </div>
  );
}

function PromptsSettingsScreen() {
  const controller = usePromptsSettingsController();
  const {
    t,
    stats,
    isLoading,
    filteredPrompts,
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    showFavoritesOnly,
    toggleFavoritesOnly,
    handleExport,
    handleImport,
    handleCreatePrompt,
    handleEditPrompt,
    handleDeletePrompt,
    handleUsePrompt,
    handleToggleFavorite,
    handleUpdatePrompt,
    isModalOpen,
    openCreateModal,
    closeModal,
    editingPrompt,
    toast,
    exportIsPending,
    importIsPending,
  } = controller;

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <PromptsHeader
          t={t}
          onExport={handleExport}
          onImport={handleImport}
          onCreate={openCreateModal}
          exportDisabled={exportIsPending}
          importDisabled={importIsPending}
        />

        {stats && <PromptsStatsSection stats={stats} t={t} />}

        <PromptsFilters
          t={t}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          showFavoritesOnly={showFavoritesOnly}
          toggleFavoritesOnly={toggleFavoritesOnly}
        />

        <PromptsGridSection
          isLoading={isLoading}
          filteredPrompts={filteredPrompts}
          searchQuery={searchQuery}
          showFavoritesOnly={showFavoritesOnly}
          selectedCategory={selectedCategory}
          onCreate={openCreateModal}
          onEdit={handleEditPrompt}
          onDelete={handleDeletePrompt}
          onUse={handleUsePrompt}
          onToggleFavorite={handleToggleFavorite}
          t={t}
        />

        <PromptFormModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={editingPrompt ? handleUpdatePrompt : handleCreatePrompt}
          initialData={editingPrompt}
        />

        <ToastContainer toasts={toast.toasts} onRemove={toast.removeToast} />
      </div>
    </div>
  );
}

export default PromptsSettingsScreen;
