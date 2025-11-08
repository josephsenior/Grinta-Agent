import { useMutation } from "@tanstack/react-query";
import { Feedback } from "#/api/forge.types";
import Forge from "#/api/forge";
import { useConversationId } from "#/hooks/use-conversation-id";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

type SubmitFeedbackArgs = {
  feedback: Feedback;
};

export const useSubmitFeedback = () => {
  const { conversationId } = useConversationId();
  return useMutation({
    mutationFn: ({ feedback }: SubmitFeedbackArgs) =>
      Forge.submitFeedback(conversationId, feedback),
    onError: (error) => {
      displayErrorToast(error.message);
    },
    retry: 2,
    retryDelay: 500,
  });
};
