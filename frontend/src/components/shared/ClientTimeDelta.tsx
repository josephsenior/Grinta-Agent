import React from "react";

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

    const d = typeof dateIso === "string" ? new Date(dateIso) : dateIso;
    if (!d || Number.isNaN(d.getTime())) {
      setLabel(String(dateIso));
      return () => {
        /* no-op cleanup */
      };
    }

    const update = () => {
      const now = new Date();
      const diff = now.getTime() - d.getTime();
      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);
      const days = Math.floor(hours / 24);

      if (seconds < 60) setLabel("Just now");
      else if (minutes < 60) setLabel(`${minutes}m ago`);
      else if (hours < 24) setLabel(`${hours}h ago`);
      else if (days < 7) setLabel(`${days}d ago`);
      else setLabel(d.toLocaleDateString());
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
