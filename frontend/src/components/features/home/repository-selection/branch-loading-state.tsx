import { useTranslation } from "react-i18next";
import { Loader2 } from "lucide-react";
import { cn } from "#/utils/utils";

interface BranchLoadingStateProps {
  wrapperClassName?: string;
}

export function BranchLoadingState({
  wrapperClassName,
}: BranchLoadingStateProps) {
  const { t } = useTranslation();
  return (
    <div
      data-testid="branch-dropdown-loading"
      className={cn(
        "flex items-center gap-2 max-w-[500px] h-10 px-3 bg-background-secondary border border-border rounded-sm",
        wrapperClassName,
      )}
    >
      <Loader2 className="animate-spin h-4 w-4" />
      <span className="text-sm">{t("HOME$LOADING_BRANCHES")}</span>
    </div>
  );
}
