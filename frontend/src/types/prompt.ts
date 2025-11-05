/**
 * TypeScript types for prompt templates
 */

export enum PromptCategory {
  CODING = "coding",
  DEBUGGING = "debugging",
  REFACTORING = "refactoring",
  TESTING = "testing",
  DOCUMENTATION = "documentation",
  CODE_REVIEW = "code_review",
  WRITING = "writing",
  ANALYSIS = "analysis",
  TRANSLATION = "translation",
  SUMMARIZATION = "summarization",
  BRAINSTORMING = "brainstorming",
  CUSTOM = "custom",
}

export interface PromptVariable {
  name: string;
  description?: string;
  default_value?: string;
  required: boolean;
}

export interface PromptTemplate {
  id: string;
  title: string;
  description?: string;
  category: PromptCategory;
  content: string;
  variables: PromptVariable[];
  tags: string[];
  is_favorite: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface CreatePromptRequest {
  title: string;
  description?: string;
  category?: PromptCategory;
  content: string;
  variables?: PromptVariable[];
  tags?: string[];
  is_favorite?: boolean;
}

export interface UpdatePromptRequest {
  title?: string;
  description?: string;
  category?: PromptCategory;
  content?: string;
  variables?: PromptVariable[];
  tags?: string[];
  is_favorite?: boolean;
}

export interface SearchPromptsRequest {
  query?: string;
  category?: PromptCategory;
  tags?: string[];
  is_favorite?: boolean;
  limit?: number;
  offset?: number;
}

export interface PromptStats {
  total_prompts: number;
  prompts_by_category: Record<string, number>;
  total_favorites: number;
  most_used_prompts: [string, number][];
  total_tags: number;
}

export interface PromptCollection {
  name: string;
  description?: string;
  version: string;
  prompts: PromptTemplate[];
  metadata: Record<string, unknown>;
}

export interface RenderPromptRequest {
  prompt_id: string;
  variables: Record<string, string>;
}

export interface RenderPromptResponse {
  rendered: string;
}

// UI-specific types
export interface PromptFormData {
  title: string;
  description: string;
  category: PromptCategory;
  content: string;
  variables: PromptVariable[];
  tags: string[];
  is_favorite: boolean;
}

export const PROMPT_CATEGORY_LABELS: Record<PromptCategory, string> = {
  [PromptCategory.CODING]: "Coding",
  [PromptCategory.DEBUGGING]: "Debugging",
  [PromptCategory.REFACTORING]: "Refactoring",
  [PromptCategory.TESTING]: "Testing",
  [PromptCategory.DOCUMENTATION]: "Documentation",
  [PromptCategory.CODE_REVIEW]: "Code Review",
  [PromptCategory.WRITING]: "Writing",
  [PromptCategory.ANALYSIS]: "Analysis",
  [PromptCategory.TRANSLATION]: "Translation",
  [PromptCategory.SUMMARIZATION]: "Summarization",
  [PromptCategory.BRAINSTORMING]: "Brainstorming",
  [PromptCategory.CUSTOM]: "Custom",
};

