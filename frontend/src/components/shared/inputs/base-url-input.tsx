import { Input } from "#/components/ui/input";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface BaseUrlInputProps {
  isDisabled: boolean;
  defaultValue: string;
}

export function BaseUrlInput({ isDisabled, defaultValue }: BaseUrlInputProps) {
  const { t } = useTranslation();

  return (
    <fieldset className="flex flex-col gap-2">
      <label htmlFor="base-url" className="font-[500] text-basic text-xs">
        {t(I18nKey.SETTINGS_FORM$BASE_URL_LABEL)}
      </label>
      <Input
        disabled={isDisabled}
        id="base-url"
        name="base-url"
        defaultValue={defaultValue}
        aria-label={t(I18nKey.SETTINGS_FORM$BASE_URL)}
        className="bg-[var(--bg-tertiary)] rounded-md text-sm px-3 py-2.5"
      />
    </fieldset>
  );
}
