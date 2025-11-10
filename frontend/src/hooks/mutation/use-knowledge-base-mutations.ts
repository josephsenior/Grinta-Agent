import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createCollection,
  updateCollection,
  deleteCollection,
  uploadDocument,
  deleteDocument,
  searchKnowledgeBase,
} from "#/api/knowledge-base";
import type {
  CreateCollectionRequest,
  UpdateCollectionRequest,
  SearchRequest,
} from "#/types/knowledge-base";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";

export function useCreateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateCollectionRequest) => createCollection(data),
    onSuccess: (newCollection) => {
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections"],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-base", "stats"] });
      displaySuccessToast(
        `Collection "${newCollection.name}" created successfully`,
      );
    },
    onError: (error: Error) => {
      displayErrorToast(`Failed to create collection: ${error.message}`);
    },
  });
}

export function useUpdateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      collectionId,
      data,
    }: {
      collectionId: string;
      data: UpdateCollectionRequest;
    }) => updateCollection(collectionId, data),
    onSuccess: (updatedCollection) => {
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections"],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections", updatedCollection.id],
      });
      displaySuccessToast(`Collection updated successfully`);
    },
    onError: (error: Error) => {
      displayErrorToast(`Failed to update collection: ${error.message}`);
    },
  });
}

export function useDeleteCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (collectionId: string) => deleteCollection(collectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections"],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-base", "stats"] });
      displaySuccessToast("Collection deleted successfully");
    },
    onError: (error: Error) => {
      displayErrorToast(`Failed to delete collection: ${error.message}`);
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      collectionId,
      file,
    }: {
      collectionId: string;
      file: File;
    }) => uploadDocument(collectionId, file),
    onSuccess: (newDocument, variables) => {
      queryClient.invalidateQueries({
        queryKey: [
          "knowledge-base",
          "collections",
          variables.collectionId,
          "documents",
        ],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections", variables.collectionId],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-base", "stats"] });
      displaySuccessToast(
        `Document "${newDocument.filename}" uploaded successfully`,
      );
    },
    onError: (error: Error) => {
      displayErrorToast(`Failed to upload document: ${error.message}`);
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      collectionId,
      documentId,
    }: {
      collectionId: string;
      documentId: string;
    }) => deleteDocument(collectionId, documentId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [
          "knowledge-base",
          "collections",
          variables.collectionId,
          "documents",
        ],
      });
      queryClient.invalidateQueries({
        queryKey: ["knowledge-base", "collections", variables.collectionId],
      });
      queryClient.invalidateQueries({ queryKey: ["knowledge-base", "stats"] });
      displaySuccessToast("Document deleted successfully");
    },
    onError: (error: Error) => {
      displayErrorToast(`Failed to delete document: ${error.message}`);
    },
  });
}

export function useSearchKnowledgeBase() {
  return useMutation({
    mutationFn: (data: SearchRequest) => searchKnowledgeBase(data),
    onError: (error: Error) => {
      displayErrorToast(`Search failed: ${error.message}`);
    },
  });
}
