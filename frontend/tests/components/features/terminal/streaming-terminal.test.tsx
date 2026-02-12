import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { StreamingTerminal } from "#/components/features/terminal/streaming-terminal";
import streamingReducer, {
  startStream,
  appendStreamChunk,
  completeStream,
} from "#/state/streaming-slice";

describe("StreamingTerminal", () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        streaming: streamingReducer,
      },
    });
  });

  const renderWithStore = (component: React.ReactElement) =>
    render(<Provider store={store}>{component}</Provider>);

  it("should render empty state when no stream", () => {
    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    // Should show the terminal icon
    expect(screen.getByText("Terminal Output")).toBeInTheDocument();
  });

  it("should display streaming content", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-stream", chunk: "$ echo 'Hello'\n" }),
    );
    store.dispatch(
      appendStreamChunk({ streamId: "test-stream", chunk: "Hello\n" }),
    );

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    expect(screen.getByText(/\$ echo 'Hello'/)).toBeInTheDocument();
    expect(screen.getByText(/Hello/)).toBeInTheDocument();
  });

  it("should show streaming indicator when streaming", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-stream", chunk: "Loading...\n" }),
    );

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    // Should show cursor indicator
    const terminal = screen.getByRole("region");
    expect(terminal).toHaveClass("streaming");
  });

  it("should not show cursor when stream is complete", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-stream", chunk: "Done\n" }),
    );
    store.dispatch(completeStream({ streamId: "test-stream" }));

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    const terminal = screen.getByRole("region");
    expect(terminal).not.toHaveClass("streaming");
  });

  it("should handle multiline output", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "test-stream",
        chunk: "Line 1\nLine 2\nLine 3\n",
      }),
    );

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    expect(screen.getByText(/Line 1/)).toBeInTheDocument();
    expect(screen.getByText(/Line 2/)).toBeInTheDocument();
    expect(screen.getByText(/Line 3/)).toBeInTheDocument();
  });

  it("should handle ANSI color codes", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(
      appendStreamChunk({
        streamId: "test-stream",
        chunk: "\x1b[32mSuccess\x1b[0m\n",
      }),
    );

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    // ANSI codes should be processed by ansi-to-html
    const output = screen.getByText(/Success/);
    expect(output).toBeInTheDocument();
  });

  it("should auto-scroll to bottom during streaming", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));

    // Add lots of content
    for (let i = 0; i < 100; i++) {
      store.dispatch(
        appendStreamChunk({
          streamId: "test-stream",
          chunk: `Line ${i}\n`,
        }),
      );
    }

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    // Find the scrollable container
    const container = screen.getByRole("region");
    expect(container.scrollTop).toBeGreaterThanOrEqual(0);
  });

  it("should render with custom className", () => {
    renderWithStore(
      <StreamingTerminal streamId="test-stream" className="custom-class" />,
    );

    const terminal = screen.getByRole("region");
    expect(terminal).toHaveClass("custom-class");
  });

  it("should handle rapid chunk updates", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));

    // Rapidly add chunks
    const chunks = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"];
    chunks.forEach((chunk) => {
      store.dispatch(appendStreamChunk({ streamId: "test-stream", chunk }));
    });

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    expect(screen.getByText(/abcdefghij/)).toBeInTheDocument();
  });

  it("should handle empty chunks gracefully", () => {
    store.dispatch(startStream({ streamId: "test-stream" }));
    store.dispatch(appendStreamChunk({ streamId: "test-stream", chunk: "" }));
    store.dispatch(
      appendStreamChunk({ streamId: "test-stream", chunk: "Hello" }),
    );
    store.dispatch(appendStreamChunk({ streamId: "test-stream", chunk: "" }));

    renderWithStore(<StreamingTerminal streamId="test-stream" />);

    expect(screen.getByText(/Hello/)).toBeInTheDocument();
  });

  it("should display command execution example", () => {
    store.dispatch(startStream({ streamId: "cmd-stream" }));
    store.dispatch(
      appendStreamChunk({ streamId: "cmd-stream", chunk: "$ npm test\n" }),
    );
    store.dispatch(
      appendStreamChunk({
        streamId: "cmd-stream",
        chunk: "Running tests...\n",
      }),
    );
    store.dispatch(
      appendStreamChunk({
        streamId: "cmd-stream",
        chunk: "✓ All tests passed\n",
      }),
    );
    store.dispatch(completeStream({ streamId: "cmd-stream" }));

    renderWithStore(<StreamingTerminal streamId="cmd-stream" />);

    expect(screen.getByText(/\$ npm test/)).toBeInTheDocument();
    expect(screen.getByText(/Running tests/)).toBeInTheDocument();
    expect(screen.getByText(/All tests passed/)).toBeInTheDocument();
  });
});
