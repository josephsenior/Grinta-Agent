import type {
  OpenHandsAction,
  OpenHandsObservation,
} from "#/types/core";
import { hasArgs, isOpenHandsObservation } from "#/types/core/guards";

/**
 * Extract a friendly title/details pair from an event for rendering.
 * This is deliberately defensive and accepts both action and observation shapes.
 */
export function getEventContent(
  event: OpenHandsAction | OpenHandsObservation,
): { title: string; details: string } {
  // Observation-style content (prefer explicit title/details/content)
  if (isOpenHandsObservation(event)) {
    let title = "";
    let details = "";
    if ("title" in event && typeof (event as any).title === "string") {
      title = (event as any).title;
    }
    if ("content" in event && typeof (event as any).content === "string") {
      details = (event as any).content;
    } else if ("details" in event && typeof (event as any).details === "string") {
      details = (event as any).details;
    }
    return { title: String(title || ""), details: String(details || "") };
  }

  // Action-style content (args.message, args.content, args.thought, message)
  const action = event as OpenHandsAction;
  const args = hasArgs(action) ? action.args : undefined;
  const a = args && typeof args === "object" ? (args as Record<string, unknown>) : ({} as Record<string, unknown>);

  const candidate =
    (typeof a.content === "string" ? a.content : undefined) ??
    (typeof a.message === "string" ? a.message : undefined) ??
    (typeof a.thought === "string" ? a.thought : undefined) ??
    (typeof action.message === "string" ? action.message : undefined) ??
    "";

  return { title: "", details: String(candidate || "") };
}

export default getEventContent;
