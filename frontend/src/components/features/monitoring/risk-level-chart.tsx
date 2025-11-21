import React, { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface RiskDataPoint {
  timestamp: string;
  low: number;
  medium: number;
  high: number;
}

interface RiskLevelChartProps {
  data: RiskDataPoint[];
  maxDataPoints?: number;
  className?: string;
}

export function RiskLevelChart({
  data,
  maxDataPoints = 20,
  className = "",
}: RiskLevelChartProps) {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Limit data points
    const displayData = data.slice(-maxDataPoints);
    if (displayData.length < 2) return;

    const padding = { top: 20, right: 20, bottom: 30, left: 40 };
    const chartWidth = rect.width - padding.left - padding.right;
    const chartHeight = rect.height - padding.top - padding.bottom;

    // Calculate max value for scaling
    const maxValue = Math.max(
      ...displayData.flatMap((d) => [d.low, d.medium, d.high]),
      5,
    );

    // Draw grid lines
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) {
      const y = padding.top + (chartHeight / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();

      // Y-axis labels
      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(
        Math.round((maxValue * (4 - i)) / 4).toString(),
        padding.left - 5,
        y + 4,
      );
    }

    // Draw areas (stacked)
    const drawArea = (
      dataKey: "low" | "medium" | "high",
      color: string,
      previousData?: number[],
    ) => {
      const gradient = ctx.createLinearGradient(0, padding.top, 0, rect.height);
      gradient.addColorStop(0, `${color}40`);
      gradient.addColorStop(1, `${color}10`);

      ctx.fillStyle = gradient;
      ctx.beginPath();

      // Draw top line
      displayData.forEach((point, i) => {
        const x = padding.left + (chartWidth / (displayData.length - 1)) * i;
        const value = point[dataKey] + (previousData?.[i] || 0);
        const y = padding.top + chartHeight - (value / maxValue) * chartHeight;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      // Draw bottom line (previous data or baseline)
      for (let i = displayData.length - 1; i >= 0; i -= 1) {
        const x = padding.left + (chartWidth / (displayData.length - 1)) * i;
        const value = previousData?.[i] || 0;
        const y = padding.top + chartHeight - (value / maxValue) * chartHeight;
        ctx.lineTo(x, y);
      }

      ctx.closePath();
      ctx.fill();

      // Draw stroke line
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      displayData.forEach((point, i) => {
        const x = padding.left + (chartWidth / (displayData.length - 1)) * i;
        const value = point[dataKey] + (previousData?.[i] || 0);
        const y = padding.top + chartHeight - (value / maxValue) * chartHeight;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
    };

    // Draw stacked areas
    drawArea("low", "#10b981");
    const lowData = displayData.map((d) => d.low);
    drawArea("medium", "#f59e0b", lowData);
    const lowMediumData = displayData.map((d) => d.low + d.medium);
    drawArea("high", "#ef4444", lowMediumData);

    // Draw X-axis
    ctx.strokeStyle = "#4b5563";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top + chartHeight);
    ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
    ctx.stroke();

    // X-axis labels (show every 5th point)
    ctx.fillStyle = "#9ca3af";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    displayData.forEach((point, i) => {
      if (i % 5 === 0 || i === displayData.length - 1) {
        const x = padding.left + (chartWidth / (displayData.length - 1)) * i;
        const time = new Date(point.timestamp).toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        });
        ctx.fillText(time, x, padding.top + chartHeight + 15);
      }
    });
  }, [data, maxDataPoints]);

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ width: "100%", height: "200px" }}
      />

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-xs text-gray-400">
            {t(I18nKey.MONITORING$LOW_RISK)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="text-xs text-gray-400">
            {t(I18nKey.MONITORING$MEDIUM_RISK)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-xs text-gray-400">
            {t(I18nKey.MONITORING$HIGH_RISK)}
          </span>
        </div>
      </div>
    </div>
  );
}
