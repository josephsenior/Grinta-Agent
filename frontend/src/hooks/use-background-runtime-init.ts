import { useEffect, useState } from "react";
import { useConversationId } from "#/hooks/use-conversation-id";

interface RuntimeInitStatus {
  isInitializing: boolean;
  isReady: boolean;
  error: string | null;
}

/**
 * Hook to handle background runtime initialization
 * Starts the runtime container in the background while user configures settings
 */
export function useBackgroundRuntimeInit() {
  const [status, setStatus] = useState<RuntimeInitStatus>({
    isInitializing: false,
    isReady: false,
    error: null,
  });

  const { conversationId } = useConversationId();

  useEffect(() => {
    const checkRuntimeStatus = async () => {
      try {
        // Check if conversation is initialized
        if (!conversationId) {
          return;
        }

        setStatus({ isInitializing: true, isReady: false, error: null });

        // Poll the conversation status to check if runtime is ready
        const checkInterval = setInterval(async () => {
          try {
            const response = await fetch(
              `/api/conversations/${conversationId}`,
            );
            if (!response.ok) {
              throw new Error("Failed to check runtime status");
            }

            const data = await response.json();

            // Check if agent is in a ready state
            if (
              data.status === "AWAITING_USER_INPUT" ||
              data.status === "RUNNING" ||
              data.status === "FINISHED"
            ) {
              setStatus({ isInitializing: false, isReady: true, error: null });
              clearInterval(checkInterval);
            } else if (data.status === "ERROR") {
              setStatus({
                isInitializing: false,
                isReady: false,
                error: "Runtime initialization failed",
              });
              clearInterval(checkInterval);
            }
          } catch (error) {
            console.error("Error checking runtime status:", error);
          }
        }, 2000); // Poll every 2 seconds

        // Timeout after 60 seconds
        setTimeout(() => {
          clearInterval(checkInterval);
          if (!status.isReady) {
            setStatus({
              isInitializing: false,
              isReady: false,
              error: "Runtime initialization timeout",
            });
          }
        }, 60000);

        return () => clearInterval(checkInterval);
      } catch (error) {
        setStatus({
          isInitializing: false,
          isReady: false,
          error: error instanceof Error ? error.message : "Unknown error",
        });
      }
    };

    checkRuntimeStatus();
  }, [conversationId]);

  return status;
}

