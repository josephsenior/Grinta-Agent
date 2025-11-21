import React from "react";
import { useTranslation } from "react-i18next";
import { Shield, AlertTriangle, X } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";

interface BlockedCommand {
  id: string;
  timestamp: string;
  command: string;
  reason: string;
  riskLevel: "HIGH" | "CRITICAL";
  patterns: string[];
}

interface CommandBlockingCardProps {
  blockedCommands: BlockedCommand[];
  className?: string;
}

export function CommandBlockingCard({
  blockedCommands,
  className = "",
}: CommandBlockingCardProps) {
  const { t } = useTranslation();
  if (blockedCommands.length === 0) {
    return (
      <div
        className={`bg-gray-800/50 border border-gray-700 rounded-xl p-6 ${className}`}
      >
        <div className="flex items-center justify-center gap-3 text-green-400">
          <Shield className="w-5 h-5" />
          <p className="text-sm font-medium">
            {t(I18nKey.MONITORING$NO_BLOCKED_COMMANDS)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-red-400" />
        <h3 className="text-sm font-semibold text-white">
          {t(I18nKey.MONITORING$BLOCKED_COMMANDS_COUNT, {
            count: blockedCommands.length,
          })}
        </h3>
      </div>

      <div className="space-y-3 max-h-64 overflow-y-auto">
        {blockedCommands.map((cmd) => (
          <div
            key={cmd.id}
            className="bg-gradient-to-r from-red-500/10 to-red-600/5 border border-red-500/30 rounded-lg p-4 animate-pulse-subtle"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <X className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    cmd.riskLevel === "CRITICAL"
                      ? "bg-red-600 text-white"
                      : "bg-red-500/20 text-red-300"
                  }`}
                >
                  {cmd.riskLevel}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(cmd.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* Command */}
            <div className="mb-3">
              <p className="text-xs text-gray-400 mb-1">
                {t(I18nKey.MONITORING$BLOCKED_COMMAND)}
              </p>
              <code className="block text-xs font-mono bg-black/40 text-red-300 p-2 rounded border border-red-500/20 break-all">
                {cmd.command}
              </code>
            </div>

            {/* Reason */}
            <div className="mb-3">
              <p className="text-xs text-gray-400 mb-1">
                {t(I18nKey.MONITORING$REASON)}
              </p>
              <p className="text-xs text-gray-200">{cmd.reason}</p>
            </div>

            {/* Matched Patterns */}
            {cmd.patterns.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-1">
                  {t(I18nKey.MONITORING$MATCHED_PATTERNS)}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {cmd.patterns.map((pattern, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 bg-red-500/10 text-red-300 rounded border border-red-500/20 font-mono"
                    >
                      {pattern}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Add CSS for pulse animation
const styles = `
@keyframes pulse-subtle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.9;
  }
}

.animate-pulse-subtle {
  animation: pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
`;

// Inject styles
if (typeof document !== "undefined") {
  const styleSheet = document.createElement("style");
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
}
