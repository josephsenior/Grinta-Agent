import React from "react";

interface ClientNumberProps {
  value: number | null | undefined;
  locale?: string;
  options?: Intl.NumberFormatOptions;
  className?: string;
}

/**
 * Render a number formatted with Intl.NumberFormat on the client.
 * During SSR it renders the raw number to keep server output stable.
 */
export function ClientNumber({
  value,
  locale,
  options,
  className,
}: ClientNumberProps) {
  const [formatted, setFormatted] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      setFormatted("");
      return;
    }

    try {
      const nf = new Intl.NumberFormat(locale ?? undefined, options);
      setFormatted(nf.format(Number(value)));
    } catch (e) {
      setFormatted(String(value));
    }
  }, [value, locale, JSON.stringify(options)]);

  return <span className={className}>{formatted ?? value ?? ""}</span>;
}

export default ClientNumber;
