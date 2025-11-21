import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useIsCreatingConversation } from "#/hooks/use-is-creating-conversation";

export function useHeaderHandlers() {
  const navigate = useNavigate();
  const { mutate: createConversation, isPending } = useCreateConversation();
  const isCreatingConversationElsewhere = useIsCreatingConversation();

  const handleCreateConversation = useCallback(() => {
    if (isPending) {
      return;
    }
    createConversation(
      {},
      {
        onSuccess: (data) => {
          try {
            localStorage.setItem(
              "RECENT_CONVERSATION_ID",
              data.conversation_id,
            );
          } catch (e) {
            // ignore errors when persisting recent conversation id (e.g., storage disabled)
          }
          navigate(`/conversations/${data.conversation_id}`);
        },
      },
    );
  }, [createConversation, isPending, navigate]);

  const handleOpenMessages = useCallback(() => {
    // Request opening the conversation overlay panel via a custom event
    const event = new CustomEvent("Forge:open-conversation-panel");
    window.dispatchEvent(event);
  }, []);

  return {
    handleCreateConversation,
    handleOpenMessages,
    isPending,
    isCreatingConversationElsewhere,
  };
}
