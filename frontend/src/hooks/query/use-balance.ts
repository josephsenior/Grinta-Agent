import { useQuery } from "@tanstack/react-query";
import { useConfig } from "./use-config";
import Forge from "#/api/forge";
import { useIsOnTosPage } from "#/hooks/use-is-on-tos-page";

export const useBalance = () => {
  const { data: config } = useConfig();
  const isOnTosPage = useIsOnTosPage();

  return useQuery({
    queryKey: ["user", "balance"],
    queryFn: Forge.getBalance,
    enabled:
      !isOnTosPage &&
      config?.APP_MODE === "saas" &&
      config?.FEATURE_FLAGS?.ENABLE_BILLING,
  });
};
