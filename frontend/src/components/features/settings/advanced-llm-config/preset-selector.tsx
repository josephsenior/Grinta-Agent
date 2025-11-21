import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { LLMPreset, LLM_PRESETS } from "#/constants/llm-presets";

interface PresetSelectorProps {
  currentPreset: LLMPreset;
  onPresetSelect: (preset: LLMPreset) => void;
}

export function PresetSelector({
  currentPreset,
  onPresetSelect,
}: PresetSelectorProps) {
  const { t } = useTranslation();

  return (
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
                onClick={() => onPresetSelect(preset)}
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
  );
}
