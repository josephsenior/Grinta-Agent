/**
 * Service for fetching conversation trajectories
 */

import OpenHands from "#/api/open-hands";

/**
 * Get the trajectory (event history) for a conversation
 */
export async function getTrajectory(conversationId: string): Promise<any> {
  const response = await OpenHands.getConversation(conversationId);
  return response;
}

