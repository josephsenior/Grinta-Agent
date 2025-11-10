import React from "react";
import type { TimeSeriesDataPoint } from "#/types/analytics";

interface CostChartProps {
  data: TimeSeriesDataPoint[];
  title: string;
}

export function CostChart({ data, title }: CostChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="p-6 bg-background-secondary border border-border rounded-lg">
        <h3 className="text-lg font-semibold text-foreground mb-4">{title}</h3>
        <p className="text-sm text-foreground-secondary">No data available</p>
      </div>
    );
  }

  const maxValue = Math.max(...data.map((d) => d.value));
  const minValue = Math.min(...data.map((d) => d.value));
  const range = maxValue - minValue || 1;

  return (
    <div className="p-6 bg-background-secondary border border-border rounded-lg">
      <h3 className="text-lg font-semibold text-foreground mb-6">{title}</h3>

      <div className="relative h-64">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-16 flex flex-col justify-between text-xs text-foreground-secondary">
          <span>${maxValue.toFixed(2)}</span>
          <span>${(maxValue / 2).toFixed(2)}</span>
          <span>$0.00</span>
        </div>

        {/* Chart area */}
        <div className="ml-16 h-full flex items-end gap-1">
          {data.map((point, index) => {
            const height =
              range > 0 ? ((point.value - minValue) / range) * 100 : 0;
            const isHighest = point.value === maxValue;

            return (
              <div
                key={index}
                className="flex-1 group relative"
                title={`${point.label || point.timestamp}: $${point.value.toFixed(2)}`}
              >
                <div
                  className={`w-full rounded-t transition-all ${
                    isHighest
                      ? "bg-brand-500"
                      : "bg-brand-500/60 hover:bg-brand-500/80"
                  }`}
                  style={{ height: `${Math.max(height, 2)}%` }}
                />

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-background-primary border border-border rounded px-2 py-1 text-xs whitespace-nowrap shadow-lg">
                    <div className="text-foreground-secondary">
                      {point.label || point.timestamp}
                    </div>
                    <div className="text-foreground font-semibold">
                      ${point.value.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* X-axis labels */}
        <div className="ml-16 mt-2 flex justify-between text-xs text-foreground-secondary">
          <span>{data[0]?.label || data[0]?.timestamp}</span>
          {data.length > 2 && (
            <span>{data[Math.floor(data.length / 2)]?.label}</span>
          )}
          <span>
            {data[data.length - 1]?.label || data[data.length - 1]?.timestamp}
          </span>
        </div>
      </div>
    </div>
  );
}
