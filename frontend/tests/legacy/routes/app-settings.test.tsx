import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import AppSettingsScreen from "#/routes/app-settings";
import Forge from "#/api/forge";
import { MOCK_DEFAULT_USER_SETTINGS } from "#/mocks/handlers";
import { AvailableLanguages } from "#/i18n";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (str: string) => str,
    i18n: {
      changeLanguage: vi.fn((_lang: string) => Promise.resolve()),
    },
  }),
}));
import * as CaptureConsent from "#/utils/handle-capture-consent";
import * as ToastHandlers from "#/utils/custom-toast-handlers";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { renderWithProviders } from "#test-utils";

const renderAppSettingsScreen = () =>
  renderWithProviders(<AppSettingsScreen />);

describe("Content", () => {
  it("should render the screen", () => {
    renderAppSettingsScreen();
    screen.getByTestId("app-settings-screen");
  });

  it("should render the correct default values", async () => {
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      language: "no",
      user_consents_to_analytics: true,
      enable_sound_notifications: true,
    });

    renderAppSettingsScreen();

    await waitFor(() => {
      const language = screen.getByTestId("language-input");
      const analytics = screen.getByTestId("enable-analytics-switch");
      const sound = screen.getByTestId("enable-sound-notifications-switch");

      expect(language).toHaveValue("Norsk");
      expect(analytics).toBeChecked();
      expect(sound).toBeChecked();
    });
  });

  it("should render the language options", async () => {
    renderAppSettingsScreen();

    const language = await screen.findByTestId("language-input");
    await userEvent.click(language);

    AvailableLanguages.forEach((lang: any) => {
      const option = screen.getByText(lang.label);
      expect(option).toBeInTheDocument();
    });
  });
});

