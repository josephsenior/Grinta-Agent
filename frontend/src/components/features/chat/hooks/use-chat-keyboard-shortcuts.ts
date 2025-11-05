import React from "react";
import { useKeyboardShortcuts } from "../keyboard-shortcuts-panel";
import { useConversationSearch } from "./use-conversation-search";
import { useConversationBookmarks } from "./use-conversation-bookmarks";

/**
 * Custom hook to manage keyboard shortcuts for the chat interface
 * Centralizes all keyboard shortcut logic
 */
export function useChatKeyboardShortcuts(
  isInputFocused: boolean,
  setShowShortcutsPanel: (show: boolean) => void
) {
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } = useConversationSearch();
  const bookmarksHook = useConversationBookmarks();

  // Use existing keyboard shortcuts hook
  useKeyboardShortcuts(() => setShowShortcutsPanel(true), isInputFocused);

  // Additional keyboard shortcuts for search and bookmarks
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
      
      // Cmd/Ctrl + B for bookmarks
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        bookmarksHook.setIsOpen(true);
      }
      
      // Escape to close panels
      if (e.key === 'Escape') {
        if (isSearchOpen) setIsSearchOpen(false);
        if (bookmarksHook.isOpen) bookmarksHook.setIsOpen(false);
        if (setShowShortcutsPanel) setShowShortcutsPanel(false);
      }
    };

    if (!isInputFocused) {
      window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isInputFocused, isSearchOpen, bookmarksHook, setShowShortcutsPanel]);

  return {
    isSearchOpen,
    setIsSearchOpen,
    bookmarksHook,
  };
}
