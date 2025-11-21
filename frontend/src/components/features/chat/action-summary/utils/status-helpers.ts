import { Check, AlertCircle, Loader2, LucideIcon } from "lucide-react";
import { ForgeEvent } from "#/types/core/base";
import { isErrorObservation } from "#/types/core/guards";

interface StatusConfig {
  icon: LucideIcon;
  color: string;
  shouldAnimate: boolean;
}

export function getStatusConfig(
  event: ForgeEvent,
  isLast: boolean,
): StatusConfig {
  const isError = isErrorObservation(event);

  if (isError) {
    return {
      icon: AlertCircle,
      color: "text-danger",
      shouldAnimate: false,
    };
  }

  if (!isLast) {
    return {
      icon: Check,
      color: "text-success-400",
      shouldAnimate: false,
    };
  }

  return {
    icon: Loader2,
    color: "text-violet-400",
    shouldAnimate: true,
  };
}