describe("Form submission", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should submit the form with the correct values", async () => {
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      user_consents_to_analytics: false,
      enable_sound_notifications: false,
    });

    renderAppSettingsScreen();

    const language = await screen.findByTestId("language-input");
    const analytics = await screen.findByTestId("enable-analytics-switch");
    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );

    expect(language).toHaveValue("English");
    expect(analytics).not.toBeChecked();
    expect(sound).not.toBeChecked();

    // change language
    await userEvent.click(language);
    const norsk = screen.getByText("Norsk");
    await userEvent.click(norsk);
    expect(language).toHaveValue("Norsk");

    // toggle options
    console.log("Toggling options...");
    await userEvent.click(analytics);
    expect(analytics).toBeChecked();
    await userEvent.click(sound);
    expect(sound).toBeChecked();

    // submit the form
    console.log("Submitting form...");
    const submit = await screen.findByTestId("submit-button");
    await userEvent.click(submit);
    console.log("Form submitted, checking spy...");
    expect(saveSettingsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        language: "no",
        user_consents_to_analytics: true,
        enable_sound_notifications: true,
      }),
    );
  });

  it("should only enable the submit button when there are changes", async () => {
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    renderAppSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    // Language check
    const language = await screen.findByTestId("language-input");
    await userEvent.click(language);
    const norsk = screen.getByText("Norsk");
    await userEvent.click(norsk);
    expect(submit).not.toBeDisabled();

    await userEvent.click(language);
    const english = screen.getByText("English");
    await userEvent.click(english);
    expect(submit).toBeDisabled();

    // Analytics check
    const analytics = await screen.findByTestId("enable-analytics-switch");
    await userEvent.click(analytics);
    expect(submit).not.toBeDisabled();

    await userEvent.click(analytics);
    expect(submit).toBeDisabled();

    // Sound check
    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );
    await userEvent.click(sound);
    expect(submit).not.toBeDisabled();

    await userEvent.click(sound);
    expect(submit).toBeDisabled();
  });

  it("should call handleCaptureConsents with true when the analytics switch is toggled", async () => {
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    const handleCaptureConsentsSpy = vi.spyOn(
      CaptureConsent,
      "handleCaptureConsent",
    );

    renderAppSettingsScreen();

    const analytics = await screen.findByTestId("enable-analytics-switch");
    const submit = await screen.findByTestId("submit-button");

    await userEvent.click(analytics);
    await userEvent.click(submit);

    await waitFor(() =>
      expect(handleCaptureConsentsSpy).toHaveBeenCalledWith(true),
    );
  });

  it("should call handleCaptureConsents with false when the analytics switch is toggled", async () => {
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      user_consents_to_analytics: true,
    });

    const handleCaptureConsentsSpy = vi.spyOn(
      CaptureConsent,
      "handleCaptureConsent",
    );

    renderAppSettingsScreen();

    const analytics = await screen.findByTestId("enable-analytics-switch");
    const submit = await screen.findByTestId("submit-button");

    await userEvent.click(analytics);
    await userEvent.click(submit);

    await waitFor(() =>
      expect(handleCaptureConsentsSpy).toHaveBeenCalledWith(false),
    );
  });

  // flaky test
  it.skip("should disable the button when submitting changes", async () => {
    renderAppSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );
    await userEvent.click(sound);
    expect(submit).not.toBeDisabled();

    // submit the form
    await userEvent.click(submit);

    expect(submit).toHaveTextContent("Saving...");
    expect(submit).toBeDisabled();

    await waitFor(() => expect(submit).toHaveTextContent("Save"));
  });

  it("should disable the button after submitting changes", async () => {
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    renderAppSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );
    await userEvent.click(sound);
    expect(submit).not.toBeDisabled();

    // submit the form
    await userEvent.click(submit);
    expect(saveSettingsSpy).toHaveBeenCalled();

    await waitFor(() => expect(submit).toBeDisabled());
  });

  it("should expose SaaS-only toggles and track their dirty state", async () => {
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      enable_proactive_conversation_starters: false,
      enable_solvability_analysis: false,
    });
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      GITHUB_CLIENT_ID: "",
      POSTHOG_CLIENT_KEY: "",
      FEATURE_FLAGS: {
        HIDE_LLM_SETTINGS: false,
      },
    } as any);

    renderAppSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    const proactive = await screen.findByTestId(
      "enable-proactive-conversations-switch",
    );
    const solvability = await screen.findByTestId(
      "enable-solvability-analysis-switch",
    );

    expect(submit).toBeDisabled();

    await userEvent.click(proactive);
    expect(submit).not.toBeDisabled();

    await userEvent.click(proactive);
    expect(submit).toBeDisabled();

    await userEvent.click(solvability);
    expect(submit).not.toBeDisabled();
  });

  it("should submit sanitized git and budget values", async () => {
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      max_budget_per_task: 250,
      git_user_name: "custom-user",
      git_user_email: "custom@example.com",
    });

    renderAppSettingsScreen();

    const budgetInput = await screen.findByTestId("max-budget-per-task-input");
    const gitNameInput = await screen.findByTestId("git-user-name-input");
    const gitEmailInput = await screen.findByTestId("git-user-email-input");
    const submit = await screen.findByTestId("submit-button");

    expect(submit).toBeDisabled();

    await userEvent.clear(budgetInput);

    await userEvent.clear(gitNameInput);
    await userEvent.clear(gitEmailInput);

    await waitFor(() => expect(submit).not.toBeDisabled());

    await userEvent.click(submit);

    await waitFor(() => expect(saveSettingsSpy).toHaveBeenCalled());

    expect(saveSettingsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        max_budget_per_task: null,
        git_user_name: DEFAULT_SETTINGS.GIT_USER_NAME,
        git_user_email: DEFAULT_SETTINGS.GIT_USER_EMAIL,
      }),
    );
  });
});

describe("Status toasts", () => {
  it("should call displaySuccessToast when the settings are saved", async () => {
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    const displaySuccessToastSpy = vi.spyOn(
      ToastHandlers,
      "displaySuccessToast",
    );

    renderAppSettingsScreen();

    // Toggle setting to change
    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );
    await userEvent.click(sound);

    const submit = await screen.findByTestId("submit-button");
    await userEvent.click(submit);

    expect(saveSettingsSpy).toHaveBeenCalled();
    await waitFor(() => expect(displaySuccessToastSpy).toHaveBeenCalled());
  });

  it("should call displayErrorToast when the settings fail to save", async () => {
    const saveSettingsSpy = vi.spyOn(Forge, "saveSettings");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    const displayErrorToastSpy = vi.spyOn(ToastHandlers, "displayErrorToast");

    saveSettingsSpy.mockRejectedValue(new Error("Failed to save settings"));

    renderAppSettingsScreen();

    // Toggle setting to change
    const sound = await screen.findByTestId(
      "enable-sound-notifications-switch",
    );
    await userEvent.click(sound);

    const submit = await screen.findByTestId("submit-button");
    await userEvent.click(submit);

    expect(saveSettingsSpy).toHaveBeenCalled();
    expect(displayErrorToastSpy).toHaveBeenCalled();
  });
});

