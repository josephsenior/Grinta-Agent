import React from "react";
import { TFunction } from "i18next";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { SettingsDropdownInput } from "#/components/features/settings/settings-dropdown-input";
import { HelpLink } from "#/components/features/settings/help-link";
import { KeyStatusIcon } from "#/components/features/settings/key-status-icon";
import { AdvancedLLMConfig } from "#/components/features/settings/advanced-llm-config";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { I18nKey } from "#/i18n/declaration";
import { DOCUMENTATION_URL } from "#/constants/app";
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
  onAgentChange,
  onAdvancedConfigChange,
  onCondenserMaxSizeChange,
  onEnableDefaultCondenserToggle,
  t,
}: AdvancedSettingsSectionProps) {
  return (
    <div
      data-testid="llm-settings-form-advanced"
      className="flex flex-col gap-8"
    >
      <SettingsInput
        testId="llm-custom-model-input"
        name="llm-custom-model-input"
        label={t(I18nKey.SETTINGS$CUSTOM_MODEL)}
        defaultValue={settings.LLM_MODEL || "anthropic/claude-3-5-sonnet-20241022"}
        placeholder="anthropic/claude-3-5-sonnet-20241022"
        type="text"
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        onChange={onCustomModelChange}
      />

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
          settings.LLM_API_KEY_SET && (
            <KeyStatusIcon isSet={settings.LLM_API_KEY_SET} />
          )
        }
      />
      <HelpLink
        testId="llm-api-key-help-anchor-advanced"
        text={t(I18nKey.SETTINGS$DONT_KNOW_API_KEY)}
        linkText={t(I18nKey.SETTINGS$CLICK_FOR_INSTRUCTIONS)}
        href={DOCUMENTATION_URL.LOCAL_SETUP_API_KEY}
      />

      <SettingsInput
        testId="agent-input"
        name="agent-input-display"
        label={t(I18nKey.SETTINGS$AGENT, { defaultValue: "Agent" })}
        type="text"
        value={agentValue}
        className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
        onChange={onAgentChange}
        placeholder="Orchestrator"
      />
      <div className="flex flex-wrap gap-2 text-xs text-foreground-tertiary">
        {agentOptions.map((option) => (
          <button
            key={option.key}
            type="button"
            className="px-3 py-1.5 rounded-xl border border-white/10 bg-black/60 text-foreground-secondary hover:border-white/20 hover:text-foreground hover:bg-white/5 transition-all"
            onClick={() => onAgentChange(option.label)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <input type="hidden" name="agent-input" value={agentValue} />

      <div className="border-t border-white/10 pt-6 mt-2">
        <h3 className="text-lg font-semibold mb-4 text-foreground">
          {t(I18nKey.SETTINGS$ADVANCED_LLM_CONFIGURATION)}
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
              <a href="mailto:contact@forge.dev">
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
          value={(
            condenserMaxSize ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE
          )?.toString()}
          onChange={onCondenserMaxSizeChange}
          isDisabled={!enableDefaultCondenser}
        />
        <p className="text-xs text-foreground-secondary mt-1">
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

