import React from "react";
import { useTranslation } from "react-i18next";

export function LoadingView() {
  const { t } = useTranslation();

  return (
    <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        <div>{t("VSCODE$LOADING")}</div>
      </div>
    </div>
  );
}
