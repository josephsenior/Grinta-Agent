import { useState, useEffect } from "react";
import { ForgeAction, ForgeObservation } from "#/types/core";
import { SearchFilter, SearchResult } from "../types";
import { getMessageText } from "../utils/message-helpers";
import {
  matchesFilter,
  calculateMatchScore,
  createSnippet,
  createSearchResult,
} from "../utils/search-helpers";

interface UseConversationSearchOptions {
  messages: (ForgeAction | ForgeObservation)[];
  query: string;
  filter: SearchFilter;
}

export function useConversationSearch({
  messages,
  query,
  filter,
}: UseConversationSearchOptions) {
  const [results, setResults] = useState<SearchResult[]>([]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const searchQuery = query.toLowerCase();
    const searchResults: SearchResult[] = [];

    messages.forEach((message, index) => {
      if (!matchesFilter(message, filter)) {
        return;
      }

      const text = getMessageText(message);
      const lowerText = text.toLowerCase();

      if (!lowerText.includes(searchQuery)) {
        return;
      }

      const matchScore = calculateMatchScore(text, searchQuery);
      const snippet = createSnippet(text, searchQuery);
      const result = createSearchResult(message, index, snippet, matchScore);

      searchResults.push(result);
    });

    searchResults.sort((a, b) => b.matchScore - a.matchScore);
    setResults(searchResults.slice(0, 50));
  }, [query, filter, messages]);

  return results;
}
