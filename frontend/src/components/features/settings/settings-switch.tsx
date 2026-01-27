import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { StyledSwitchComponent } from "./styled-switch-component";

interface SettingsSwitchProps {
  testId?: string;
  name?: string;
  onToggle?: (value: boolean) => void;
  defaultIsToggled?: boolean;
  isToggled?: boolean;
  isBeta?: boolean;
  isDisabled?: boolean;
  tooltip?: string;
}

export function SettingsSwitch({
  children,
  testId,
  name,
  onToggle,
  defaultIsToggled,
  isToggled: controlledIsToggled,
  isBeta,
  isDisabled,
  tooltip,
}: React.PropsWithChildren<SettingsSwitchProps>) {
  const { t } = useTranslation();
  const [isToggled, setIsToggled] = React.useState(defaultIsToggled ?? false);

  const handleToggle = (value: boolean) => {
    setIsToggled(value);
    onToggle?.(value);
  };

  return (
    <label
      className={`flex items-center gap-2 w-fit ${isDisabled ? "cursor-not-allowed" : "cursor-pointer"}`}
      title={tooltip}
    >
      <input
        hidden
        data-testid={testId}
        name={name}
        type="checkbox"
        onChange={(e) => handleToggle(e.target.checked)}
        checked={controlledIsToggled ?? isToggled}
        disabled={isDisabled}
        aria-disabled={isDisabled}
      />

      <StyledSwitchComponent
        isToggled={controlledIsToggled ?? isToggled}
        isDisabled={isDisabled}
      />

      <div className="flex items-center gap-1">
        <span className="text-sm text-foreground">{children}</span>
        {isBeta && (
          <span className="text-[11px] leading-4 text-white font-[500] tracking-tighter bg-brand-500 px-1 rounded-full">
            {t(I18nKey.BADGE$BETA)}
          </span>
        )}
      </div>
    </label>
  );
}
