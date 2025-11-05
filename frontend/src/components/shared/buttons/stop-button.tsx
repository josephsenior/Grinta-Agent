import { useTranslation } from "react-i18next";
import ModernStopIcon from "#/icons/modern-stop.svg?react";
import { I18nKey } from "#/i18n/declaration";

interface StopButtonProps {
  isDisabled?: boolean;
  onClick?: () => void;
}

export function StopButton({ isDisabled, onClick }: StopButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      data-testid="stop-button"
      aria-label={t(I18nKey.BUTTON$STOP)}
      disabled={isDisabled}
      onClick={onClick}
      type="button"
      className={`
        relative w-8 h-8 rounded-xl transition-all duration-300 ease-in-out
        flex items-center justify-center cursor-pointer
        bg-gradient-to-br from-danger-500 to-danger-600
        hover:from-danger-400 hover:to-danger-500
        border border-danger-400/30 hover:border-danger-300/50
        shadow-lg hover:shadow-xl shadow-danger-500/25 hover:shadow-danger-500/40
        active:scale-[0.95] hover:scale-[1.02]
        before:absolute before:inset-0 before:rounded-xl
        before:bg-gradient-to-br before:from-white/20 before:to-transparent
        before:opacity-0 hover:before:opacity-100 before:transition-opacity
        disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none
        disabled:hover:scale-100 disabled:bg-grey-600
        disabled:border-grey-500/30
        group
      `}
    >
      <ModernStopIcon className="w-3 h-3 text-white transition-transform duration-200 group-hover:scale-110" />
    </button>
  );
}
