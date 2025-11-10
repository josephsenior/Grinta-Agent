import { useQuery } from "@tanstack/react-query";
import {
  getCollections,
  getCollection,
  getDocuments,
  getDocument,
  getKnowledgeBaseStats,
} from "#/api/knowledge-base";

export function useKnowledgeBaseCollections() {
  return useQuery({
    queryKey: ["knowledge-base", "collections"],
    queryFn: getCollections,
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useKnowledgeBaseCollection(collectionId: string | null) {
  return useQuery({
    queryKey: ["knowledge-base", "collections", collectionId],
    queryFn: () => getCollection(collectionId!),
    enabled: !!collectionId,
    staleTime: 1000 * 30,
    gcTime: 1000 * 60 * 5,
  });
}

export function useKnowledgeBaseDocuments(collectionId: string | null) {
  return useQuery({
    queryKey: ["knowledge-base", "collections", collectionId, "documents"],
    queryFn: () => getDocuments(collectionId!),
    enabled: !!collectionId,
    staleTime: 1000 * 10, // 10 seconds
    gcTime: 1000 * 60 * 5,
  });
}

export function useKnowledgeBaseDocument(
  collectionId: string | null,
  documentId: string | null,
) {
  return useQuery({
    queryKey: [
      "knowledge-base",
      "collections",
      collectionId,
      "documents",
      documentId,
    ],
    queryFn: () => getDocument(collectionId!, documentId!),
    enabled: !!collectionId && !!documentId,
    staleTime: 1000 * 30,
    gcTime: 1000 * 60 * 5,
  });
}

export function useKnowledgeBaseStats() {
  return useQuery({
    queryKey: ["knowledge-base", "stats"],
    queryFn: getKnowledgeBaseStats,
    staleTime: 1000 * 60, // 1 minute
    gcTime: 1000 * 60 * 5,
  });
}
