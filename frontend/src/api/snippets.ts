/**
 * API client for code snippets
 */

import type {
  CodeSnippet,
  CreateSnippetRequest,
  SearchSnippetsRequest,
  SnippetCategory,
  SnippetCollection,
  SnippetLanguage,
  SnippetStats,
  UpdateSnippetRequest,
} from "#/types/snippet";

const API_BASE = "/api/snippets";

export async function listSnippets(params?: {
  language?: SnippetLanguage;
  category?: SnippetCategory;
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}): Promise<CodeSnippet[]> {
  const searchParams = new URLSearchParams();

  if (params?.language) searchParams.append("language", params.language);
  if (params?.category) searchParams.append("category", params.category);
  if (params?.is_favorite !== undefined)
    searchParams.append("is_favorite", String(params.is_favorite));
  if (params?.limit !== undefined)
    searchParams.append("limit", String(params.limit));
  if (params?.offset !== undefined)
    searchParams.append("offset", String(params.offset));

  const url = `${API_BASE}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to list snippets: ${response.statusText}`);
  }

  return response.json();
}

export async function createSnippet(
  data: CreateSnippetRequest,
): Promise<CodeSnippet> {
  const response = await fetch(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create snippet: ${response.statusText}`);
  }

  return response.json();
}

export async function getSnippet(snippetId: string): Promise<CodeSnippet> {
  const response = await fetch(`${API_BASE}/${snippetId}`);

  if (!response.ok) {
    throw new Error(`Failed to get snippet: ${response.statusText}`);
  }

  return response.json();
}

export async function updateSnippet(
  snippetId: string,
  data: UpdateSnippetRequest,
): Promise<CodeSnippet> {
  const response = await fetch(`${API_BASE}/${snippetId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update snippet: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteSnippet(snippetId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${snippetId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete snippet: ${response.statusText}`);
  }
}

export async function searchSnippets(
  params: SearchSnippetsRequest,
): Promise<CodeSnippet[]> {
  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Failed to search snippets: ${response.statusText}`);
  }

  return response.json();
}

export async function getSnippetStats(): Promise<SnippetStats> {
  const response = await fetch(`${API_BASE}/stats`);

  if (!response.ok) {
    throw new Error(`Failed to get snippet stats: ${response.statusText}`);
  }

  return response.json();
}

export async function exportSnippets(params?: {
  language?: SnippetLanguage;
  category?: SnippetCategory;
  is_favorite?: boolean;
}): Promise<SnippetCollection> {
  const searchParams = new URLSearchParams();

  if (params?.language) searchParams.append("language", params.language);
  if (params?.category) searchParams.append("category", params.category);
  if (params?.is_favorite !== undefined)
    searchParams.append("is_favorite", String(params.is_favorite));

  const url = `${API_BASE}/export${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to export snippets: ${response.statusText}`);
  }

  return response.json();
}

export async function importSnippets(
  collection: SnippetCollection,
): Promise<{ imported: number; updated: number; skipped: number; total: number }> {
  const response = await fetch(`${API_BASE}/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collection),
  });

  if (!response.ok) {
    throw new Error(`Failed to import snippets: ${response.statusText}`);
  }

  return response.json();
}

export async function trackSnippetUsage(
  snippetId: string,
): Promise<CodeSnippet> {
  const response = await fetch(`${API_BASE}/${snippetId}/use`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to track snippet usage: ${response.statusText}`);
  }

  return response.json();
}

