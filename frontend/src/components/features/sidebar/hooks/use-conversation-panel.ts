import { useState, useEffect } from "react";

interface WindowWithE2E extends Window {
  __Forge_PLAYWRIGHT?: boolean;
}

export function useConversationPanel() {
  const [conversationPanelIsOpen, setConversationPanelIsOpen] = useState(false);

  useEffect(() => {
    const win =
      typeof window !== "undefined"
        ? (window as unknown as WindowWithE2E)
        : undefined;

    const openHandler = () => setConversationPanelIsOpen(true);
    window.addEventListener("Forge:open-conversation-panel", openHandler);

    // If Playwright is running, open immediately
    if (win?.__Forge_PLAYWRIGHT === true) {
      openHandler();
    }

    return () => {
      window.removeEventListener("Forge:open-conversation-panel", openHandler);
    };
  }, []);

  return {
    conversationPanelIsOpen,
    setConversationPanelIsOpen,
  };
}
