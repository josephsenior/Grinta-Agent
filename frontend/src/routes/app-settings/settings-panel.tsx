import React from "react";

interface SettingsPanelProps {
  title: string;
  children: React.ReactNode;
}

export function SettingsPanel({ title, children }: SettingsPanelProps) {
  const panelClass =
    "relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/80 backdrop-blur-xl p-6 shadow-[0_40px_120px_rgba(0,0,0,0.45)]";

  return (
    <div className={panelClass}>
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute inset-y-0 left-1/2 w-1/2 bg-gradient-to-r from-brand-500/5 via-accent-500/3 to-transparent blur-2xl" />
      </div>
      <div className="relative z-[1]">
        <h2 className="text-xl font-semibold text-foreground mb-6 w-full">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
