import React from "react";

interface ClientFormattedDateProps {
  iso: string | null | undefined;
  locale?: string;
  options?: Intl.DateTimeFormatOptions;
  fallback?: string;
  className?: string;
}

/**
 * Render a date string formatted using the user's locale on the client.
 * During SSR this renders the raw ISO (or provided fallback) so the server
 * output is stable and we avoid hydration mismatches. The localized string
 * is applied in a useEffect after hydration.
 */
export function ClientFormattedDate({
  iso,
  locale,
  options,
  fallback,
  className,
}: ClientFormattedDateProps) {
  const [formatted, setFormatted] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!iso) {
      setFormatted(fallback ?? "");
      return;
    }

    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) {
        setFormatted(fallback ?? String(iso));
        return;
      }

      const nf = new Intl.DateTimeFormat(locale ?? undefined, options);
      setFormatted(nf.format(d));
    } catch (e) {
      // Fall back to the raw string if anything goes wrong
      setFormatted(fallback ?? String(iso));
    }
  }, [iso, locale, JSON.stringify(options), fallback]);

  // Render the raw ISO on the server / initial render to keep SSR stable.
  const initial = iso ?? fallback ?? "";

  return <span className={className}>{formatted ?? initial}</span>;
}

export default ClientFormattedDate;
