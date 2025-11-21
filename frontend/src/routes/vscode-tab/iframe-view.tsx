import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface IframeViewProps {
  url: string;
}

export function IframeView({ url }: IframeViewProps) {
  const { t } = useTranslation();
  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  return (
    <div className="h-full w-full relative">
      <div className="absolute inset-0 rounded-lg border border-yellow-500/20 shadow-[0_0_12px_rgba(255,200,80,0.15)] pointer-events-none" />
      <iframe
        ref={iframeRef}
        title={t(I18nKey.VSCODE$TITLE)}
        src={url}
        className="w-full h-full border-0 rounded-lg bg-[#0b0b0c]"
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
}
