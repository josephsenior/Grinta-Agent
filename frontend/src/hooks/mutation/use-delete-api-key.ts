import { useMutation, useQueryClient } from "@tanstack/react-query";
import ApiKeysClient from "#/api/api-keys";

export function useDeleteApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => ApiKeysClient.deleteApiKey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}
