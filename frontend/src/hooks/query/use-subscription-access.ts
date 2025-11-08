import { useQuery } from "@tanstack/react-query";
import { useConfig } from "./use-config";
import Forge from "#/api/forge";
import { useIsOnTosPage } from "#/hooks/use-is-on-tos-page";

export const useSubscriptionAccess = () => {
  const { data: config } = useConfig();
  const isOnTosPage = useIsOnTosPage();

  return useQuery({
    queryKey: ["user", "subscription_access"],
    queryFn: Forge.getSubscriptionAccess,
    enabled:
      !isOnTosPage &&
      config?.APP_MODE === "saas" &&
      config?.FEATURE_FLAGS?.ENABLE_BILLING,
  });
};
