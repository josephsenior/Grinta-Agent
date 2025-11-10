/**
 * API client for prompt templates
 */

import type {
  CreatePromptRequest,
  PromptCategory,
  PromptCollection,
  PromptStats,
  PromptTemplate,
  RenderPromptRequest,
  RenderPromptResponse,
  SearchPromptsRequest,
  UpdatePromptRequest,
} from "#/types/prompt";

const API_BASE = "/api/prompts";

/**
 * List all prompts with optional filtering
 */
export async function listPrompts(params?: {
  category?: PromptCategory;
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}): Promise<PromptTemplate[]> {
  const searchParams = new URLSearchParams();

  if (params?.category) {
    searchParams.append("category", params.category);
  }
  if (params?.is_favorite !== undefined) {
    searchParams.append("is_favorite", String(params.is_favorite));
  }
  if (params?.limit !== undefined) {
    searchParams.append("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    searchParams.append("offset", String(params.offset));
  }

  const url = `${API_BASE}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to list prompts: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new prompt
 */
export async function createPrompt(
  data: CreatePromptRequest,
): Promise<PromptTemplate> {
  const response = await fetch(API_BASE, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create prompt: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get a specific prompt by ID
 */
export async function getPrompt(promptId: string): Promise<PromptTemplate> {
  const response = await fetch(`${API_BASE}/${promptId}`);

  if (!response.ok) {
    throw new Error(`Failed to get prompt: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing prompt
 */
export async function updatePrompt(
  promptId: string,
  data: UpdatePromptRequest,
): Promise<PromptTemplate> {
  const response = await fetch(`${API_BASE}/${promptId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update prompt: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a prompt
 */
export async function deletePrompt(promptId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${promptId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete prompt: ${response.statusText}`);
  }
}

/**
 * Search prompts with advanced filtering
 */
export async function searchPrompts(
  params: SearchPromptsRequest,
): Promise<PromptTemplate[]> {
  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Failed to search prompts: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get prompt library statistics
 */
export async function getPromptStats(): Promise<PromptStats> {
  const response = await fetch(`${API_BASE}/stats`);

  if (!response.ok) {
    throw new Error(`Failed to get prompt stats: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Export prompts as a collection
 */
export async function exportPrompts(params?: {
  category?: PromptCategory;
  is_favorite?: boolean;
}): Promise<PromptCollection> {
  const searchParams = new URLSearchParams();

  if (params?.category) {
    searchParams.append("category", params.category);
  }
  if (params?.is_favorite !== undefined) {
    searchParams.append("is_favorite", String(params.is_favorite));
  }

  const url = `${API_BASE}/export${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to export prompts: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Import prompts from a collection
 */
export async function importPrompts(collection: PromptCollection): Promise<{
  imported: number;
  updated: number;
  skipped: number;
  total: number;
}> {
  const response = await fetch(`${API_BASE}/import`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(collection),
  });

  if (!response.ok) {
    throw new Error(`Failed to import prompts: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Render a prompt with variables
 */
export async function renderPrompt(
  data: RenderPromptRequest,
): Promise<RenderPromptResponse> {
  const response = await fetch(`${API_BASE}/render`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to render prompt: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Track usage of a prompt
 */
export async function trackPromptUsage(
  promptId: string,
): Promise<PromptTemplate> {
  const response = await fetch(`${API_BASE}/${promptId}/use`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to track prompt usage: ${response.statusText}`);
  }

  return response.json();
}
