import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  useLoadingState,
  useMultipleLoadingStates,
  useAsyncOperation,
} from "#/hooks/use-loading-state";

describe("useLoadingState", () => {
  it("shows loading immediately when no delay", () => {
    const { result } = renderHook(() => useLoadingState());

    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.setLoading(false);
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("respects delay before showing loading", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useLoadingState({ delay: 500 }));

    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(false);

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current.isLoading).toBe(true);
    vi.useRealTimers();
  });

  it("enforces minimum duration before hiding loading", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useLoadingState({ minDuration: 1000 }));

    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.setLoading(false);
    });

    // still true because min duration not elapsed
    expect(result.current.isLoading).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(result.current.isLoading).toBe(false);
    vi.useRealTimers();
  });

  it("clears pending delay when toggled quickly", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useLoadingState({ delay: 500 }));

    act(() => {
      result.current.setLoading(true);
      result.current.setLoading(true);
      result.current.setLoading(false);
    });

    expect(result.current.isLoading).toBe(false);
    vi.useRealTimers();
  });

  it("immediately hides loading when minimum duration satisfied", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useLoadingState({ minDuration: 200 }));

    act(() => {
      result.current.setLoading(true);
    });

    act(() => {
      vi.advanceTimersByTime(300);
      result.current.setLoading(false);
    });

    expect(result.current.isLoading).toBe(false);
    vi.useRealTimers();
  });

  it("withLoading wraps async function and toggles state", async () => {
    const { result } = renderHook(() => useLoadingState());
    const asyncSpy = vi.fn().mockResolvedValue("done");

    await act(async () => {
      const value = await result.current.withLoading(asyncSpy);
      expect(value).toBe("done");
    });

    expect(asyncSpy).toHaveBeenCalledTimes(1);
    expect(result.current.isLoading).toBe(false);
  });

  it("withLoadingSync wraps sync function and toggles state", () => {
    const { result } = renderHook(() => useLoadingState());
    const syncSpy = vi.fn().mockReturnValue(42);
    const value = result.current.withLoadingSync(syncSpy);

    expect(value).toBe(42);
    expect(syncSpy).toHaveBeenCalledTimes(1);
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useMultipleLoadingStates", () => {
  it("tracks multiple keys and reports aggregate state", async () => {
    const { result } = renderHook(() => useMultipleLoadingStates(["first", "second"]));

    expect(result.current.loadingStates).toEqual({ first: false, second: false });
    expect(result.current.isAnyLoading).toBe(false);
    expect(result.current.isAllLoading).toBe(false);

    act(() => {
      result.current.setLoading("first", true);
    });

    expect(result.current.isLoading("first")).toBe(true);
    expect(result.current.isAnyLoading).toBe(true);
    expect(result.current.isAllLoading).toBe(false);

    act(() => {
      result.current.setLoading("second", true);
    });

    expect(result.current.isAllLoading).toBe(true);

    const asyncResult = result.current.withLoading("second", async () => "done");

    await act(async () => {
      await asyncResult;
    });

    expect(result.current.isLoading("second")).toBe(false);
    expect(result.current.isAnyLoading).toBe(true);
    expect(result.current.isAllLoading).toBe(false);

    act(() => {
      result.current.setLoading("first", false);
    });

    expect(result.current.isAnyLoading).toBe(false);
    expect(result.current.isAllLoading).toBe(false);
  });
});

describe("useAsyncOperation", () => {
  it("executes async function and stores result", async () => {
    const { result } = renderHook(() => useAsyncOperation<string>());

    const value = await act(async () => result.current.execute(async () => "data"));

    expect(value).toBe("data");
    expect(result.current.data).toBe("data");
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("handles errors and exposes reset", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    let caught: unknown;

    await act(async () => {
      try {
        await result.current.execute(async () => {
          throw new Error("boom");
        });
      } catch (error) {
        caught = error;
      }
    });

    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error).message).toBe("boom");
    expect(result.current.error?.message).toBe("boom");
    expect(result.current.isLoading).toBe(false);

    act(() => {
      result.current.reset();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it("normalizes non-error rejections", async () => {
    const { result } = renderHook(() => useAsyncOperation());
    let caught: unknown;

    await act(async () => {
      try {
        await result.current.execute(async () => {
          throw "plain";
        });
      } catch (error) {
        caught = error;
      }
    });

    expect((caught as Error).message).toBe("plain");
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("plain");
  });
});
