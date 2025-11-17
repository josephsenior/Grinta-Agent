import { act, renderHook, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { useBackgroundRuntimeInit } from "#/hooks/use-background-runtime-init";

const conversationState = { conversationId: "123" };

vi.mock("#/hooks/use-conversation-id", () => ({
  useConversationId: () => conversationState,
}));

describe("useBackgroundRuntimeInit", () => {
  const originalFetch = global.fetch;
  const originalSetInterval = global.setInterval;

  beforeEach(() => {
    vi.useFakeTimers();
    global.fetch = vi.fn() as unknown as typeof fetch;
    (global.fetch as Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: "RUNNING" }),
    });
    conversationState.conversationId = "123";
  });

  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    global.fetch = originalFetch;
    global.setInterval = originalSetInterval;
    vi.restoreAllMocks();
  });

  it("returns initial idle state when no conversation id", async () => {
    conversationState.conversationId = "" as any;
    const { result } = renderHook(() => useBackgroundRuntimeInit());

    expect(result.current).toEqual({
      isInitializing: false,
      isReady: false,
      error: null,
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("polls runtime status and marks ready", async () => {
    const fetchMock = global.fetch as Mock;
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "RUNNING" }),
    });

    const { result, unmount } = renderHook(() => useBackgroundRuntimeInit());

    await waitFor(() => expect(result.current.isInitializing).toBe(true));

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(result.current.isReady).toBe(true));
    unmount();
    expect(result.current.error).toBeNull();
  });

  it("sets error when runtime returns error status", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "ERROR" }),
    });

    const { result } = renderHook(() => useBackgroundRuntimeInit());

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    await waitFor(() =>
      expect(result.current.error).toBe("Runtime initialization failed"),
    );
    expect(result.current.isReady).toBe(false);
  });

  it("times out after 60 seconds if runtime never ready", async () => {
    (global.fetch as Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: "PENDING" }),
    });

    const { result } = renderHook(() => useBackgroundRuntimeInit());

    act(() => {
      vi.advanceTimersByTime(60000);
      vi.runOnlyPendingTimers();
    });

    await waitFor(() =>
      expect(result.current.error).toBe("Runtime initialization timeout"),
    );
    expect(result.current.isInitializing).toBe(false);
  });

  it("handles fetch failures gracefully", async () => {
    const fetchMock = global.fetch as Mock;
    fetchMock.mockResolvedValueOnce({ ok: false });
    fetchMock.mockRejectedValueOnce(new Error("network"));

    const { result } = renderHook(() => useBackgroundRuntimeInit());

    act(() => {
      vi.advanceTimersToNextTimer();
      vi.advanceTimersToNextTimer();
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(result.current.error === null || result.current.error === "Runtime initialization timeout").toBe(true);
    expect(result.current.isReady).toBe(false);
  });

  it("sets error state when initialization throws", async () => {
    global.setInterval = vi.fn(() => {
      throw new Error("interval failure");
    }) as any;

    const { result } = renderHook(() => useBackgroundRuntimeInit());

    await waitFor(() => expect(result.current.error).toBe("interval failure"));
    expect(result.current.isInitializing).toBe(false);
    expect(result.current.isReady).toBe(false);
  });
});
