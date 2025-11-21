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

export function shouldPreloadAbout(behavior: UserBehavior): boolean {
  return (
    behavior.timeOnPage > 15000 &&
    behavior.scrollDepth > 50 &&
    behavior.interactions > 3
  );
}

export function shouldPreloadContact(behavior: UserBehavior): boolean {
  return (
    behavior.timeOnPage > 20000 &&
    behavior.scrollDepth > 70 &&
    behavior.interactions < 3
  );
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

  if (shouldPreloadAbout(behavior)) {
    preloadRoute("/about", "low");
  }

  if (shouldPreloadContact(behavior)) {
    preloadRoute("/contact", "low");
  }
}
