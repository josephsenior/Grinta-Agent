import { useEffect } from "react";
import { useConversationId } from "#/hooks/use-conversation-id";
import { useUserConversation } from "./use-user-conversation";
import Forge from "#/api/forge";

const FIVE_MINUTES = 1000 * 60 * 5;

export const useActiveConversation = () => {
  const { conversationId } = useConversationId();
  const userConversation = useUserConversation(conversationId, (query) => {
    if (query.state.data?.status === "STARTING") {
      return 3000; // 3 seconds
    }
    return FIVE_MINUTES;
  });

  useEffect(() => {
    const conversation = userConversation.data;
    Forge.setCurrentConversation(conversation || null);
  }, [
    conversationId,
    userConversation.isFetched,
    userConversation?.data?.status,
  ]);
  return userConversation;
};
