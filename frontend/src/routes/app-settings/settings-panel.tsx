import React from "react";

interface SettingsPanelProps {
  title: string;
  children: React.ReactNode;
}

export function SettingsPanel({ title, children }: SettingsPanelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}
