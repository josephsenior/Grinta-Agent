import React from "react";
import { Plus, Database, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { KBCollectionCard } from "../kb-collection-card";
import type { KnowledgeBaseCollection } from "#/types/knowledge-base";

interface CollectionsContentProps {
  isLoading: boolean;
  error: unknown;
  filteredCollections?: KnowledgeBaseCollection[];
  searchQuery: string;
  onDeleteCollection: (id: string) => void;
  onUploadDocument: (id: string, name: string) => void;
  onCreateCollection: () => void;
}

// Helper components
function ErrorState({ message }: { message: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <AlertCircle className="w-8 h-8 text-red-500" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {t("KB$FAILED_TO_LOAD_COLLECTIONS", "Failed to load collections")}
      </h3>
      <p className="text-sm text-foreground-secondary max-w-md">{message}</p>
    </div>
  );
}

function EmptyState({
  hasSearchQuery,
  onCreateCollection,
}: {
  hasSearchQuery: boolean;
  onCreateCollection: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="w-16 h-16 rounded-full bg-brand-500/10 flex items-center justify-center mb-4">
        <Database className="w-8 h-8 text-violet-500" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {hasSearchQuery
          ? t("KB$NO_COLLECTIONS_FOUND", "No collections found")
          : t("KB$NO_COLLECTIONS_YET", "No collections yet")}
      </h3>
      <p className="text-sm text-foreground-secondary mb-4 max-w-md">
        {hasSearchQuery
          ? t("KB$TRY_ADJUSTING_SEARCH", "Try adjusting your search query")
          : t(
              "KB$CREATE_FIRST_COLLECTION",
              "Create your first collection to start organizing your knowledge base",
            )}
      </p>
      {!hasSearchQuery && (
        <Button onClick={onCreateCollection}>
          <Plus className="w-4 h-4 mr-2" />
          {t("KB$CREATE_COLLECTION", "Create Collection")}
        </Button>
      )}
    </div>
  );
}

export function CollectionsContent({
  isLoading,
  error,
  filteredCollections,
  searchQuery,
  onDeleteCollection,
  onUploadDocument,
  onCreateCollection,
}: CollectionsContentProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        message={
          error instanceof Error ? error.message : "An unknown error occurred"
        }
      />
    );
  }

  if (!filteredCollections || filteredCollections.length === 0) {
    return (
      <EmptyState
        hasSearchQuery={!!searchQuery}
        onCreateCollection={onCreateCollection}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {filteredCollections.map((collection) => (
        <KBCollectionCard
          key={collection.id}
          collection={collection}
          onDelete={onDeleteCollection}
          onUploadDocument={(id) => onUploadDocument(id, collection.name)}
        />
      ))}
    </div>
  );
}
