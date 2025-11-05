import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { useVSCodeUrl } from "#/hooks/query/use-vscode-url";
import { VSCODE_IN_NEW_TAB } from "#/utils/feature-flags";

function VSCodeTab() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useVSCodeUrl();
  const isRuntimeInactive = !useRuntimeIsReady();
  const iframeRef = React.useRef<HTMLIFrameElement>(null);
  const [isCrossProtocol, setIsCrossProtocol] = useState(false);
  const [iframeError, setIframeError] = useState<string | null>(null);


  useEffect(() => {
    if (data?.url) {
      try {
        const iframeProtocol = new URL(data.url).protocol;
        const currentProtocol = window.location.protocol;

        // Check if the iframe URL has a different protocol than the current page
        setIsCrossProtocol(
          VSCODE_IN_NEW_TAB() || iframeProtocol !== currentProtocol,
        );
      } catch (e) {
        // Silently handle URL parsing errors
        setIframeError(t("VSCODE$URL_PARSE_ERROR"));
      }
    }
  }, [data?.url]);

  const handleOpenInNewTab = () => {
    if (data?.url) {
      window.open(data.url, "_blank", "noopener,noreferrer");
    }
  };

  if (isRuntimeInactive) {
    return (
      <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
        {t("DIFF_VIEWER$WAITING_FOR_RUNTIME")}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
          <div>{t("VSCODE$LOADING")}</div>
        </div>
      </div>
    );
  }

  if (error || (data && data.error) || !data?.url || iframeError) {
    return (
      <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
        {iframeError ||
          data?.error ||
          String(error) ||
          t(I18nKey.VSCODE$URL_NOT_AVAILABLE)}
      </div>
    );
  }

  // If cross-origin, show a button to open in new tab
  if (isCrossProtocol) {
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

  // If same origin, use the iframe
  return (
    <div className="h-full w-full relative">
      <div className="absolute inset-0 rounded-lg border border-yellow-500/20 shadow-[0_0_12px_rgba(255,200,80,0.15)] pointer-events-none" />
      <iframe
        ref={iframeRef}
        title={t(I18nKey.VSCODE$TITLE)}
        src={data.url}
        className="w-full h-full border-0 rounded-lg bg-[#0b0b0c]"
        allow="clipboard-read; clipboard-write"
      />
    </div>
  );
}

// Export the VSCodeTab directly since we're using the provider at a higher level
export default VSCodeTab;
