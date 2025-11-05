import React, { useState } from "react";
import { ChevronDown, ChevronRight, Shield, AlertTriangle } from "lucide-react";

interface AuditEntry {
  id: string;
  timestamp: string;
  iteration: number;
  action_type: string;
  action_content: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
  validation_result: string;
  blocked_reason?: string;
  matched_risk_patterns: string[];
}

interface EnhancedAuditTrailProps {
  entries: AuditEntry[];
  className?: string;
}

export function EnhancedAuditTrail({
  entries,
  className = "",
}: EnhancedAuditTrailProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getRiskConfig = (level: string) => {
    switch (level) {
      case "HIGH":
        return {
          bg: "bg-red-500/20",
          text: "text-red-400",
          border: "border-red-500/40",
          icon: AlertTriangle,
        };
      case "MEDIUM":
        return {
          bg: "bg-yellow-500/20",
          text: "text-yellow-400",
          border: "border-yellow-500/40",
          icon: AlertTriangle,
        };
      case "LOW":
        return {
          bg: "bg-green-500/20",
          text: "text-green-400",
          border: "border-green-500/40",
          icon: Shield,
        };
      default:
        return {
          bg: "bg-gray-500/20",
          text: "text-gray-400",
          border: "border-gray-500/40",
          icon: Shield,
        };
    }
  };

  if (entries.length === 0) {
    return (
      <div className={`text-center text-gray-400 py-8 ${className}`}>
        No audit entries yet
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {entries.map((entry) => {
        const isExpanded = expandedRows.has(entry.id);
        const riskConfig = getRiskConfig(entry.risk_level);
        const RiskIcon = riskConfig.icon;
        const isBlocked = entry.validation_result === "blocked";

        return (
          <div
            key={entry.id}
            className={`bg-gray-800/50 border ${
              isBlocked ? "border-red-500/40" : "border-gray-700"
            } rounded-lg overflow-hidden transition-all duration-300 hover:bg-gray-800/70`}
          >
            {/* Main Row - Always visible */}
            <div
              className="flex items-center gap-3 p-3 cursor-pointer"
              onClick={() => toggleRow(entry.id)}
            >
              {/* Expand Icon */}
              <div className="flex-shrink-0">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </div>

              {/* Iteration */}
              <div className="flex-shrink-0 w-12 text-center">
                <span className="text-xs font-mono text-gray-400">
                  #{entry.iteration}
                </span>
              </div>

              {/* Action Type */}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-mono text-gray-300 truncate block">
                  {entry.action_type}
                </span>
              </div>

              {/* Risk Badge */}
              <div className="flex-shrink-0">
                <span
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${riskConfig.bg} ${riskConfig.text} border ${riskConfig.border}`}
                >
                  <RiskIcon className="w-3 h-3" />
                  {entry.risk_level}
                </span>
              </div>

              {/* Result Badge */}
              <div className="flex-shrink-0">
                <span
                  className={`px-2 py-1 rounded text-xs font-semibold ${
                    isBlocked
                      ? "bg-red-600 text-white"
                      : "bg-green-500/20 text-green-300"
                  }`}
                >
                  {entry.validation_result}
                </span>
              </div>

              {/* Timestamp */}
              <div className="flex-shrink-0 hidden md:block">
                <span className="text-xs text-gray-500">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>

            {/* Expanded Details */}
            {isExpanded && (
              <div className="border-t border-gray-700 bg-gray-900/50 p-4 space-y-3">
                {/* Action Content with Syntax Highlighting */}
                <div>
                  <p className="text-xs text-gray-400 mb-2 font-semibold">
                    Action Content:
                  </p>
                  <pre className="text-xs font-mono bg-black/60 text-gray-300 p-3 rounded border border-gray-700 overflow-x-auto">
                    <code className="language-bash">{entry.action_content}</code>
                  </pre>
                </div>

                {/* Blocked Reason (if any) */}
                {entry.blocked_reason && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2 font-semibold">
                      Blocked Reason:
                    </p>
                    <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                      <p className="text-xs text-red-300">
                        {entry.blocked_reason}
                      </p>
                    </div>
                  </div>
                )}

                {/* Matched Risk Patterns */}
                {entry.matched_risk_patterns.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2 font-semibold">
                      Matched Risk Patterns:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {entry.matched_risk_patterns.map((pattern, i) => (
                        <span
                          key={i}
                          className="text-xs px-2 py-1 bg-yellow-500/10 text-yellow-300 rounded border border-yellow-500/30 font-mono"
                        >
                          {pattern}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Full Timestamp */}
                <div className="flex items-center gap-4 text-xs text-gray-500 pt-2 border-t border-gray-700">
                  <span>ID: {entry.id}</span>
                  <span>•</span>
                  <span>{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

