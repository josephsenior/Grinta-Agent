/**
 * Utility functions for keyboard event handling
 */

export function isInputElement(target: EventTarget | null): boolean {
  if (!target) return false;
  const element = target as HTMLElement;
  return (
    element.tagName === "INPUT" ||
    element.tagName === "TEXTAREA" ||
    element.isContentEditable ||
    Boolean(element.closest("[role='textbox']") && element.isContentEditable)
  );
}

export function isModifierPressed(
  event: KeyboardEvent,
  modifier: "ctrl" | "meta" | "shift" | "alt",
): boolean {
  switch (modifier) {
    case "ctrl":
      return event.ctrlKey;
    case "meta":
      return event.metaKey || event.ctrlKey; // Cmd on Mac, Ctrl on Windows/Linux
    case "shift":
      return event.shiftKey;
    case "alt":
      return event.altKey;
    default:
      return false;
  }
}

export function matchesKey(
  event: KeyboardEvent,
  key: string,
  caseSensitive = false,
): boolean {
  if (caseSensitive) {
    return event.key === key;
  }
  return event.key.toLowerCase() === key.toLowerCase() || event.key === key;
}
