import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const useConfigMock = vi.fn();
const useIsAuthedMock = vi.fn();
const useUserProvidersMock = vi.fn();

vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => useConfigMock(),
}));

vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => useIsAuthedMock(),
}));

vi.mock("#/hooks/use-user-providers", () => ({
  useUserProviders: () => useUserProvidersMock(),
}));

import { useShouldShowUserFeatures } from "#/hooks/use-should-show-user-features";

describe("useShouldShowUserFeatures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useConfigMock.mockReturnValue({ data: { APP_MODE: "saas" } });
    useIsAuthedMock.mockReturnValue({ data: true });
    useUserProvidersMock.mockReturnValue({ providers: [] });
  });

  it("returns false when config app mode missing or unauthenticated", () => {
    useConfigMock.mockReturnValueOnce({ data: undefined });

    const { result, rerender } = renderHook(() => useShouldShowUserFeatures());
    expect(result.current).toBe(false);

    useConfigMock.mockReturnValueOnce({ data: { APP_MODE: "saas" } });
    useIsAuthedMock.mockReturnValueOnce({ data: false });
    rerender();
    expect(result.current).toBe(false);
  });

  it("requires providers when in oss mode", () => {
    useConfigMock.mockReturnValue({ data: { APP_MODE: "oss" } });

    const { result, rerender } = renderHook(() => useShouldShowUserFeatures());
    expect(result.current).toBe(false);

    useUserProvidersMock.mockReturnValueOnce({ providers: ["github"] });
    rerender();
    expect(result.current).toBe(true);
  });

  it("returns true in non-oss modes when authenticated", () => {
    useConfigMock.mockReturnValue({ data: { APP_MODE: "saas" } });
    useUserProvidersMock.mockReturnValue({ providers: [] });

    const { result } = renderHook(() => useShouldShowUserFeatures());

    expect(result.current).toBe(true);
  });

  it("recomputes when provider count changes", () => {
    useConfigMock.mockReturnValue({ data: { APP_MODE: "oss" } });
    const providers: string[] = [];
    useUserProvidersMock.mockReturnValue({ providers });

    const { result, rerender } = renderHook(() => useShouldShowUserFeatures());
    expect(result.current).toBe(false);

    act(() => {
      providers.push("gitlab");
    });
    rerender();
    expect(result.current).toBe(true);
  });
});
