/**
 * API client for memory management
 */

import { Forge } from "./forge-axios";
import type {
  Memory,
  CreateMemoryRequest,
  UpdateMemoryRequest,
  SearchMemoriesRequest,
  MemoryStats,
  MemoryExport,
} from "#/types/memory";

/**
 * List all memories
 */
export async function listMemories(): Promise<Memory[]> {
  const response = await Forge.get("/api/memory");
  return response.data;
}

/**
 * Get a single memory by ID
 */
export async function getMemory(memoryId: string): Promise<Memory> {
  const response = await Forge.get(`/api/memory/${memoryId}`);
  return response.data;
}

/**
 * Create a new memory
 */
export async function createMemory(
  memory: CreateMemoryRequest,
): Promise<{ status: string; memory: Memory }> {
  const response = await Forge.post("/api/memory", memory);
  return response.data;
}

/**
 * Update an existing memory
 */
export async function updateMemory(
  memoryId: string,
  updates: UpdateMemoryRequest,
): Promise<{ status: string }> {
  const response = await Forge.patch(`/api/memory/${memoryId}`, updates);
  return response.data;
}

/**
 * Delete a memory
 */
export async function deleteMemory(memoryId: string): Promise<void> {
  await Forge.delete(`/api/memory/${memoryId}`);
}

/**
 * Search memories
 */
export async function searchMemories(
  search: SearchMemoriesRequest,
): Promise<Memory[]> {
  const response = await Forge.post("/api/memory/search", search);
  return response.data;
}

/**
 * Get memory statistics
 */
export async function getMemoryStats(): Promise<MemoryStats> {
  const response = await Forge.get("/api/memory/stats");
  return response.data;
}

/**
 * Track memory usage
 */
export async function trackMemoryUsage(memoryId: string): Promise<void> {
  await Forge.post(`/api/memory/${memoryId}/track-usage`);
}

/**
 * Export memories to JSON
 */
export async function exportMemories(): Promise<MemoryExport> {
  const response = await Forge.get("/api/memory/export");
  return response.data;
}

/**
 * Import memories from JSON
 */
export async function importMemories(
  data: any,
  merge: boolean = false,
): Promise<{ status: string; imported: number; total: number }> {
  const response = await Forge.post(`/api/memory/import?merge=${merge}`, data);
  return response.data;
}

