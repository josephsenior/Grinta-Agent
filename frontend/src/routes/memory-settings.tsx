import { useState, useMemo, useCallback } from "react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import {
  Brain,
  Plus,
  Search,
  Download,
  Upload,
  Loader2,
  Lightbulb,
  Palette,
  Building2,
} from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import { MemoryCard } from "#/components/features/memory/memory-card";
import { MemoryFormModal } from "#/components/features/memory/memory-form-modal";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import {
  useMemories,
  useCreateMemory,
  useUpdateMemory,
  useDeleteMemory,
  useMemoryStats,
  useExportMemories,
  useImportMemories,
} from "#/hooks/query/use-memory";
import type {
  CreateMemoryRequest,
  Memory,
  MemoryCategory,
  MemoryStats,
  UpdateMemoryRequest,
} from "#/types/memory";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { useDebounce } from "#/hooks/use-debounce";

type CategoryFilter = MemoryCategory | "all";

type MemoryFormValues = CreateMemoryRequest;

interface MemoryImportResult {
  status: string;
  imported: number;
  total: number;
}

interface CategoryOption {
  key: CategoryFilter;
  labelKey: string;
  defaultLabel: string;
  icon?: ComponentType<{ className?: string }>;
  activeClass: string;
}

const JSON_MIME_TYPE = "application/json";

const CATEGORY_OPTIONS: CategoryOption[] = [
  {
    key: "all",
    labelKey: "memorySettings.filters.all",
    defaultLabel: "All",
    activeClass: "bg-white text-black",
  },
  {
    key: "technical",
    labelKey: "memorySettings.filters.technical",
    defaultLabel: "Technical",
    icon: Lightbulb,
    activeClass: "bg-blue-500 text-white",
  },
  {
    key: "preference",
    labelKey: "memorySettings.filters.preference",
    defaultLabel: "Preferences",
    icon: Palette,
    activeClass: "bg-purple-500 text-white",
  },
  {
    key: "project",
    labelKey: "memorySettings.filters.project",
    defaultLabel: "Project",
    icon: Building2,
    activeClass: "bg-green-500 text-white",
  },
];

function filterMemories(
  memories: Memory[] | undefined,
  category: CategoryFilter,
  rawQuery: string,
): Memory[] {
  if (!Array.isArray(memories) || memories.length === 0) {
    return [];
  }

  const query = rawQuery.trim().toLowerCase();

  const byCategory =
    category === "all"
      ? memories
      : memories.filter((memory) => memory.category === category);

  const byQuery = query
    ? byCategory.filter(
        (memory) =>
          memory.title.toLowerCase().includes(query) ||
          memory.content.toLowerCase().includes(query) ||
          memory.tags.some((tag) => tag.toLowerCase().includes(query)),
      )
    : byCategory;

  return [...byQuery].sort((a, b) => (b.usageCount || 0) - (a.usageCount || 0));
}

function toUpdateRequest(values: MemoryFormValues): UpdateMemoryRequest {
  const { title, content, category, tags, importance, conversationId } = values;
  return {
    title,
    content,
    category,
    tags,
    importance,
    ...(conversationId ? { conversationId } : {}),
  };
}

interface MemoryHeaderProps {
  t: TFunction;
  onCreate: () => void;
  onExport: () => void;
  onImport: () => void;
}

function MemoryHeader({ t, onCreate, onExport, onImport }: MemoryHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Brain className="w-8 h-8 text-foreground-tertiary" />
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            {t("memorySettings.header.title", "Memory Management")}
          </h2>
          <p className="text-sm text-foreground-secondary mt-1">
            {t(
              "memorySettings.header.subtitle",
              "Store and manage persistent memories for better AI assistance",
            )}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <BrandButton
          variant="secondary"
          onClick={onExport}
          type="button"
          testId="export-memories"
          className="flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          {t("memorySettings.actions.export", "Export")}
        </BrandButton>
        <BrandButton
          variant="secondary"
          onClick={onImport}
          type="button"
          testId="import-memories"
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          {t("memorySettings.actions.import", "Import")}
        </BrandButton>
        <BrandButton
          variant="primary"
          onClick={onCreate}
          type="button"
          testId="add-memory"
          className="flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          {t("memorySettings.actions.addMemory", "Add Memory")}
        </BrandButton>
      </div>
    </div>
  );
}

