import React from "react";
import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";
import { LanguageInput } from "#/components/features/settings/app-settings/language-input";
import { Accordion } from "#/components/features/settings/accordion";

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
    <Accordion
      title={t("SETTINGS$LANGUAGE_AND_REGION", "Language & Region")}
      icon={Languages}
      defaultOpen
    >
      <div className="w-full">
        <LanguageInput
          name="language-input"
          defaultKey={language}
          onChange={onLanguageChange}
        />
      </div>
    </Accordion>
  );
}
