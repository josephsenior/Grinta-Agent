import { useIsMutating } from "@tanstack/react-query";

export const useIsCreatingConversation = () => {
  const numberOfPendingMutations = useIsMutating({
    mutationKey: ["create-conversation"],
  });

  const hasPendingMutations = numberOfPendingMutations > 0;

  return hasPendingMutations;
};
