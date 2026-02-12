import { RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { IconButton } from "./icon-button";
import { I18nKey } from "#/i18n/declaration";

interface RefreshIconButtonProps {
  onClick: () => void;
}

export function RefreshIconButton({ onClick }: RefreshIconButtonProps) {
  const { t } = useTranslation();

  return (
    <IconButton
      icon={
        <RefreshCw
          size={16}
          className="text-foreground-secondary hover:text-foreground transition"
        />
      }
      testId="refresh"
      ariaLabel={t("BUTTON$REFRESH" as I18nKey)}
      onClick={onClick}
    />
  );
}
