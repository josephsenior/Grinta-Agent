import React, { useState } from "react";
import { Plus, Search, Database, AlertCircle } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { KBCollectionCard } from "./kb-collection-card";
import { KBCreateCollectionModal } from "./kb-create-collection-modal";
import { KBDocumentUpload } from "./kb-document-upload";
import {
  useKnowledgeBaseCollections,
  useKnowledgeBaseStats,
} from "#/hooks/query/use-knowledge-base";
import { useDeleteCollection } from "#/hooks/mutation/use-knowledge-base-mutations";

export function KnowledgeBaseManager() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [uploadCollectionId, setUploadCollectionId] = useState<string | null>(
    null,
  );
  const [uploadCollectionName, setUploadCollectionName] = useState("");

  const { data: collections, isLoading, error } = useKnowledgeBaseCollections();
  const { data: stats } = useKnowledgeBaseStats();
  const deleteMutation = useDeleteCollection();

  const handleDeleteCollection = async (collectionId: string) => {
    if (
      !confirm(
        "Are you sure you want to delete this collection? All documents will be removed.",
      )
    ) {
      return;
    }
    await deleteMutation.mutateAsync(collectionId);
  };

  const handleUploadClick = (collectionId: string, collectionName: string) => {
    setUploadCollectionId(collectionId);
    setUploadCollectionName(collectionName);
  };

  const filteredCollections = collections?.filter(
    (collection) =>
      collection.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      collection.description?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-background-secondary px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Database className="w-6 h-6 text-violet-500" />
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                Knowledge Base
              </h1>
              <p className="text-sm text-foreground-secondary">
                Manage your document collections and AI context
              </p>
            </div>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            New Collection
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-background-tertiary/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-foreground">
                {stats.total_collections}
              </div>
              <div className="text-xs text-foreground-secondary">
                Collections
              </div>
            </div>
            <div className="bg-background-tertiary/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-foreground">
                {stats.total_documents}
              </div>
              <div className="text-xs text-foreground-secondary">Documents</div>
            </div>
            <div className="bg-background-tertiary/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-foreground">
                {stats.total_chunks}
              </div>
              <div className="text-xs text-foreground-secondary">Chunks</div>
            </div>
            <div className="bg-background-tertiary/50 rounded-lg p-3">
              <div className="text-2xl font-bold text-foreground">
                {stats.total_size_mb.toFixed(1)} MB
              </div>
              <div className="text-xs text-foreground-secondary">
                Total Size
              </div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
            <Input
              type="text"
              placeholder="Search collections..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
      </div>

      {/* Collections Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner size="large" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              Failed to load collections
            </h3>
            <p className="text-sm text-foreground-secondary max-w-md">
              {error instanceof Error
                ? error.message
                : "An unknown error occurred"}
            </p>
          </div>
        ) : !filteredCollections || filteredCollections.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 rounded-full bg-brand-500/10 flex items-center justify-center mb-4">
              <Database className="w-8 h-8 text-violet-500" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {searchQuery ? "No collections found" : "No collections yet"}
            </h3>
            <p className="text-sm text-foreground-secondary mb-4 max-w-md">
              {searchQuery
                ? "Try adjusting your search query"
                : "Create your first collection to start organizing your knowledge base"}
            </p>
            {!searchQuery && (
              <Button onClick={() => setShowCreateModal(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Collection
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredCollections.map((collection) => (
              <KBCollectionCard
                key={collection.id}
                collection={collection}
                onDelete={handleDeleteCollection}
                onUploadDocument={(id) =>
                  handleUploadClick(id, collection.name)
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreateModal && (
        <KBCreateCollectionModal onClose={() => setShowCreateModal(false)} />
      )}

      {uploadCollectionId && (
        <KBDocumentUpload
          collectionId={uploadCollectionId}
          collectionName={uploadCollectionName}
          onClose={() => {
            setUploadCollectionId(null);
            setUploadCollectionName("");
          }}
        />
      )}
    </div>
  );
}
