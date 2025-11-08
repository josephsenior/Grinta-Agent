const PRIORITY_BADGE_CLASSES: Record<string, string> = {
  critical: "text-red-400 bg-red-500/20 border-red-500/30",
  high: "text-orange-400 bg-orange-500/20 border-orange-500/30",
  medium: "text-yellow-400 bg-yellow-500/20 border-yellow-500/30",
  low: "text-green-400 bg-green-500/20 border-green-500/30",
};

const DEFAULT_PRIORITY_BADGE_CLASS = "text-neutral-400 bg-neutral-500/20 border-neutral-500/30";

export function getPriorityBadgeClass(priority?: string | null): string {
  if (!priority) {
    return DEFAULT_PRIORITY_BADGE_CLASS;
  }

  const normalized = priority.toLowerCase();
  return PRIORITY_BADGE_CLASSES[normalized] ?? DEFAULT_PRIORITY_BADGE_CLASS;
}


