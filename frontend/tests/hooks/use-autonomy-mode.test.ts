import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAutonomyMode } from "#/hooks/use-autonomy-mode";
import type { AutonomyMode } from "#/components/features/controls/autonomy-mode-selector";

const useSettingsMock = vi.hoisted(() =>
  vi.fn(() => ({ data: { autonomy_level: "balanced" } })),
);
const mutateMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: () => useSettingsMock(),
}));

vi.mock("#/hooks/mutation/use-save-settings", () => ({
  useSaveSettings: () => ({ mutate: mutateMock }),
}));

const mockI18n = {
  changeLanguage: vi.fn(() => Promise.resolve()),
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: mockI18n,
  }),
}));

describe("useAutonomyMode", () => {
  beforeEach(() => {
    vi.resetModules();
    mutateMock.mockReset();
    useSettingsMock.mockReturnValue({ data: { autonomy_level: "balanced" } });
    localStorage.clear();
  });

  it("uses backend autonomy level when available", () => {
    useSettingsMock.mockReturnValue({ data: { autonomy_level: "full" } });

    const { result } = renderHook(() => useAutonomyMode());

    expect(result.current.currentMode).toBe("full");
  });

  it("falls back to local storage when backend missing autonomy level", () => {
    useSettingsMock.mockReturnValue({ data: {} as any });
    localStorage.setItem("autonomy_mode", "supervised");

    const { result } = renderHook(() => useAutonomyMode());

    expect(result.current.currentMode).toBe("supervised");
  });

  it("defaults to balanced when no sources provided", () => {
    useSettingsMock.mockReturnValue({ data: null } as any);

    const { result } = renderHook(() => useAutonomyMode());

    expect(result.current.currentMode).toBe("balanced");
  });

  it("saves mode changes and toggles loading state on success", async () => {
    const mutateFn = vi.fn();
    mutateMock.mockImplementation((payload, opts) => mutateFn(payload, opts));

    const { result } = renderHook(() => useAutonomyMode());

    expect(result.current.isLoading).toBe(false);

    act(() => {
      result.current.handleModeChange("full");
    });

    expect(result.current.isLoading).toBe(true);
    expect(mutateFn).toHaveBeenCalledWith(
      { autonomy_level: "full" },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );

    const callbacks = mutateFn.mock.calls[0][1];
    act(() => {
      callbacks.onSuccess();
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it("resets loading state on error", async () => {
    const mutateFn = vi.fn();
    mutateMock.mockImplementation((payload, opts) => mutateFn(payload, opts));

    const { result } = renderHook(() => useAutonomyMode());

    act(() => {
      result.current.handleModeChange("supervised");
    });

    const callbacks = mutateFn.mock.calls[0][1];
    act(() => {
      callbacks.onError(new Error("boom"));
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it("returns localized mode descriptions", () => {
    const { result } = renderHook(() => useAutonomyMode());

    const descriptions = (
      ["supervised", "balanced", "full"] as AutonomyMode[]
    ).map((mode) => result.current.getModeDescription(mode));

    expect(descriptions).toEqual([
      "Supervised mode: Agent will always ask for confirmation before taking actions",
      "Balanced mode: Agent will ask for confirmation only for high-risk actions",
      "Full autonomous mode: Agent will execute tasks without asking for confirmation",
    ]);

    expect(result.current.getModeDescription("unknown" as AutonomyMode)).toBe(
      "",
    );
  });

  it("provides icon and color info for each mode", () => {
    const { result } = renderHook(() => useAutonomyMode());

    expect(result.current.getModeInfo("supervised")).toEqual({
      color: "orange",
      icon: "shield",
    });
    expect(result.current.getModeInfo("balanced")).toEqual({
      color: "blue",
      icon: "eye",
    });
    expect(result.current.getModeInfo("full")).toEqual({
      color: "green",
      icon: "zap",
    });
    expect(result.current.getModeInfo("unknown" as AutonomyMode)).toEqual({
      color: "gray",
      icon: "settings",
    });
  });
});
