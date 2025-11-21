import React from "react";
import { motion } from "framer-motion";
import type { QASpecArtifact } from "#/types/metasop-artifacts";

interface TestResultsSummaryProps {
  artifact: QASpecArtifact;
  animated: boolean;
  passRate: number;
}

interface TestStatCardProps {
  value: number | string;
  label: string;
  color: "green" | "red" | "yellow" | "orange";
  animated: boolean;
  delay: number;
}

function TestStatCard({
  value,
  label,
  color,
  animated,
  delay,
}: TestStatCardProps) {
  const colorClasses = {
    green: "bg-green-500/10 border-green-500/20 text-green-400 text-green-300",
    red: "bg-red-500/10 border-red-500/20 text-red-400 text-red-300",
    yellow:
      "bg-yellow-500/10 border-yellow-500/20 text-yellow-400 text-yellow-300",
    orange:
      "bg-orange-500/10 border-orange-500/20 text-orange-400 text-orange-300",
  };

  const classes = colorClasses[color].split(" ");

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 20 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      transition={{ delay }}
      className={`${classes[0]} border ${classes[1]} rounded p-3 text-center`}
    >
      <p className={`text-2xl font-bold ${classes[2]}`}>{value}</p>
      <p className={`text-xs ${classes[3]} mt-1`}>{label}</p>
    </motion.div>
  );
}

export function TestResultsSummary({
  artifact,
  animated,
  passRate,
}: TestResultsSummaryProps) {
  const testResults = artifact.test_results!;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-orange-300 uppercase tracking-wide">
        Test Results
      </h4>
      <div className="grid grid-cols-4 gap-2">
        <TestStatCard
          value={testResults.passed || 0}
          label="Passed"
          color="green"
          animated={animated}
          delay={0}
        />
        <TestStatCard
          value={testResults.failed || 0}
          label="Failed"
          color="red"
          animated={animated}
          delay={0.05}
        />
        <TestStatCard
          value={testResults.skipped || 0}
          label="Skipped"
          color="yellow"
          animated={animated}
          delay={0.1}
        />
        <TestStatCard
          value={`${passRate}%`}
          label="Pass Rate"
          color="orange"
          animated={animated}
          delay={0.15}
        />
      </div>
    </div>
  );
}
