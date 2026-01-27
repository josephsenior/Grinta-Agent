import { useCallback } from "react";

export function useHeaderHandlers() {
  const handleOpenMessages = useCallback(() => {
    // Request opening the conversation overlay panel via a custom event
    const event = new CustomEvent("Forge:open-conversation-panel");
    window.dispatchEvent(event);
  }, []);

  return {
    handleOpenMessages,
  };
}
