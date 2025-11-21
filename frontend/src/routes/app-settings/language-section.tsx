import React from "react";
import { useTranslation } from "react-i18next";
import { LanguageInput } from "#/components/features/settings/app-settings/language-input";
import { SettingsPanel } from "./settings-panel";

interface LanguageSectionProps {
  language: string;
  onLanguageChange: (key: string) => void;
}

export function LanguageSection({
  language,
  onLanguageChange,
}: LanguageSectionProps) {
  const { t } = useTranslation();

  return (
    <SettingsPanel
      title={t("SETTINGS$LANGUAGE_AND_REGION", "Language & Region")}
    >
      <div className="grid gap-4">
        <div className="w-full">
          <LanguageInput
            name="language-input"
            defaultKey={language}
            onChange={onLanguageChange}
          />
        </div>
      </div>
    </SettingsPanel>
  );
}
