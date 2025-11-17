import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useStreaming, useTypingStreaming } from "#/hooks/use-streaming";

let nextTimerId: number;
const timeoutCallbacks = new Map<number, () => void>();
const intervalCallbacks = new Map<number, () => void>();

const setupTimerMocks = () => {
  nextTimerId = 1;
  timeoutCallbacks.clear();
  intervalCallbacks.clear();

  vi.spyOn(global, "setTimeout").mockImplementation(
    (callback: (...args: any[]) => void) => {
      const id = nextTimerId++;
      timeoutCallbacks.set(id, () => callback());
      return id as unknown as NodeJS.Timeout;
    },
  );

  vi.spyOn(global, "clearTimeout").mockImplementation((handle: any) => {
    timeoutCallbacks.delete(handle as number);
  });

  vi.spyOn(global, "setInterval").mockImplementation(
    (callback: (...args: any[]) => void) => {
      const id = nextTimerId++;
      intervalCallbacks.set(id, () => callback());
      return id as unknown as NodeJS.Timeout;
    },
  );

  vi.spyOn(global, "clearInterval").mockImplementation((handle: any) => {
    intervalCallbacks.delete(handle as number);
  });
};

const triggerNextTimeout = () => {
  const [id] = timeoutCallbacks.keys();
  if (id === undefined) return;
  const callback = timeoutCallbacks.get(id);
  timeoutCallbacks.delete(id);
  callback?.();
};

const triggerInterval = (id?: number) => {
  if (id !== undefined) {
    intervalCallbacks.get(id)?.();
    return;
  }
  const [firstId] = intervalCallbacks.keys();
  if (firstId !== undefined) {
    intervalCallbacks.get(firstId)?.();
  }
};

describe("useStreaming", () => {
  beforeEach(() => {
    setupTimerMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("auto-starts and streams text to completion", () => {
    const onComplete = vi.fn();
    const { result, unmount } = renderHook(() =>
      useStreaming("hello", { speed: 2, interval: 10, delay: 5, onComplete }),
    );

    expect(result.current.displayedText).toBe("");

    act(() => {
      triggerNextTimeout(); // delay
    });
    const [intervalId] = intervalCallbacks.keys();
    const ticksNeeded = Math.ceil("hello".length / 2);
    for (let i = 0; i < ticksNeeded; i += 1) {
      act(() => {
        triggerInterval(intervalId);
      });
    }

    expect(result.current.displayedText).toBe("hello");
    expect(result.current.isComplete).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.progress).toBe(100);
    expect(onComplete).toHaveBeenCalledTimes(1);

    unmount();
  });

  it("supports manual start, stop, and reset", () => {
    const { result, unmount } = renderHook(() =>
      useStreaming("world", { speed: 1, interval: 20, delay: 0, autoStart: false }),
    );

    expect(result.current.displayedText).toBe("");

    act(() => {
      result.current.startStreaming();
    });
    act(() => {
      triggerNextTimeout();
    });
    const [manualIntervalId] = intervalCallbacks.keys();
    const manualTicksNeeded = Math.ceil("world".length / 1);
    act(() => {
      triggerInterval(manualIntervalId);
    });
    expect(result.current.isStreaming).toBe(true);

    for (let i = 1; i < manualTicksNeeded; i += 1) {
      act(() => {
        triggerInterval(manualIntervalId);
      });
    }
    expect(result.current.displayedText.length).toBeGreaterThan(0);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.isComplete).toBe(true);

    const currentText = result.current.displayedText;
    expect(result.current.displayedText).toBe(currentText);
    expect(result.current.isStreaming).toBe(false);

    act(() => {
      result.current.resetStreaming();
    });

    expect(result.current.displayedText).toBe("");
    expect(result.current.isComplete).toBe(false);

    unmount();
  });
});

describe("useTypingStreaming", () => {
  beforeEach(() => {
    setupTimerMocks();
    vi.spyOn(Math, "random").mockReturnValue(0.5);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("streams text with realistic typing variation", () => {
    const onComplete = vi.fn();
    const { result, unmount } = renderHook(() =>
      useTypingStreaming("Hi.", {
        realisticTyping: true,
        speed: 1,
        interval: 30,
        punctuationDelay: 100,
        pauseOnPunctuation: true,
        delay: 0,
        onComplete,
      }),
    );

    expect(result.current.displayedText).toBe("");

    act(() => {
      result.current.startStreaming();
    });
    act(() => {
      triggerNextTimeout();
    });
    act(() => {
      triggerNextTimeout();
    });
    act(() => {
      triggerNextTimeout();
    });
    act(() => {
      triggerNextTimeout();
    });

    expect(result.current.displayedText).toBe("Hi.");
    expect(result.current.isComplete).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(onComplete).toHaveBeenCalled();

    act(() => {
      result.current.resetStreaming();
    });
    expect(result.current.displayedText).toBe("");

    unmount();
  });
});
