import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useSequentialStreaming } from "#/hooks/use-streaming";

describe("useSequentialStreaming", () => {
  const setTimeoutSpy = vi.spyOn(global, "setTimeout").mockImplementation((cb: TimerHandler) => {
    (cb as () => void)();
    return 0 as unknown as NodeJS.Timeout;
  });

  const setIntervalSpy = vi.spyOn(global, "setInterval").mockImplementation((cb: TimerHandler) => {
    (cb as () => void)();
    return 0 as unknown as NodeJS.Timeout;
  });

  vi.spyOn(global, "clearTimeout").mockImplementation(() => undefined);
  vi.spyOn(global, "clearInterval").mockImplementation(() => undefined);

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("streams items sequentially with immediate timers", () => {
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

    expect(setTimeoutSpy).toHaveBeenCalled();
    expect(setIntervalSpy).toHaveBeenCalled();
    expect(result.current.allStreamedItems).toEqual(["a", "b"]);
    expect(result.current.currentIndex).toBe(1);
    expect(result.current.currentItem).toBe("b");
    expect(result.current.isComplete).toBe(true);
    expect(result.current.progress).toBe(100);
  });

  it("resets sequential streaming state", () => {
    const items = ["x", "y"];
    const { result } = renderHook(() =>
      useSequentialStreaming({
        items,
        speed: 10,
        interval: 1,
        delay: 0,
        itemDelay: 1,
      }),
    );

    result.current.reset();

    expect(result.current.allStreamedItems).toEqual([]);
    expect(result.current.currentIndex).toBe(0);
    expect(result.current.isComplete).toBe(false);
    expect(result.current.currentItem).toBe("");
  });
});
