import { Lock } from "lucide-react";
import { Tooltip } from "#/components/ui/tooltip";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { I18nKey } from "#/i18n/declaration";

export function SecurityLock() {
  const { t } = useTranslation();

  return (
    <Tooltip
      content={
        <div className="max-w-xs p-2">
          {t(I18nKey.SETTINGS$CONFIRMATION_MODE_LOCK_TOOLTIP)}
        </div>
      }
      placement="top"
    >
      <Link
        to="/settings"
        className="mr-2 cursor-pointer hover:opacity-80 transition-all"
        aria-label={t(I18nKey.SETTINGS$TITLE)}
      >
        <Lock size={20} />
      </Link>
    </Tooltip>
  );
}
