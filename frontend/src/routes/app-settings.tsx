import React from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { useSettings } from "#/hooks/query/use-settings";
import { AvailableLanguages } from "#/i18n";
import { DEFAULT_SETTINGS } from "#/services/settings";
import type { Settings } from "#/types/settings";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { I18nKey } from "#/i18n/declaration";
import { LanguageInput } from "#/components/features/settings/app-settings/language-input";
import { handleCaptureConsent } from "#/utils/handle-capture-consent";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { AppSettingsInputsSkeleton } from "#/components/features/settings/app-settings/app-settings-inputs-skeleton";
import { useConfig } from "#/hooks/query/use-config";
import { parseMaxBudgetPerTask } from "#/utils/settings-utils";

type DirtyFlagKey =
  | "language"
  | "analytics"
  | "sound"
  | "proactive"
  | "solvability"
  | "budget"
  | "gitUserName"
  | "gitUserEmail";

type DirtyFlags = Record<DirtyFlagKey, boolean>;

const INITIAL_DIRTY_FLAGS: DirtyFlags = {
  language: false,
  analytics: false,
  sound: false,
  proactive: false,
  solvability: false,
  budget: false,
  gitUserName: false,
  gitUserEmail: false,
};

interface AppSettingsController {
  settings: ReturnType<typeof useSettings>["data"];
  config: ReturnType<typeof useConfig>["data"];
  formAction: (formData: FormData) => void;
  handlers: {
    onLanguageChange: (value: string) => void;
    onAnalyticsToggle: (checked: boolean) => void;
    onSoundToggle: (checked: boolean) => void;
    onProactiveToggle: (checked: boolean) => void;
    onSolvabilityToggle: (checked: boolean) => void;
    onBudgetChange: (value: string) => void;
    onGitUserNameChange: (value: string) => void;
    onGitUserEmailChange: (value: string) => void;
  };
  formIsClean: boolean;
  isPending: boolean;
  shouldBeLoading: boolean;
  viewSettings: Settings;
}

