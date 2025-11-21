import React from "react";
import { useTranslation } from "react-i18next";

export function RuntimeInactiveView() {
  const { t } = useTranslation();

  return (
    <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
      {t("DIFF_VIEWER$WAITING_FOR_RUNTIME")}
    </div>
  );
}
