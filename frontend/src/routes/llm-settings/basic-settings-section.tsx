import React from "react";
import { TFunction } from "i18next";
import { ModelSelector } from "#/components/shared/modals/settings/model-selector";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { HelpLink } from "#/components/features/settings/help-link";
import { KeyStatusIcon } from "#/components/features/settings/key-status-icon";
import { I18nKey } from "#/i18n/declaration";
import { DOCUMENTATION_URL } from "#/constants/app";
import type { Settings } from "#/types/settings";

export interface BasicSettingsSectionProps {
  settings: Settings;
  modelsAndProviders: Record<string, { separator: string; models: string[] }>;
  currentSelectedModel: string | null;
  isLoading: boolean;
  isFetching: boolean;
  onModelChange: (model: string | null) => void;
  onApiKeyChange: (value: string) => void;
  t: TFunction;
}

export function BasicSettingsSection({
  settings,
  modelsAndProviders,
  currentSelectedModel,
  isLoading,
  isFetching,
  onModelChange,
  onApiKeyChange,
  t,
}: BasicSettingsSectionProps) {
  return (
    <div data-testid="llm-settings-form-basic" className="space-y-6">
      {!isLoading && !isFetching && (
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--text-primary)] block">
              {t("SETTINGS$MODEL", "Model")}
            </label>
            <ModelSelector
              models={modelsAndProviders}
              currentModel={settings.LLM_MODEL || "anthropic/claude-3-5-sonnet-20241022"}
              onChange={onModelChange}
            />
          </div>
        </div>
      )}

      <div className="space-y-4">
        <SettingsInput
          testId="llm-api-key-input"
          name="llm-api-key-input"
          label={t(I18nKey.SETTINGS_FORM$API_KEY)}
          type="password"
          className="w-full"
          placeholder={settings.LLM_API_KEY_SET ? "<hidden>" : ""}
          onChange={onApiKeyChange}
          startContent={
            settings.LLM_API_KEY_SET && (
              <KeyStatusIcon isSet={settings.LLM_API_KEY_SET} />
            )
          }
          helpText={t(
            "settings.apiKeyStorageHelp",
            "Stored encrypted. Rotate or remove keys anytime.",
          )}
          autoComplete="off"
        />

        <HelpLink
          testId="llm-api-key-help-anchor"
          text={t(I18nKey.SETTINGS$DONT_KNOW_API_KEY)}
          linkText={t(I18nKey.SETTINGS$CLICK_FOR_INSTRUCTIONS)}
          href={DOCUMENTATION_URL.LOCAL_SETUP_API_KEY}
        />
      </div>
    </div>
  );
}

