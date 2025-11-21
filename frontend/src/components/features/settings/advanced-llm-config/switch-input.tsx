import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { SettingsSwitch } from "../settings-switch";

interface SwitchInputProps {
  testId: string;
  label: I18nKey;
  helpText: I18nKey;
  value: boolean;
  onChange: (value: boolean) => void;
}

export function SwitchInput({
  testId,
  label,
  helpText,
  value,
  onChange,
}: SwitchInputProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2">
      <SettingsSwitch testId={testId} isToggled={value} onToggle={onChange}>
        {t(label)}
      </SettingsSwitch>
      <p className="text-xs text-neutral-500">{t(helpText)}</p>
    </div>
  );
}
