/**
 * React Query hooks for code snippets
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  createSnippet,
  deleteSnippet,
  exportSnippets,
  getSnippet,
  getSnippetStats,
  importSnippets,
  listSnippets,
  searchSnippets,
  trackSnippetUsage,
  updateSnippet,
} from "#/api/snippets";
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

const QUERY_KEYS = {
  snippets: ["snippets"] as const,
  snippet: (id: string) => ["snippets", id] as const,
  stats: ["snippets", "stats"] as const,
  search: (params: SearchSnippetsRequest) => ["snippets", "search", params] as const,
};

export function useSnippets(params?: {
  language?: SnippetLanguage;
  category?: SnippetCategory;
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}): UseQueryResult<CodeSnippet[], Error> {
  return useQuery({
    queryKey: [...QUERY_KEYS.snippets, params],
    queryFn: () => listSnippets(params),
  });
}

export function useSnippet(
  snippetId: string,
): UseQueryResult<CodeSnippet, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.snippet(snippetId),
    queryFn: () => getSnippet(snippetId),
    enabled: !!snippetId,
  });
}

export function useSnippetStats(): UseQueryResult<SnippetStats, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.stats,
    queryFn: getSnippetStats,
  });
}

export function useSearchSnippets(
  params: SearchSnippetsRequest,
): UseQueryResult<CodeSnippet[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.search(params),
    queryFn: () => searchSnippets(params),
    enabled: !!params.query || !!params.language || !!params.category || !!params.tags?.length,
  });
}

export function useCreateSnippet(): UseMutationResult<
  CodeSnippet,
  Error,
  CreateSnippetRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSnippet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

export function useUpdateSnippet(): UseMutationResult<
  CodeSnippet,
  Error,
  { snippetId: string; data: UpdateSnippetRequest }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ snippetId, data }) => updateSnippet(snippetId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippet(data.id) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

export function useDeleteSnippet(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSnippet,
    onSuccess: (_, snippetId) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippet(snippetId) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

export function useExportSnippets(): UseMutationResult<
  SnippetCollection,
  Error,
  { language?: SnippetLanguage; category?: SnippetCategory; is_favorite?: boolean } | undefined
> {
  return useMutation({
    mutationFn: exportSnippets,
  });
}

export function useImportSnippets(): UseMutationResult<
  { imported: number; updated: number; skipped: number; total: number },
  Error,
  SnippetCollection
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importSnippets,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

export function useTrackSnippetUsage(): UseMutationResult<
  CodeSnippet,
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: trackSnippetUsage,
    onSuccess: (data) => {
      queryClient.setQueryData(QUERY_KEYS.snippet(data.id), data);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.snippets });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