function useAppSettingsController(t: TFunction): AppSettingsController {
  const { mutate: saveSettings, isPending } = useSaveSettings();
  const { data: settings, isLoading } = useSettings();
  const { data: config } = useConfig();
  const normalizedSettings = settings ?? DEFAULT_SETTINGS;
  const [dirtyFlags, setDirtyFlags] =
    React.useState<DirtyFlags>(INITIAL_DIRTY_FLAGS);

  const updateFlag = React.useCallback((key: DirtyFlagKey, value: boolean) => {
    setDirtyFlags((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFlags = React.useCallback(() => {
    setDirtyFlags(INITIAL_DIRTY_FLAGS);
  }, []);

  const formAction = React.useCallback(
    (formData: FormData) => {
      const languageLabel = formData.get("language-input")?.toString();
      const languageValue = AvailableLanguages.find(
        ({ label }) => label === languageLabel,
      )?.value;
      const language = languageValue || DEFAULT_SETTINGS.LANGUAGE;

      const enableAnalytics =
        formData.get("enable-analytics-switch")?.toString() === "on";
      const enableSoundNotifications =
        formData.get("enable-sound-notifications-switch")?.toString() === "on";

      const enableProactiveConversations =
        formData.get("enable-proactive-conversations-switch")?.toString() ===
        "on";

      const enableSolvabilityAnalysis =
        formData.get("enable-solvability-analysis-switch")?.toString() === "on";

      const maxBudgetPerTaskValue = formData
        .get("max-budget-per-task-input")
        ?.toString();
      const maxBudgetPerTask = parseMaxBudgetPerTask(
        maxBudgetPerTaskValue || "",
      );

      const gitUserName =
        formData.get("git-user-name-input")?.toString() ||
        DEFAULT_SETTINGS.GIT_USER_NAME;
      const gitUserEmail =
        formData.get("git-user-email-input")?.toString() ||
        DEFAULT_SETTINGS.GIT_USER_EMAIL;

      saveSettings(
        {
          LANGUAGE: language,
          user_consents_to_analytics: enableAnalytics,
          ENABLE_SOUND_NOTIFICATIONS: enableSoundNotifications,
          ENABLE_PROACTIVE_CONVERSATION_STARTERS: enableProactiveConversations,
          ENABLE_SOLVABILITY_ANALYSIS: enableSolvabilityAnalysis,
          MAX_BUDGET_PER_TASK: maxBudgetPerTask,
          GIT_USER_NAME: gitUserName,
          GIT_USER_EMAIL: gitUserEmail,
        },
        {
          onSuccess: () => {
            handleCaptureConsent(enableAnalytics);
            displaySuccessToast(t(I18nKey.SETTINGS$SAVED));
          },
          onError: (error) => {
            const errorMessage = retrieveAxiosErrorMessage(error);
            displayErrorToast(
              t(I18nKey.ERROR$GENERIC, { defaultValue: errorMessage }),
            );
          },
          onSettled: () => {
            resetFlags();
          },
        },
      );
    },
    [resetFlags, saveSettings, t],
  );

  const handlers: AppSettingsController["handlers"] = React.useMemo(
    () => ({
      onLanguageChange: (value: string) => {
        const selectedLanguage =
          AvailableLanguages.find(({ label: langValue }) => langValue === value)
            ?.label ?? value;
        const currentLanguageValue = normalizedSettings.LANGUAGE;
        const currentLanguage =
          AvailableLanguages.find(
            ({ value: langValue }) => langValue === currentLanguageValue,
          )?.label ?? currentLanguageValue;
        updateFlag("language", selectedLanguage !== currentLanguage);
      },
      onAnalyticsToggle: (checked: boolean) => {
        const currentAnalytics =
          !!normalizedSettings.USER_CONSENTS_TO_ANALYTICS;
        updateFlag("analytics", checked !== currentAnalytics);
      },
      onSoundToggle: (checked: boolean) => {
        const current = !!normalizedSettings.ENABLE_SOUND_NOTIFICATIONS;
        updateFlag("sound", checked !== current);
      },
      onProactiveToggle: (checked: boolean) => {
        const current =
          !!normalizedSettings.ENABLE_PROACTIVE_CONVERSATION_STARTERS;
        updateFlag("proactive", checked !== current);
      },
      onSolvabilityToggle: (checked: boolean) => {
        const current = !!normalizedSettings.ENABLE_SOLVABILITY_ANALYSIS;
        updateFlag("solvability", checked !== current);
      },
      onBudgetChange: (value: string) => {
        const newValue = parseMaxBudgetPerTask(value);
        const currentValue = normalizedSettings.MAX_BUDGET_PER_TASK;
        updateFlag("budget", newValue !== currentValue);
      },
      onGitUserNameChange: (value: string) => {
        const currentValue = normalizedSettings.GIT_USER_NAME;
        updateFlag("gitUserName", value !== currentValue);
      },
      onGitUserEmailChange: (value: string) => {
        const currentValue = normalizedSettings.GIT_USER_EMAIL;
        updateFlag("gitUserEmail", value !== currentValue);
      },
    }),
    [normalizedSettings, updateFlag],
  );

  const formIsClean = React.useMemo(
    () => Object.values(dirtyFlags).every((flag) => !flag),
    [dirtyFlags],
  );

  const shouldBeLoading = !settings || isLoading || isPending;

  return {
    settings,
    config,
    formAction,
    handlers,
    formIsClean,
    isPending,
    shouldBeLoading,
    viewSettings: normalizedSettings,
  };
}

function AppSettingsScreen() {
  const { t } = useTranslation();
  const controller = useAppSettingsController(t);
  const { settings, config, viewSettings } = controller;

  return (
    <form
      data-testid="app-settings-screen"
      action={controller.formAction}
      className="flex flex-col h-full"
    >
      {controller.shouldBeLoading && <AppSettingsInputsSkeleton />}
      {!controller.shouldBeLoading && settings && (
        <div className="flex-1 p-6 bg-black">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* Language Settings */}
            <div className="card-modern">
              <h2 className="text-lg font-semibold text-foreground mb-4">
                Language & Region
              </h2>
              <LanguageInput
                name="language-input"
                defaultKey={viewSettings.LANGUAGE}
                onChange={controller.handlers.onLanguageChange}
              />
            </div>

            {/* Preferences */}
            <div className="card-modern">
              <h2 className="text-lg font-semibold text-foreground mb-6">
                Preferences
              </h2>
              <div className="space-y-4">
                <SettingsSwitch
                  testId="enable-analytics-switch"
                  name="enable-analytics-switch"
                  defaultIsToggled={!!viewSettings.USER_CONSENTS_TO_ANALYTICS}
                  onToggle={controller.handlers.onAnalyticsToggle}
                >
                  {t(I18nKey.ANALYTICS$SEND_ANONYMOUS_DATA)}
                </SettingsSwitch>

                <SettingsSwitch
                  testId="enable-sound-notifications-switch"
                  name="enable-sound-notifications-switch"
                  defaultIsToggled={!!viewSettings.ENABLE_SOUND_NOTIFICATIONS}
                  onToggle={controller.handlers.onSoundToggle}
                >
                  {t(I18nKey.SETTINGS$SOUND_NOTIFICATIONS)}
                </SettingsSwitch>

                {config?.APP_MODE === "saas" && (
                  <SettingsSwitch
                    testId="enable-proactive-conversations-switch"
                    name="enable-proactive-conversations-switch"
                    defaultIsToggled={
                      !!viewSettings.ENABLE_PROACTIVE_CONVERSATION_STARTERS
                    }
                    onToggle={controller.handlers.onProactiveToggle}
                  >
                    {t(I18nKey.SETTINGS$PROACTIVE_CONVERSATION_STARTERS)}
                  </SettingsSwitch>
                )}

                {config?.APP_MODE === "saas" && (
                  <SettingsSwitch
                    testId="enable-solvability-analysis-switch"
                    name="enable-solvability-analysis-switch"
                    defaultIsToggled={
                      !!viewSettings.ENABLE_SOLVABILITY_ANALYSIS
                    }
                    onToggle={controller.handlers.onSolvabilityToggle}
                  >
                    {t(I18nKey.SETTINGS$SOLVABILITY_ANALYSIS)}
                  </SettingsSwitch>
                )}
              </div>
            </div>

            {/* Budget Settings */}
            <div className="card-modern">
              <h2 className="text-lg font-semibold text-foreground mb-4">
                Budget & Usage
              </h2>
              <SettingsInput
                testId="max-budget-per-task-input"
                name="max-budget-per-task-input"
                type="number"
                label={t(I18nKey.SETTINGS$MAX_BUDGET_PER_CONVERSATION)}
                defaultValue={
                  viewSettings.MAX_BUDGET_PER_TASK?.toString() || ""
                }
                onChange={controller.handlers.onBudgetChange}
                placeholder={t(I18nKey.SETTINGS$MAXIMUM_BUDGET_USD)}
                min={1}
                step={1}
                className="w-full max-w-md"
              />
            </div>

            {/* Git Settings */}
            <div className="card-modern">
              <h2 className="text-lg font-semibold text-foreground mb-2">
                {t(I18nKey.SETTINGS$GIT_SETTINGS)}
              </h2>
              <p className="text-sm text-foreground-secondary mb-6">
                {t(I18nKey.SETTINGS$GIT_SETTINGS_DESCRIPTION)}
              </p>
              <div className="space-y-4">
                <SettingsInput
                  testId="git-user-name-input"
                  name="git-user-name-input"
                  type="text"
                  label={t(I18nKey.SETTINGS$GIT_USERNAME)}
                  defaultValue={viewSettings.GIT_USER_NAME || ""}
                  onChange={controller.handlers.onGitUserNameChange}
                  placeholder="Username for git commits"
                  className="w-full max-w-md"
                />
                <SettingsInput
                  testId="git-user-email-input"
                  name="git-user-email-input"
                  type="email"
                  label={t(I18nKey.SETTINGS$GIT_EMAIL)}
                  defaultValue={viewSettings.GIT_USER_EMAIL || ""}
                  onChange={controller.handlers.onGitUserEmailChange}
                  placeholder="Email for git commits"
                  className="w-full max-w-md"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fixed footer */}
      <div className="flex-shrink-0 border-t border-violet-500/20 bg-black">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex justify-end">
            <BrandButton
              testId="submit-button"
              variant="primary"
              type="submit"
              isDisabled={controller.isPending || controller.formIsClean}
              className="px-6 py-2 gradient-brand hover:opacity-90 transition-opacity rounded-lg font-medium text-white disabled:opacity-50"
            >
              {!controller.isPending && t("SETTINGS$SAVE_CHANGES")}
              {controller.isPending && t("SETTINGS$SAVING")}
            </BrandButton>
          </div>
        </div>
      </div>
    </form>
  );
}

export default AppSettingsScreen;
