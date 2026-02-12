import { useCallback, useEffect, useRef } from "react";

/**
 * Known shortcut definitions used across the chat UI.
 *
 * Each handler is optional — only shortcuts whose handlers are provided
 * will be active. Modifier key is Ctrl on Windows/Linux, Cmd on macOS.
 */
interface ShortcutHandlers {
  /** Ctrl/Cmd + K — open search */
  openSearch?: () => void;
  /** Ctrl/Cmd + B — toggle bookmarks / sidebar */
  openBookmarks?: () => void;
  /** Ctrl/Cmd + / — toggle keyboard shortcut help */
  toggleShortcutHelp?: () => void;
  /** Ctrl/Cmd + Shift + C — copy last agent message */
  copyLastMessage?: () => void;
  /** Ctrl/Cmd + L — clear conversation */
  clearConversation?: () => void;
  /** Escape — close any open panel / cancel */
  escape?: () => void;
  /** Ctrl/Cmd + Enter — send / submit (when focused in chat input) */
  submitMessage?: () => void;
}

/**
 * Registers global keyboard shortcuts for the chat interface.
 *
 * @param handlers - Map of shortcut keys to handler callbacks
 * @returns Empty object (for future expansion)
 */
export function useKeyboardShortcuts(
  handlers: ShortcutHandlers = {},
) {
  // Keep a ref to avoid re-registering the listener every time handlers changes
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const h = handlersRef.current;
    const mod = e.ctrlKey || e.metaKey;

    // Escape — no modifier required
    if (e.key === "Escape" && h.escape) {
      e.preventDefault();
      h.escape();
      return;
    }

    if (!mod) return;

    switch (e.key.toLowerCase()) {
      case "k":
        if (h.openSearch) {
          e.preventDefault();
          h.openSearch();
        }
        break;
      case "b":
        if (h.openBookmarks) {
          e.preventDefault();
          h.openBookmarks();
        }
        break;
      case "/":
        if (h.toggleShortcutHelp) {
          e.preventDefault();
          h.toggleShortcutHelp();
        }
        break;
      case "l":
        if (h.clearConversation) {
          e.preventDefault();
          h.clearConversation();
        }
        break;
      case "c":
        if (e.shiftKey && h.copyLastMessage) {
          e.preventDefault();
          h.copyLastMessage();
        }
        break;
      case "enter":
        if (h.submitMessage) {
          e.preventDefault();
          h.submitMessage();
        }
        break;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return {};
}
