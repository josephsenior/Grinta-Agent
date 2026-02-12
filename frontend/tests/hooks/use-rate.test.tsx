import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { useRate } from "#/hooks/use-rate";

describe("useRate", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-01-01T00:00:00.000Z"));
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("records entries and computes rate under threshold", () => {
    const { result } = renderHook(() => useRate({ threshold: 1000 }));

    act(() => {
      result.current.record(Date.now());
      vi.setSystemTime(Date.now() + 300);
      result.current.record(Date.now());
    });

    // Internal buffer is implementation detail
    // expect(result.current.items).toHaveLength(2);
    expect(result.current.rate).toBe(300);
    expect(result.current.isUnderThreshold).toBe(true);
  });

  it("marks rate above threshold", () => {
    const { result } = renderHook(() => useRate({ threshold: 200 }));

    act(() => {
      result.current.record(Date.now());
      vi.setSystemTime(Date.now() + 500);
      result.current.record(Date.now());
    });

    expect(result.current.rate).toBe(500);
    expect(result.current.isUnderThreshold).toBe(false);
  });

  it("handles inactivity beyond threshold", () => {
    const { result } = renderHook(() => useRate({ threshold: 400 }));

    act(() => {
      result.current.record(Date.now());
    });

    expect(result.current.lastUpdated).not.toBeNull();

    act(() => {
      vi.setSystemTime(new Date(Date.now() + 401));
      vi.advanceTimersByTime(401);
    });

    expect(result.current.isUnderThreshold).toBe(false);

    act(() => {
      vi.setSystemTime(new Date(Date.now() + 5));
      result.current.record(Date.now());
      vi.setSystemTime(new Date(Date.now() + 5));
      result.current.record(Date.now());
    });

    expect(result.current.isUnderThreshold).toBe(true);
  });

  it("sets isUnderThreshold false when never updated", () => {
    const { result } = renderHook(() => useRate({ threshold: 100 }));

    act(() => {
      vi.advanceTimersByTime(150);
    });

    expect(result.current.isUnderThreshold).toBe(false);
  });
});
