import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mutateMock = vi.fn();

vi.mock("#/hooks/mutation/use-save-settings", () => ({
  useSaveSettings: () => ({ mutate: mutateMock }),
}));

const handleCaptureConsentMock = vi.fn();
vi.mock("#/utils/handle-capture-consent", () => ({
  handleCaptureConsent: (...args: unknown[]) => handleCaptureConsentMock(...args),
}));

import { useMigrateUserConsent } from "#/hooks/use-migrate-user-consent";

describe("useMigrateUserConsent", () => {
  beforeEach(() => {
    mutateMock.mockReset();
    handleCaptureConsentMock.mockReset();
    localStorage.clear();
  });

  it("skips migration when no consent present", async () => {
    const { result } = renderHook(() => useMigrateUserConsent());

    await act(async () => {
      await result.current.migrateUserConsent();
    });

    expect(mutateMock).not.toHaveBeenCalled();
    expect(handleCaptureConsentMock).not.toHaveBeenCalled();
  });

  it("migrates and cleans up analytics consent", async () => {
    const onSuccess = vi.fn((opts: { onSuccess?: () => void }) => opts.onSuccess?.());
    mutateMock.mockImplementation((_payload, opts) => onSuccess(opts));
    localStorage.setItem("analytics-consent", "true");
    const handleAnalyticsWasPresentInLocalStorage = vi.fn();

    const { result } = renderHook(() => useMigrateUserConsent());

    await act(async () => {
      await result.current.migrateUserConsent({ handleAnalyticsWasPresentInLocalStorage });
    });

    expect(handleAnalyticsWasPresentInLocalStorage).toHaveBeenCalled();
    expect(mutateMock).toHaveBeenCalledWith(
      { user_consents_to_analytics: true },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(handleCaptureConsentMock).toHaveBeenCalledWith(true);
    expect(localStorage.getItem("analytics-consent")).toBeNull();
  });

  it("supports false consent value", async () => {
    mutateMock.mockImplementation((_payload, opts) => opts.onSuccess?.());
    localStorage.setItem("analytics-consent", "false");

    const { result } = renderHook(() => useMigrateUserConsent());

    await act(async () => {
      await result.current.migrateUserConsent();
    });

    expect(mutateMock).toHaveBeenCalledWith(
      { user_consents_to_analytics: false },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(handleCaptureConsentMock).toHaveBeenCalledWith(false);
  });
});
