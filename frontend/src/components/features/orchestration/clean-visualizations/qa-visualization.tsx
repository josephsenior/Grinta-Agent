import React from "react";
import { motion } from "framer-motion";
import {
  TestTube,
  Activity,
  Shield,
  Zap,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  Circle,
  Clock,
} from "lucide-react";
import type { QASpecArtifact, TestScenario } from "#/types/metasop-artifacts";
import { cn } from "#/utils/utils";
import { TestResultsSummary } from "./test-results-summary";

export interface QAVisualizationProps {
  artifact: QASpecArtifact;
  animated?: boolean;
  className?: string;
  onInteraction?: (action: string, data: unknown) => void;
}

// Helper functions
function hasTestResults(artifact: QASpecArtifact): boolean {
  return Boolean(
    artifact.test_results && artifact.test_results.total !== undefined,
  );
}

function hasCoverage(artifact: QASpecArtifact): boolean {
  return Boolean(
    artifact.code_coverage && Object.keys(artifact.code_coverage).length > 0,
  );
}

function hasPerformanceMetrics(artifact: QASpecArtifact): boolean {
  return Boolean(
    artifact.performance_metrics &&
      Object.keys(artifact.performance_metrics).length > 0,
  );
}

function calculatePassRate(artifact: QASpecArtifact): number {
  if (
    !artifact.test_results ||
    !artifact.test_results.total ||
    artifact.test_results.total === 0
  ) {
    return 0;
  }

  return Math.round(
    ((artifact.test_results.passed || 0) / artifact.test_results.total) * 100,
  );
}

function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: "bg-red-500/30 text-red-200 border border-red-500/50",
    high: "bg-orange-500/30 text-orange-200 border border-orange-500/50",
    medium: "bg-yellow-500/30 text-yellow-200 border border-yellow-500/50",
    low: "bg-blue-500/30 text-blue-200 border border-blue-500/50",
    info: "bg-neutral-500/30 text-neutral-200 border border-neutral-500/50",
  };
  return colors[severity] || colors.info;
}

function getLintStatusColor(status: string): string {
  const colors: Record<string, string> = {
    clean: "bg-green-500/10 border-green-500/20 text-green-300",
    warnings: "bg-yellow-500/10 border-yellow-500/20 text-yellow-300",
    errors: "bg-red-500/10 border-red-500/20 text-red-300",
  };
  return (
    colors[status] || "bg-neutral-500/10 border-neutral-500/20 text-neutral-300"
  );
}

function getPriorityBadgeColor(priority: string): string {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300 border border-red-500/30",
    high: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
    medium: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
    low: "bg-green-500/20 text-green-300 border border-green-500/30",
  };
  return (
    colors[priority] ||
    "bg-neutral-500/20 text-neutral-300 border border-neutral-500/30"
  );
}

