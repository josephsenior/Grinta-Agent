import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { getRandomTip, type Tip } from "#/utils/tips";

export function RandomTip() {
  const { t } = useTranslation();
  // Avoid SSR hydration mismatches: don't call Math.random() during initial render.
  const [randomTip, setRandomTip] = React.useState<Tip | null>(null);

  // Allow disabling tips via Vite env var (see .env.sample VITE_HIDE_TIPS)
  // import.meta.env values are strings; treat "true" (case-insensitive) as enabled hide
  const hideTips = React.useMemo(() => {
    type MaybeImportMeta = { env?: Record<string, unknown> } | undefined;
    const meta =
      typeof import.meta !== "undefined"
        ? (import.meta as MaybeImportMeta)
        : undefined;
    return (
      String(meta?.env?.VITE_HIDE_TIPS || "false").toLowerCase() === "true"
    );
  }, []);

  React.useEffect(() => {
    if (!hideTips) {
      setRandomTip(getRandomTip());
    }
  }, [hideTips]);

  if (hideTips) {
    return null;
  }

  return (
    <div>
      <h4 className="font-bold">{t(I18nKey.TIPS$PROTIP)}:</h4>
      {randomTip ? (
        <p>
          {t(randomTip.key)}{" "}
          {randomTip.link && (
            <a
              href={randomTip.link}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              {t(I18nKey.TIPS$LEARN_MORE)}
            </a>
          )}
        </p>
      ) : null}
    </div>
  );
}
