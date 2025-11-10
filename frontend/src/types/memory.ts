/**
 * Memory system types and interfaces
 */

export type MemoryCategory =
  | "technical"
  | "preference"
  | "project"
  | "fact"
  | "custom";

export type MemorySource = "manual" | "ai-suggested";

export type MemoryImportance = "low" | "medium" | "high";

export interface Memory {
  id: string;
  title: string;
  content: string;
  category: MemoryCategory;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  usageCount: number;
  lastUsed: string | null;
  source: MemorySource;
  conversationId: string | null;
  importance: MemoryImportance;
}

export interface CreateMemoryRequest {
  title: string;
  content: string;
  category: MemoryCategory;
  tags?: string[];
  importance?: MemoryImportance;
  conversationId?: string;
}

export interface UpdateMemoryRequest {
  title?: string;
  content?: string;
  category?: MemoryCategory;
  tags?: string[];
  importance?: MemoryImportance;
}

export interface SearchMemoriesRequest {
  query: string;
  category?: MemoryCategory;
  tags?: string[];
  minUsageCount?: number;
  importance?: MemoryImportance;
}

export interface MemoryStats {
  total: number;
  byCategory: Record<MemoryCategory, number>;
  usedToday: number;
  mostUsed: Memory[];
  recentlyUsed: Memory[];
}

export interface MemoryExport {
  version: string;
  exportedAt: string;
  memories: Memory[];
  stats: MemoryStats;
}
