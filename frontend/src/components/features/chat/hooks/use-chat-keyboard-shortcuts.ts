import React from "react";
import { useConversationSearch } from "./use-conversation-search";

function isSearchShortcut(event: KeyboardEvent) {
  return (event.ctrlKey || event.metaKey) && event.key === "k";
}

function closePanels({
  event,
  isSearchOpen,
  setIsOpen,
}: {
  event: KeyboardEvent;
  isSearchOpen: boolean;
  setIsOpen: (open: boolean) => void;
}) {
  event.preventDefault();
  if (isSearchOpen) {
    setIsOpen(false);
  }
}

/**
 * Custom hook to manage keyboard shortcuts for the chat interface
 * Centralizes all keyboard shortcut logic
 */
export function useChatKeyboardShortcuts(isInputFocused: boolean) {
  const { isOpen: isSearchOpen, setIsOpen: setIsSearchOpen } =
    useConversationSearch();

  // Additional keyboard shortcuts for search
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isSearchShortcut(event)) {
        event.preventDefault();
        setIsSearchOpen(true);
        return;
      }

      if (event.key === "Escape") {
        closePanels({
          event,
          isSearchOpen,
          setIsOpen: setIsSearchOpen,
        });
      }
    };

    if (!isInputFocused) {
      window.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isInputFocused, isSearchOpen, setIsSearchOpen]);

  return {
    isSearchOpen,
    setIsSearchOpen,
  };
}
