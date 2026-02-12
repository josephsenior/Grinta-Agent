import { Switch } from "#/components/ui/switch";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface AdvancedOptionSwitchProps {
  isDisabled: boolean;
  showAdvancedOptions: boolean;
  setShowAdvancedOptions: (value: boolean) => void;
}

export function AdvancedOptionSwitch({
  isDisabled,
  showAdvancedOptions,
  setShowAdvancedOptions,
}: AdvancedOptionSwitchProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2">
      <Switch
        data-testid="advanced-option-switch"
        disabled={isDisabled}
        name="use-advanced-options"
        defaultChecked={showAdvancedOptions}
        onCheckedChange={setShowAdvancedOptions}
      />
      <label className="text-basic text-xs">
        {t(I18nKey.SETTINGS_FORM$ADVANCED_OPTIONS_LABEL)}
      </label>
    </div>
  );
}
