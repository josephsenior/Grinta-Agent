import { renderWithProviders } from "../../test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import UserSettingsScreen from "#/routes/user-settings";
import { Forge } from "#/api/forge-axios";

const useSettingsMock = vi.hoisted(() => vi.fn());
const displaySuccessToastMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: useSettingsMock,
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: displaySuccessToastMock,
  displayErrorToast: vi.fn(),
}));

vi.mock("#/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>(
    "react-i18next",
  );
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
    }),
  };
});

describe("UserSettingsScreen", () => {
  let queryClient: QueryClient;
  let invalidateSpy: MockInstance;
  let refetchSpy: ReturnType<typeof vi.fn>;
  let settingsState: {
    EMAIL: string;
    EMAIL_VERIFIED: boolean | undefined;
  };

  const renderUserSettings = () =>
    renderWithProviders(<UserSettingsScreen />, {
      queryClient,
    });

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    refetchSpy = vi.fn();
    settingsState = {
      EMAIL: "owner@example.com",
      EMAIL_VERIFIED: true,
    };

    useSettingsMock.mockImplementation(() => ({
      get data() {
        return settingsState;
      },
      isLoading: false,
      refetch: refetchSpy,
    }));

    displaySuccessToastMock.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("renders skeleton while loading settings", () => {
    useSettingsMock.mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      refetch: refetchSpy,
    });

    renderUserSettings();

    expect(screen.getByTestId("user-settings-screen")).toBeInTheDocument();
    expect(screen.queryByTestId("email-input")).not.toBeInTheDocument();
  });

  it("validates email format and toggles save button state", async () => {
    const user = userEvent.setup();

    renderUserSettings();

    const input = await screen.findByTestId("email-input");
    expect(input).toHaveValue("owner@example.com");

    await user.clear(input);
    await user.type(input, "invalid-email");

    expect(screen.getByTestId("email-validation-error")).toBeInTheDocument();
    expect(screen.getByTestId("save-email-button")).toBeDisabled();

    await user.clear(input);
    await user.type(input, "new@example.com");

    expect(screen.queryByTestId("email-validation-error")).not.toBeInTheDocument();
    expect(screen.getByTestId("save-email-button")).not.toBeDisabled();
  });

  it("saves a new email and invalidates the settings query", async () => {
    const user = userEvent.setup();
    const postSpy = vi.spyOn(Forge, "post").mockResolvedValue({ data: {} } as any);

    renderUserSettings();

    const input = await screen.findByTestId("email-input");
    await user.clear(input);
    await user.type(input, "updated@example.com");
    await user.click(screen.getByTestId("save-email-button"));

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith(
        "/api/email",
        { email: "updated@example.com" },
        { withCredentials: true },
      ),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith(
      "SETTINGS$EMAIL_SAVED_SUCCESSFULLY",
    );
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["settings"] });
  });

  it("resends the verification email when requested", async () => {
    const user = userEvent.setup();
    const putSpy = vi.spyOn(Forge, "put").mockResolvedValue({ data: {} } as any);
    settingsState.EMAIL_VERIFIED = false;

    renderUserSettings();

    const resendButton = await screen.findByTestId("resend-verification-button");
    await user.click(resendButton);

    await waitFor(() =>
      expect(putSpy).toHaveBeenCalledWith(
        "/api/email/verify",
        {},
        { withCredentials: true },
      ),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith(
      "SETTINGS$VERIFICATION_EMAIL_SENT",
    );
  });

  it("polls for verification status changes and shows success toast once verified", async () => {
    vi.useFakeTimers();
    settingsState.EMAIL_VERIFIED = false;

    const { rerender } = renderUserSettings();

    await screen.findByTestId("resend-verification-button");

    vi.advanceTimersByTime(5000);
    expect(refetchSpy).toHaveBeenCalledTimes(1);

    settingsState = {
      ...settingsState,
      EMAIL_VERIFIED: true,
    };
    rerender(<UserSettingsScreen />);

    await waitFor(() =>
      expect(displaySuccessToastMock).toHaveBeenCalledWith(
        "SETTINGS$EMAIL_VERIFIED_SUCCESSFULLY",
      ),
    );

    await vi.advanceTimersByTimeAsync(2000);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["settings"] });

    vi.advanceTimersByTime(5000);
    expect(refetchSpy).toHaveBeenCalledTimes(1);
  });
});

