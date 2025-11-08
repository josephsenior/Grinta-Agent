import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import Forge from "#/api/forge";
import { useConversationId } from "#/hooks/use-conversation-id";
import { I18nKey } from "#/i18n/declaration";
import { transformVSCodeUrl } from "#/utils/vscode-url-helper";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

// Define the return type for the VS Code URL query
interface VSCodeUrlResult {
  url: string | null;
  error: string | null;
}

export const useVSCodeUrl = () => {
  const { t } = useTranslation();
  const { conversationId } = useConversationId();
  const runtimeIsReady = useRuntimeIsReady();

  return useQuery<VSCodeUrlResult>({
    queryKey: ["vscode_url", conversationId],
    queryFn: async () => {
      if (!conversationId) {
        throw new Error("No conversation ID");
      }
      const data = await Forge.getVSCodeUrl(conversationId);
      if (data.vscode_url) {
        const vsCodeUrl = data.vscode_url;
        const transformedUrl = transformVSCodeUrl(vsCodeUrl);
        return {
          url: transformedUrl,
          error: null,
        };
      }
      return {
        url: null,
        error: t(I18nKey.VSCODE$URL_NOT_AVAILABLE),
      };
    },
    enabled: !!conversationId && runtimeIsReady, // Only query when runtime is ready
    refetchOnMount: false, // Don't refetch on mount to reduce API calls
    retry: 1, // Reduce retries to prevent infinite loops
    retryDelay: 3000, // Wait 3 seconds between retries
  });
};
