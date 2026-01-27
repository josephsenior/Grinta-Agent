import { useQuery } from "@tanstack/react-query";
import { SecretsService } from "#/api/secrets-service";

export function useGetSecrets() {
  return useQuery({
    queryKey: ["secrets"],
    queryFn: () => SecretsService.getSecrets(),
  });
}
