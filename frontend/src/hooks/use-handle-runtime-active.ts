import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

export const useHandleRuntimeActive = () => {
  const runtimeActive = useRuntimeIsReady();

  return { runtimeActive };
};
