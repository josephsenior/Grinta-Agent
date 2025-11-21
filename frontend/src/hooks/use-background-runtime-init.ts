import { useEffect, useState } from "react";
import { useConversationId } from "#/hooks/use-conversation-id";
import { logger } from "#/utils/logger";

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
    let cleanupFn: (() => void) | undefined;

    const checkRuntimeStatus = async (): Promise<(() => void) | undefined> => {
      try {
        // Check if conversation is initialized
        if (!conversationId) {
          return undefined;
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
            logger.error("Error checking runtime status:", error);
          }
        }, 2000); // Poll every 2 seconds

        const timeoutId = setTimeout(() => {
          clearInterval(checkInterval);
          if (!status.isReady) {
            setStatus({
              isInitializing: false,
              isReady: false,
              error: "Runtime initialization timeout",
            });
          }
        }, 60000);

        return () => {
          clearInterval(checkInterval);
          clearTimeout(timeoutId);
        };
      } catch (error) {
        setStatus({
          isInitializing: false,
          isReady: false,
          error: error instanceof Error ? error.message : "Unknown error",
        });
        return undefined;
      }
    };

    checkRuntimeStatus().then((cleanup) => {
      cleanupFn = cleanup;
    });

    return () => {
      if (cleanupFn) {
        cleanupFn();
      }
    };
  }, [conversationId]);

  return status;
}
