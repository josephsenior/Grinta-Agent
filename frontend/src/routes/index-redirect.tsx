import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { logger } from "#/utils/logger";

/**
 * Root route - Auto-creates or loads first conversation
 * Shows main chat interface immediately
 */
export default function IndexRedirect() {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending: isCreating } =
    useCreateConversation();
  const {
    data,
    isLoading: conversationsLoading,
    isError,
  } = usePaginatedConversations(1);
  const hasAttemptedCreation = useRef(false);

  useEffect(() => {
    // Wait for conversations to load
    if (conversationsLoading) return;

    // If we have conversations, navigate to the first one
    const firstPage = data?.pages?.[0];
    if (firstPage?.results?.length) {
      const firstConversation = firstPage.results[0];
      logger.debug(
        `IndexRedirect: Navigating to existing conversation ${firstConversation.conversation_id}`,
      );
      navigate(`/conversations/${firstConversation.conversation_id}`, {
        replace: true,
      });
      return;
    }

    // If no conversations and not loading, create a new one (only once)
    if (!isCreating && !hasAttemptedCreation.current) {
      hasAttemptedCreation.current = true;
      logger.debug("IndexRedirect: No conversations found, creating new one");
      createConversation(
        {},
        {
          onSuccess: (response) => {
            navigate(`/conversations/${response.conversation_id}`, {
              replace: true,
            });
          },
          onError: (err) => {
            logger.error(
              "IndexRedirect: Failed to create initial conversation",
              err,
            );
            // Fallback - stay on root which will render the welcome screen via DesktopLayout fallback
          },
        },
      );
    } else if (isError) {
      logger.error("IndexRedirect: Error loading conversations");
    }
  }, [
    data,
    conversationsLoading,
    isCreating,
    isError,
    createConversation,
    navigate,
  ]);

  // Show loading while determining where to navigate
  return (
    <div className="h-full w-full flex items-center justify-center bg-[var(--bg-primary)]">
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="large" />
        <span className="text-xs font-medium text-[var(--text-tertiary)] animate-pulse">
          Preparing your workspace...
        </span>
      </div>
    </div>
  );
}
