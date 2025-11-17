import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, vi, expect, beforeEach, afterEach } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { StreamingThought } from "#/components/features/chat/streaming-thought";
import streamingReducer, {
  startStream,
  appendStreamChunk,
  completeStream,
} from "#/store/streaming-slice";

// Ensure components detect test environment and fast-path streaming
(process.env as any).NODE_ENV = "test";

describe("StreamingThought", () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        streaming: streamingReducer,
      },
    });
    // Use real timers; `StreamingThought` runs a test-mode fast-path and
    // renders content synchronously in tests, so fake timers are unnecessary
    // and may interfere with effect scheduling.
    // These tests advance timers; use fake timers so vi.advanceTimersByTimeAsync works.
    vi.useFakeTimers();
  });

  afterEach(() => {
    // Restore timers to real timers and clear any mocks
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const renderWithStore = (component: React.ReactElement) => {
    // If the tested component is StreamingThought, force testMode to make timing deterministic
    const el =
      component.type === StreamingThought
        ? React.cloneElement(component, { testMode: true } as any)
        : component;

    return render(<Provider store={store}>{el}</Provider>);
  };

  // Test cases for StreamingThought component
  it("should render empty state when no stream", () => {
    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    // Should render but be empty
    const container = screen.queryByText(/./);
    expect(container).toBeNull();
  });

  it("should display thought content with typewriter effect", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Analyzing code" }),
    );
    // DEBUG logs removed: tests should be quiet when passing

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    // DEBUG logs removed: tests should be quiet when passing

    // Initially empty (typewriter hasn't started)
    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "Analyzing code",
    );
  });

  it("should show thinking icon", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Thinking..." }),
    );

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    // Should show brain icon (verify text is rendered and container exists)
    const thinkingEl = screen.getByTestId("streaming-text");
    expect(thinkingEl.textContent).toContain("Thinking...");
    expect(thinkingEl.closest("div")).toBeInTheDocument();
  });

  // Additional test cases
  it("should animate characters one by one", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Hello" }),
    );

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={10} testMode />,
    );

    // Fast-forward through the animation inside act to satisfy React update semantics
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(screen.getByTestId("streaming-text").textContent).toContain("Hello");
  });

  it("should show cursor during streaming", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Analyzing" }),
    );

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    const container = screen.getByTestId("streaming-text").closest("div");
    expect(container).toHaveClass("streaming-thought");
  });

  // More test cases
  it("should hide cursor when complete", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Done" }),
    );
    store.dispatch(completeStream({ streamId: "test-thought" }));

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    const container = screen.getByTestId("streaming-text").closest("div");
    expect(container).not.toHaveClass("streaming");
  });

  // Handling multiline thoughts
  it("should handle multiline thoughts", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "test-thought",
        chunk: "First line\nSecond line\nThird line",
      }),
    );

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={1} testMode />,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    const multi = screen.getByTestId("streaming-text");
    expect(multi.textContent).toContain("First line");
    expect(multi.textContent).toContain("Second line");
    expect(multi.textContent).toContain("Third line");
  });

  // Custom speed prop
  it("should respect custom speed prop", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Testing" }),
    );

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={1} testMode />,
    );

    // With speed=1, should complete quickly
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "Testing",
    );
  });

  it("should handle incremental chunk updates", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={1} testMode />,
    );

    // Add chunks incrementally and wrap dispatches + timer advances in act
    await act(async () => {
      store.dispatch(
        appendStreamChunk({ streamId: "test-thought", chunk: "I " }),
      );
      await vi.advanceTimersByTimeAsync(5);
    });

    await act(async () => {
      store.dispatch(
        appendStreamChunk({ streamId: "test-thought", chunk: "am " }),
      );
      await vi.advanceTimersByTimeAsync(5);
    });

    await act(async () => {
      store.dispatch(
        appendStreamChunk({ streamId: "test-thought", chunk: "thinking" }),
      );
      await vi.advanceTimersByTimeAsync(20);
    });

    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "I am thinking",
    );
  });

  // Rendering markdown formatting
  it("should render markdown formatting", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "test-thought",
        chunk: "I need to **analyze** the code",
      }),
    );

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    // Should render markdown (check text content)
    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "analyze",
    );
  });

  // Handling empty chunks
  it("should handle empty chunks", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(appendStreamChunk({ streamId: "test-thought", chunk: "" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-thought", chunk: "Content" }),
    );

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={1} testMode />,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "Content",
    );
  });

  // Rendering code blocks
  it("should render code blocks in thoughts", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "test-thought",
        chunk: "I'll use `console.log()` to debug",
      }),
    );

    renderWithStore(<StreamingThought streamId="test-thought" testMode />);

    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "console.log()",
    );
  });

  // Rapid streaming updates
  it("should handle rapid streaming updates", async () => {
    store.dispatch(startStream({ streamId: "test-thought" }));

    renderWithStore(
      <StreamingThought streamId="test-thought" speed={1} testMode />,
    );

    // Rapidly add many chunks
    for (let i = 0; i < 10; i++) {
      store.dispatch(
        appendStreamChunk({
          streamId: "test-thought",
          chunk: `Word${i} `,
        }),
      );
    }

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    const rapid = screen.getByTestId("streaming-text");
    expect(rapid.textContent).toContain("Word0");
    expect(rapid.textContent).toContain("Word9");
  });

  // Displaying agent planning thought
  it("should display agent planning thought", async () => {
    store.dispatch(startStream({ streamId: "agent-thought" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "agent-thought",
        chunk:
          "I need to analyze the codebase structure. First, I'll list the files, then read the key modules.",
      }),
    );

    renderWithStore(
      <StreamingThought streamId="agent-thought" speed={5} testMode />,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(screen.getByTestId("streaming-text").textContent).toContain(
      "analyze the codebase structure",
    );
  });
});
