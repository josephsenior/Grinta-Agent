import { useMutation, useQueryClient } from "@tanstack/react-query";
import ApiKeysClient from "#/api/api-keys";

export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => ApiKeysClient.createApiKey(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}
