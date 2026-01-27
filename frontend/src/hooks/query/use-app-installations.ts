import { useQuery } from "@tanstack/react-query";
import Forge from "../../api/forge";
import { Provider } from "../../types/settings";

export function useAppInstallations(provider: Provider | null) {
  return useQuery({
    queryKey: ["installations", provider],
    queryFn: () => Forge.getUserInstallationIds(provider!),
    enabled: !!provider,
  });
}
