import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, vi, expect, beforeEach, afterEach } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { StreamingThought } from "../streaming-thought";
import streamingReducer, {
  startStream,
  appendStreamChunk,
  completeStream,
} from "#/store/streaming-slice";

describe("StreamingThought", () => {
  let store: ReturnType<typeof configureStore>;
  
  beforeEach(() => {
    store = configureStore({
      reducer: {
        streaming: streamingReducer,
      },
    });
    vi.useFakeTimers();
  });
  
  afterEach(() => {
    vi.restoreAllMocks();
  });
  
  const renderWithStore = (component: React.ReactElement) => {
    return render(<Provider store={store}>{component}</Provider>);
  };
  
  it("should render empty state when no stream", () => {
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    // Should render but be empty
    const container = screen.queryByText(/./);
    expect(container).toBeNull();
  });
  
  it("should display thought content with typewriter effect", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Analyzing code" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    // Initially empty (typewriter hasn't started)
    await waitFor(() => {
      expect(screen.queryByText("Analyzing code")).toBeInTheDocument();
    });
  });
  
  it("should show thinking icon", () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Thinking..." }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    // Should show brain icon
    expect(screen.getByText("Thinking...").closest("div")).toBeInTheDocument();
  });
  
  it("should animate characters one by one", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Hello" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={10} />);
    
    // Fast-forward through the animation
    await vi.advanceTimersByTimeAsync(50);
    
    await waitFor(() => {
      expect(screen.getByText(/Hello/)).toBeInTheDocument();
    });
  });
  
  it("should show cursor during streaming", () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Analyzing" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    const container = screen.getByText(/Analyzing/).closest("div");
    expect(container).toHaveClass("streaming-thought");
  });
  
  it("should hide cursor when complete", () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Done" }));
    store.dispatch(completeStream({ streamId: "test-thought" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    const container = screen.getByText(/Done/).closest("div");
    expect(container).not.toHaveClass("streaming");
  });
  
  it("should handle multiline thoughts", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({
      streamId: "test-thought",
      chunk: "First line\nSecond line\nThird line"
    }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={1} />);
    
    await vi.advanceTimersByTimeAsync(100);
    
    await waitFor(() => {
      const text = screen.getByText(/First line.*Second line.*Third line/s);
      expect(text).toBeInTheDocument();
    });
  });
  
  it("should respect custom speed prop", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Testing" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={1} />);
    
    // With speed=1, should complete quickly
    await vi.advanceTimersByTimeAsync(10);
    
    await waitFor(() => {
      expect(screen.getByText(/Testing/)).toBeInTheDocument();
    });
  });
  
  it("should handle incremental chunk updates", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={1} />);
    
    // Add chunks incrementally
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "I " }));
    await vi.advanceTimersByTimeAsync(5);
    
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "am " }));
    await vi.advanceTimersByTimeAsync(5);
    
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "thinking" }));
    await vi.advanceTimersByTimeAsync(10);
    
    await waitFor(() => {
      expect(screen.getByText(/I am thinking/)).toBeInTheDocument();
    });
  });
  
  it("should render markdown formatting", () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({
      streamId: "test-thought",
      chunk: "I need to **analyze** the code"
    }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    // Should render markdown (check for strong tag or class)
    expect(screen.getByText(/analyze/)).toBeInTheDocument();
  });
  
  it("should handle empty chunks", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "Content" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={1} />);
    
    await vi.advanceTimersByTimeAsync(10);
    
    await waitFor(() => {
      expect(screen.getByText(/Content/)).toBeInTheDocument();
    });
  });
  
  it("should render code blocks in thoughts", () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({
      streamId: "test-thought",
      chunk: "I'll use `console.log()` to debug"
    }));
    
    renderWithStore(<StreamingThought streamId="test-thought" />);
    
    expect(screen.getByText(/console\.log\(\)/)).toBeInTheDocument();
  });
  
  it("should handle rapid streaming updates", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    
    renderWithStore(<StreamingThought streamId="test-thought" speed={1} />);
    
    // Rapidly add many chunks
    for (let i = 0; i < 10; i++) {
      store.dispatch(appendStreamChunk({
        streamId: "test-thought",
        chunk: `Word${i} `
      }));
    }
    
    await vi.advanceTimersByTimeAsync(100);
    
    await waitFor(() => {
      expect(screen.getByText(/Word0.*Word9/s)).toBeInTheDocument();
    });
  });
  
  it("should display agent planning thought", async () => {
    store.dispatch(startStream({ streamId: "agent-thought" }));
    store.dispatch(appendStreamChunk({
      streamId: "agent-thought",
      chunk: "I need to analyze the codebase structure. First, I'll list the files, then read the key modules."
    }));
    
    renderWithStore(<StreamingThought streamId="agent-thought" speed={5} />);
    
    await vi.advanceTimersByTimeAsync(200);
    
    await waitFor(() => {
      expect(screen.getByText(/analyze the codebase structure/)).toBeInTheDocument();
    });
  });
});

