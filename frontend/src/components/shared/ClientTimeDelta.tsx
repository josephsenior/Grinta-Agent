import React from "react";
import { formatTimeDelta } from "#/utils/format-time-delta";

interface ClientTimeDeltaProps {
  dateIso: string | Date | null | undefined;
  className?: string;
}

export function ClientTimeDelta({ dateIso, className }: ClientTimeDeltaProps) {
  const [label, setLabel] = React.useState<string | null>(null);

  React.useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;

    if (!dateIso) {
      setLabel("");
      return () => {
        /* no-op cleanup */
      };
    }

    const parsedDate = typeof dateIso === "string" ? new Date(dateIso) : dateIso;
    if (!parsedDate || Number.isNaN(parsedDate.getTime())) {
      setLabel(String(dateIso));
      return () => {
        /* no-op cleanup */
      };
    }

    const calculateLabel = (targetDate: Date) => {
      const diff = Date.now() - targetDate.getTime();
      if (diff < 60_000) {
        return "Just now";
      }
      return formatTimeDelta(targetDate);
    };

    const update = () => {
      setLabel(calculateLabel(parsedDate));
    };

    update();
    intervalId = setInterval(update, 60_000);
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [dateIso]);

  return <span className={className}>{label ?? ""}</span>;
}

export default ClientTimeDelta;
