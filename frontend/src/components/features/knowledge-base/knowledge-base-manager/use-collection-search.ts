import { useState, useMemo } from "react";
import type { KnowledgeBaseCollection } from "#/types/knowledge-base";

export function useCollectionSearch(collections?: KnowledgeBaseCollection[]) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredCollections = useMemo(() => {
    if (!collections) return undefined;
    if (!searchQuery.trim()) return collections;

    const query = searchQuery.toLowerCase();
    return collections.filter(
      (collection) =>
        collection.name.toLowerCase().includes(query) ||
        collection.description?.toLowerCase().includes(query),
    );
  }, [collections, searchQuery]);

  return {
    searchQuery,
    setSearchQuery,
    filteredCollections,
  };
}
