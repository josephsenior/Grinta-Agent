import React from "react";

interface HeaderContentProps {
  maintitle: string;
  subtitle?: string;
}

export function HeaderContent({
  maintitle,
  subtitle = undefined,
}: HeaderContentProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-2xl font-semibold text-foreground leading-tight font-sans">
        {maintitle}
      </h3>
      {subtitle && (
        <p className="text-foreground-secondary text-sm font-normal leading-relaxed">
          {subtitle}
        </p>
      )}
    </div>
  );
}
