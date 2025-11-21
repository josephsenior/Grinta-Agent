import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface SliderInputProps {
  name: string;
  label: I18nKey;
  value: number;
  min: number;
  max: number;
  step: number;
  helpText: I18nKey;
  onChange: (value: number) => void;
}

export function SliderInput({
  name,
  label,
  value,
  min,
  max,
  step,
  helpText,
  onChange,
}: SliderInputProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-neutral-400">
          {t(label)}
        </label>
        <span className="text-sm text-white font-mono">{value}</span>
      </div>
      <input
        type="range"
        name={name}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer slider-thumb"
      />
      <p className="text-xs text-neutral-500">{t(helpText)}</p>
    </div>
  );
}
