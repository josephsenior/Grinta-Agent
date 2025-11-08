import React from "react";
import { TFunction } from "i18next";
import { ModelSelector } from "#/components/shared/modals/settings/model-selector";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { HelpLink } from "#/components/features/settings/help-link";
import { KeyStatusIcon } from "#/components/features/settings/key-status-icon";
import { DEFAULT_OPENHANDS_MODEL } from "#/utils/verified-models";
import { I18nKey } from "#/i18n/declaration";
import type { Settings } from "#/types/settings";

export interface BasicSettingsSectionProps {
  settings: Settings;
  modelsAndProviders: Record<string, { separator: string; models: string[] }>;
  currentSelectedModel: string | null;
  isLoading: boolean;
  isFetching: boolean;
  onModelChange: (model: string | null) => void;
  onApiKeyChange: (value: string) => void;
  onSearchApiKeyChange: (value: string) => void;
  t: TFunction;
}

const isOpenhandsModel = (model?: string | null) =>
  !!model && (model.startsWith("Openhands/") || model.startsWith("Forge/"));

export function BasicSettingsSection({
  settings,
  modelsAndProviders,
  currentSelectedModel,
  isLoading,
  isFetching,
  onModelChange,
  onApiKeyChange,
  onSearchApiKeyChange,
  t,
}: BasicSettingsSectionProps) {
  const showOpenhandsHelpLink =
    isOpenhandsModel(settings.LLM_MODEL) || isOpenhandsModel(currentSelectedModel);

  return (
    <div data-testid="llm-settings-form-basic" className="flex flex-col gap-6">
      {!isLoading && !isFetching && (
        <>
          <ModelSelector
            models={modelsAndProviders}
            currentModel={settings.LLM_MODEL || DEFAULT_OPENHANDS_MODEL}
            onChange={onModelChange}
          />
          {showOpenhandsHelpLink && (
            <HelpLink
              testId="Openhands-api-key-help"
              text={t(I18nKey.SETTINGS$Forge_API_KEY_HELP_TEXT)}
              linkText={t(I18nKey.SETTINGS$NAV_API_KEYS)}
              href="https://app.all-hands.dev/settings/api-keys"
              suffix={t(I18nKey.SETTINGS$Forge_API_KEY_HELP_SUFFIX)}
            />
          )}
        </>
      )}

      <SettingsInput
        testId="llm-api-key-input"
        name="llm-api-key-input"
        label={t(I18nKey.SETTINGS_FORM$API_KEY)}
        type="password"
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        placeholder={settings.LLM_API_KEY_SET ? "<hidden>" : ""}
        onChange={onApiKeyChange}
        startContent={
          settings.LLM_API_KEY_SET && <KeyStatusIcon isSet={settings.LLM_API_KEY_SET} />
        }
      />

      <HelpLink
        testId="llm-api-key-help-anchor"
        text={t(I18nKey.SETTINGS$DONT_KNOW_API_KEY)}
        linkText={t(I18nKey.SETTINGS$CLICK_FOR_INSTRUCTIONS)}
        href="https://docs.all-hands.dev/usage/local-setup#getting-an-api-key"
      />

      <SettingsInput
        testId="search-api-key-input"
        name="search-api-key-input"
        label={t(I18nKey.SETTINGS$SEARCH_API_KEY)}
        type="password"
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        defaultValue={settings.SEARCH_API_KEY || ""}
        onChange={onSearchApiKeyChange}
        placeholder={t(I18nKey.API$TAVILY_KEY_EXAMPLE)}
        startContent={
          settings.SEARCH_API_KEY_SET && (
            <KeyStatusIcon isSet={settings.SEARCH_API_KEY_SET} />
          )
        }
      />

      <HelpLink
        testId="search-api-key-help-anchor"
        text={t(I18nKey.SETTINGS$SEARCH_API_KEY_OPTIONAL)}
        linkText={t(I18nKey.SETTINGS$SEARCH_API_KEY_INSTRUCTIONS)}
        href="https://tavily.com/"
      />
    </div>
  );
}


