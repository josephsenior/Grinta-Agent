import { useState } from "react";

/**
 * Placeholder hook for conversation search functionality
 * TODO: Implement actual search functionality
 */
export function useConversationSearch() {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const openSearch = () => setIsSearchOpen(true);
  const closeSearch = () => {
    setIsSearchOpen(false);
    setSearchQuery("");
  };

  return {
    isSearchOpen,
    // Backwards-compatible aliases used across callers
    isOpen: isSearchOpen,
    setIsOpen: setIsSearchOpen,
    searchQuery,
    setSearchQuery,
    openSearch,
    closeSearch,
  };
}
