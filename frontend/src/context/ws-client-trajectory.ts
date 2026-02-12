/**
 * Trajectory hydration utilities extracted from ws-client-provider.
 *
 * These are pure functions (no React hooks) that merge trajectory
 * data fetched from the REST API into the live event stream.
 */

import { ForgeAction } from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";
import { ForgeParsedEvent } from "#/types/core";
import { isForgeAction, isForgeObservation } from "#/types/core/guards";
import { getProp } from "./ws-client-message-utils";
import { logger } from "#/utils/logger";
import Forge from "#/api/forge";

// ── Individual helpers ─────────────────────────────────────────────

export function extractTrajectoryMessageCandidate(
  item: Record<string, unknown>,
): string | undefined {
  const messageProp = getProp(item, "message");
  const contentProp = getProp(item, "content");
  const argsProp = getProp(item, "args") as Record<string, unknown> | undefined;

  const candidates = [
    typeof messageProp === "string" ? messageProp : undefined,
    typeof contentProp === "string" ? contentProp : undefined,
    typeof argsProp?.content === "string" ? argsProp.content : undefined,
    typeof argsProp?.command === "string" ? argsProp.command : undefined,
  ];

  return candidates.find((value): value is string => Boolean(value));
}

export function logTrajectoryNullCandidate(
  item: Record<string, unknown>,
): void {
  try {
    const candidate = extractTrajectoryMessageCandidate(item);
    if (!candidate) return;
    if (candidate.toUpperCase() === "NULL") {
      logger.warn("Trajectory contains literal 'NULL'", {
        id: getProp(item, "id"),
        item,
      });
    }
  } catch {
    // ignore logging failures
  }
}

export function extractTrajectoryId(item: Record<string, unknown>): string {
  const rawId = getProp(item, "id");
  if (typeof rawId === "string" && rawId.trim().length > 0) return rawId;
  if (typeof rawId === "number" && Number.isFinite(rawId)) return String(rawId);
  return Math.random().toString(36).slice(2, 9);
}

export function markItemAsHydrated(
  item: Record<string, unknown>,
  hydratedIds: Set<string>,
  id: string,
): void {
  try {
    (item as Record<string, unknown>).__hydrated = true;
  } catch {
    // ignore if flag cannot be set
  }
  hydratedIds.add(id);
}

export function isTrajectoryCandidate(item: Record<string, unknown>): boolean {
  return (
    "id" in item && "source" in item && "message" in item && "timestamp" in item
  );
}

// ── Merge & hydrate ────────────────────────────────────────────────

export function mergeTrajectoryEvents(
  prev: (ForgeAction | ForgeObservation)[],
  trajectory: unknown[],
  hydratedIds: Set<string>,
): (ForgeAction | ForgeObservation)[] {
  const existingIds = new Set(
    prev.map((event) => String(getProp(event, "id") ?? "")),
  );
  const merged = [...prev];

  for (const rawItem of trajectory) {
    const item = rawItem as Record<string, unknown>;
    if (item && typeof item === "object") {
      logTrajectoryNullCandidate(item);
      const id = extractTrajectoryId(item);
      if (!existingIds.has(id)) {
        markItemAsHydrated(item, hydratedIds, id);
        if (isTrajectoryCandidate(item)) {
          if (
            isForgeAction(item as unknown) ||
            isForgeObservation(item as unknown)
          ) {
            merged.push(item as unknown as ForgeParsedEvent);
            existingIds.add(id);
          } else {
            logger.debug("Skipping non-event trajectory item", { id, item });
          }
        } else {
          logger.debug("Skipping incomplete trajectory item", { id, item });
        }
      }
    } else {
      logger.debug("Skipping non-object trajectory item", { item });
    }
  }

  return merged;
}

export async function hydrateTrajectoryState({
  conversationId,
  setParsedEvents,
  hydratedEventIdsRef,
}: {
  conversationId: string;
  setParsedEvents: React.Dispatch<
    React.SetStateAction<(ForgeAction | ForgeObservation)[]>
  >;
  hydratedEventIdsRef: React.MutableRefObject<Set<string>>;
}): Promise<void> {
  try {
    const resp = await Forge.getTrajectory(conversationId);
    const trajectory = resp?.trajectory ?? [];
    if (!Array.isArray(trajectory) || trajectory.length === 0) return;

    setParsedEvents((prev) =>
      mergeTrajectoryEvents(prev, trajectory, hydratedEventIdsRef.current),
    );
  } catch {
    // Ignore trajectory hydration failures - UI can still operate with live socket
  }
}
