import { describe, it, expect, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import streamingReducer, {
  startStream,
  appendStreamChunk,
  completeStream,
  clearStream,
  setStreamError,
  selectStreamContent,
  selectIsStreaming,
  selectStreamError,
} from "#/store/streaming-slice";
import type { RootState } from "#/store";

describe("streamingSlice", () => {
  let store: any;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        streaming: streamingReducer,
      },
    });
  });

  describe("startStream", () => {
    it("should start a new stream", () => {
      store.dispatch(startStream({ streamId: "test-stream-1" }));

      const state = store.getState().streaming;
      expect(state.streams["test-stream-1"]).toEqual({
        content: "",
        isComplete: false,
        isStreaming: true,
        error: null,
        startedAt: expect.any(Number),
      });
    });

    it("should create multiple independent streams", () => {
      store.dispatch(startStream({ streamId: "stream-1" }));
      store.dispatch(startStream({ streamId: "stream-2" }));

      const state = store.getState().streaming;
      expect(Object.keys(state.streams)).toHaveLength(2);
      expect(state.streams["stream-1"]).toBeDefined();
      expect(state.streams["stream-2"]).toBeDefined();
    });

    it("should reset existing stream if started again", () => {
      // Start stream
      store.dispatch(startStream({ streamId: "test-stream" }));
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "old content" }),
      );

      // Start again
      store.dispatch(startStream({ streamId: "test-stream" }));

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe("");
      expect(state.streams["test-stream"].isStreaming).toBe(true);
    });
  });

  describe("appendStreamChunk", () => {
    beforeEach(() => {
      store.dispatch(startStream({ streamId: "test-stream" }));
    });

    it("should append chunk to stream content", () => {
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "Hello " }),
      );
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "World" }),
      );

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe("Hello World");
    });

    it("should handle empty chunks", () => {
      store.dispatch(appendStreamChunk({ streamId: "test-stream", chunk: "" }));

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe("");
    });

    it("should handle newlines and special characters", () => {
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "Line 1\n" }),
      );
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "Line 2\n" }),
      );
      store.dispatch(
        appendStreamChunk({
          streamId: "test-stream",
          chunk: "Special: !@#$%\n",
        }),
      );

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe(
        "Line 1\nLine 2\nSpecial: !@#$%\n",
      );
    });

    it("should lazily create stream if not started", () => {
      store.dispatch(
        appendStreamChunk({ streamId: "nonexistent", chunk: "test" }),
      );

      const state = store.getState().streaming;
      expect(state.streams.nonexistent).toEqual(
        expect.objectContaining({
          content: "test",
          isStreaming: true,
          isComplete: false,
          error: null,
        }),
      );
    });
  });

  describe("completeStream", () => {
    beforeEach(() => {
      store.dispatch(startStream({ streamId: "test-stream" }));
      store.dispatch(
        appendStreamChunk({
          streamId: "test-stream",
          chunk: "Complete content",
        }),
      );
    });

    it("should mark stream as complete", () => {
      store.dispatch(completeStream({ streamId: "test-stream" }));

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].isComplete).toBe(true);
      expect(state.streams["test-stream"].isStreaming).toBe(false);
    });

    it("should preserve content when completing", () => {
      store.dispatch(completeStream({ streamId: "test-stream" }));

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe("Complete content");
    });

    it("should do nothing if stream does not exist", () => {
      store.dispatch(completeStream({ streamId: "nonexistent" }));

      const state = store.getState().streaming;
      expect(state.streams.nonexistent).toBeUndefined();
    });
  });

  describe("clearStream", () => {
    beforeEach(() => {
      store.dispatch(startStream({ streamId: "stream-1" }));
      store.dispatch(startStream({ streamId: "stream-2" }));
      store.dispatch(
        appendStreamChunk({ streamId: "stream-1", chunk: "Content 1" }),
      );
    });

    it("should remove stream from state", () => {
      store.dispatch(clearStream({ streamId: "stream-1" }));

      const state = store.getState().streaming;
      expect(state.streams["stream-1"]).toBeUndefined();
      expect(state.streams["stream-2"]).toBeDefined();
    });

    it("should do nothing if stream does not exist", () => {
      const initialState = store.getState().streaming;
      store.dispatch(clearStream({ streamId: "nonexistent" }));

      const newState = store.getState().streaming;
      expect(newState).toEqual(initialState);
    });
  });

  describe("setStreamError", () => {
    beforeEach(() => {
      store.dispatch(startStream({ streamId: "test-stream" }));
    });

    it("should set error and stop streaming", () => {
      store.dispatch(
        setStreamError({ streamId: "test-stream", error: "Connection lost" }),
      );

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].error).toBe("Connection lost");
      expect(state.streams["test-stream"].isStreaming).toBe(false);
      expect(state.streams["test-stream"].isComplete).toBe(false);
    });

    it("should preserve content when error occurs", () => {
      store.dispatch(
        appendStreamChunk({
          streamId: "test-stream",
          chunk: "Partial content",
        }),
      );
      store.dispatch(
        setStreamError({ streamId: "test-stream", error: "Error occurred" }),
      );

      const state = store.getState().streaming;
      expect(state.streams["test-stream"].content).toBe("Partial content");
    });
  });

  describe("selectors", () => {
    beforeEach(() => {
      store.dispatch(startStream({ streamId: "test-stream" }));
      store.dispatch(
        appendStreamChunk({ streamId: "test-stream", chunk: "Test content" }),
      );
    });

    it("selectStreamContent should return stream content", () => {
      const state = store.getState() as RootState;
      const content = selectStreamContent(state, "test-stream");
      expect(content).toBe("Test content");
    });

    it("selectStreamContent should return empty string for nonexistent stream", () => {
      const state = store.getState() as RootState;
      const content = selectStreamContent(state, "nonexistent");
      expect(content).toBe("");
    });

    it("selectIsStreaming should return streaming status", () => {
      const state = store.getState() as RootState;
      expect(selectIsStreaming(state, "test-stream")).toBe(true);

      store.dispatch(completeStream({ streamId: "test-stream" }));
      const newState = store.getState() as RootState;
      expect(selectIsStreaming(newState, "test-stream")).toBe(false);
    });

    it("selectIsStreaming should return false for nonexistent stream", () => {
      const state = store.getState() as RootState;
      expect(selectIsStreaming(state, "nonexistent")).toBe(false);
    });

    it("selectStreamError should return error message", () => {
      store.dispatch(
        setStreamError({ streamId: "test-stream", error: "Test error" }),
      );

      const state = store.getState() as RootState;
      expect(selectStreamError(state, "test-stream")).toBe("Test error");
    });

    it("selectStreamError should return null for nonexistent stream", () => {
      const state = store.getState() as RootState;
      expect(selectStreamError(state, "nonexistent")).toBeNull();
    });
  });

  describe("complete streaming workflow", () => {
    it("should handle typical terminal output streaming", () => {
      const streamId = "terminal-output-123";

      // Start stream
      store.dispatch(startStream({ streamId }));
      let state = store.getState() as RootState;
      expect(selectIsStreaming(state, streamId)).toBe(true);
      expect(selectStreamContent(state, streamId)).toBe("");

      // Append chunks
      store.dispatch(appendStreamChunk({ streamId, chunk: "$ npm install\n" }));
      store.dispatch(
        appendStreamChunk({ streamId, chunk: "Installing packages...\n" }),
      );
      store.dispatch(appendStreamChunk({ streamId, chunk: "✓ Success!\n" }));

      state = store.getState() as RootState;
      expect(selectStreamContent(state, streamId)).toBe(
        "$ npm install\nInstalling packages...\n✓ Success!\n",
      );

      // Complete stream
      store.dispatch(completeStream({ streamId }));
      state = store.getState() as RootState;
      expect(selectIsStreaming(state, streamId)).toBe(false);
      expect(selectStreamContent(state, streamId)).toBe(
        "$ npm install\nInstalling packages...\n✓ Success!\n",
      );

      // Clear stream
      store.dispatch(clearStream({ streamId }));
      state = store.getState() as RootState;
      expect(selectStreamContent(state, streamId)).toBe("");
    });

    it("should handle agent thought streaming", () => {
      const streamId = "agent-thought-456";

      store.dispatch(startStream({ streamId }));
      store.dispatch(appendStreamChunk({ streamId, chunk: "I need to " }));
      store.dispatch(appendStreamChunk({ streamId, chunk: "analyze the " }));
      store.dispatch(
        appendStreamChunk({ streamId, chunk: "codebase structure" }),
      );
      store.dispatch(completeStream({ streamId }));

      const state = store.getState() as RootState;
      expect(selectStreamContent(state, streamId)).toBe(
        "I need to analyze the codebase structure",
      );
      expect(selectIsStreaming(state, streamId)).toBe(false);
    });

    it("should handle stream error during streaming", () => {
      const streamId = "error-stream-789";

      store.dispatch(startStream({ streamId }));
      store.dispatch(
        appendStreamChunk({ streamId, chunk: "Starting process..." }),
      );
      store.dispatch(setStreamError({ streamId, error: "Connection timeout" }));

      const state = store.getState() as RootState;
      expect(selectStreamContent(state, streamId)).toBe("Starting process...");
      expect(selectIsStreaming(state, streamId)).toBe(false);
      expect(selectStreamError(state, streamId)).toBe("Connection timeout");
    });
  });
});
