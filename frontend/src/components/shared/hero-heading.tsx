import { useTranslation } from "react-i18next";
import BuildIt from "#/icons/build-it.svg?react";
import { I18nKey } from "#/i18n/declaration";
import { DOCUMENTATION_URL } from "#/constants/app";

export function HeroHeading() {
  const { t } = useTranslation();
  return (
    <div className="w-full max-w-[520px] sm:min-w-[400px] md:min-w-[450px] lg:min-w-[500px] text-center flex flex-col gap-4 items-center py-4 px-4 mx-auto">
      <BuildIt width={88} height={104} />
      <h1 className="text-[38px] leading-[32px] -tracking-[0.02em] whitespace-normal">
        {t(I18nKey.LANDING$TITLE)}
      </h1>
      <p className="text-sm flex flex-col gap-2 whitespace-normal">
        {t(I18nKey.LANDING$SUBTITLE)}{" "}
        <span>
          {t(I18nKey.LANDING$START_HELP)}{" "}
          <a
            rel="noopener noreferrer"
            target="_blank"
            href={DOCUMENTATION_URL.GETTING_STARTED}
            className="text-white underline underline-offset-[3px]"
          >
            {t(I18nKey.LANDING$START_HELP_LINK)}
          </a>
        </span>
      </p>
    </div>
  );
}