// Leaf components
function CodeCoverageSection({
  coverage,
  animated,
}: {
  coverage: NonNullable<QASpecArtifact["code_coverage"]>;
  animated: boolean;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
        <Activity className="w-4 h-4" />
        Code Coverage
      </h4>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(coverage).map(([key, value]) => (
          <motion.div
            key={key}
            initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            className="bg-orange-500/5 border border-orange-500/20 rounded p-2"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs text-orange-300 capitalize">{key}</p>
              <p className="text-sm font-bold text-orange-400">{`${Number(value) || 0}%`}</p>
            </div>
            <div className="w-full bg-neutral-800 rounded-full h-1.5 mt-2">
              <div
                className="bg-orange-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Number(value) || 0}%` }}
              />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function TestScenarioCard({
  scenario,
  index,
  animated,
  onInteraction,
}: {
  scenario: TestScenario;
  index: number;
  animated?: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const statusIcons: Record<string, React.ReactElement> = {
    passed: <CheckCircle className="w-4 h-4 text-green-400" />,
    failed: <AlertCircle className="w-4 h-4 text-red-400" />,
    skipped: <Circle className="w-4 h-4 text-yellow-400" />,
    pending: <Clock className="w-4 h-4 text-neutral-400" />,
  };

  const statusColors: Record<string, string> = {
    passed: "border-green-500/20 bg-green-500/5",
    failed: "border-red-500/20 bg-red-500/5",
    skipped: "border-yellow-500/20 bg-yellow-500/5",
    pending: "border-neutral-500/20 bg-neutral-500/5",
  };

  const status = scenario.status || "pending";

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 20 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      transition={{ delay: index * 0.05 }}
      className={cn(
        "border rounded-lg p-3 hover:opacity-80 transition-opacity cursor-pointer",
        statusColors[status],
      )}
      onClick={() => onInteraction?.("scenario_click", scenario)}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{statusIcons[status]}</div>
        <div className="flex-1">
          <div className="flex items-start justify-between mb-1">
            <h5 className="text-sm font-medium text-orange-200">
              {scenario.title}
            </h5>
            <div className="flex items-center gap-1">
              {scenario.priority && (
                <span
                  className={cn(
                    "text-xs px-2 py-1 rounded",
                    getPriorityBadgeColor(scenario.priority),
                  )}
                >
                  {scenario.priority}
                </span>
              )}
              {scenario.type && (
                <span className="text-xs px-2 py-1 bg-orange-500/10 text-orange-400 rounded border border-orange-500/20">
                  {scenario.type}
                </span>
              )}
            </div>
          </div>

          {scenario.description && (
            <p className="text-xs text-neutral-400 mt-1">
              {scenario.description}
            </p>
          )}

          {scenario.tags && scenario.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {scenario.tags.map((tag, i) => (
                <span
                  key={i}
                  className="text-xs px-1.5 py-0.5 bg-orange-500/10 text-orange-400 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function TestScenarioSection({
  scenarios,
  animated,
  onInteraction,
}: {
  scenarios: TestScenario[];
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  const displayCount = Math.min(scenarios.length, 10);

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
        <TestTube className="w-4 h-4" />
        Test Scenarios ({scenarios.length})
      </h4>
      {scenarios.slice(0, displayCount).map((scenario, index) => (
        <TestScenarioCard
          key={scenario.id || index}
          scenario={scenario}
          index={index}
          animated={animated}
          onInteraction={onInteraction}
        />
      ))}
      {scenarios.length > displayCount && (
        <p className="text-xs text-neutral-500 text-center py-2">
          + {scenarios.length - displayCount} more scenarios
        </p>
      )}
    </div>
  );
}

function SecurityFindingsSection({
  findings,
  animated,
  onInteraction,
}: {
  findings: NonNullable<QASpecArtifact["security_findings"]>;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
        <Shield className="w-4 h-4" />
        Security Findings ({findings.length})
      </h4>
      {findings.map((finding, index) => (
        <motion.div
          key={index}
          initial={animated ? { opacity: 0, x: -20 } : undefined}
          animate={animated ? { opacity: 1, x: 0 } : undefined}
          transition={{ delay: index * 0.05 }}
          className="bg-red-500/10 border border-red-500/20 rounded p-3 hover:bg-red-500/15 transition-colors cursor-pointer"
          onClick={() => onInteraction?.("finding_click", finding)}
        >
          <div className="flex items-start justify-between mb-1">
            <h5 className="text-sm font-medium text-red-300">
              {finding.title}
            </h5>
            <span
              className={cn(
                "text-xs px-2 py-1 rounded",
                getSeverityColor(finding.severity ?? ""),
              )}
            >
              {finding.severity}
            </span>
          </div>
          {finding.description && (
            <p className="text-xs text-neutral-400 mt-1">
              {finding.description}
            </p>
          )}
          {finding.file && (
            <p className="text-xs text-neutral-500 mt-1">
              {finding.file}
              {finding.line && `:${finding.line}`}
            </p>
          )}
          {finding.recommendation && (
            <div className="mt-2 bg-black/20 rounded p-2">
              <p className="text-xs text-orange-300">Recommendation:</p>
              <p className="text-xs text-neutral-400 mt-0.5">
                {finding.recommendation}
              </p>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function NoSecurityFindingsCard({ animated }: { animated: boolean }) {
  return (
    <motion.div
      initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
      animate={animated ? { opacity: 1, scale: 1 } : undefined}
      className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center"
    >
      <Shield className="w-8 h-8 text-green-400 mx-auto mb-2" />
      <p className="text-sm text-green-300 font-medium">
        No security vulnerabilities found
      </p>
    </motion.div>
  );
}

function PerformanceMetricsSection({
  metrics,
  animated,
}: {
  metrics: NonNullable<QASpecArtifact["performance_metrics"]>;
  animated: boolean;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide flex items-center gap-2">
        <Zap className="w-4 h-4" />
        Performance Metrics
      </h4>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(metrics).map(([key, value]) => (
          <motion.div
            key={key}
            initial={animated ? { opacity: 0, scale: 0.9 } : undefined}
            animate={animated ? { opacity: 1, scale: 1 } : undefined}
            className="bg-orange-500/5 border border-orange-500/20 rounded px-3 py-2"
          >
            <p className="text-xs text-orange-400 capitalize">
              {key.replace(/_/g, " ")}
            </p>
            <p className="text-sm font-mono text-orange-300 mt-0.5">
              {String(value)}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function LintStatusCard({
  status,
  animated,
}: {
  status: string;
  animated: boolean;
}) {
  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 20 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      className={cn("rounded-lg p-3 border", getLintStatusColor(status))}
    >
      <div className="flex items-center gap-2">
        {status === "clean" ? (
          <CheckCircle className="w-5 h-5 text-green-400" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
        )}
        <p className="text-sm font-medium">
          Lint Status: {status === "clean" ? "Clean ✓" : status}
        </p>
      </div>
    </motion.div>
  );
}

function QualityScoreCard({
  score,
  animated,
}: {
  score: number;
  animated: boolean;
}) {
  return (
    <motion.div
      initial={animated ? { opacity: 0, scale: 0.95 } : undefined}
      animate={animated ? { opacity: 1, scale: 1 } : undefined}
      className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 text-center"
    >
      <p className="text-3xl font-bold text-orange-400">{score}/100</p>
      <p className="text-xs text-orange-300 mt-1">Overall Quality Score</p>
    </motion.div>
  );
}

function buildSecuritySections({
  artifact,
  animated,
  onInteraction,
}: {
  artifact: QASpecArtifact;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}): React.ReactNode | null {
  const findings = artifact.security_findings;
  if (!findings) {
    return null;
  }

  if (findings.length === 0) {
    return <NoSecurityFindingsCard key="security-clean" animated={animated} />;
  }

  return (
    <SecurityFindingsSection
      key="security-findings"
      findings={findings}
      animated={animated}
      onInteraction={onInteraction}
    />
  );
}

function buildQASections({
  artifact,
  animated,
  onInteraction,
}: {
  artifact: QASpecArtifact;
  animated: boolean;
  onInteraction?: (action: string, data: unknown) => void;
}): React.ReactNode[] {
  const passRate = calculatePassRate(artifact);
  const builders: Array<() => React.ReactNode | null> = [
    () =>
      hasTestResults(artifact) ? (
        <TestResultsSummary
          key="test-results"
          artifact={artifact}
          animated={animated}
          passRate={passRate}
        />
      ) : null,
    () =>
      hasCoverage(artifact) ? (
        <CodeCoverageSection
          key="coverage"
          coverage={artifact.code_coverage!}
          animated={animated}
        />
      ) : null,
    () =>
      artifact.test_scenarios?.length ? (
        <TestScenarioSection
          key="scenarios"
          scenarios={artifact.test_scenarios}
          animated={animated}
          onInteraction={onInteraction}
        />
      ) : null,
    () => buildSecuritySections({ artifact, animated, onInteraction }),
    () =>
      hasPerformanceMetrics(artifact) ? (
        <PerformanceMetricsSection
          key="performance"
          metrics={artifact.performance_metrics!}
          animated={animated}
        />
      ) : null,
    () =>
      artifact.lint_status ? (
        <LintStatusCard
          key="lint"
          status={artifact.lint_status}
          animated={animated}
        />
      ) : null,
    () =>
      artifact.quality_score !== undefined ? (
        <QualityScoreCard
          key="quality"
          score={artifact.quality_score}
          animated={animated}
        />
      ) : null,
  ];

  return builders
    .map((buildFn) => buildFn())
    .filter((section): section is React.ReactNode => Boolean(section));
}

export function QAVisualization({
  artifact,
  animated = true,
  className = "",
  onInteraction,
}: QAVisualizationProps) {
  const sections = buildQASections({ artifact, animated, onInteraction });

  if (sections.length === 0) {
    return (
      <div className={cn("metasop-viz-empty", className)}>
        <TestTube className="w-12 h-12 text-orange-400 opacity-50 mb-2" />
        <p className="text-sm text-neutral-400">No test results yet...</p>
      </div>
    );
  }

  return (
    <div className={cn("metasop-viz-qa", className)}>
      <div className="metasop-viz-header bg-orange-500/10 border-orange-500/20">
        <TestTube className="w-5 h-5 text-orange-400" />
        <h3 className="text-sm font-semibold text-orange-300">QA Engineer</h3>
        <span className="text-xs text-orange-400/60">
          Testing & Quality Assurance
        </span>
      </div>

      <div className="p-4 space-y-6">{sections}</div>
    </div>
  );
}
