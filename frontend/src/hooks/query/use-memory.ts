/**
 * React Query hooks for memory management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as memoryAPI from "#/api/memory";
import type { UpdateMemoryRequest } from "#/types/memory";

/**
 * Fetch all memories
 */
export function useMemories() {
  return useQuery({
    queryKey: ["memories"],
    queryFn: memoryAPI.listMemories,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Get a single memory
 */
export function useMemory(memoryId: string | null) {
  return useQuery({
    queryKey: ["memory", memoryId],
    queryFn: () => memoryAPI.getMemory(memoryId!),
    enabled: !!memoryId,
  });
}

/**
 * Create a new memory
 */
export function useCreateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: memoryAPI.createMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
    },
  });
}

/**
 * Update a memory
 */
export function useUpdateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memoryId,
      updates,
    }: {
      memoryId: string;
      updates: UpdateMemoryRequest;
    }) => memoryAPI.updateMemory(memoryId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
    },
  });
}

/**
 * Delete a memory
 */
export function useDeleteMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: memoryAPI.deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
    },
  });
}

/**
 * Search memories
 */
export function useSearchMemories() {
  return useMutation({
    mutationFn: memoryAPI.searchMemories,
  });
}

/**
 * Get memory statistics
 */
export function useMemoryStats() {
  return useQuery({
    queryKey: ["memory-stats"],
    queryFn: memoryAPI.getMemoryStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Track memory usage
 */
export function useTrackMemoryUsage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: memoryAPI.trackMemoryUsage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
    },
  });
}

/**
 * Export memories
 */
export function useExportMemories() {
  return useMutation({
    mutationFn: memoryAPI.exportMemories,
  });
}

/**
 * Import memories
 */
export function useImportMemories() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ data, merge }: { data: any; merge: boolean }) =>
      memoryAPI.importMemories(data, merge),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      queryClient.invalidateQueries({ queryKey: ["memory-stats"] });
    },
  });
}
