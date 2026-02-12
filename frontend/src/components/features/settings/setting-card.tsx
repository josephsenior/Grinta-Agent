import React from "react";
import { cn } from "#/utils/utils";

interface SettingCardProps {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
}

export function SettingCard({
  title,
  description,
  icon: Icon,
  children,
  className,
}: SettingCardProps) {
  return (
    <div
      className={cn(
        "bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-5 transition-all duration-200 hover:border-[var(--border-accent)]/30",
        className,
      )}
    >
      <div className="flex items-start gap-3 mb-4">
        {Icon && (
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
            <Icon className="w-5 h-5 text-[var(--text-accent)]" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-[var(--text-primary)] mb-1">
            {title}
          </h3>
          {description && (
            <p className="text-sm text-[var(--text-tertiary)] leading-relaxed">
              {description}
            </p>
          )}
        </div>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
