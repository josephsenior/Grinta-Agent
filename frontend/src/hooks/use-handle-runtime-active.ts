import { useRuntimeIsReady } from "./use-runtime-is-ready";

/**
 * Hook to handle runtime active state.
 * Only works on conversation routes that have a conversationId.
 */
export const useHandleRuntimeActive = () => {
  const runtimeActive = useRuntimeIsReady();
  return { runtimeActive };
};
