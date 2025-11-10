/**
 * Knowledge Base types matching backend API models
 */

export interface KnowledgeBaseCollection {
  id: string;
  name: string;
  description: string | null;
  document_count: number;
  total_size_bytes: number;
  total_size_mb: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseDocument {
  id: string;
  collection_id: string;
  filename: string;
  file_size_bytes: number;
  file_size_kb: number;
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
  total_chunks: number;
  total_size_bytes: number;
  total_size_mb: number;
}
