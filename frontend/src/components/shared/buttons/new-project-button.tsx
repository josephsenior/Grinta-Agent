import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import ModernPlusIcon from "#/icons/modern-plus.svg?react";
import { TooltipButton } from "./tooltip-button";

interface NewProjectButtonProps {
  disabled?: boolean;
}

export function NewProjectButton({ disabled = false }: NewProjectButtonProps) {
  const { t } = useTranslation();
  const startNewProject = t(I18nKey.CONVERSATION$START_NEW);
  return (
    <TooltipButton
      tooltip={startNewProject}
      ariaLabel={startNewProject}
      navLinkTo="/"
      testId="new-project-button"
      disabled={disabled}
    >
      <ModernPlusIcon width={24} height={24} />
    </TooltipButton>
  );
}
