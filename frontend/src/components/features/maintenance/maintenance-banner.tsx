import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { isBefore } from "date-fns";
import { useLocalStorage } from "@uidotdev/usehooks";
import { FaTriangleExclamation } from "react-icons/fa6";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import CloseIcon from "#/icons/close.svg?react";
import { cn } from "#/utils/utils";

interface MaintenanceBannerProps {
  startTime: string;
}

export function MaintenanceBanner({ startTime }: MaintenanceBannerProps) {
  const { t } = useTranslation();
  const [dismissedAt, setDismissedAt] = useLocalStorage<string | null>(
    "maintenance_banner_dismissed_at",
    null,
  );

  // Convert EST timestamp to user's local timezone
  // We format on the client to avoid SSR mismatch. Validation remains the same.
  const formatMaintenanceTime = (estTimeString: string): string => {
    const date = new Date(estTimeString);
    if (Number.isNaN(date.getTime())) {
      throw new Error("Invalid date");
    }

    // Return ISO here; the UI will render ClientFormattedDate when needed.
    return estTimeString;
  };

  // Determine visibility before attempting to format the time to avoid
  // emitting console warnings during render for invalid input.
  const isBannerVisible = useMemo(() => {
    const isValid = !Number.isNaN(new Date(startTime).getTime());
    if (!isValid) {
      return false;
    }
    return dismissedAt
      ? isBefore(new Date(dismissedAt), new Date(startTime))
      : true;
  }, [dismissedAt, startTime]);

  if (!isBannerVisible) {
    return null;
  }

  // Only compute the raw ISO; the rendered component will format it on the client.
  let localTime: string;
  try {
    localTime = formatMaintenanceTime(startTime);
  } catch (err) {
    localTime = startTime;
  }

  if (!isBannerVisible) {
    return null;
  }

  return (
    <div
      data-testid="maintenance-banner"
      className={cn(
        "bg-primary text-[#0D0F11] p-4 rounded",
        "flex flex-row items-center justify-between",
      )}
    >
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <FaTriangleExclamation className="text-white align-middle" />
        </div>
        <div className="ml-3">
          <p className="text-sm font-medium">
            {t("MAINTENANCE$SCHEDULED_MESSAGE", {
              // Inject the client-formatted element. Translation strings that
              // expect a plain string should continue to work because during
              // SSR the ISO will be used.
              time: (
                <ClientFormattedDate
                  iso={localTime}
                  options={{
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    timeZoneName: "short",
                  }}
                />
              ),
            })}
          </p>
        </div>
      </div>

      <button
        type="button"
        data-testid="dismiss-button"
        onClick={() => {
          try {
            const iso = new Date(startTime).toISOString();
            setDismissedAt(iso);
          } catch (e) {
            // Fallback to storing the raw startTime if parsing fails
            setDismissedAt(startTime);
          }
        }}
        className={cn(
          "bg-[#0D0F11] rounded-full w-5 h-5 flex items-center justify-center cursor-pointer",
        )}
      >
        <CloseIcon />
      </button>
    </div>
  );
}
