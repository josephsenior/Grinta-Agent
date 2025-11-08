import { useTranslation } from "react-i18next";
import { AvailableLanguages } from "#/i18n";
import { I18nKey } from "#/i18n/declaration";
import { SettingsDropdownInput } from "../settings-dropdown-input";

interface LanguageInputProps {
  name: string;
  onChange: (value: string) => void;
  defaultKey: string;
}

export function LanguageInput({
  defaultKey,
  onChange,
  name,
}: LanguageInputProps) {
  const { t } = useTranslation();

  return (
    <SettingsDropdownInput
      testId={name}
      name={name}
      onInputChange={onChange}
      onSelectionChange={(key) => {
        if (typeof key === "string") {
          const selectedLabel =
            AvailableLanguages.find(({ value }) => value === key)?.label || key;
          onChange(selectedLabel);
        }
      }}
      label={t(I18nKey.SETTINGS$LANGUAGE)}
      items={AvailableLanguages.map((l) => ({
        key: l.value,
        label: l.label,
      }))}
      defaultSelectedKey={defaultKey}
      isClearable={false}
      wrapperClassName="w-full max-w-[680px]"
    />
  );
}
