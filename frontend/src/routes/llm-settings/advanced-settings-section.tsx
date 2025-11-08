import React from "react";
import { TFunction } from "i18next";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { SettingsDropdownInput } from "#/components/features/settings/settings-dropdown-input";
import { HelpLink } from "#/components/features/settings/help-link";
import { KeyStatusIcon } from "#/components/features/settings/key-status-icon";
import { AdvancedLLMConfig } from "#/components/features/settings/advanced-llm-config";
import { DEFAULT_OPENHANDS_MODEL } from "#/utils/verified-models";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { I18nKey } from "#/i18n/declaration";
import type { Settings } from "#/types/settings";

export interface AdvancedSettingsSectionProps {
  settings: Settings;
  advancedSettings: Settings;
  currentSelectedModel: string | null;
  agentValue: string;
  agentOptions: { key: string; label: string }[];
  appMode?: string;
  enableDefaultCondenser: boolean;
  condenserMaxSize: number | null;
  onCustomModelChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onApiKeyChange: (value: string) => void;
  onSearchApiKeyChange: (value: string) => void;
  onAgentChange: (value: string) => void;
  onAdvancedConfigChange: (config: Partial<Settings>) => void;
  onCondenserMaxSizeChange: (value: string) => void;
  onEnableDefaultCondenserToggle: (isToggled: boolean) => void;
  t: TFunction;
}

export function AdvancedSettingsSection({
  settings,
  advancedSettings,
  currentSelectedModel,
  agentValue,
  agentOptions,
  appMode,
  enableDefaultCondenser,
  condenserMaxSize,
  onCustomModelChange,
  onBaseUrlChange,
  onApiKeyChange,
  onSearchApiKeyChange,
  onAgentChange,
  onAdvancedConfigChange,
  onCondenserMaxSizeChange,
  onEnableDefaultCondenserToggle,
  t,
}: AdvancedSettingsSectionProps) {
  const isOpenhandsModel = (model?: string | null) =>
    !!model && (model.startsWith("Openhands/") || model.startsWith("Forge/"));
  const showOpenhandsHelpLink =
    isOpenhandsModel(settings.LLM_MODEL) || isOpenhandsModel(currentSelectedModel);

  return (
    <div data-testid="llm-settings-form-advanced" className="flex flex-col gap-6">
      <SettingsInput
        testId="llm-custom-model-input"
        name="llm-custom-model-input"
        label={t(I18nKey.SETTINGS$CUSTOM_MODEL)}
        defaultValue={settings.LLM_MODEL || DEFAULT_OPENHANDS_MODEL}
        placeholder={DEFAULT_OPENHANDS_MODEL}
        type="text"
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        onChange={onCustomModelChange}
      />
      {showOpenhandsHelpLink && (
        <HelpLink
          testId="Openhands-api-key-help-2"
          text={t(I18nKey.SETTINGS$Forge_API_KEY_HELP_TEXT)}
          linkText={t(I18nKey.SETTINGS$NAV_API_KEYS)}
          href="https://app.all-hands.dev/settings/api-keys"
          suffix={t(I18nKey.SETTINGS$Forge_API_KEY_HELP_SUFFIX)}
        />
      )}

      <SettingsInput
        testId="base-url-input"
        name="base-url-input"
        label={t(I18nKey.SETTINGS$BASE_URL)}
        defaultValue={settings.LLM_BASE_URL}
        placeholder="https://api.openai.com"
        type="text"
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        onChange={onBaseUrlChange}
      />

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
        testId="llm-api-key-help-anchor-advanced"
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

      <SettingsInput
        testId="agent-input"
        name="agent-input-display"
        label={t(I18nKey.SETTINGS$AGENT as any, { defaultValue: "Agent" })}
        type="text"
        value={agentValue}
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        onChange={onAgentChange}
        placeholder="CodeActAgent"
      />
      <div className="flex flex-wrap gap-2 text-xs text-text-tertiary">
        {agentOptions.map((option) => (
          <button
            key={option.key}
            type="button"
            className="px-2 py-1 rounded border border-border hover:border-brand-500/50 hover:text-text-primary transition-colors"
            onClick={() => onAgentChange(option.label)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <input type="hidden" name="agent-input" value={agentValue} />

      <div className="border-t border-violet-500/20 pt-6 mt-2">
        <h3 className="text-lg font-semibold mb-4 text-white">
          Advanced LLM Configuration
        </h3>
        <AdvancedLLMConfig
          settings={advancedSettings}
          onConfigChange={onAdvancedConfigChange}
        />
      </div>

      {appMode === "saas" && (
        <SettingsDropdownInput
          testId="runtime-settings-input"
          name="runtime-settings-input"
          label={
            <>
              {t(I18nKey.SETTINGS$RUNTIME_SETTINGS)}
              <a href="mailto:contact@all-hands.dev">
                {t(I18nKey.SETTINGS$GET_IN_TOUCH)}
              </a>
            </>
          }
          items={[]}
          isDisabled
          wrapperClassName="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        />
      )}

      <div className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]">
        <SettingsInput
          testId="condenser-max-size-input"
          name="condenser-max-size-input"
          type="number"
          min={20}
          step={1}
          label={t(I18nKey.SETTINGS$CONDENSER_MAX_SIZE)}
          value={(condenserMaxSize ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE)?.toString()}
          onChange={onCondenserMaxSizeChange}
          isDisabled={!enableDefaultCondenser}
        />
        <p className="text-xs text-text-foreground-secondary mt-1">
          {t(I18nKey.SETTINGS$CONDENSER_MAX_SIZE_TOOLTIP)}
        </p>
      </div>

      <SettingsSwitch
        testId="enable-memory-condenser-switch"
        name="enable-memory-condenser-switch"
        defaultIsToggled={enableDefaultCondenser}
        isToggled={enableDefaultCondenser}
        onToggle={onEnableDefaultCondenserToggle}
      >
        {t(I18nKey.SETTINGS$ENABLE_MEMORY_CONDENSATION)}
      </SettingsSwitch>
    </div>
  );
}


