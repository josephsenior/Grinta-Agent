import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useConversationId } from "./use-conversation-id";

export interface ServerReadyDetail {
  url: string;
  health_status: "healthy" | "unhealthy" | string;
}

/**
 * Hook to automatically navigate to the browser tab when a server is ready.
 * This is triggered when the agent starts a web server (e.g., React dev server).
 */
export function useAutoNavigateToApp() {
  const navigate = useNavigate();
  const location = useLocation();
  const { conversationId } = useConversationId();

  React.useEffect(() => {
    const handleServerReady = (event: Event) => {
      const customEvent = event as CustomEvent<ServerReadyDetail>;
      const { url, health_status: healthStatus } = customEvent.detail;

      if (healthStatus === "healthy") {
        // Only navigate if we're not already on the browser page
        if (!location.pathname.endsWith("/browser") && conversationId) {
          navigate(`/conversations/${conversationId}/browser`);
        }

        // Always dispatch the load event to update the browser URL
        // Give a small delay to ensure the browser component is mounted if we just navigated
        setTimeout(() => {
          window.dispatchEvent(
            new CustomEvent("Forge:load-server-url", {
              detail: { url },
            }),
          );
        }, 100);
      }
    };

    window.addEventListener("Forge:server-ready", handleServerReady);
    return () => {
      window.removeEventListener("Forge:server-ready", handleServerReady);
    };
  }, [navigate, location.pathname, conversationId]);
}
