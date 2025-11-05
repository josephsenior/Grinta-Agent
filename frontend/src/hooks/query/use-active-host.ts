import { useQueries, useQuery } from "@tanstack/react-query";
import axios from "axios";
import React from "react";
import OpenHands from "#/api/open-hands";
import { useConversationId } from "#/hooks/use-conversation-id";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

export const useActiveHost = () => {
  const [activeHost, setActiveHost] = React.useState<string | null>(null);
  const { conversationId } = useConversationId();
  const runtimeIsReady = useRuntimeIsReady();

  const { data } = useQuery({
    queryKey: [conversationId, "hosts"],
    queryFn: async () => {
      const hosts = await OpenHands.getWebHosts(conversationId);
      return { hosts };
    },
    enabled: runtimeIsReady && !!conversationId,
    initialData: { hosts: [] },
    meta: {
      disableToast: true,
    },
  });

  // Host probing can trigger noisy network errors in the browser (failed
  // connections to arbitrary localhost ports). Make probes explicitly
  // opt-in so they don't run unless a developer intentionally enables them.
  // Set VITE_ENABLE_HOST_PROBES=true in a development environment to enable.
  type MaybeImportMeta = { env?: Record<string, unknown> } | undefined;
  const meta = import.meta as MaybeImportMeta;
  const env = meta?.env || {};
  const enableProbes =
    Boolean(env.VITE_ENABLE_HOST_PROBES) && env.MODE === "development";

  // Build queries array but always call the hook to preserve hook ordering rules
  const probeQueries =
    !enableProbes || !data?.hosts || data.hosts.length === 0
      ? []
      : data.hosts.map((host) => ({
          queryKey: [conversationId, "hosts", host],
          queryFn: async () => {
            try {
              // Keep probes quick with a short timeout
              await axios.get(host, { timeout: 1500 });
              return host;
            } catch (e) {
              return "";
            }
          },
          // refetchInterval: 3000,
          meta: {
            disableToast: true,
          },
        }));

  const apps = useQueries({ queries: probeQueries });

  const appsData = apps.map((app) => app.data);

  React.useEffect(() => {
    const successfulApp = appsData.find((app) => app);
    setActiveHost(successfulApp || "");
  }, [appsData]);

  return { activeHost };
};