interface MemoryStatsSummaryProps {
  t: TFunction;
  stats: MemoryStats;
}

function MemoryStatsSummary({ t, stats }: MemoryStatsSummaryProps) {
  const cards = [
    {
      label: t("memorySettings.stats.total", "Total"),
      value: stats.total,
      valueClass: "text-foreground",
    },
    {
      label: t("memorySettings.stats.technical", "Technical"),
      value: stats.byCategory?.technical ?? 0,
      valueClass: "text-foreground-tertiary",
    },
    {
      label: t("memorySettings.stats.preferences", "Preferences"),
      value: stats.byCategory?.preference ?? 0,
      valueClass: "text-foreground-tertiary",
    },
    {
      label: t("memorySettings.stats.project", "Project"),
      value: stats.byCategory?.project ?? 0,
      valueClass: "text-foreground-tertiary",
    },
    {
      label: t("memorySettings.stats.usedToday", "Used Today"),
      value: stats.usedToday,
      valueClass: "text-foreground-tertiary",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map(({ label, value, valueClass }) => (
        <div
          key={label}
          className="p-3 bg-black/60 border border-white/10 rounded-lg"
        >
          <p className="text-xs text-foreground-secondary mb-1">{label}</p>
          <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
        </div>
      ))}
    </div>
  );
}

interface MemoryFiltersProps {
  t: TFunction;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedCategory: CategoryFilter;
  onCategoryChange: (category: CategoryFilter) => void;
  totalCount: number;
}

function MemoryFilters({
  t,
  searchQuery,
  onSearchChange,
  selectedCategory,
  onCategoryChange,
  totalCount,
}: MemoryFiltersProps) {
  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t(
            "memorySettings.filters.searchPlaceholder",
            "Search memories...",
          )}
          className="w-full pl-10 pr-4 py-2 bg-black/60 border border-white/10 rounded-xl text-foreground placeholder:text-foreground-secondary focus:outline-none focus:border-white/20"
        />
      </div>

      <div className="flex items-center gap-2">
        {CATEGORY_OPTIONS.map(
          ({ key, labelKey, defaultLabel, icon: Icon, activeClass }) => {
            const isActive = selectedCategory === key;
            const baseClass =
              "px-3 py-2 text-sm rounded-md transition-colors flex items-center gap-2";
            const inactiveClass =
              "bg-black text-foreground-secondary hover:text-foreground";
            const label =
              key === "all"
                ? t(labelKey, {
                    defaultValue: "All ({{count}})",
                    count: totalCount,
                  })
                : t(labelKey, defaultLabel);

            return (
              <button
                key={key}
                type="button"
                onClick={() => onCategoryChange(key)}
                className={`${baseClass} ${isActive ? activeClass : inactiveClass}`}
              >
                {Icon && <Icon className="w-4 h-4" />}
                {label}
              </button>
            );
          },
        )}
      </div>
    </div>
  );
}

interface MemoryListProps {
  t: TFunction;
  memories: Memory[];
  hasFilters: boolean;
  onCreate: () => void;
  onEdit: (memory: Memory) => void;
  onDelete: (memoryId: string) => void;
}

interface MemoryEmptyStateProps {
  t: TFunction;
  hasFilters: boolean;
  onCreate: () => void;
}

