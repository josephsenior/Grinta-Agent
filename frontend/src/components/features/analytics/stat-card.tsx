import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
  subtitle?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  subtitle,
}: StatCardProps) {
  const getTrendColor = () => {
    if (!trend) return "text-foreground-secondary";
    if (trend.value > 0) return "text-success-500";
    if (trend.value < 0) return "text-error-500";
    return "text-foreground-secondary";
  };
  const trendColor = getTrendColor();

  return (
    <div className="p-6 bg-background-secondary border border-border rounded-lg hover:border-brand-500/50 transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-brand-500/10 rounded-lg">
          <Icon className="w-6 h-6 text-violet-500" />
        </div>
        {trend && (
          <div className={`text-sm font-medium ${trendColor}`}>
            {trend.value > 0 ? "+" : ""}
            {trend.value.toFixed(1)}%
            <div className="text-xs text-foreground-secondary mt-0.5">
              {trend.label}
            </div>
          </div>
        )}
      </div>

      <h3 className="text-sm font-medium text-foreground-secondary mb-1">
        {title}
      </h3>
      <p className="text-3xl font-bold text-foreground mb-1">{value}</p>
      {subtitle && (
        <p className="text-xs text-foreground-secondary">{subtitle}</p>
      )}
    </div>
  );
}
