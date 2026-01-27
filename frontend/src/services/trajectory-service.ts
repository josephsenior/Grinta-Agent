/**
 * Service for fetching conversation trajectories
 */

import Forge from "#/api/forge";
import type { Conversation } from "#/api/forge.types";

/**
 * Get the trajectory (event history) for a conversation
 */
export async function getTrajectory(
  conversationId: string,
): Promise<Conversation | null> {
  const response = await Forge.getConversation(conversationId);
  return response;
}
