/**
 * Service for fetching conversation trajectories
 */

import Forge from "#/api/forge";

/**
 * Get the trajectory (event history) for a conversation
 */
export async function getTrajectory(conversationId: string): Promise<any> {
  const response = await Forge.getConversation(conversationId);
  return response;
}
