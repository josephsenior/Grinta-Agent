import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { VSCODE_IN_NEW_TAB } from "#/utils/feature-flags";

export function useVSCodeProtocol(url: string | undefined) {
  const { t } = useTranslation();
  const [isCrossProtocol, setIsCrossProtocol] = useState(false);
  const [iframeError, setIframeError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;

    try {
      const iframeProtocol = new URL(url).protocol;
      const currentProtocol = window.location.protocol;

      setIsCrossProtocol(
        VSCODE_IN_NEW_TAB() || iframeProtocol !== currentProtocol,
      );
    } catch (e) {
      setIframeError(t("VSCODE$URL_PARSE_ERROR"));
    }
  }, [url, t]);

  return { isCrossProtocol, iframeError };
}
