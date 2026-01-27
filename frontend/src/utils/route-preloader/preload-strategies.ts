interface UserBehavior {
  timeOnPage: number;
  scrollDepth: number;
  interactions: number;
}

export function shouldPreloadConversation(behavior: UserBehavior): boolean {
  return (
    behavior.timeOnPage > 3000 &&
    (behavior.scrollDepth > 20 || behavior.interactions > 2)
  );
}

export function shouldPreloadSettings(behavior: UserBehavior): boolean {
  return behavior.timeOnPage > 10000 && behavior.interactions > 5;
}

export async function applyPreloadStrategies(
  behavior: UserBehavior,
): Promise<void> {
  // Import from core module to avoid circular dependency
  const { preloadRoute } = await import("./preload-core");

  if (shouldPreloadConversation(behavior)) {
    preloadRoute("/conversation", "high");
  }

  if (shouldPreloadSettings(behavior)) {
    preloadRoute("/settings", "medium");
  }
}
