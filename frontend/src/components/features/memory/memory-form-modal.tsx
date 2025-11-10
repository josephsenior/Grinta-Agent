import { useState } from "react";
import { X, Brain, Tag as TagIcon } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import type { Memory, MemoryCategory, MemoryImportance } from "#/types/memory";

interface MemoryFormModalProps {
  memory?: Memory;
  onSave: (data: any) => void;
  onClose: () => void;
  isLoading?: boolean;
}

export function MemoryFormModal({
  memory,
  onSave,
  onClose,
  isLoading = false,
}: MemoryFormModalProps) {
  const controller = useMemoryFormController({ memory, onSave, onClose });

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Modal */}
        <div
          className="bg-background-secondary border border-border rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={controller.handleKeyDown}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <Brain className="w-6 h-6 text-violet-500" />
              <h2 className="text-xl font-semibold text-foreground">
                {memory ? "Edit Memory" : "Add Memory"}
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 text-foreground-secondary hover:text-foreground hover:bg-background-tertiary rounded-md transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Title *
              </label>
              <input
                type="text"
                value={controller.title}
                onChange={controller.handleTitleChange}
                placeholder="e.g., Uses TypeScript for all projects"
                className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                autoFocus
              />
            </div>

            {/* Content */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Content *
              </label>
              <textarea
                value={controller.content}
                onChange={controller.handleContentChange}
                placeholder="Detailed description of what to remember..."
                rows={6}
                className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Category and Importance */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Category *
                </label>
                <select
                  value={controller.category}
                  onChange={controller.handleCategoryChange}
                  className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                >
                  <option value="technical">💡 Technical</option>
                  <option value="preference">🎨 Preference</option>
                  <option value="project">🏗️ Project</option>
                  <option value="fact">📚 Fact</option>
                  <option value="custom">📌 Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Importance
                </label>
                <select
                  value={controller.importance}
                  onChange={controller.handleImportanceChange}
                  className="w-full px-3 py-2 bg-background-primary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Tags
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={controller.tagInput}
                  onChange={controller.handleTagInputChange}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      controller.handleAddTag();
                    }
                  }}
                  placeholder="Add tag and press Enter"
                  className="flex-1 px-3 py-2 bg-background-primary border border-border rounded-md text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
                <BrandButton
                  variant="secondary"
                  onClick={controller.handleAddTag}
                  type="button"
                  testId="add-tag"
                  isDisabled={!controller.tagInput.trim()}
                >
                  Add
                </BrandButton>
              </div>
              {controller.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {controller.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 text-xs bg-background-tertiary border border-border rounded text-foreground flex items-center gap-1"
                    >
                      <TagIcon className="w-3 h-3" />
                      {tag}
                      <button
                        type="button"
                        onClick={() => controller.handleRemoveTag(tag)}
                        className="ml-1 text-foreground-secondary hover:text-error-500 transition-colors"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 p-6 border-t border-border">
            <BrandButton
              variant="secondary"
              onClick={onClose}
              type="button"
              testId="cancel-memory"
            >
              Cancel
            </BrandButton>
            <BrandButton
              variant="primary"
              onClick={controller.handleSubmit}
              type="button"
              testId="save-memory"
              isDisabled={controller.isSaveDisabled || isLoading}
            >
              {memory ? "Update memory" : "Save memory"}
            </BrandButton>
          </div>
        </div>
      </div>
    </>
  );
}

function useMemoryFormController({
  memory,
  onSave,
  onClose,
}: MemoryFormModalProps) {
  const [title, setTitle] = useState(memory?.title || "");
  const [content, setContent] = useState(memory?.content || "");
  const [category, setCategory] = useState<MemoryCategory>(
    memory?.category || "technical",
  );
  const [importance, setImportance] = useState<MemoryImportance>(
    memory?.importance || "medium",
  );
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>(memory?.tags || []);

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !tags.includes(tag)) {
      setTags((prev) => [...prev, tag]);
      setTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags((prev) => prev.filter((tag) => tag !== tagToRemove));
  };

  const handleSubmit = () => {
    if (!title.trim() || !content.trim()) {
      return;
    }

    onSave({
      title: title.trim(),
      content: content.trim(),
      category,
      tags,
      importance,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    }
  };

  return {
    title,
    content,
    category,
    importance,
    tagInput,
    tags,
    isSaveDisabled: !title.trim() || !content.trim(),
    handleTitleChange: (event: React.ChangeEvent<HTMLInputElement>) =>
      setTitle(event.target.value),
    handleContentChange: (event: React.ChangeEvent<HTMLTextAreaElement>) =>
      setContent(event.target.value),
    handleCategoryChange: (event: React.ChangeEvent<HTMLSelectElement>) =>
      setCategory(event.target.value as MemoryCategory),
    handleImportanceChange: (event: React.ChangeEvent<HTMLSelectElement>) =>
      setImportance(event.target.value as MemoryImportance),
    handleTagInputChange: (event: React.ChangeEvent<HTMLInputElement>) =>
      setTagInput(event.target.value),
    handleAddTag,
    handleRemoveTag,
    handleSubmit,
    handleKeyDown,
  };
}
