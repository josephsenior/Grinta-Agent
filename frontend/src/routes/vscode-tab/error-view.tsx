import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface ErrorViewProps {
  error?: unknown;
  dataError?: string;
  iframeError?: string | null;
}

export function ErrorView({ error, dataError, iframeError }: ErrorViewProps) {
  const { t } = useTranslation();

  const errorMessage =
    iframeError ||
    dataError ||
    (error ? String(error) : null) ||
    t(I18nKey.VSCODE$URL_NOT_AVAILABLE);

  return (
    <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
      {errorMessage}
    </div>
  );
}
