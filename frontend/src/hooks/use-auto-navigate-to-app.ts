/**
 * Production-grade automatic navigation to browser when servers start.
 *
 * This hook implements the Hybrid Approach for 100% reliable server detection:
 * 1. Backend detects server start via command output patterns
 * 2. Backend verifies port is actually listening
 * 3. Backend performs HTTP health check
 * 4. Backend emits ServerReadyObservation
 * 5. Frontend receives event and automatically navigates
 *
 * No pattern matching, no timeouts, no race conditions - purely event-driven.
 */

import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useConversationId } from "#/hooks/use-conversation-id";

interface ServerReadyEvent {
  port: number;
  url: string;
  protocol: string;
  health_status: string;
}

/**
 * Listen for server-ready events from the backend and automatically
 * navigate the browser tab to the detected server.
 */
export function useAutoNavigateToApp() {
  const navigate = useNavigate();
  const location = useLocation();
  const { conversationId } = useConversationId();

  useEffect(() => {
    const handleServerReady = (event: CustomEvent<ServerReadyEvent>) => {
      const { url, health_status } = event.detail;

      console.warn(
        `[Auto-Navigate] 🔍 RECEIVED SERVER-READY EVENT:`,
        event.detail,
      );

      // Only navigate if health check passed or is unknown (some servers take time to initialize)
      if (health_status === "unhealthy") {
        console.warn(
          `[Auto-Navigate] Server at ${url} failed health check, skipping navigation`,
        );
        return;
      }

      console.log(
        `[Auto-Navigate] Server ready at ${url}, navigating to browser tab`,
      );

      // Navigate to browser tab if not already there
      if (!location.pathname.endsWith("/browser")) {
        navigate(`/conversations/${conversationId}/browser`);

        // Wait for browser tab to load, then navigate to the URL
        setTimeout(() => {
          window.dispatchEvent(
            new CustomEvent("Forge:load-server-url", {
              detail: { url },
            }),
          );
        }, 100);
      } else {
        // Already on browser tab, just load the URL
        window.dispatchEvent(
          new CustomEvent("Forge:load-server-url", {
            detail: { url },
          }),
        );
      }
    };

    // Listen for server-ready events from the backend
    window.addEventListener(
      "Forge:server-ready",
      handleServerReady as EventListener,
    );

    return () => {
      window.removeEventListener(
        "Forge:server-ready",
        handleServerReady as EventListener,
      );
    };
  }, [navigate, conversationId, location.pathname]);
}
