import React from "react";
import { useTranslation } from "react-i18next";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { I18nKey } from "#/i18n/declaration";
import { SettingsPanel } from "./settings-panel";

interface PreferencesSectionProps {
  enableAnalytics: boolean;
  enableSound: boolean;
  enableProactive: boolean;
  enableSolvability: boolean;
  isSaas: boolean;
  onAnalyticsToggle: (isToggled: boolean) => void;
  onSoundToggle: (isToggled: boolean) => void;
  onProactiveToggle: (isToggled: boolean) => void;
  onSolvabilityToggle: (isToggled: boolean) => void;
}

export function PreferencesSection({
  enableAnalytics,
  enableSound,
  enableProactive,
  enableSolvability,
  isSaas,
  onAnalyticsToggle,
  onSoundToggle,
  onProactiveToggle,
  onSolvabilityToggle,
}: PreferencesSectionProps) {
  const { t } = useTranslation();

  return (
    <SettingsPanel title={t("SETTINGS$PREFERENCES", "Preferences")}>
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-2">
        <SettingsSwitch
          testId="enable-analytics-switch"
          name="enable-analytics-switch"
          defaultIsToggled={enableAnalytics}
          onToggle={onAnalyticsToggle}
        >
          {t(I18nKey.ANALYTICS$SEND_ANONYMOUS_DATA)}
        </SettingsSwitch>

        <SettingsSwitch
          testId="enable-sound-notifications-switch"
          name="enable-sound-notifications-switch"
          defaultIsToggled={enableSound}
          onToggle={onSoundToggle}
        >
          {t(I18nKey.SETTINGS$SOUND_NOTIFICATIONS)}
        </SettingsSwitch>

        {isSaas && (
          <SettingsSwitch
            testId="enable-proactive-conversations-switch"
            name="enable-proactive-conversations-switch"
            defaultIsToggled={enableProactive}
            onToggle={onProactiveToggle}
          >
            {t(I18nKey.SETTINGS$PROACTIVE_CONVERSATION_STARTERS)}
          </SettingsSwitch>
        )}

        {isSaas && (
          <SettingsSwitch
            testId="enable-solvability-analysis-switch"
            name="enable-solvability-analysis-switch"
            defaultIsToggled={enableSolvability}
            onToggle={onSolvabilityToggle}
          >
            {t(I18nKey.SETTINGS$SOLVABILITY_ANALYSIS)}
          </SettingsSwitch>
        )}
      </div>
    </SettingsPanel>
  );
}
