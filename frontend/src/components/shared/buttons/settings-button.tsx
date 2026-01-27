import { useTranslation } from "react-i18next";
import ModernSettingsIcon from "#/icons/modern-settings.svg?react";
import { TooltipButton } from "./tooltip-button";
import { I18nKey } from "#/i18n/declaration";

interface SettingsButtonProps {
  onClick?: () => void;
  disabled?: boolean;
}

export function SettingsButton({
  onClick,
  disabled = false,
}: SettingsButtonProps) {
  const { t } = useTranslation();

  // Navigate to app settings
  const settingsPath = "/settings/app";

  return (
    <TooltipButton
      testId="settings-button"
      tooltip={t(I18nKey.SETTINGS$TITLE)}
      ariaLabel={t(I18nKey.SETTINGS$TITLE)}
      onClick={onClick}
      navLinkTo={settingsPath}
      disabled={disabled}
    >
      <ModernSettingsIcon width={24} height={24} />
    </TooltipButton>
  );
}
