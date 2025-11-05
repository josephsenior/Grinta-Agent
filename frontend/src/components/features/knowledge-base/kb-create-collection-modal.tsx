import React, { useState } from "react";
import { X } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { Textarea } from "#/components/ui/textarea";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { useCreateCollection } from "#/hooks/mutation/use-knowledge-base-mutations";

interface KBCreateCollectionModalProps {
  onClose: () => void;
}

export function KBCreateCollectionModal({ onClose }: KBCreateCollectionModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const createMutation = useCreateCollection();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      onClose();
    } catch (error) {
      // Error handled by mutation
      console.error("Failed to create collection:", error);
    }
  };

  return (
    <ModalBackdrop onClose={onClose}>
      <div className="bg-background-secondary p-6 rounded-xl max-w-md w-full border border-border shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-foreground">
            Create Knowledge Base Collection
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-background-tertiary/70 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-foreground-secondary" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="collection-name" className="block text-sm font-medium text-foreground mb-2">
              Collection Name *
            </label>
            <Input
              id="collection-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Project Documentation"
              required
              autoFocus
              className="w-full"
            />
          </div>

          <div>
            <label htmlFor="collection-description" className="block text-sm font-medium text-foreground mb-2">
              Description (optional)
            </label>
            <Textarea
              id="collection-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this collection..."
              rows={3}
              className="w-full resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={!name.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create Collection"}
            </Button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  );
}

