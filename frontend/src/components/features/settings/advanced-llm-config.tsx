import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { SettingsInput } from "./settings-input";
import { LLMPreset, LLM_PRESETS, detectPreset } from "#/constants/llm-presets";
import { Settings } from "#/types/settings";
import { PresetSelector } from "./advanced-llm-config/preset-selector";
import { SliderInput } from "./advanced-llm-config/slider-input";
import { SwitchInput } from "./advanced-llm-config/switch-input";

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
      <PresetSelector
        currentPreset={currentPreset}
        onPresetSelect={handlePresetSelect}
      />

      <SliderInput
        name="LLM_TEMPERATURE"
        label={I18nKey.LLM_SETTINGS$TEMPERATURE_LABEL}
        value={settings.LLM_TEMPERATURE ?? 0.1}
        min={0}
        max={2}
        step={0.1}
        helpText={I18nKey.LLM_SETTINGS$TEMPERATURE_HELP}
        onChange={(value) => handleSliderChange("LLM_TEMPERATURE", value)}
      />

      <SliderInput
        name="LLM_TOP_P"
        label={I18nKey.LLM_SETTINGS$TOP_P_LABEL}
        value={settings.LLM_TOP_P ?? 1.0}
        min={0}
        max={1}
        step={0.05}
        helpText={I18nKey.LLM_SETTINGS$TOP_P_HELP}
        onChange={(value) => handleSliderChange("LLM_TOP_P", value)}
      />

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

      <SettingsInput
        testId="timeout-input"
        name="LLM_TIMEOUT"
        label={t(I18nKey.LLM_SETTINGS$TIMEOUT_LABEL)}
        type="number"
        value={settings.LLM_TIMEOUT?.toString() ?? "120"}
        onChange={(v) => handleSliderChange("LLM_TIMEOUT", parseInt(v, 10))}
        helpText={t(I18nKey.LLM_SETTINGS$TIMEOUT_HELP)}
      />

      <SettingsInput
        testId="num-retries-input"
        name="LLM_NUM_RETRIES"
        label={t(I18nKey.LLM_SETTINGS$NUM_RETRIES_LABEL)}
        type="number"
        value={settings.LLM_NUM_RETRIES?.toString() ?? "5"}
        onChange={(v) => handleSliderChange("LLM_NUM_RETRIES", parseInt(v, 10))}
        helpText={t(I18nKey.LLM_SETTINGS$NUM_RETRIES_HELP)}
      />

      <SwitchInput
        testId="caching-prompt-switch"
        label={I18nKey.LLM_SETTINGS$CACHING_PROMPT_LABEL}
        helpText={I18nKey.LLM_SETTINGS$CACHING_PROMPT_HELP}
        value={settings.LLM_CACHING_PROMPT ?? true}
        onChange={(value) => handleSwitchChange("LLM_CACHING_PROMPT", value)}
      />

      <SwitchInput
        testId="disable-vision-switch"
        label={I18nKey.LLM_SETTINGS$DISABLE_VISION_LABEL}
        helpText={I18nKey.LLM_SETTINGS$DISABLE_VISION_HELP}
        value={settings.LLM_DISABLE_VISION ?? false}
        onChange={(value) => handleSwitchChange("LLM_DISABLE_VISION", value)}
      />

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
        placeholder="e.g., anthropic, openai, gemini, xai"
      />

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
