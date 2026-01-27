import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SecretsService } from "#/api/secrets-service";

export function useCreateSecret() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      value,
      description,
    }: {
      name: string;
      value: string;
      description?: string;
    }) => SecretsService.createSecret(name, value, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["secrets"] });
    },
  });
}
