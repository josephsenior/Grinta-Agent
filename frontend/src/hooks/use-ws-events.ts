import React from "react";
import { useWsClient } from "#/context/ws-client-provider";
import { OpenHandsAction, OpenHandsObservation } from "#/types/core";
import { isStreamingChunkAction, isFileWriteAction, isFileEditAction } from "#/types/core/guards";

export function useWsEvents() {
  const wsClient = useWsClient();
  
  // Safeguard: If WebSocket client is not available, return empty data
  if (!wsClient || !wsClient.parsedEvents) {
    return {
      parsedEvents: [],
      webSocketStatus: "DISCONNECTED" as const,
      isLoadingMessages: false,
    };
  }

  return {
    parsedEvents: wsClient.parsedEvents,
    webSocketStatus: wsClient.webSocketStatus,
    isLoadingMessages: wsClient.isLoadingMessages,
  };
}

export function useStreamingChunks() {
  const { parsedEvents } = useWsEvents();
  return parsedEvents.filter(isStreamingChunkAction);
}

export function useFileActions() {
  const { parsedEvents } = useWsEvents();
  
  const fileWriteActions = parsedEvents.filter(isFileWriteAction);
  const fileEditActions = parsedEvents.filter(isFileEditAction);
  
  return {
    fileWriteActions,
    fileEditActions,
    allFileActions: [...fileWriteActions, ...fileEditActions],
  };
}

export function useLatestStreamingContent(filePath?: string) {
  const { parsedEvents } = useWsEvents();
  
  // Get the latest streaming chunk for a specific file or the most recent one
  const streamingChunks = parsedEvents.filter(isStreamingChunkAction);
  
  if (filePath) {
    // Find streaming chunks that might be related to this file
    // This is a heuristic - in practice, streaming chunks are for LLM responses
    // but we can use them to show real-time content generation
    const relevantChunks = streamingChunks.filter(chunk => 
      chunk.args.accumulated && chunk.args.accumulated.length > 0
    );
    
    return relevantChunks[relevantChunks.length - 1]?.args.accumulated || "";
  }
  
  // Return the most recent streaming content
  return streamingChunks[streamingChunks.length - 1]?.args.accumulated || "";
}
