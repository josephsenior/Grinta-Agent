import { renderHook, act } from "@testing-library/react";
import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";

import { useSequentialStreaming } from "#/hooks/use-streaming";

describe("useSequentialStreaming", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("streams items sequentially with immediate timers", async () => {
    const items = ["a", "b"];
    const { result } = renderHook(() =>
      useSequentialStreaming({
        items,
        speed: 10,
        interval: 1,
        delay: 0,
        itemDelay: 1,
      }),
    );

    // Run timers for first item
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Run timers for item delay
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    // Run timers for second item
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.allStreamedItems).toEqual(["a", "b"]);
    expect(result.current.currentIndex).toBe(1);
    expect(result.current.currentItem).toBe("b");
    expect(result.current.isComplete).toBe(true);
  });

  it("resets sequential streaming state", async () => {
    const items = ["x", "y"];
    const { result } = renderHook(() =>
      useSequentialStreaming({
        items,
        speed: 10,
        interval: 10,
        delay: 0,
        itemDelay: 10,
      }),
    );

    await act(async () => {
      vi.advanceTimersByTime(200);
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.allStreamedItems).toEqual([]);
    expect(result.current.currentIndex).toBe(0);
    expect(result.current.isComplete).toBe(false);
    expect(result.current.currentItem).toBe("");
  });
});
