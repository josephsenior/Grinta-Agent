import type { OpenHandsEvent } from "#/types/core/base";
import {
  isUserMessage,
  isStreamingChunkAction,
  isOpenHandsAction,
} from "#/types/core/guards";

export interface MessageTurn {
  type: "user" | "agent";
  events: OpenHandsEvent[];
  startIndex: number;
  endIndex: number;
}

/**
 * Groups consecutive messages into "turns" for bolt.new-style rendering
 * 
 * A "turn" is:
 * - User message (single event)
 * - Agent response (multiple consecutive agent events grouped together)
 * 
 * This creates the conversational flow where:
 * - User says something → one bubble
 * - Agent responds with multiple actions → ONE grouped visual unit
 * 
 * Special handling for StreamingChunkAction:
 * - Multiple streaming chunks update THE SAME turn (not create new turns)
 * - This gives real-time token-by-token updates within one message
 */
export function groupMessagesIntoTurns(messages: OpenHandsEvent[]): MessageTurn[] {
  const turns: MessageTurn[] = [];
  let currentTurn: MessageTurn | null = null;

  messages.forEach((event, index) => {
    // User messages are always their own turn
    if (isUserMessage(event)) {
      // Save previous turn if exists
      if (currentTurn) {
        turns.push(currentTurn);
        currentTurn = null;
      }
      
      // Create new user turn (single event)
      turns.push({
        type: "user",
        events: [event],
        startIndex: index,
        endIndex: index,
      });
      return;
    }

    // Agent events get grouped together
    // This includes: assistant messages, actions, observations, streaming chunks
    
    // If we're already in an agent turn, add to it
    if (currentTurn && currentTurn.type === "agent") {
      currentTurn.events.push(event);
      currentTurn.endIndex = index;
      
      // Special case: If this is a streaming chunk, we might want to
      // update the previous assistant message instead of adding a new event
      if (isStreamingChunkAction(event)) {
        // Find the last assistant message in this turn and update it
        const lastAssistantIndex = currentTurn.events.findLastIndex((e) =>
          isOpenHandsAction(e) && e.source === "agent" && e.action === "message",
        );
        
        if (lastAssistantIndex !== -1) {
          // Update the last assistant message with accumulated content
          const lastAssistant = currentTurn.events[lastAssistantIndex];
          if (isOpenHandsAction(lastAssistant) && lastAssistant.action === "message") {
            // Update the content with accumulated streaming text
            (lastAssistant.args as any) = {
              ...(lastAssistant.args as any),
              content: (event as any).args.accumulated,
            };
          }
          // Don't add the streaming chunk as a separate event
          currentTurn.events.pop();
        }
      }
    } else {
      // Start a new agent turn
      currentTurn = {
        type: "agent",
        events: [event],
        startIndex: index,
        endIndex: index,
      };
    }
  });

  // Don't forget the last turn
  if (currentTurn) {
    turns.push(currentTurn);
  }

  return turns;
}

/**
 * Check if a turn contains streaming content (used for animations)
 */
export function turnHasStreaming(turn: MessageTurn): boolean {
  return turn.events.some((event) => isStreamingChunkAction(event));
}

/**
 * Get the latest streaming content from a turn
 */
export function getTurnStreamingContent(turn: MessageTurn): string | null {
  const streamingEvents = turn.events.filter((event) => isStreamingChunkAction(event));
  if (streamingEvents.length === 0) return null;
  
  const lastStreaming = streamingEvents[streamingEvents.length - 1];
  return lastStreaming.args?.accumulated || null;
}

