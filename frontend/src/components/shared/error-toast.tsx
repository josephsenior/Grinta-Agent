import type { Toast } from "react-hot-toast";
import { useTranslation } from "react-i18next";
import safeToast from "#/utils/safe-hot-toast";
import { I18nKey } from "#/i18n/declaration";

interface ErrorToastProps {
  id: Toast["id"];
  error: string;
}

export function ErrorToast({ id, error }: ErrorToastProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-between w-full p-4 bg-gradient-to-br from-danger-500/90 to-danger-600/95 backdrop-blur-xl border border-danger-400/30 rounded-xl shadow-lg text-white">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
        <span className="font-medium text-sm leading-relaxed">{error}</span>
      </div>
      <button
        type="button"
        onClick={() => safeToast.dismiss(id)}
        className={`
          px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200
          bg-white/20 hover:bg-white/30 backdrop-blur-sm
          border border-white/30 hover:border-white/50
          active:scale-95 flex-shrink-0 ml-4
        `}
      >
        {t(I18nKey.ERROR_TOAST$CLOSE_BUTTON_LABEL)}
      </button>
    </div>
  );
}
