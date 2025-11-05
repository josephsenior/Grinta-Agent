/**
 * React Query hooks for prompt templates
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  createPrompt,
  deletePrompt,
  exportPrompts,
  getPrompt,
  getPromptStats,
  importPrompts,
  listPrompts,
  renderPrompt,
  searchPrompts,
  trackPromptUsage,
  updatePrompt,
} from "#/api/prompts";
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

const QUERY_KEYS = {
  prompts: ["prompts"] as const,
  prompt: (id: string) => ["prompts", id] as const,
  stats: ["prompts", "stats"] as const,
  search: (params: SearchPromptsRequest) => ["prompts", "search", params] as const,
};

/**
 * Hook to fetch all prompts
 */
export function usePrompts(params?: {
  category?: PromptCategory;
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}): UseQueryResult<PromptTemplate[], Error> {
  return useQuery({
    queryKey: [...QUERY_KEYS.prompts, params],
    queryFn: () => listPrompts(params),
  });
}

/**
 * Hook to fetch a single prompt by ID
 */
export function usePrompt(
  promptId: string,
): UseQueryResult<PromptTemplate, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.prompt(promptId),
    queryFn: () => getPrompt(promptId),
    enabled: !!promptId,
  });
}

/**
 * Hook to fetch prompt statistics
 */
export function usePromptStats(): UseQueryResult<PromptStats, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.stats,
    queryFn: getPromptStats,
  });
}

/**
 * Hook to search prompts
 */
export function useSearchPrompts(
  params: SearchPromptsRequest,
): UseQueryResult<PromptTemplate[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.search(params),
    queryFn: () => searchPrompts(params),
    enabled: !!params.query || !!params.category || !!params.tags?.length,
  });
}

/**
 * Hook to create a new prompt
 */
export function useCreatePrompt(): UseMutationResult<
  PromptTemplate,
  Error,
  CreatePromptRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPrompt,
    onSuccess: () => {
      // Invalidate all prompt queries to refetch
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

/**
 * Hook to update an existing prompt
 */
export function useUpdatePrompt(): UseMutationResult<
  PromptTemplate,
  Error,
  { promptId: string; data: UpdatePromptRequest }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ promptId, data }) => updatePrompt(promptId, data),
    onSuccess: (data) => {
      // Invalidate specific prompt and list queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompt(data.id) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

/**
 * Hook to delete a prompt
 */
export function useDeletePrompt(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deletePrompt,
    onSuccess: (_, promptId) => {
      // Invalidate all prompt queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompt(promptId) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

/**
 * Hook to export prompts
 */
export function useExportPrompts(): UseMutationResult<
  PromptCollection,
  Error,
  { category?: PromptCategory; is_favorite?: boolean } | undefined
> {
  return useMutation({
    mutationFn: exportPrompts,
  });
}

/**
 * Hook to import prompts
 */
export function useImportPrompts(): UseMutationResult<
  { imported: number; updated: number; skipped: number; total: number },
  Error,
  PromptCollection
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importPrompts,
    onSuccess: () => {
      // Invalidate all prompt queries to refetch
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

/**
 * Hook to render a prompt with variables
 */
export function useRenderPrompt(): UseMutationResult<
  RenderPromptResponse,
  Error,
  RenderPromptRequest
> {
  return useMutation({
    mutationFn: renderPrompt,
  });
}

/**
 * Hook to track prompt usage
 */
export function useTrackPromptUsage(): UseMutationResult<
  PromptTemplate,
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: trackPromptUsage,
    onSuccess: (data) => {
      // Update the specific prompt in cache
      queryClient.setQueryData(QUERY_KEYS.prompt(data.id), data);
      // Invalidate list to update usage counts
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.prompts });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.stats });
    },
  });
}

