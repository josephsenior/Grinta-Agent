import { useMutation, useQueryClient } from "@tanstack/react-query";
import posthog from "#/utils/posthog";
import Forge from "#/api/forge";
import { SuggestedTask } from "#/api/forge.types";
import { Provider } from "#/types/settings";
import { CreatePlaybook } from "#/api/forge.types";

interface CreateConversationVariables {
  query?: string;
  repository?: {
    name: string;
    gitProvider: Provider;
    branch?: string;
  };
  suggestedTask?: SuggestedTask;
  conversationInstructions?: string;
  createPlaybook?: CreatePlaybook;
}

export const useCreateConversation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["create-conversation"],
    mutationFn: async (variables: CreateConversationVariables) => {
      const {
        query,
        repository,
        suggestedTask,
        conversationInstructions,
        createPlaybook,
      } = variables;

      return Forge.createConversation(
        repository?.name,
        repository?.gitProvider,
        query,
        suggestedTask,
        repository?.branch,
        conversationInstructions,
        createPlaybook,
      );
    },
    onSuccess: async (_, { query, repository }) => {
      posthog.capture("initial_query_submitted", {
        entry_point: "task_form",
        query_character_length: query?.length,
        has_repository: !!repository,
      });
      await queryClient.invalidateQueries({
        queryKey: ["user", "conversations"],
      });
    },
  });
};
