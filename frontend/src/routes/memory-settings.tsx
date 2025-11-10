import { useState, useMemo, useCallback } from "react";
import type { ComponentType } from "react";
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
import type { Memory, MemoryCategory, MemoryStats } from "#/types/memory";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { useDebounce } from "#/hooks/use-debounce";

function MemorySettingsScreen() {
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
  const [selectedCategory, setSelectedCategory] = useState<
    MemoryCategory | "all"
  >("all");

  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  const filteredMemories = useMemo(
    () => filterMemories(memories, selectedCategory, debouncedSearchQuery),
    [memories, selectedCategory, debouncedSearchQuery],
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
        displaySuccessToast("Memory deleted successfully");
        handleCancelDelete();
      },
      onError: (error) => {
        displayErrorToast(
          `Failed to delete memory: ${error instanceof Error ? error.message : "Unknown error"}`,
        );
      },
    });
  }, [deleteMemory, handleCancelDelete, memoryToDelete]);

  const createMemoryEntry = useCallback(
    (data: any) => {
      createMemory(data, {
        onSuccess: () => {
          displaySuccessToast("Memory created successfully");
          handleCloseForm();
        },
        onError: (error) => {
          displayErrorToast(
            `Failed to create memory: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      });
    },
    [createMemory, handleCloseForm],
  );

  const updateMemoryEntry = useCallback(
    (memoryId: string, data: any) => {
      updateMemory(
        { memoryId, updates: data },
        {
          onSuccess: () => {
            displaySuccessToast("Memory updated successfully");
            handleCloseForm();
          },
          onError: (error) => {
            displayErrorToast(
              `Failed to update memory: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    },
    [handleCloseForm, updateMemory],
  );

  const handleSave = useCallback(
    (data: any) => {
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
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `memories-export-${Date.now()}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      displaySuccessToast("Memories exported successfully");
    } catch (error) {
      displayErrorToast("Failed to export memories");
    }
  }, [exportMemories]);

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
        const data = JSON.parse(text);

        importMemories(
          { data, merge: true },
          {
            onSuccess: (result) => {
              displaySuccessToast(
                `Imported ${result.imported} memories (Total: ${result.total})`,
              );
            },
            onError: () => {
              displayErrorToast("Failed to import memories");
            },
          },
        );
      } catch (error) {
        displayErrorToast("Invalid JSON file");
      }
    };
    input.click();
  }, [importMemories]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
  }, []);

  const handleCategoryChange = useCallback(
    (category: MemoryCategory | "all") => {
      setSelectedCategory(category);
    },
    [],
  );

  const hasFilters =
    searchQuery.trim().length > 0 || selectedCategory !== "all";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    );
  }

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      <MemoryHeader
        onCreate={handleCreate}
        onExport={handleExport}
        onImport={handleImport}
      />

      {stats && <MemoryStatsSummary stats={stats} />}

      <MemoryFilters
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        selectedCategory={selectedCategory}
        onCategoryChange={handleCategoryChange}
        totalCount={memories?.length ?? 0}
      />

      <MemoryList
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
          text="Are you sure you want to delete this memory? This action cannot be undone."
          onConfirm={handleConfirmDelete}
          onCancel={handleCancelDelete}
        />
      )}
    </div>
  );
}

export default MemorySettingsScreen;

type CategoryFilter = MemoryCategory | "all";

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

interface MemoryHeaderProps {
  onCreate: () => void;
  onExport: () => void;
  onImport: () => void;
}

function MemoryHeader({ onCreate, onExport, onImport }: MemoryHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Brain className="w-8 h-8 text-brand-500" />
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            Memory Management
          </h2>
          <p className="text-sm text-foreground-secondary mt-1">
            Store and manage persistent memories for better AI assistance
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
          Export
        </BrandButton>
        <BrandButton
          variant="secondary"
          onClick={onImport}
          type="button"
          testId="import-memories"
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Import
        </BrandButton>
        <BrandButton
          variant="primary"
          onClick={onCreate}
          type="button"
          testId="add-memory"
          className="flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Memory
        </BrandButton>
      </div>
    </div>
  );
}

interface MemoryStatsSummaryProps {
  stats: MemoryStats;
}

function MemoryStatsSummary({ stats }: MemoryStatsSummaryProps) {
  return (
    <div className="grid grid-cols-5 gap-4">
      <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
        <p className="text-sm text-foreground-secondary mb-1">Total</p>
        <p className="text-2xl font-bold text-foreground">{stats.total}</p>
      </div>
      <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
        <p className="text-sm text-foreground-secondary mb-1">Technical</p>
        <p className="text-2xl font-bold text-blue-500">
          {stats.byCategory?.technical ?? 0}
        </p>
      </div>
      <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
        <p className="text-sm text-foreground-secondary mb-1">Preferences</p>
        <p className="text-2xl font-bold text-purple-500">
          {stats.byCategory?.preference ?? 0}
        </p>
      </div>
      <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
        <p className="text-sm text-foreground-secondary mb-1">Project</p>
        <p className="text-2xl font-bold text-green-500">
          {stats.byCategory?.project ?? 0}
        </p>
      </div>
      <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
        <p className="text-sm text-foreground-secondary mb-1">Used Today</p>
        <p className="text-2xl font-bold text-brand-500">{stats.usedToday}</p>
      </div>
    </div>
  );
}

interface MemoryFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  selectedCategory: CategoryFilter;
  onCategoryChange: (category: CategoryFilter) => void;
  totalCount: number;
}

const CATEGORY_OPTIONS: Array<{
  key: CategoryFilter;
  label: string;
  icon?: ComponentType<{ className?: string }>;
  activeClass: string;
}> = [
  { key: "all", label: "All", activeClass: "bg-brand-500 text-white" },
  {
    key: "technical",
    label: "Technical",
    icon: Lightbulb,
    activeClass: "bg-blue-500 text-white",
  },
  {
    key: "preference",
    label: "Preferences",
    icon: Palette,
    activeClass: "bg-purple-500 text-white",
  },
  {
    key: "project",
    label: "Project",
    icon: Building2,
    activeClass: "bg-green-500 text-white",
  },
];

function MemoryFilters({
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
          placeholder="Search memories..."
          className="w-full pl-10 pr-4 py-2 bg-black border border-violet-500/20 rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
      </div>

      <div className="flex items-center gap-2">
        {CATEGORY_OPTIONS.map(({ key, label, icon: Icon, activeClass }) => {
          const isActive = selectedCategory === key;
          const baseClass =
            "px-3 py-2 text-sm rounded-md transition-colors flex items-center gap-2";
          const inactiveClass =
            "bg-black text-foreground-secondary hover:text-foreground";

          return (
            <button
              key={key}
              type="button"
              onClick={() => onCategoryChange(key)}
              className={`${baseClass} ${isActive ? activeClass : inactiveClass}`}
            >
              {Icon && <Icon className="w-4 h-4" />}
              {key === "all" ? `${label} (${totalCount})` : label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface MemoryListProps {
  memories: Memory[];
  hasFilters: boolean;
  onCreate: () => void;
  onEdit: (memory: Memory) => void;
  onDelete: (memoryId: string) => void;
}

function MemoryList({
  memories,
  hasFilters,
  onCreate,
  onEdit,
  onDelete,
}: MemoryListProps) {
  if (memories.length === 0) {
    return <MemoryEmptyState hasFilters={hasFilters} onCreate={onCreate} />;
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

interface MemoryEmptyStateProps {
  hasFilters: boolean;
  onCreate: () => void;
}

function MemoryEmptyState({ hasFilters, onCreate }: MemoryEmptyStateProps) {
  return (
    <div className="text-center p-12 bg-black border border-violet-500/20 rounded-lg">
      <Brain className="w-12 h-12 text-foreground-secondary mx-auto mb-4" />
      <h3 className="text-lg font-medium text-foreground mb-2">
        {hasFilters ? "No memories found" : "No Memories Yet"}
      </h3>
      <p className="text-sm text-foreground-secondary mb-4">
        {hasFilters
          ? "Try adjusting your filters"
          : "Create your first memory to help the AI remember your preferences"}
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
          Add First Memory
        </BrandButton>
      )}
    </div>
  );
}
