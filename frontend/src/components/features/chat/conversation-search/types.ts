import { ForgeAction, ForgeObservation } from "#/types/core";

export interface SearchResult {
  index: number;
  message: ForgeAction | ForgeObservation;
  snippet: string;
  timestamp?: Date;
  matchScore: number;
}

export type SearchFilter = "all" | "user" | "agent" | "code" | "errors";
