import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { SettingsInput } from "./settings-input";
import { SettingsSwitch } from "./settings-switch";
import { LLMPreset, LLM_PRESETS, detectPreset } from "#/constants/llm-presets";
import { Settings } from "#/types/settings";

interface AdvancedLLMConfigProps {
  settings: Settings;
  onPresetChange?: (preset: LLMPreset) => void;
  onConfigChange?: (config: Partial<Settings>) => void;
}

export function AdvancedLLMConfig({
  settings,
  onPresetChange,
  onConfigChange,
}: AdvancedLLMConfigProps) {
  const { t } = useTranslation();

  // Detect current preset
  const currentPreset = React.useMemo(
    () =>
      detectPreset({
        temperature: settings.LLM_TEMPERATURE ?? undefined,
        top_p: settings.LLM_TOP_P ?? undefined,
        max_output_tokens: settings.LLM_MAX_OUTPUT_TOKENS ?? undefined,
        timeout: settings.LLM_TIMEOUT ?? undefined,
        num_retries: settings.LLM_NUM_RETRIES ?? undefined,
        caching_prompt: settings.LLM_CACHING_PROMPT ?? undefined,
        disable_vision: settings.LLM_DISABLE_VISION ?? undefined,
      }),
    [settings],
  );

  const handlePresetSelect = (preset: LLMPreset) => {
    if (onPresetChange) {
      onPresetChange(preset);
    }

    if (onConfigChange && preset !== "custom") {
      const presetConfig = LLM_PRESETS[preset];
      onConfigChange({
        LLM_TEMPERATURE: presetConfig.temperature,
        LLM_TOP_P: presetConfig.top_p,
        LLM_MAX_OUTPUT_TOKENS: presetConfig.max_output_tokens,
        LLM_TIMEOUT: presetConfig.timeout,
        LLM_NUM_RETRIES: presetConfig.num_retries,
        LLM_CACHING_PROMPT: presetConfig.caching_prompt,
        LLM_DISABLE_VISION: presetConfig.disable_vision,
      });
    }
  };

  const handleSliderChange = (name: string, value: number) => {
    if (onConfigChange) {
      onConfigChange({ [name]: value });
    }
  };

  const handleSwitchChange = (name: string, value: boolean) => {
    if (onConfigChange) {
      onConfigChange({ [name]: value });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Preset Selector */}
      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-neutral-400">
          {t(I18nKey.LLM_SETTINGS$PRESET_LABEL)}
        </label>
        <div className="grid grid-cols-3 gap-2">
          {(["conservative", "balanced", "creative"] as LLMPreset[]).map(
            (preset) => {
              const presetConfig = LLM_PRESETS[preset];
              const isSelected = currentPreset === preset;

              return (
                <button
                  key={preset}
                  type="button"
                  onClick={() => handlePresetSelect(preset)}
                  className={`
                  flex flex-col items-start p-4 rounded-lg border-2 transition-all
                  ${
                    isSelected
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50"
                  }
                `}
                >
                  <span
                    className={`text-sm font-semibold ${isSelected ? "text-primary" : "text-white"}`}
                  >
                    {presetConfig.name}
                  </span>
                  <span className="text-xs text-neutral-400 mt-1 text-left">
                    {presetConfig.description}
                  </span>
                </button>
              );
            },
          )}
        </div>
        {currentPreset === "custom" && (
          <p className="text-xs text-neutral-400">
            {t(I18nKey.LLM_SETTINGS$CUSTOM_PRESET_INFO)}
          </p>
        )}
      </div>

      {/* Temperature Slider */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium text-neutral-400">
            {t(I18nKey.LLM_SETTINGS$TEMPERATURE_LABEL)}
          </label>
          <span className="text-sm text-white font-mono">
            {settings.LLM_TEMPERATURE ?? 0.1}
          </span>
        </div>
        <input
          type="range"
          name="LLM_TEMPERATURE"
          min="0"
          max="2"
          step="0.1"
          value={settings.LLM_TEMPERATURE ?? 0.1}
          onChange={(e) =>
            handleSliderChange("LLM_TEMPERATURE", parseFloat(e.target.value))
          }
          className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider-thumb"
        />
        <p className="text-xs text-neutral-500">
          {t(I18nKey.LLM_SETTINGS$TEMPERATURE_HELP)}
        </p>
      </div>

      {/* Top P Slider */}
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium text-neutral-400">
            {t(I18nKey.LLM_SETTINGS$TOP_P_LABEL)}
          </label>
          <span className="text-sm text-white font-mono">
            {settings.LLM_TOP_P ?? 1.0}
          </span>
        </div>
        <input
          type="range"
          name="LLM_TOP_P"
          min="0"
          max="1"
          step="0.05"
          value={settings.LLM_TOP_P ?? 1.0}
          onChange={(e) =>
            handleSliderChange("LLM_TOP_P", parseFloat(e.target.value))
          }
          className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider-thumb"
        />
        <p className="text-xs text-neutral-500">
          {t(I18nKey.LLM_SETTINGS$TOP_P_HELP)}
        </p>
      </div>

      {/* Max Output Tokens */}
      <SettingsInput
        testId="max-output-tokens-input"
        name="LLM_MAX_OUTPUT_TOKENS"
        label={t(I18nKey.LLM_SETTINGS$MAX_OUTPUT_TOKENS_LABEL)}
        type="number"
        value={settings.LLM_MAX_OUTPUT_TOKENS?.toString() ?? "4096"}
        onChange={(v) =>
          handleSliderChange("LLM_MAX_OUTPUT_TOKENS", parseInt(v, 10))
        }
        helpText={t(I18nKey.LLM_SETTINGS$MAX_OUTPUT_TOKENS_HELP)}
      />

      {/* Timeout */}
      <SettingsInput
        testId="timeout-input"
        name="LLM_TIMEOUT"
        label={t(I18nKey.LLM_SETTINGS$TIMEOUT_LABEL)}
        type="number"
        value={settings.LLM_TIMEOUT?.toString() ?? "120"}
        onChange={(v) => handleSliderChange("LLM_TIMEOUT", parseInt(v, 10))}
        helpText={t(I18nKey.LLM_SETTINGS$TIMEOUT_HELP)}
      />

      {/* Number of Retries */}
      <SettingsInput
        testId="num-retries-input"
        name="LLM_NUM_RETRIES"
        label={t(I18nKey.LLM_SETTINGS$NUM_RETRIES_LABEL)}
        type="number"
        value={settings.LLM_NUM_RETRIES?.toString() ?? "5"}
        onChange={(v) => handleSliderChange("LLM_NUM_RETRIES", parseInt(v, 10))}
        helpText={t(I18nKey.LLM_SETTINGS$NUM_RETRIES_HELP)}
      />

      {/* Caching Prompt Switch */}
      <div className="flex flex-col gap-2">
        <SettingsSwitch
          testId="caching-prompt-switch"
          isToggled={settings.LLM_CACHING_PROMPT ?? true}
          onToggle={(value) => handleSwitchChange("LLM_CACHING_PROMPT", value)}
        >
          {t(I18nKey.LLM_SETTINGS$CACHING_PROMPT_LABEL)}
        </SettingsSwitch>
        <p className="text-xs text-neutral-500">
          {t(I18nKey.LLM_SETTINGS$CACHING_PROMPT_HELP)}
        </p>
      </div>

      {/* Disable Vision Switch */}
      <div className="flex flex-col gap-2">
        <SettingsSwitch
          testId="disable-vision-switch"
          isToggled={settings.LLM_DISABLE_VISION ?? false}
          onToggle={(value) => handleSwitchChange("LLM_DISABLE_VISION", value)}
        >
          {t(I18nKey.LLM_SETTINGS$DISABLE_VISION_LABEL)}
        </SettingsSwitch>
        <p className="text-xs text-neutral-500">
          {t(I18nKey.LLM_SETTINGS$DISABLE_VISION_HELP)}
        </p>
      </div>

      {/* Custom LLM Provider (Advanced) */}
      <SettingsInput
        testId="custom-provider-input"
        name="LLM_CUSTOM_LLM_PROVIDER"
        label={t(I18nKey.LLM_SETTINGS$CUSTOM_PROVIDER_LABEL)}
        type="text"
        value={settings.LLM_CUSTOM_LLM_PROVIDER ?? ""}
        onChange={(v) =>
          onConfigChange?.({ LLM_CUSTOM_LLM_PROVIDER: v || null })
        }
        helpText={t(I18nKey.LLM_SETTINGS$CUSTOM_PROVIDER_HELP)}
        placeholder="e.g., anthropic, openai, azure"
      />

      {/* Info about autonomy settings location */}
      <div className="border-t border-border pt-6">
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
              <span className="text-blue-400 text-sm">ℹ️</span>
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-blue-400 mb-1">
                Autonomy Mode Settings Moved
              </h4>
              <p className="text-xs text-blue-300/80">
                For better UX, autonomy mode settings are now available directly
                in the chat interface. Look for the mode selector button (🛡️
                Supervised / 👁️ Balanced / ⚡ Full Autonomous) in the top
                control bar when chatting with the agent. You can also use the
                keyboard shortcut
                <kbd className="mx-1 px-1.5 py-0.5 bg-blue-500/20 rounded text-blue-300 text-[10px]">
                  Ctrl+Shift+A
                </kbd>
                to cycle through modes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
