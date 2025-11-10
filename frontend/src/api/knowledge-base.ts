/**
 * Knowledge Base API client
 */

import type {
  KnowledgeBaseCollection,
  KnowledgeBaseDocument,
  KnowledgeBaseSearchResult,
  CreateCollectionRequest,
  UpdateCollectionRequest,
  SearchRequest,
  KnowledgeBaseStats,
} from "#/types/knowledge-base";

const BASE_URL = "/api/knowledge-base";

/**
 * Collection endpoints
 */

export async function createCollection(
  data: CreateCollectionRequest,
): Promise<KnowledgeBaseCollection> {
  const response = await fetch(`${BASE_URL}/collections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create collection: ${response.statusText}`);
  }

  return response.json();
}

export async function getCollections(): Promise<KnowledgeBaseCollection[]> {
  const response = await fetch(`${BASE_URL}/collections`);

  if (!response.ok) {
    throw new Error(`Failed to fetch collections: ${response.statusText}`);
  }

  return response.json();
}

export async function getCollection(
  collectionId: string,
): Promise<KnowledgeBaseCollection> {
  const response = await fetch(`${BASE_URL}/collections/${collectionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch collection: ${response.statusText}`);
  }

  return response.json();
}

export async function updateCollection(
  collectionId: string,
  data: UpdateCollectionRequest,
): Promise<KnowledgeBaseCollection> {
  const response = await fetch(`${BASE_URL}/collections/${collectionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update collection: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteCollection(collectionId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/collections/${collectionId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete collection: ${response.statusText}`);
  }
}

/**
 * Document endpoints
 */

export async function uploadDocument(
  collectionId: string,
  file: File,
): Promise<KnowledgeBaseDocument> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("collection_id", collectionId);

  const response = await fetch(
    `${BASE_URL}/collections/${collectionId}/documents`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to upload document: ${response.statusText}`);
  }

  return response.json();
}

export async function getDocuments(
  collectionId: string,
): Promise<KnowledgeBaseDocument[]> {
  const response = await fetch(
    `${BASE_URL}/collections/${collectionId}/documents`,
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.statusText}`);
  }

  return response.json();
}

export async function getDocument(
  collectionId: string,
  documentId: string,
): Promise<KnowledgeBaseDocument> {
  const response = await fetch(
    `${BASE_URL}/collections/${collectionId}/documents/${documentId}`,
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch document: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteDocument(
  collectionId: string,
  documentId: string,
): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/collections/${collectionId}/documents/${documentId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.statusText}`);
  }
}

/**
 * Search endpoints
 */

export async function searchKnowledgeBase(
  data: SearchRequest,
): Promise<KnowledgeBaseSearchResult[]> {
  const response = await fetch(`${BASE_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to search knowledge base: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Stats endpoints
 */

export async function getKnowledgeBaseStats(): Promise<KnowledgeBaseStats> {
  const response = await fetch(`${BASE_URL}/stats`);

  if (!response.ok) {
    throw new Error(
      `Failed to fetch knowledge base stats: ${response.statusText}`,
    );
  }

  return response.json();
}
