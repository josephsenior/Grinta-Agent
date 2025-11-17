import { cleanup, renderHook, act } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { useAutoNavigateToApp } from "#/hooks/use-auto-navigate-to-app";

const navigateMock = vi.fn();
const locationValue = { pathname: "/conversations/123/terminal" };
const conversationIdValue = { conversationId: "123" };

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  useLocation: () => locationValue,
}));

vi.mock("#/hooks/use-conversation-id", () => ({
  useConversationId: () => conversationIdValue,
}));

describe("useAutoNavigateToApp", () => {
  const originalDispatch = window.dispatchEvent;

  beforeEach(() => {
    vi.resetModules();
    navigateMock.mockClear();
    locationValue.pathname = "/conversations/123/terminal";
    window.dispatchEvent = originalDispatch;
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("navigates to browser and dispatches load event on healthy server", () => {
    vi.useFakeTimers();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent").mockReturnValue(true);
    const addListenerSpy = vi.spyOn(window, "addEventListener");
    const removeListenerSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() => useAutoNavigateToApp());

    expect(addListenerSpy).toHaveBeenCalledWith(
      "Forge:server-ready",
      expect.any(Function),
    );

    const handler = addListenerSpy.mock.calls[0][1] as EventListener;

    act(() => {
      handler(
        new CustomEvent("Forge:server-ready", {
          detail: { url: "http://localhost:3000", health_status: "healthy" },
        }) as any,
      );
    });

    expect(navigateMock).toHaveBeenCalledWith("/conversations/123/browser");

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(dispatchSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        type: "Forge:load-server-url",
        detail: { url: "http://localhost:3000" },
      }),
    );

    unmount();
    expect(removeListenerSpy).toHaveBeenCalledWith(
      "Forge:server-ready",
      handler,
    );
  });

  it("skips navigation for unhealthy servers and handles existing browser route", () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent").mockReturnValue(true);
    const addListenerSpy = vi.spyOn(window, "addEventListener");

    renderHook(() => useAutoNavigateToApp());
    const handler = addListenerSpy.mock.calls[0][1] as EventListener;

    act(() => {
      handler(
        new CustomEvent("Forge:server-ready", {
          detail: { url: "http://localhost:3000", health_status: "unhealthy" },
        }) as any,
      );
    });

    expect(navigateMock).not.toHaveBeenCalled();
    expect(dispatchSpy).not.toHaveBeenCalled();

    navigateMock.mockClear();
    dispatchSpy.mockClear();
    locationValue.pathname = "/conversations/123/browser";

    act(() => {
      handler(
        new CustomEvent("Forge:server-ready", {
          detail: { url: "http://localhost:3000", health_status: "healthy" },
        }) as any,
      );
    });

    expect(navigateMock).not.toHaveBeenCalled();
    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "Forge:load-server-url",
        detail: { url: "http://localhost:3000" },
      }),
    );
  });
});
