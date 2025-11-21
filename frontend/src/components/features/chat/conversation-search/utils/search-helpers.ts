import { ForgeAction, ForgeObservation } from "#/types/core";
import { isUserMessage, isAssistantMessage } from "#/types/core/guards";
import { SearchFilter, SearchResult } from "../types";

export function matchesFilter(
  message: ForgeAction | ForgeObservation,
  filter: SearchFilter,
): boolean {
  if (filter === "all") return true;
  if (filter === "user") return isUserMessage(message);
  if (filter === "agent") return isAssistantMessage(message);
  return true;
}

export function calculateMatchScore(text: string, query: string): number {
  const lowerText = text.toLowerCase();
  const exactMatch = lowerText === query;
  const startsWithMatch = lowerText.startsWith(query);
  const wordMatch = lowerText.split(/\s+/).some((word) => word === query);

  if (exactMatch) return 100;
  if (startsWithMatch) return 80;
  if (wordMatch) return 60;
  return 40;
}

export function createSnippet(
  text: string,
  query: string,
  contextLength: number = 50,
): string {
  const lowerText = text.toLowerCase();
  const matchIndex = lowerText.indexOf(query);
  const snippetStart = Math.max(0, matchIndex - contextLength);
  const snippetEnd = Math.min(
    text.length,
    matchIndex + query.length + contextLength,
  );
  let snippet = text.slice(snippetStart, snippetEnd);

  if (snippetStart > 0) snippet = `...${snippet}`;
  if (snippetEnd < text.length) snippet += "...";

  return snippet;
}

export function createSearchResult(
  message: ForgeAction | ForgeObservation,
  index: number,
  snippet: string,
  matchScore: number,
): SearchResult {
  return {
    index,
    message,
    snippet,
    timestamp: message.timestamp ? new Date(message.timestamp) : undefined,
    matchScore,
  };
}