function MemoryEmptyState({ t, hasFilters, onCreate }: MemoryEmptyStateProps) {
  return (
    <div className="text-center p-8 bg-black/60 border border-white/10 rounded-2xl">
      <Brain className="w-12 h-12 text-foreground-secondary mx-auto mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">
        {hasFilters
          ? t("memorySettings.empty.filteredTitle", "No memories found")
          : t("memorySettings.empty.title", "No Memories Yet")}
      </h3>
      <p className="text-sm text-foreground-secondary mb-4">
        {hasFilters
          ? t(
              "memorySettings.empty.filteredDescription",
              "Try adjusting your filters",
            )
          : t(
              "memorySettings.empty.description",
              "Create your first memory to help the AI remember your preferences",
            )}
      </p>
      {!hasFilters && (
        <BrandButton
          variant="primary"
          onClick={onCreate}
          type="button"
          testId="add-first-memory"
          className="flex items-center gap-2 justify-center"
        >
          <Plus className="w-4 h-4" />
          {t("memorySettings.actions.addFirstMemory", "Add First Memory")}
        </BrandButton>
      )}
    </div>
  );
}

function MemoryList({
  t,
  memories,
  hasFilters,
  onCreate,
  onEdit,
  onDelete,
}: MemoryListProps) {
  if (memories.length === 0) {
    return (
      <MemoryEmptyState t={t} hasFilters={hasFilters} onCreate={onCreate} />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {memories.map((memory) => (
        <MemoryCard
          key={memory.id}
          memory={memory}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

function MemorySettingsScreen() {
  const { t } = useTranslation();
  const { data: memories, isLoading } = useMemories();
  const { data: stats } = useMemoryStats();
  const { mutate: createMemory, isPending: isCreating } = useCreateMemory();
  const { mutate: updateMemory, isPending: isUpdating } = useUpdateMemory();
  const { mutate: deleteMemory } = useDeleteMemory();
  const { mutateAsync: exportMemories } = useExportMemories();
  const { mutate: importMemories } = useImportMemories();

  const [showForm, setShowForm] = useState(false);
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [memoryToDelete, setMemoryToDelete] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] =
    useState<CategoryFilter>("all");

  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const filteredMemories = useMemo(
    () => filterMemories(memories, selectedCategory, debouncedSearchQuery),
    [memories, selectedCategory, debouncedSearchQuery],
  );

  const resolveErrorMessage = useCallback(
    (error: unknown) =>
      error instanceof Error
        ? error.message
        : t("common.error.unknown", "Unknown error"),
    [t],
  );

  const handleCreate = useCallback(() => {
    setEditingMemory(null);
    setShowForm(true);
  }, []);

  const handleEdit = useCallback((memory: Memory) => {
    setEditingMemory(memory);
    setShowForm(true);
  }, []);

  const handleCloseForm = useCallback(() => {
    setShowForm(false);
    setEditingMemory(null);
  }, []);

  const handleDeleteClick = useCallback((memoryId: string) => {
    setMemoryToDelete(memoryId);
    setDeleteConfirmOpen(true);
  }, []);

  const handleCancelDelete = useCallback(() => {
    setDeleteConfirmOpen(false);
    setMemoryToDelete(null);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (!memoryToDelete) {
      return;
    }

    deleteMemory(memoryToDelete, {
      onSuccess: () => {
        displaySuccessToast(
          t(
            "memorySettings.notifications.delete.success",
            "Memory deleted successfully",
          ),
        );
        handleCancelDelete();
      },
      onError: (error) => {
        displayErrorToast(
          t("memorySettings.notifications.delete.error", {
            defaultValue: "Failed to delete memory: {{message}}",
            message: resolveErrorMessage(error),
          }),
        );
      },
    });
  }, [
    deleteMemory,
    handleCancelDelete,
    memoryToDelete,
    resolveErrorMessage,
    t,
  ]);

  const createMemoryEntry = useCallback(
    (data: MemoryFormValues) => {
      createMemory(data, {
        onSuccess: () => {
          displaySuccessToast(
            t(
              "memorySettings.notifications.create.success",
              "Memory created successfully",
            ),
          );
          handleCloseForm();
        },
        onError: (error) => {
          displayErrorToast(
            t("memorySettings.notifications.create.error", {
              defaultValue: "Failed to create memory: {{message}}",
              message: resolveErrorMessage(error),
            }),
          );
        },
      });
    },
    [createMemory, handleCloseForm, resolveErrorMessage, t],
  );

  const updateMemoryEntry = useCallback(
    (memoryId: string, data: MemoryFormValues) => {
      updateMemory(
        { memoryId, updates: toUpdateRequest(data) },
        {
          onSuccess: () => {
            displaySuccessToast(
              t(
                "memorySettings.notifications.update.success",
                "Memory updated successfully",
              ),
            );
            handleCloseForm();
          },
          onError: (error) => {
            displayErrorToast(
              t("memorySettings.notifications.update.error", {
                defaultValue: "Failed to update memory: {{message}}",
                message: resolveErrorMessage(error),
              }),
            );
          },
        },
      );
    },
    [handleCloseForm, resolveErrorMessage, t, updateMemory],
  );

  const handleSave = useCallback(
    (data: MemoryFormValues) => {
      if (editingMemory) {
        updateMemoryEntry(editingMemory.id, data);
        return;
      }
      createMemoryEntry(data);
    },
    [createMemoryEntry, editingMemory, updateMemoryEntry],
  );

  const handleExport = useCallback(async () => {
    try {
      const data = await exportMemories();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: JSON_MIME_TYPE,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${t(
        "memorySettings.export.filePrefix",
        "memories-export",
      )}-${Date.now()}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      displaySuccessToast(
        t(
          "memorySettings.notifications.export.success",
          "Memories exported successfully",
        ),
      );
    } catch (error) {
      displayErrorToast(
        t(
          "memorySettings.notifications.export.error",
          "Failed to export memories",
        ),
      );
    }
  }, [exportMemories, t]);

  const handleImport = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (event) => {
      const target = event.target as HTMLInputElement;
      const file = target.files?.[0];
      if (!file) {
        return;
      }

      try {
        const text = await file.text();
        const data: unknown = JSON.parse(text);

        importMemories(
          { data, merge: true },
          {
            onSuccess: (result: MemoryImportResult) => {
              displaySuccessToast(
                t("memorySettings.notifications.import.success", {
                  defaultValue:
                    "Imported {{imported}} memories (Total: {{total}})",
                  imported: result.imported,
                  total: result.total,
                }),
              );
            },
            onError: (error) => {
              displayErrorToast(
                t("memorySettings.notifications.import.error", {
                  defaultValue: "Failed to import memories: {{message}}",
                  message: resolveErrorMessage(error),
                }),
              );
            },
          },
        );
      } catch (error) {
        displayErrorToast(
          t(
            "memorySettings.notifications.import.invalidFile",
            "Invalid JSON file",
          ),
        );
      }
    };
    input.click();
  }, [importMemories, resolveErrorMessage, t]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
  }, []);

  const handleCategoryChange = useCallback((category: CategoryFilter) => {
    setSelectedCategory(category);
  }, []);

  const hasFilters =
    searchQuery.trim().length > 0 || selectedCategory !== "all";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-foreground-tertiary" />
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <MemoryHeader
          t={t}
          onCreate={handleCreate}
          onExport={handleExport}
          onImport={handleImport}
        />

        {stats && <MemoryStatsSummary t={t} stats={stats} />}

        <MemoryFilters
          t={t}
          searchQuery={searchQuery}
          onSearchChange={handleSearchChange}
          selectedCategory={selectedCategory}
          onCategoryChange={handleCategoryChange}
          totalCount={memories?.length ?? 0}
        />

        <MemoryList
          t={t}
          memories={filteredMemories}
          hasFilters={hasFilters}
          onCreate={handleCreate}
          onEdit={handleEdit}
          onDelete={handleDeleteClick}
        />

        {showForm && (
          <MemoryFormModal
            memory={editingMemory || undefined}
            onSave={handleSave}
            onClose={handleCloseForm}
            isLoading={isCreating || isUpdating}
          />
        )}

        {deleteConfirmOpen && (
          <ConfirmationModal
            text={t(
              "memorySettings.notifications.delete.confirmation",
              "Are you sure you want to delete this memory? This action cannot be undone.",
            )}
            onConfirm={handleConfirmDelete}
            onCancel={handleCancelDelete}
          />
        )}
      </div>
    </div>
  );
}

export default MemorySettingsScreen;
