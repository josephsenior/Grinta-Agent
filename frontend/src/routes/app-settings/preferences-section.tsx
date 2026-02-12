import React from "react";
import { useTranslation } from "react-i18next";
import {
  Settings2,
  BarChart,
  Volume2,
  MessageSquare,
  Brain,
} from "lucide-react";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { I18nKey } from "#/i18n/declaration";
import { Accordion } from "#/components/features/settings/accordion";
import { SettingCard } from "#/components/features/settings/setting-card";

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
    <Accordion
      title={t("SETTINGS$PREFERENCES", "Preferences")}
      icon={Settings2}
      defaultOpen
    >
      <div className="space-y-3">
        <SettingCard
          title={t(I18nKey.ANALYTICS$SEND_ANONYMOUS_DATA)}
          description="Help improve Forge by sending anonymous usage data"
          icon={BarChart}
        >
          <SettingsSwitch
            testId="enable-analytics-switch"
            name="enable-analytics-switch"
            defaultIsToggled={enableAnalytics}
            onToggle={onAnalyticsToggle}
          >
            {t(I18nKey.ANALYTICS$SEND_ANONYMOUS_DATA)}
          </SettingsSwitch>
        </SettingCard>

        <SettingCard
          title={t(I18nKey.SETTINGS$SOUND_NOTIFICATIONS)}
          description="Play sounds for notifications and events"
          icon={Volume2}
        >
          <SettingsSwitch
            testId="enable-sound-notifications-switch"
            name="enable-sound-notifications-switch"
            defaultIsToggled={enableSound}
            onToggle={onSoundToggle}
          >
            {t(I18nKey.SETTINGS$SOUND_NOTIFICATIONS)}
          </SettingsSwitch>
        </SettingCard>

        <SettingCard
          title={t(I18nKey.SETTINGS$PROACTIVE_CONVERSATION_STARTERS)}
          description="Get AI-suggested conversation starters"
          icon={MessageSquare}
        >
          <SettingsSwitch
            testId="enable-proactive-conversations-switch"
            name="enable-proactive-conversations-switch"
            defaultIsToggled={enableProactive}
            onToggle={onProactiveToggle}
            isDisabled={!isSaas}
            tooltip={
              !isSaas
                ? t("settings.saasOnlyTooltip", {
                    defaultValue:
                      "Enable SaaS mode to turn on proactive nudges.",
                  })
                : undefined
            }
          >
            {t(I18nKey.SETTINGS$PROACTIVE_CONVERSATION_STARTERS)}
          </SettingsSwitch>
        </SettingCard>

        <SettingCard
          title={t(I18nKey.SETTINGS$SOLVABILITY_ANALYSIS)}
          description="Analyze task complexity before execution"
          icon={Brain}
        >
          <SettingsSwitch
            testId="enable-solvability-analysis-switch"
            name="enable-solvability-analysis-switch"
            defaultIsToggled={enableSolvability}
            onToggle={onSolvabilityToggle}
            isDisabled={!isSaas}
            tooltip={
              !isSaas
                ? t("settings.saasOnlyTooltip", {
                    defaultValue:
                      "Enable SaaS mode to unlock solvability analysis.",
                  })
                : undefined
            }
          >
            {t(I18nKey.SETTINGS$SOLVABILITY_ANALYSIS)}
          </SettingsSwitch>
        </SettingCard>

        {!isSaas && (
          <p className="text-xs text-(--text-tertiary) mt-2">
            {t(I18nKey.SETTINGS$SAAS_ONLY_CONTROLS_NOTE)}
          </p>
        )}
      </div>
    </Accordion>
  );
}
