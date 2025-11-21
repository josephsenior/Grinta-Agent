import React from "react";
import { useTranslation } from "react-i18next";

interface OrchestrationStepsProps {
  steps?: unknown[];
}

/**
 * Placeholder for OrchestrationSteps
 * TODO: Implement actual orchestration steps functionality
 */
export function OrchestrationSteps({ steps = [] }: OrchestrationStepsProps) {
  const { t } = useTranslation();
  if (steps.length === 0) return null;

  return (
    <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
      <h3 className="text-sm font-semibold mb-2">
        {t("chat.orchestrationSteps", "Orchestration Steps")}
      </h3>
      <div className="space-y-2">
        {steps.map((step, index: number) => {
          const s =
            typeof step === "object" && step !== null
              ? (step as Record<string, unknown>)
              : undefined;
          return (
            <div
              key={index}
              className="text-xs text-gray-600 dark:text-gray-400"
            >
              {t("chat.step", "Step")} {index + 1}:{" "}
              {String(s?.name ?? t("common.unknown", "Unknown"))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
