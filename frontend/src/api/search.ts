/**
 * API client for global search endpoints
 */

import { Forge } from "./forge-axios";

export interface SearchResult {
  id: string;
  type: string;
  title: string;
  description?: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface SearchResults {
  conversations: SearchResult[];
  files: SearchResult[];
}

export interface GlobalSearchResponse {
  status: string;
  data: {
    query: string;
    results: SearchResults;
    total: number;
  };
}

/**
 * Perform global search across conversations and files
 */
export async function globalSearch(
  query: string,
  type?: "conversations" | "files" | "all",
  limit?: number,
): Promise<GlobalSearchResponse["data"]> {
  const params: Record<string, string | number> = {
    q: query,
  };
  if (type && type !== "all") {
    params.type = type;
  }
  if (limit !== undefined) {
    params.limit = limit;
  }

  const response = await Forge.get<GlobalSearchResponse>("/api/search", {
    params,
  });
  return response.data.data;
}
