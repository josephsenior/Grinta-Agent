import React from "react";
import { useTranslation } from "react-i18next";

interface CrossOriginViewProps {
  url: string;
}

export function CrossOriginView({ url }: CrossOriginViewProps) {
  const { t } = useTranslation();

  const handleOpenInNewTab = () => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-4">
      <div className="text-xl text-foreground-secondary text-center max-w-md">
        {t("VSCODE$CROSS_ORIGIN_WARNING")}
      </div>
      <button
        type="button"
        onClick={handleOpenInNewTab}
        className="px-4 py-2 bg-primary text-white rounded-sm hover:bg-primary-dark transition-colors"
      >
        {t("VSCODE$OPEN_IN_NEW_TAB")}
      </button>
    </div>
  );
}
