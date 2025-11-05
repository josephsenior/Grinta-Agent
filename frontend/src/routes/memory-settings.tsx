import { useState, useMemo } from "react";
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
import type { Memory, MemoryCategory } from "#/types/memory";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { useDebounce } from "#/hooks/use-debounce";

function MemorySettingsScreen() {
  const { data: memories, isLoading } = useMemories();
  const { data: stats } = useMemoryStats();
  
  // Debug: Log the memories data
  console.log('[Memory] Memories data:', { memories, isLoading, isArray: Array.isArray(memories) });
  const { mutate: createMemory, isPending: isCreating } = useCreateMemory();
  const { mutate: updateMemory, isPending: isUpdating } = useUpdateMemory();
  const { mutate: deleteMemory, isPending: isDeleting } = useDeleteMemory();
  const { mutateAsync: exportMemories } = useExportMemories();
  const { mutate: importMemories } = useImportMemories();

  const [showForm, setShowForm] = useState(false);
  const [editingMemory, setEditingMemory] = useState<Memory | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [memoryToDelete, setMemoryToDelete] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<MemoryCategory | "all">(
    "all",
  );

  // Debounce search query for performance
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // Filter memories
  const filteredMemories = useMemo(() => {
    if (!memories || !Array.isArray(memories)) return [];

    let filtered = memories;

    // Category filter
    if (selectedCategory !== "all") {
      filtered = filtered.filter((m) => m.category === selectedCategory);
    }

    // Search filter (using debounced query)
    if (debouncedSearchQuery.trim()) {
      const query = debouncedSearchQuery.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          m.title.toLowerCase().includes(query) ||
          m.content.toLowerCase().includes(query) ||
          m.tags.some((tag) => tag.toLowerCase().includes(query)),
      );
    }

    // Ensure filtered is an array before sorting
    if (!Array.isArray(filtered)) {
      console.warn('Filtered memories is not an array:', filtered);
      return [];
    }

    // Sort by usage count (most used first)
    return filtered.sort((a, b) => (b.usageCount || 0) - (a.usageCount || 0));
  }, [memories, selectedCategory, debouncedSearchQuery]);

  const handleCreate = () => {
    setEditingMemory(null);
    setShowForm(true);
  };

  const handleEdit = (memory: Memory) => {
    setEditingMemory(memory);
    setShowForm(true);
  };

  const handleDeleteClick = (memoryId: string) => {
    setMemoryToDelete(memoryId);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = () => {
    if (memoryToDelete) {
      deleteMemory(memoryToDelete, {
        onSuccess: () => {
          displaySuccessToast("Memory deleted successfully");
          setDeleteConfirmOpen(false);
          setMemoryToDelete(null);
        },
        onError: (error) => {
          displayErrorToast(
            `Failed to delete memory: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      });
    }
  };

  const handleSave = (data: any) => {
    if (editingMemory) {
      // Update existing memory
      updateMemory(
        { memoryId: editingMemory.id, updates: data },
        {
          onSuccess: () => {
            displaySuccessToast("Memory updated successfully");
            setShowForm(false);
            setEditingMemory(null);
          },
          onError: (error) => {
            displayErrorToast(
              `Failed to update memory: ${error instanceof Error ? error.message : "Unknown error"}`,
            );
          },
        },
      );
    } else {
      // Create new memory
      createMemory(data, {
        onSuccess: () => {
          displaySuccessToast("Memory created successfully");
          setShowForm(false);
        },
        onError: (error) => {
          displayErrorToast(
            `Failed to create memory: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      });
    }
  };

  const handleExport = async () => {
    try {
      const data = await exportMemories();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `memories-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      displaySuccessToast("Memories exported successfully");
    } catch (error) {
      displayErrorToast("Failed to export memories");
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
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    );
  }

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="w-8 h-8 text-brand-500" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">Memory Management</h2>
            <p className="text-sm text-foreground-secondary mt-1">
              Store and manage persistent memories for better AI assistance
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <BrandButton
            variant="secondary"
            onClick={handleExport}
            type="button"
            testId="export-memories"
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export
          </BrandButton>
          <BrandButton
            variant="secondary"
            onClick={handleImport}
            type="button"
            testId="import-memories"
            className="flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Import
          </BrandButton>
          <BrandButton
            variant="primary"
            onClick={handleCreate}
            type="button"
            testId="add-memory"
            className="flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Memory
          </BrandButton>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-5 gap-4">
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <p className="text-sm text-foreground-secondary mb-1">Total</p>
            <p className="text-2xl font-bold text-foreground">{stats.total}</p>
          </div>
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <p className="text-sm text-foreground-secondary mb-1">Technical</p>
            <p className="text-2xl font-bold text-blue-500">
              {stats.byCategory?.technical || 0}
            </p>
          </div>
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <p className="text-sm text-foreground-secondary mb-1">Preferences</p>
            <p className="text-2xl font-bold text-purple-500">
              {stats.byCategory?.preference || 0}
            </p>
          </div>
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <p className="text-sm text-foreground-secondary mb-1">Project</p>
            <p className="text-2xl font-bold text-green-500">
              {stats.byCategory?.project || 0}
            </p>
          </div>
          <div className="p-4 bg-black border border-violet-500/20 rounded-lg">
            <p className="text-sm text-foreground-secondary mb-1">Used Today</p>
            <p className="text-2xl font-bold text-brand-500">
              {stats.usedToday}
            </p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memories..."
            className="w-full pl-10 pr-4 py-2 bg-black border border-violet-500/20 rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* Category filters */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setSelectedCategory("all")}
            className={`px-3 py-2 text-sm rounded-md transition-colors ${
              selectedCategory === "all"
                ? "bg-brand-500 text-white"
                : "bg-black text-foreground-secondary hover:text-foreground"
            }`}
          >
            All ({memories?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory("technical")}
            className={`px-3 py-2 text-sm rounded-md transition-colors flex items-center gap-2 ${
              selectedCategory === "technical"
                ? "bg-blue-500 text-white"
                : "bg-black text-foreground-secondary hover:text-foreground"
            }`}
          >
            <Lightbulb className="w-4 h-4" />
            Technical
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory("preference")}
            className={`px-3 py-2 text-sm rounded-md transition-colors flex items-center gap-2 ${
              selectedCategory === "preference"
                ? "bg-purple-500 text-white"
                : "bg-black text-foreground-secondary hover:text-foreground"
            }`}
          >
            <Palette className="w-4 h-4" />
            Preferences
          </button>
          <button
            type="button"
            onClick={() => setSelectedCategory("project")}
            className={`px-3 py-2 text-sm rounded-md transition-colors flex items-center gap-2 ${
              selectedCategory === "project"
                ? "bg-green-500 text-white"
                : "bg-black text-foreground-secondary hover:text-foreground"
            }`}
          >
            <Building2 className="w-4 h-4" />
            Project
          </button>
        </div>
      </div>

      {/* Memory List */}
      {filteredMemories.length === 0 ? (
        <div className="text-center p-12 bg-black border border-violet-500/20 rounded-lg">
          <Brain className="w-12 h-12 text-foreground-secondary mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">
            {searchQuery || selectedCategory !== "all"
              ? "No memories found"
              : "No Memories Yet"}
          </h3>
          <p className="text-sm text-foreground-secondary mb-4">
            {searchQuery || selectedCategory !== "all"
              ? "Try adjusting your filters"
              : "Create your first memory to help the AI remember your preferences"}
          </p>
          {!searchQuery && selectedCategory === "all" && (
            <BrandButton
              variant="primary"
              onClick={handleCreate}
              type="button"
              testId="add-first-memory"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add First Memory
            </BrandButton>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredMemories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onEdit={handleEdit}
              onDelete={handleDeleteClick}
            />
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <MemoryFormModal
          memory={editingMemory || undefined}
          onSave={handleSave}
          onClose={() => {
            setShowForm(false);
            setEditingMemory(null);
          }}
          isLoading={isCreating || isUpdating}
        />
      )}

      {/* Delete Confirmation */}
      {deleteConfirmOpen && (
        <ConfirmationModal
          text="Are you sure you want to delete this memory? This action cannot be undone."
          onConfirm={handleConfirmDelete}
          onCancel={() => {
            setDeleteConfirmOpen(false);
            setMemoryToDelete(null);
          }}
        />
      )}
    </div>
  );
}

export default MemorySettingsScreen;

