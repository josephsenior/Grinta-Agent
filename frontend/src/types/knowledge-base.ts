import type { Provider } from "./settings";

export interface KnowledgeBaseCollection {
  id: string;
  name: string;
  description: string | null;
  document_count: number;
  total_size_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseDocument {
  id: string;
  collection_id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  content_preview: string | null;
  chunk_count: number;
  uploaded_at: string;
}

export interface KnowledgeBaseSearchResult {
  document_id: string;
  collection_id: string;
  filename: string;
  chunk_content: string;
  relevance_score: number;
  metadata?: Record<string, string | number | boolean>;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string;
}

export interface UpdateCollectionRequest {
  name?: string;
  description?: string;
}

export interface SearchRequest {
  query: string;
  collection_ids?: string[];
  top_k?: number;
  relevance_threshold?: number;
}

export interface KnowledgeBaseStats {
  total_collections: number;
  total_documents: number;
  total_size_bytes: number;
}
