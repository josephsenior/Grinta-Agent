import React from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { useSettings } from "#/hooks/query/use-settings";
import { AvailableLanguages } from "#/i18n";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { I18nKey } from "#/i18n/declaration";
import { handleCaptureConsent } from "#/utils/handle-capture-consent";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { useConfig } from "#/hooks/query/use-config";
import { parseMaxBudgetPerTask } from "#/utils/settings-utils";
import { LanguageSection } from "./app-settings/language-section";
import { PreferencesSection } from "./app-settings/preferences-section";
import { BudgetSection } from "./app-settings/budget-section";
import { GitSection } from "./app-settings/git-section";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";

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
  viewSettings: typeof DEFAULT_SETTINGS;
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
}

function useAppSettingsController(t: TFunction): AppSettingsController {
  const { mutate: saveSettings, isPending } = useSaveSettings();
  const { data: settings, isLoading } = useSettings();
  const { data: config } = useConfig();
  const normalizedSettings = (settings ??
    DEFAULT_SETTINGS) as typeof DEFAULT_SETTINGS;
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
      console.log("[formAction] formData entries:", Array.from(formData.entries()));
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
          USER_CONSENTS_TO_ANALYTICS: enableAnalytics,
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

  if (controller.shouldBeLoading) {
    return (
      <Card className="bg-transparent border-0 shadow-none">
        <CardHeader className="space-y-4 px-0 pb-8">
          <div className="animate-pulse h-8 w-64 bg-black/50 rounded-xl mx-auto" />
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full">
        <form
          data-testid="app-settings-screen"
          action={controller.formAction}
          className="w-full space-y-6"
        >
          {settings && (
            <>
              <Card className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-2xl p-6">
                <CardHeader className="space-y-4 px-0 pb-8">
                  <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
                    {t("SETTINGS$APP_SETTINGS", "App Settings")}
                  </CardTitle>
                  <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
                    Configure your application preferences and settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="px-0 pt-0">
                  <div className="space-y-4">
                    <LanguageSection
                      language={viewSettings.LANGUAGE}
                      onLanguageChange={controller.handlers.onLanguageChange}
                    />

                    <PreferencesSection
                      enableAnalytics={
                        !!viewSettings.USER_CONSENTS_TO_ANALYTICS
                      }
                      enableSound={!!viewSettings.ENABLE_SOUND_NOTIFICATIONS}
                      enableProactive={
                        !!viewSettings.ENABLE_PROACTIVE_CONVERSATION_STARTERS
                      }
                      enableSolvability={
                        !!viewSettings.ENABLE_SOLVABILITY_ANALYSIS
                      }
                      isSaas={config?.APP_MODE === "saas"}
                      onAnalyticsToggle={controller.handlers.onAnalyticsToggle}
                      onSoundToggle={controller.handlers.onSoundToggle}
                      onProactiveToggle={controller.handlers.onProactiveToggle}
                      onSolvabilityToggle={
                        controller.handlers.onSolvabilityToggle
                      }
                    />

                    <BudgetSection
                      maxBudget={
                        viewSettings.MAX_BUDGET_PER_TASK?.toString() || ""
                      }
                      onBudgetChange={controller.handlers.onBudgetChange}
                    />

                    <GitSection
                      gitUserName={viewSettings.GIT_USER_NAME || ""}
                      gitUserEmail={viewSettings.GIT_USER_EMAIL || ""}
                      onGitUserNameChange={
                        controller.handlers.onGitUserNameChange
                      }
                      onGitUserEmailChange={
                        controller.handlers.onGitUserEmailChange
                      }
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Save Button */}
              <div className="space-y-2">
                <p className="text-sm text-[var(--text-tertiary)] text-center">
                  {t(I18nKey.SETTINGS$UNSAVED_CHANGES_NOTE)}
                </p>
                <button
                  type="submit"
                  data-testid="submit-button"
                  disabled={controller.isPending || controller.formIsClean}
                  className="w-full h-12 rounded-lg bg-[rgba(0,0,0,0.6)] border border-[#8b5cf6] text-white font-medium text-sm transition-all duration-150 hover:bg-[rgba(0,0,0,0.8)] active:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {controller.isPending
                    ? t("SETTINGS$SAVING")
                    : t("SETTINGS$SAVE_CHANGES")}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  );
}

export default AppSettingsScreen;
