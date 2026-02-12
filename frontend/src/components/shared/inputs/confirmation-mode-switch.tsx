import { Switch } from "#/components/ui/switch";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface ConfirmationModeSwitchProps {
  isDisabled: boolean;
  defaultSelected: boolean;
}

export function ConfirmationModeSwitch({
  isDisabled,
  defaultSelected,
}: ConfirmationModeSwitchProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2">
      <Switch
        disabled={isDisabled}
        name="confirmation-mode"
        defaultChecked={defaultSelected}
      />
      <label className="text-foreground text-xs">
        {t(I18nKey.SETTINGS_FORM$ENABLE_CONFIRMATION_MODE_LABEL)}
      </label>
    </div>
  );
}
