export function usePlaywrightDetection(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  type WindowWithE2E = Window & { __Forge_PLAYWRIGHT?: boolean };
  return (window as unknown as WindowWithE2E).__Forge_PLAYWRIGHT === true;
}
