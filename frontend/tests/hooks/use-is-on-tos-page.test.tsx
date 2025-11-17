import { renderHook } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import * as ReactRouterDom from "react-router-dom";

const useLocationSpy = vi.spyOn(ReactRouterDom, "useLocation");
let useIsOnTosPageHook: (overridePathname?: string) => boolean;

beforeAll(async () => {
  vi.doUnmock("#/hooks/use-is-on-tos-page");
  const module = await import("#/hooks/use-is-on-tos-page");
  useIsOnTosPageHook = module.useIsOnTosPage;
});

afterEach(() => {
  useLocationSpy.mockReset();
});

afterAll(() => {
  useLocationSpy.mockRestore();
});

describe("useIsOnTosPage", () => {
  it("exposes optional override parameter", () => {
    expect(useIsOnTosPageHook.length).toBe(1);
  });

  it("returns true when override pathname is /accept-tos", () => {
    const { result } = renderHook((path: string) => useIsOnTosPageHook(path), {
      initialProps: "/accept-tos",
    });

    expect(result.current).toBe(true);
  });

  it("returns false for other override paths", () => {
    const { result } = renderHook((path: string) => useIsOnTosPageHook(path), {
      initialProps: "/dashboard",
    });

    expect(result.current).toBe(false);
  });

  it("falls back to useLocation when override is undefined", () => {
    useLocationSpy.mockReturnValue({ pathname: "/accept-tos" } as unknown as ReturnType<
      typeof ReactRouterDom.useLocation
    >);

    const { result } = renderHook(() => useIsOnTosPageHook());

    expect(useLocationSpy).toHaveBeenCalled();
    expect(result.current).toBe(true);
  });

  it("returns false when useLocation pathname does not match", () => {
    useLocationSpy.mockReturnValue({ pathname: "/dashboard" } as unknown as ReturnType<
      typeof ReactRouterDom.useLocation
    >);

    const { result } = renderHook(() => useIsOnTosPageHook());

    expect(useLocationSpy).toHaveBeenCalled();
    expect(result.current).toBe(false);
  });

  it("uses empty string fallback when useLocation returns undefined", () => {
    useLocationSpy.mockReturnValue(undefined as unknown as ReturnType<
      typeof ReactRouterDom.useLocation
    >);

    const { result } = renderHook(() => useIsOnTosPageHook());

    expect(useLocationSpy).toHaveBeenCalled();
    expect(result.current).toBe(false);
  });
});
