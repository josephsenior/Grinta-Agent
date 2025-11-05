import { useTranslation } from "react-i18next";
import { cn } from "#/utils/utils";

interface BranchErrorStateProps {
  wrapperClassName?: string;
}

export function BranchErrorState({ wrapperClassName }: BranchErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div
      data-testid="branch-dropdown-error"
      className={cn(
        "flex items-center gap-2 max-w-[500px] h-10 px-3 bg-background-secondary border border-border rounded-sm text-error-500",
        wrapperClassName,
      )}
    >
      <span className="text-sm">{t("HOME$FAILED_TO_LOAD_BRANCHES")}</span>
    </div>
  );
}
