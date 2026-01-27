export type MemoryCategory = "technical" | "preference" | "project" | "fact" | "custom";
export type MemorySource = "manual" | "ai-suggested";
export type MemoryImportance = "low" | "medium" | "high";

export interface Memory {
  id: string;
  title: string;
  content: string;
  category: MemoryCategory;
  tags: string[];
  created_at: string;
  updated_at: string;
  usage_count: number;
  last_used: string | null;
  source: MemorySource;
  conversation_id: string | null;
  importance: MemoryImportance;
}

export interface CreateMemoryRequest {
  title: string;
  content: string;
  category: MemoryCategory;
  tags?: string[];
  importance?: MemoryImportance;
  conversation_id?: string;
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
  min_usage_count?: number;
  importance?: MemoryImportance;
}

export interface MemoryStats {
  total: number;
  by_category: Record<string, number>;
  used_today: number;
  most_used: Memory[];
  recently_used: Memory[];
}

export interface MemoryExport {
  memories: Memory[];
  exported_at: string;
}
