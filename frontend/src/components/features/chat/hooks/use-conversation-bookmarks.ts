import { useState } from "react";

/**
 * Placeholder hook for conversation bookmarks functionality
 * TODO: Implement actual bookmarks functionality
 */
export function useConversationBookmarks() {
  // Provide a backwards-compatible bookmarks hook surface.
  // Newer code defines the more complete hook in `conversation-bookmarks.tsx`.
  const [isOpen, setIsOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState<any[]>([]);

  const openBookmarks = () => setIsOpen(true);
  const closeBookmarks = () => setIsOpen(false);

  const addBookmark = (messageId: string) => {
    setBookmarks((prev) => [...prev, { id: messageId, timestamp: Date.now() }]);
  };

  const removeBookmark = (messageId: string) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== messageId));
  };

  return {
    // primary names used by callers in various places
    isOpen,
    setIsOpen,
    bookmarks,
    openBookmarks,
    closeBookmarks,
    addBookmark,
    removeBookmark,
    // legacy alias retained for some consumers
    isBookmarksOpen: isOpen,
  };
}

