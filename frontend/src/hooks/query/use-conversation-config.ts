import { useQuery } from "@tanstack/react-query";
import React from "react";
import { useConversationId } from "#/hooks/use-conversation-id";
import Forge from "#/api/forge";
import { useRuntimeIsReady } from "../use-runtime-is-ready";
import { logger } from "#/utils/logger";

export const useConversationConfig = () => {
  const { conversationId } = useConversationId();
  const runtimeIsReady = useRuntimeIsReady();

  const query = useQuery({
    queryKey: ["conversation_config", conversationId],
    queryFn: () => {
      if (!conversationId) {
        throw new Error("No conversation ID");
      }
      return Forge.getRuntimeId(conversationId);
    },
    enabled: runtimeIsReady && !!conversationId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
    retry: (failureCount, error: unknown) => {
      // Don't retry on 404 - endpoint might not be available
      if (
        error &&
        typeof error === "object" &&
        "response" in error &&
        error.response &&
        typeof error.response === "object" &&
        "status" in error.response &&
        error.response.status === 404
      ) {
        return false;
      }
      return failureCount < 2;
    },
    meta: {
      disableToast: true, // Don't show toast for optional endpoints
    },
  });

  React.useEffect(() => {
    if (query.data) {
      const { runtime_id: runtimeId } = query.data;

      logger.debug("Runtime ID:", runtimeId);
    }
  }, [query.data]);

  return query;
};
