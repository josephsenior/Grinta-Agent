import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Play, Pause, Square, Shield, Activity, FileText } from "lucide-react";
import { SafetyScoreGauge } from "./safety-score-gauge";
import { RiskLevelChart } from "./risk-level-chart";
import { CommandBlockingCard } from "./command-blocking-card";
import { AnimatedAlertBanner } from "./animated-alert-banner";
import { EnhancedAuditTrail } from "./enhanced-audit-trail";
import { LiveMetricsCards } from "./live-metrics-cards";

interface SessionStatus {
  session_id: string;
  agent_state: string;
  current_iteration: number;
  max_iterations: number;
  progress_percentage: number;
  estimated_completion: string | null;
  is_making_progress: boolean;
  stagnation_iterations: number;
  consecutive_errors: number;
  high_risk_actions_count: number;
  last_action_type: string | null;
  last_action_timestamp: string | null;
  circuit_breaker_status: "normal" | "warning" | "tripped";
}

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

interface RiskAlert {
  id: string;
  session_id: string;
  timestamp: string;
  severity: "high" | "critical";
  action_type: string;
  description: string;
  resolved: boolean;
}

interface AutonomousMonitorProps {
  sessionId: string;
  onIntervene?: (action: string) => void;
}

export function AutonomousMonitor({
  sessionId,
  onIntervene,
}: AutonomousMonitorProps) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskHistory, setRiskHistory] = useState<Array<{
    timestamp: string;
    low: number;
    medium: number;
    high: number;
  }>>([]);

  // Fetch session status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`/api/monitoring/sessions/${sessionId}/status`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data);
        }
      } catch (err) {
        setError("Failed to fetch session status");
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000); // Update every 2 seconds

    return () => clearInterval(interval);
  }, [sessionId]);

  // Update risk history when audit trail changes
  useEffect(() => {
    if (auditTrail.length > 0) {
      const counts = auditTrail.reduce(
        (acc, entry) => {
          if (entry.risk_level === "LOW") acc.low++;
          else if (entry.risk_level === "MEDIUM") acc.medium++;
          else if (entry.risk_level === "HIGH") acc.high++;
          return acc;
        },
        { low: 0, medium: 0, high: 0 }
      );

      setRiskHistory(prev => [
        ...prev,
        {
          timestamp: new Date().toISOString(),
          ...counts,
        },
      ].slice(-50)); // Keep last 50 data points
    }
  }, [auditTrail]);

  // Fetch audit trail
  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const response = await fetch(
          `/api/monitoring/sessions/${sessionId}/audit?limit=50`
        );
        if (response.ok) {
          const data = await response.json();
          setAuditTrail(data);
        }
      } catch (err) {
        console.error("Failed to fetch audit trail:", err);
      }
    };

    fetchAudit();
    const interval = setInterval(fetchAudit, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [sessionId]);

  // Fetch risk alerts
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch(
          `/api/monitoring/sessions/${sessionId}/alerts?resolved=false`
        );
        if (response.ok) {
          const data = await response.json();
          setAlerts(data);
        }
      } catch (err) {
        console.error("Failed to fetch alerts:", err);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000); // Update every 3 seconds

    return () => clearInterval(interval);
  }, [sessionId]);

  const handleIntervention = async (action: string) => {
    try {
      const response = await fetch(
        `/api/monitoring/sessions/${sessionId}/intervention`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        }
      );

      if (response.ok) {
        onIntervene?.(action);
      }
    } catch (err) {
      console.error("Failed to perform intervention:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-400">Loading monitoring data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  // Calculate safety score (0-100)
  const calculateSafetyScore = () => {
    const errorPenalty = status.consecutive_errors * 10;
    const highRiskPenalty = status.high_risk_actions_count * 5;
    const stagnationPenalty = status.stagnation_iterations * 2;
    const circuitBreakerPenalty = 
      status.circuit_breaker_status === "tripped" ? 30 :
      status.circuit_breaker_status === "warning" ? 15 : 0;
    
    return Math.max(0, 100 - errorPenalty - highRiskPenalty - stagnationPenalty - circuitBreakerPenalty);
  };

  // Prepare metrics for LiveMetricsCards
  const metrics = {
    errorRate: (status.consecutive_errors / Math.max(status.current_iteration, 1)) * 100,
    highRiskActions: status.high_risk_actions_count,
    progress: status.progress_percentage * 100,
    iterationsPerMinute: status.current_iteration / Math.max(1, (Date.now() - Date.parse(status.last_action_timestamp || new Date().toISOString())) / 60000),
    avgResponseTime: 2500, // Mock data - would come from backend
    securityScore: calculateSafetyScore(),
  };

  // Prepare blocked commands
  const blockedCommands = auditTrail
    .filter(entry => entry.validation_result === "blocked")
    .map(entry => ({
      id: entry.id,
      timestamp: entry.timestamp,
      command: entry.action_content,
      reason: entry.blocked_reason || "Security policy violation",
      riskLevel: entry.risk_level === "HIGH" ? "HIGH" as const : "CRITICAL" as const,
      patterns: entry.matched_risk_patterns,
    }));

  // Prepare alerts from risk alerts
  const formattedAlerts = alerts.map(alert => ({
    id: alert.id,
    severity: alert.severity as "warning" | "error" | "critical",
    title: `${alert.action_type} Action`,
    message: alert.description,
    timestamp: alert.timestamp,
  }));

  return (
    <div className="flex flex-col gap-6 p-6 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl shadow-2xl border border-gray-700">
      {/* Enhanced Header with Glassmorphism */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-700/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Autonomous Safety Monitor
            </h2>
            <p className="text-xs text-gray-400">Real-time security & performance tracking</p>
          </div>
        </div>
        
        {/* Control Buttons with Icons */}
        <div className="flex gap-2">
          {status.agent_state === "paused" ? (
            <button
              onClick={() => handleIntervention("resume")}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg hover:from-green-600 hover:to-emerald-700 transition-all duration-200 shadow-lg shadow-green-500/30"
            >
              <Play className="w-4 h-4" />
              Resume
            </button>
          ) : (
            <button
              onClick={() => handleIntervention("pause")}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-yellow-500 to-orange-600 text-white rounded-lg hover:from-yellow-600 hover:to-orange-700 transition-all duration-200 shadow-lg shadow-yellow-500/30"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          )}
          <button
            onClick={() => handleIntervention("stop")}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-red-500 to-rose-600 text-white rounded-lg hover:from-red-600 hover:to-rose-700 transition-all duration-200 shadow-lg shadow-red-500/30"
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        </div>
      </div>

      {/* Animated Alerts */}
      <AnimatedAlertBanner alerts={formattedAlerts} />

      {/* Top Section: Safety Score + Live Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Safety Score Gauge */}
        <div className="lg:col-span-1 bg-gray-800/50 border border-gray-700 rounded-xl p-6 flex items-center justify-center">
          <SafetyScoreGauge score={calculateSafetyScore()} size="md" />
        </div>

        {/* Live Metrics */}
        <div className="lg:col-span-3">
          <LiveMetricsCards metrics={metrics} />
        </div>
      </div>

      {/* Middle Section: Risk Chart + Blocked Commands */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Level Chart */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            Risk Levels Over Time
          </h3>
          {riskHistory.length > 1 ? (
            <RiskLevelChart data={riskHistory} />
          ) : (
            <div className="text-center text-gray-400 py-8">
              Collecting data...
            </div>
          )}
        </div>

        {/* Command Blocking Cards */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <CommandBlockingCard blockedCommands={blockedCommands} />
        </div>
      </div>

      {/* Bottom Section: Enhanced Audit Trail */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4 text-purple-400" />
          Audit Trail ({auditTrail.length} entries)
        </h3>
        <EnhancedAuditTrail entries={auditTrail.slice(0, 20)} />
      </div>

      {/* Footer Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-700/50">
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Agent State</p>
          <p className="text-sm font-semibold text-white capitalize">{status.agent_state}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Iterations</p>
          <p className="text-sm font-semibold text-white">
            {status.current_iteration} / {status.max_iterations}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Circuit Breaker</p>
          <p
            className={`text-sm font-semibold capitalize ${
              status.circuit_breaker_status === "tripped"
                ? "text-red-400"
                : status.circuit_breaker_status === "warning"
                  ? "text-yellow-400"
                  : "text-green-400"
            }`}
          >
            {status.circuit_breaker_status}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Last Action</p>
          <p className="text-sm font-mono text-white truncate">
            {status.last_action_type || "N/A"}
          </p>
        </div>
      </div>
    </div>
  );
}

