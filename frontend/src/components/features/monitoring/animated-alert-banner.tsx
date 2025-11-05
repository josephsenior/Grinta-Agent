import React from "react";
import { AlertTriangle, XCircle, AlertCircle, Info } from "lucide-react";

interface Alert {
  id: string;
  severity: "info" | "warning" | "error" | "critical";
  title: string;
  message: string;
  timestamp: string;
}

interface AnimatedAlertBannerProps {
  alerts: Alert[];
  onDismiss?: (id: string) => void;
  className?: string;
}

export function AnimatedAlertBanner({
  alerts,
  onDismiss,
  className = "",
}: AnimatedAlertBannerProps) {
  if (alerts.length === 0) return null;

  const getAlertConfig = (severity: Alert["severity"]) => {
    switch (severity) {
      case "critical":
        return {
          icon: XCircle,
          gradient: "from-red-600/30 via-red-500/20 to-red-600/30",
          border: "border-red-500",
          iconColor: "text-red-400",
          bgPulse: "bg-red-500/10",
          animation: "animate-pulse-fast",
        };
      case "error":
        return {
          icon: AlertCircle,
          gradient: "from-red-500/20 via-red-400/10 to-red-500/20",
          border: "border-red-400",
          iconColor: "text-red-300",
          bgPulse: "bg-red-400/10",
          animation: "animate-pulse",
        };
      case "warning":
        return {
          icon: AlertTriangle,
          gradient: "from-yellow-500/20 via-yellow-400/10 to-yellow-500/20",
          border: "border-yellow-400",
          iconColor: "text-yellow-300",
          bgPulse: "bg-yellow-400/10",
          animation: "animate-pulse-slow",
        };
      case "info":
        return {
          icon: Info,
          gradient: "from-blue-500/20 via-blue-400/10 to-blue-500/20",
          border: "border-blue-400",
          iconColor: "text-blue-300",
          bgPulse: "bg-blue-400/10",
          animation: "",
        };
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {alerts.map((alert) => {
        const config = getAlertConfig(alert.severity);
        const Icon = config.icon;

        return (
          <div
            key={alert.id}
            className={`relative overflow-hidden bg-gradient-to-r ${config.gradient} backdrop-blur-sm border-2 ${config.border} rounded-xl ${config.animation}`}
          >
            {/* Pulsing background layer */}
            <div
              className={`absolute inset-0 ${config.bgPulse} animate-pulse`}
            />

            {/* Animated border glow */}
            <div
              className={`absolute inset-0 bg-gradient-to-r ${config.gradient} opacity-50 animate-border-glow`}
            />

            {/* Content */}
            <div className="relative flex items-start gap-4 p-4">
              {/* Icon */}
              <div className="flex-shrink-0 mt-0.5">
                <Icon className={`w-5 h-5 ${config.iconColor}`} />
              </div>

              {/* Text Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h4 className="text-sm font-semibold text-white">
                    {alert.title}
                  </h4>
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm text-gray-300">{alert.message}</p>
              </div>

              {/* Dismiss Button */}
              {onDismiss && (
                <button
                  onClick={() => onDismiss(alert.id)}
                  className="flex-shrink-0 p-1 rounded-lg hover:bg-white/10 transition-colors"
                  aria-label="Dismiss alert"
                >
                  <XCircle className="w-4 h-4 text-gray-400 hover:text-white" />
                </button>
              )}
            </div>

            {/* Animated shimmer effect for critical alerts */}
            {alert.severity === "critical" && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Add CSS animations
const styles = `
@keyframes pulse-fast {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@keyframes pulse-slow {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.85;
  }
}

@keyframes border-glow {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.6;
  }
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-pulse-fast {
  animation: pulse-fast 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-pulse-slow {
  animation: pulse-slow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-border-glow {
  animation: border-glow 2s ease-in-out infinite;
}

.animate-shimmer {
  animation: shimmer 2s linear infinite;
}
`;

// Inject styles
if (typeof document !== "undefined") {
  const existingStyle = document.getElementById("animated-alert-styles");
  if (!existingStyle) {
    const styleSheet = document.createElement("style");
    styleSheet.id = "animated-alert-styles";
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
  }
}

