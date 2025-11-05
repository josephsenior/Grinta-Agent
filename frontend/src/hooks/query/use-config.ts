import { useQuery } from "@tanstack/react-query";
import OpenHands from "#/api/open-hands";
import { useIsOnTosPage } from "#/hooks/use-is-on-tos-page";

const DEFAULT_FEATURE_FLAGS = {
  ENABLE_BILLING: false,
  HIDE_LLM_SETTINGS: false,
  ENABLE_JIRA: false,
  ENABLE_JIRA_DC: false,
  ENABLE_LINEAR: false,
};

export const useConfig = () => {
  const isOnTosPage = useIsOnTosPage();

  return useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const data = await OpenHands.getConfig();
      // Ensure FEATURE_FLAGS exists with sensible defaults so consumers
      // can safely read properties without defensive chaining everywhere.
      return {
        ...data,
        FEATURE_FLAGS: {
          ...DEFAULT_FEATURE_FLAGS,
          ...(data?.FEATURE_FLAGS || {}),
        },
      };
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes,
    enabled: !isOnTosPage,
  });
};
