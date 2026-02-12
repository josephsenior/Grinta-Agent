import { createSlice, PayloadAction } from "@reduxjs/toolkit";

/**
 * Streaming State Management
 * Handles real-time streaming of terminal output, agent thoughts, and progress tracking
 */

export type StreamType = "terminal" | "thought" | "file" | "search" | "command";
export type StreamStatus = "pending" | "streaming" | "complete" | "error";

export interface StreamData {
  id: string;
  type: StreamType;
  status: StreamStatus;
  startTime: number;
  completeTime?: number;
  error?: string;
}

export interface ProgressData {
  id: string;
  operation: string;
  progress: number; // 0-100
  total?: number;
  current?: number;
  message?: string;
  startTime: number;
  elapsed: number;
}

export interface StreamingState {
  // Active streams being displayed
  activeStreams: Record<string, StreamData>;

  // Accumulated chunks for each stream (for incremental display)
  chunks: Record<string, string[]>;

  // Progress tracking for operations
  progress: Record<string, ProgressData>;

  // Current operation being executed (for status bar)
  currentOperation: string | null;

  // Streaming settings
  enableStreaming: boolean;
  streamSpeed: number; // ms per chunk
}

/** Maximum chunks retained per stream. Beyond this, oldest chunks are dropped. */
const MAX_CHUNKS_PER_STREAM = 500;

const initialState: StreamingState = {
  activeStreams: {},
  chunks: {},
  progress: {},
  currentOperation: null,
  enableStreaming: true,
  streamSpeed: 16, // ~60fps for smooth streaming
};

const streamingSlice = createSlice({
  name: "streaming",
  initialState,
  reducers: {
    /**
     * Start a new stream
     */
    startStream: (
      state,
      action: PayloadAction<{
        id?: string;
        streamId?: string;
        type?: StreamType;
      }>,
    ) => {
      const id =
        action.payload.id ??
        action.payload.streamId ??
        String(Math.random().toString(36).slice(2, 9));
      const type = action.payload.type ?? ("terminal" as StreamType);
      state.activeStreams[id] = {
        id,
        type,
        status: "streaming",
        startTime: Date.now(),
      };
      state.chunks[id] = [];
    },

    /**
     * Append chunk to stream
     */
    appendStreamChunk: (
      state,
      action: PayloadAction<{ id?: string; streamId?: string; chunk: string }>,
    ) => {
      const id = action.payload.id ?? action.payload.streamId ?? "";
      const { chunk } = action.payload;

      if (!id) return;

      if (!state.chunks[id]) {
        state.chunks[id] = [];
      }

      state.chunks[id].push(chunk);

      // Evict oldest chunks when exceeding cap
      if (state.chunks[id].length > MAX_CHUNKS_PER_STREAM) {
        state.chunks[id] = state.chunks[id].slice(-MAX_CHUNKS_PER_STREAM);
      }

      // Update stream status to streaming
      if (state.activeStreams[id]) {
        state.activeStreams[id].status = "streaming";
      }
    },

    /**
     * Complete a stream
     */
    completeStream: (
      state,
      action: PayloadAction<string | { streamId: string }>,
    ) => {
      const id =
        typeof action.payload === "string"
          ? action.payload
          : action.payload.streamId;

      if (!id) return;

      if (state.activeStreams[id]) {
        state.activeStreams[id].status = "complete";
        state.activeStreams[id].completeTime = Date.now();
      }
    },

    /**
     * Mark stream as error
     */
    errorStream: (
      state,
      action: PayloadAction<{ id?: string; streamId?: string; error: string }>,
    ) => {
      const id = action.payload.id ?? action.payload.streamId;
      const { error } = action.payload;

      if (!id) return;

      if (state.activeStreams[id]) {
        state.activeStreams[id].status = "error";
        state.activeStreams[id].error = error;
        state.activeStreams[id].completeTime = Date.now();
      }
    },

    /**
     * Clear a stream (cleanup)
     */
    clearStream: (
      state,
      action: PayloadAction<string | { streamId: string }>,
    ) => {
      const id =
        typeof action.payload === "string"
          ? action.payload
          : action.payload.streamId;
      if (!id) return;
      delete state.activeStreams[id];
      delete state.chunks[id];
      delete state.progress[id];
    },

    /**
     * Update progress for an operation
     */
    updateProgress: (state, action: PayloadAction<ProgressData>) => {
      const data = action.payload;

      // Calculate elapsed time
      const existing = state.progress[data.id];
      const startTime = existing?.startTime || Date.now();
      const elapsed = (Date.now() - startTime) / 1000; // seconds

      state.progress[data.id] = {
        ...data,
        startTime,
        elapsed,
      };
    },

    /**
     * Clear progress data
     */
    clearProgress: (state, action: PayloadAction<string>) => {
      const id = action.payload;
      delete state.progress[id];
    },

    /**
     * Set current operation (for status bar)
     */
    setCurrentOperation: (state, action: PayloadAction<string | null>) => {
      state.currentOperation = action.payload;
    },

    /**
     * Toggle streaming on/off
     */
    setStreamingEnabled: (state, action: PayloadAction<boolean>) => {
      state.enableStreaming = action.payload;
    },

    /**
     * Set stream speed (ms per chunk)
     */
    setStreamSpeed: (state, action: PayloadAction<number>) => {
      state.streamSpeed = Math.max(1, Math.min(100, action.payload));
    },

    /**
     * Clear all streams and progress (cleanup)
     */
    clearAllStreams: (state) => {
      state.activeStreams = {};
      state.chunks = {};
      state.progress = {};
      state.currentOperation = null;
    },
  },
});

export const {
  startStream,
  appendStreamChunk,
  completeStream,
  errorStream,
  clearStream,
  updateProgress,
  clearProgress,
  setCurrentOperation,
  setStreamingEnabled,
  setStreamSpeed,
  clearAllStreams,
} = streamingSlice.actions;

export default streamingSlice.reducer;

/**
 * Selectors
 */
export const selectStreamData = (
  state: { streaming: StreamingState },
  id: string,
) => state.streaming.activeStreams[id];

export const selectStreamChunks = (
  state: { streaming: StreamingState },
  id: string,
) => state.streaming.chunks[id] || [];

export const selectStreamContent = (
  state: { streaming: StreamingState },
  id: string,
) => (state.streaming.chunks[id] || []).join("");

export const selectProgressData = (
  state: { streaming: StreamingState },
  id: string,
) => state.streaming.progress[id];

export const selectCurrentOperation = (state: { streaming: StreamingState }) =>
  state.streaming.currentOperation;

export const selectIsStreaming = (
  state: { streaming: StreamingState },
  id: string,
) => state.streaming.activeStreams[id]?.status === "streaming";

export const selectStreamingEnabled = (state: { streaming: StreamingState }) =>
  state.streaming.enableStreaming;

export const selectStreamError = (
  state: { streaming: StreamingState },
  id: string,
) => state.streaming.activeStreams[id]?.error ?? null;

// Backwards-compatible action alias used by older tests
export const setStreamError = errorStream;
