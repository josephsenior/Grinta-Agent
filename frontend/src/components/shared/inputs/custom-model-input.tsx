import { Input } from "#/components/ui/input";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface CustomModelInputProps {
  isDisabled: boolean;
  defaultValue: string;
}

export function CustomModelInput({
  isDisabled,
  defaultValue,
}: CustomModelInputProps) {
  const { t } = useTranslation();

  return (
    <fieldset className="flex flex-col gap-2">
      <label htmlFor="custom-model" className="font-medium text-basic text-xs">
        {t(I18nKey.SETTINGS_FORM$CUSTOM_MODEL_LABEL)}
      </label>
      <Input
        data-testid="custom-model-input"
        disabled={isDisabled}
        required
        id="custom-model"
        name="custom-model"
        defaultValue={defaultValue}
        aria-label={t(I18nKey.MODEL$CUSTOM_MODEL)}
        className="bg-[var(--bg-tertiary)] rounded-md text-sm px-3 py-2.5"
      />
    </fieldset>
  );
}
