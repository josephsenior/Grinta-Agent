import { renderHook } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { useErrorActionHandler } from "#/hooks/use-error-action-handler";

const navigateMock = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

describe("useErrorActionHandler", () => {
  const originalOpen = window.open;
  const originalLocation = window.location;
  const openMock = vi.fn();
  const reloadMock = vi.fn();

  beforeAll(() => {
    Object.defineProperty(window, "open", {
      configurable: true,
      writable: true,
      value: openMock,
    });

    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...originalLocation,
        reload: reloadMock,
      },
    });
  });

  beforeEach(() => {
    vi.clearAllMocks();
    navigateMock.mockClear();
    openMock.mockClear();
    reloadMock.mockClear();
  });

  afterAll(() => {
    Object.defineProperty(window, "open", {
      configurable: true,
      writable: true,
      value: originalOpen,
    });

    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("invokes custom handlers when available", () => {
    const customRetry = vi.fn();
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction(
      { type: "retry", label: "Retry" },
      { retry: customRetry },
    );

    expect(customRetry).toHaveBeenCalled();
    expect(result.current.lastHandledAction.current).toBe("custom:retry");
  });

  it("handles refresh utility action", () => {
    const reloadSpy = vi.spyOn(window.location, "reload");
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "refresh", label: "Refresh" });

    expect(reloadSpy).toHaveBeenCalled();
    expect(result.current.lastHandledAction.current).toBe("utility:refresh");
  });

  it("handles retry utility action without custom handler", () => {
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "retry", label: "Retry" });

    expect(result.current.lastHandledAction.current).toBe("utility:retry");
  });

  it("navigates for built-in navigation actions", () => {
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "upgrade", label: "Upgrade" });

    expect(navigateMock).toHaveBeenCalledWith("/billing");
    expect(result.current.lastHandledAction.current).toBe("navigate:upgrade");
  });

  it("opens external links for help/support/status", () => {
    const openSpy = vi.spyOn(window, "open");
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "help", label: "Help" });

    expect(openSpy).toHaveBeenCalled();
    expect(result.current.lastHandledAction.current).toBe("external:help");
  });

  it("opens report link when url provided", () => {
    const openSpy = vi.spyOn(window, "open");
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({
      type: "report",
      label: "Report",
      url: "https://report",
    });

    expect(openSpy).toHaveBeenCalledWith("https://report", "_blank");
    expect(result.current.lastHandledAction.current).toBe("external:report");
  });

  it("handles placeholder actions without side effects", () => {
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "export", label: "Export" });

    expect(result.current.lastHandledAction.current).toBe("placeholder:export");
  });

  it("falls back to opening action url when no handler exists", () => {
    const openSpy = vi.spyOn(window, "open");
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({
      type: "unknown",
      label: "Unknown",
      url: "https://example.com",
    });

    expect(openSpy).toHaveBeenCalledWith("https://example.com", "_blank");
    expect(result.current.lastHandledAction.current).toBe("fallback:unknown");
  });

  it("logs warning when no handler or url is provided", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { result } = renderHook(() => useErrorActionHandler());

    result.current.handleErrorAction({ type: "unhandled", label: "Unhandled" });

    expect(warnSpy).toHaveBeenCalledWith("Unknown error action: unhandled");
    expect(result.current.lastHandledAction.current).toBe("fallback:unhandled");
  });
});
