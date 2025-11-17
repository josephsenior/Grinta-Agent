import { Switch } from "@heroui/react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { cn } from "#/utils/utils";

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
    <Switch
      isDisabled={isDisabled}
      name="confirmation-mode"
      defaultSelected={defaultSelected}
      classNames={{
        thumb: cn(
          "bg-foreground-tertiary w-3 h-3",
          "group-data-[selected=true]:bg-white",
        ),
        wrapper: cn(
          "border border-white/10 bg-black/60 px-[6px] w-12 h-6 rounded-xl",
          "group-data-[selected=true]:border-white/20 group-data-[selected=true]:bg-white/20",
        ),
        label: "text-foreground text-xs",
      }}
    >
      {t(I18nKey.SETTINGS_FORM$ENABLE_CONFIRMATION_MODE_LABEL)}
    </Switch>
  );
}
