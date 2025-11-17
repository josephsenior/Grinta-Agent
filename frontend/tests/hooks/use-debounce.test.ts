import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDebounce, useDebouncedCallback } from "#/hooks/use-debounce";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns initial value immediately and updates after delay", () => {
    const { result, rerender } = renderHook(({ value, delay }) => useDebounce(value, delay), {
      initialProps: { value: "a", delay: 500 },
    });

    expect(result.current).toBe("a");

    rerender({ value: "b", delay: 500 });
    expect(result.current).toBe("a");

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toBe("b");
  });

  it("clears previous timeout when value changes quickly", () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 1 },
    });

    rerender({ value: 2 });
    rerender({ value: 3 });

    act(() => {
      vi.advanceTimersByTime(299);
    });

    expect(result.current).toBe(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });

    expect(result.current).toBe(3);
  });
});

describe("useDebouncedCallback", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces callback execution", () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 200));

    act(() => {
      result.current("first");
      vi.advanceTimersByTime(100);
      result.current("second");
      vi.advanceTimersByTime(200);
    });

    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith("second");
  });

  it("cleans up timeout on unmount", () => {
    const callback = vi.fn();
    const { result, unmount } = renderHook(() => useDebouncedCallback(callback, 200));

    act(() => {
      result.current();
    });

    unmount();
    expect(callback).not.toHaveBeenCalled();
  });
});
