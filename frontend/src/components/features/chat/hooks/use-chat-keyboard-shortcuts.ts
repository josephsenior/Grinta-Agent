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
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isSearchShortcut(event)) {
        event.preventDefault();
        setIsSearchOpen(true);
        return;
      }

      if (isBookmarkShortcut(event)) {
        event.preventDefault();
        bookmarksHook.setIsOpen(true);
        return;
      }

      if (event.key === "Escape") {
        closePanels({
          event,
          isSearchOpen,
          setIsSearchOpen,
          bookmarksHook,
          setShowShortcutsPanel,
        });
      }
    };

    if (!isInputFocused) {
      window.addEventListener("keydown", handleKeyDown);
    }
    
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isInputFocused, isSearchOpen, bookmarksHook, setShowShortcutsPanel]);

  return {
    isSearchOpen,
    setIsSearchOpen,
    bookmarksHook,
  };
}

function isSearchShortcut(event: KeyboardEvent) {
  return (event.ctrlKey || event.metaKey) && event.key === "k";
}

function isBookmarkShortcut(event: KeyboardEvent) {
  return (event.ctrlKey || event.metaKey) && event.key === "b";
}

function closePanels({
  event,
  isSearchOpen,
  setIsSearchOpen,
  bookmarksHook,
  setShowShortcutsPanel,
}: {
  event: KeyboardEvent;
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
  bookmarksHook: ReturnType<typeof useConversationBookmarks>;
  setShowShortcutsPanel: (show: boolean) => void;
}) {
  event.preventDefault();
  if (isSearchOpen) {
    setIsSearchOpen(false);
  }
  if (bookmarksHook.isOpen) {
    bookmarksHook.setIsOpen(false);
  }
  setShowShortcutsPanel(false);
}
