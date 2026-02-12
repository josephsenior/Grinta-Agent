import { useCallback, useMemo, useState } from "react";

/** Minimal event shape that the search hook can filter over. */
interface SearchableEvent {
  id?: number;
  message?: string;
  content?: string;
  args?: Record<string, unknown>;
  extras?: Record<string, unknown>;
}

/** A single search hit with the matching event and highlighted excerpt. */
export interface SearchHit {
  /** Original event index in the source array. */
  index: number;
  /** The matched event. */
  event: SearchableEvent;
  /** A short excerpt around the first match (plain text). */
  excerpt: string;
}

function extractText(event: SearchableEvent): string {
  const parts: string[] = [];
  if (event.message) parts.push(event.message);
  if (event.content) parts.push(event.content);
  if (event.args) {
    const c = event.args.content ?? event.args.thought;
    if (typeof c === "string") parts.push(c);
  }
  if (event.extras) {
    const c = event.extras.content;
    if (typeof c === "string") parts.push(c);
  }
  return parts.join(" ");
}

function buildExcerpt(text: string, query: string, radius = 60): string {
  const lower = text.toLowerCase();
  const idx = lower.indexOf(query.toLowerCase());
  if (idx === -1) return text.slice(0, radius * 2);
  const start = Math.max(0, idx - radius);
  const end = Math.min(text.length, idx + query.length + radius);
  let excerpt = text.slice(start, end);
  if (start > 0) excerpt = `...${excerpt}`;
  if (end < text.length) excerpt = `${excerpt}...`;
  return excerpt;
}

/**
 * Provides conversation search with real text-matching over events.
 *
 * @param events - Array of chat events to search over.
 */
export function useConversationSearch(events: SearchableEvent[] = []) {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const openSearch = useCallback(() => setIsSearchOpen(true), []);
  const closeSearch = useCallback(() => {
    setIsSearchOpen(false);
    setSearchQuery("");
  }, []);

  /** Filtered search results — only computed when query is non-empty. */
  const results: SearchHit[] = useMemo(() => {
    const q = searchQuery.trim();
    if (!q || q.length < 2) return [];

    const hits: SearchHit[] = [];
    const qLower = q.toLowerCase();

    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      const text = extractText(event);
      if (text.toLowerCase().includes(qLower)) {
        hits.push({
          index: i,
          event,
          excerpt: buildExcerpt(text, q),
        });
      }
    }
    return hits;
  }, [events, searchQuery]);

  return {
    isSearchOpen,
    isOpen: isSearchOpen,
    setIsOpen: setIsSearchOpen,
    searchQuery,
    setSearchQuery,
    openSearch,
    closeSearch,
    /** Number of matching events. */
    resultCount: results.length,
    /** Array of search hits with excerpts. */
    results,
  };
}
