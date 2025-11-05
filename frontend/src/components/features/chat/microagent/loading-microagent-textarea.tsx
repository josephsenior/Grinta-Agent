import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";

export function LoadingMicroagentTextarea() {
  const { t } = useTranslation();

  return (
    <textarea
      required
      disabled
      defaultValue=""
      placeholder={t("MICROAGENT$LOADING_PROMPT")}
      rows={6}
      className={cn(
        "bg-background-glass backdrop-blur-xl border border-border-glass w-full rounded-xl p-3 placeholder:italic placeholder:text-text-foreground-secondary text-text-primary resize-none transition-all duration-200 focus:border-primary-500/50 focus:bg-primary-500/5 focus:shadow-lg focus:shadow-primary-500/10",
        "disabled:bg-background-surface disabled:border-border-subtle disabled:cursor-not-allowed disabled:opacity-50",
      )}
    />
  );
}
