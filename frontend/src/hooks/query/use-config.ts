import { useQuery } from "@tanstack/react-query";
import Forge from "#/api/forge";

const DEFAULT_FEATURE_FLAGS = {
  HIDE_LLM_SETTINGS: false,
};

export const useConfig = () => {
  return useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      try {
        const data = await Forge.getConfig();
        return {
          ...data,
          FEATURE_FLAGS: {
            ...DEFAULT_FEATURE_FLAGS,
            ...(data?.FEATURE_FLAGS || {}),
          },
        };
      } catch (err) {
        return {
          APP_MODE: "oss",
          FEATURE_FLAGS: DEFAULT_FEATURE_FLAGS,
          PROVIDERS_CONFIGURED: false,
        } as unknown as ReturnType<typeof Forge.getConfig>;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
    enabled: true,
  });
};
