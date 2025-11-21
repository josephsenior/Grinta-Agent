import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useKnowledgeBaseCollections,
  useKnowledgeBaseStats,
} from "#/hooks/query/use-knowledge-base";
import { useDeleteCollection } from "#/hooks/mutation/use-knowledge-base-mutations";
import { KBCreateCollectionModal } from "./kb-create-collection-modal";
import { KBDocumentUpload } from "./kb-document-upload";
import { useCollectionSearch } from "./knowledge-base-manager/use-collection-search";
import { HeaderSection } from "./knowledge-base-manager/header-section";
import { CollectionsContent } from "./knowledge-base-manager/collections-content";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";

export function KnowledgeBaseManager() {
  const { t } = useTranslation();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [uploadCollectionId, setUploadCollectionId] = useState<string | null>(
    null,
  );
  const [uploadCollectionName, setUploadCollectionName] = useState("");
  const [deleteCollectionId, setDeleteCollectionId] = useState<string | null>(
    null,
  );

  const { data: collections, isLoading, error } = useKnowledgeBaseCollections();
  const { data: stats } = useKnowledgeBaseStats();
  const deleteMutation = useDeleteCollection();

  const { searchQuery, setSearchQuery, filteredCollections } =
    useCollectionSearch(collections);

  const handleDeleteCollection = async (collectionId: string) => {
    setDeleteCollectionId(collectionId);
  };

  const confirmDelete = async () => {
    if (deleteCollectionId) {
      await deleteMutation.mutateAsync(deleteCollectionId);
      setDeleteCollectionId(null);
    }
  };

  const handleUploadClick = (collectionId: string, collectionName: string) => {
    setUploadCollectionId(collectionId);
    setUploadCollectionName(collectionName);
  };

  return (
    <div className="h-full flex flex-col">
      <HeaderSection
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onCreateCollection={() => setShowCreateModal(true)}
        stats={stats}
      />

      <div className="flex-1 overflow-y-auto p-6">
        <CollectionsContent
          isLoading={isLoading}
          error={error}
          filteredCollections={filteredCollections}
          searchQuery={searchQuery}
          onDeleteCollection={handleDeleteCollection}
          onUploadDocument={handleUploadClick}
          onCreateCollection={() => setShowCreateModal(true)}
        />
      </div>

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

      {deleteCollectionId && (
        <ConfirmationModal
          text={t(
            "KB$DELETE_COLLECTION_CONFIRM",
            "Are you sure you want to delete this collection? All documents will be removed.",
          )}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteCollectionId(null)}
        />
      )}
    </div>
  );
}
