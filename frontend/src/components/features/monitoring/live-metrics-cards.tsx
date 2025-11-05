import React from "react";
import {
  Activity,
  AlertCircle,
  TrendingUp,
  Zap,
  Clock,
  Shield,
} from "lucide-react";

interface MetricsData {
  errorRate: number; // 0-100
  highRiskActions: number;
  progress: number; // 0-100
  iterationsPerMinute: number;
  avgResponseTime: number; // in ms
  securityScore: number; // 0-100
}

interface LiveMetricsCardsProps {
  metrics: MetricsData;
  className?: string;
}

export function LiveMetricsCards({
  metrics,
  className = "",
}: LiveMetricsCardsProps) {
  const cards = [
    {
      icon: AlertCircle,
      label: "Error Rate",
      value: `${metrics.errorRate.toFixed(1)}%`,
      trend: metrics.errorRate > 10 ? "danger" : "success",
      color: metrics.errorRate > 10 ? "red" : "green",
      gradient: "from-red-500/20 to-red-600/5",
    },
    {
      icon: Shield,
      label: "High-Risk Actions",
      value: metrics.highRiskActions.toString(),
      trend: metrics.highRiskActions > 5 ? "warning" : "success",
      color: metrics.highRiskActions > 5 ? "yellow" : "green",
      gradient: "from-yellow-500/20 to-yellow-600/5",
    },
    {
      icon: TrendingUp,
      label: "Progress",
      value: `${metrics.progress.toFixed(0)}%`,
      trend: metrics.progress > 50 ? "success" : "info",
      color: "blue",
      gradient: "from-blue-500/20 to-blue-600/5",
    },
    {
      icon: Zap,
      label: "Iterations/Min",
      value: metrics.iterationsPerMinute.toFixed(1),
      trend: "info",
      color: "purple",
      gradient: "from-purple-500/20 to-purple-600/5",
    },
    {
      icon: Clock,
      label: "Avg Response",
      value: `${(metrics.avgResponseTime / 1000).toFixed(1)}s`,
      trend: "info",
      color: "cyan",
      gradient: "from-cyan-500/20 to-cyan-600/5",
    },
    {
      icon: Activity,
      label: "Security Score",
      value: `${metrics.securityScore.toFixed(0)}%`,
      trend: metrics.securityScore >= 80 ? "success" : "warning",
      color: metrics.securityScore >= 80 ? "green" : "yellow",
      gradient:
        metrics.securityScore >= 80
          ? "from-green-500/20 to-green-600/5"
          : "from-yellow-500/20 to-yellow-600/5",
    },
  ];

  return (
    <div
      className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 ${className}`}
    >
      {cards.map((card, index) => {
        const Icon = card.icon;
        const iconColorClass = `text-${card.color}-400`;
        const borderColorClass = `border-${card.color}-500/30`;

        return (
          <div
            key={index}
            className={`relative overflow-hidden bg-gradient-to-br ${card.gradient} backdrop-blur-sm border ${borderColorClass} rounded-xl p-4 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-${card.color}-500/20`}
          >
            {/* Background glow effect */}
            <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-2xl" />

            {/* Content */}
            <div className="relative">
              <div className="flex items-center justify-between mb-2">
                <Icon className={`w-4 h-4 ${iconColorClass}`} />
                {card.trend === "danger" && (
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                )}
                {card.trend === "warning" && (
                  <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                )}
                {card.trend === "success" && (
                  <div className="w-2 h-2 bg-green-500 rounded-full" />
                )}
              </div>

              <div className="text-2xl font-bold text-white mb-1 transition-all duration-300">
                {card.value}
              </div>

              <div className="text-xs text-gray-400 font-medium">
                {card.label}
              </div>
            </div>

            {/* Shine effect on hover */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
          </div>
        );
      })}
    </div>
  );
}

