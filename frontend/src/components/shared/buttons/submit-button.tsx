import { useTranslation } from "react-i18next";
import ModernSendIcon from "#/icons/modern-send.svg?react";
import { I18nKey } from "#/i18n/declaration";

interface SubmitButtonProps {
  isDisabled?: boolean;
  onClick: () => void;
}

export function SubmitButton({ isDisabled, onClick }: SubmitButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      aria-label={t(I18nKey.BUTTON$SEND)}
      disabled={isDisabled}
      onClick={onClick}
      type="submit"
      className={`
        relative w-8 h-8 rounded-xl transition-all duration-300 ease-in-out
        flex items-center justify-center cursor-pointer
        bg-gradient-to-br from-primary-500 to-primary-600
        hover:from-primary-400 hover:to-primary-500
        border border-primary-400/30 hover:border-primary-300/50
        shadow-lg hover:shadow-xl shadow-primary-500/25 hover:shadow-primary-500/40
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
      <ModernSendIcon className="w-4 h-4 text-white transition-transform duration-200 group-hover:translate-x-0.5" />
    </button>
  );
}
