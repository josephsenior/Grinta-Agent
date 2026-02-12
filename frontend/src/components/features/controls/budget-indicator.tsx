import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "#/store";

/**
 * Compact budget indicator shown inline next to the agent controls.
 *
 * Displays current accumulated cost and, when a budget is set, shows a
 * color-coded percentage bar:
 *   - green  < 50%
 *   - yellow >= 50%
 *   - orange >= 80%
 *   - red    >= 90%
 *
 * Hidden when no cost data is available yet (first message not sent).
 */
export function BudgetIndicator() {
  const { cost, max_budget_per_task: budget } = useSelector(
    (state: RootState) => state.metrics,
  );

  // Don't render until we have cost data
  if (cost === null) return null;

  const pct = budget && budget > 0 ? cost / budget : null;

  const barColor =
    pct === null
      ? "bg-foreground-secondary"
      : pct >= 0.9
        ? "bg-red-500"
        : pct >= 0.8
          ? "bg-orange-400"
          : pct >= 0.5
            ? "bg-yellow-400"
            : "bg-green-500";

  return (
    <div
      className="flex items-center gap-1.5 text-xs text-foreground-secondary select-none"
      title={
        budget
          ? `$${cost.toFixed(4)} / $${budget.toFixed(2)} (${((pct ?? 0) * 100).toFixed(1)}%)`
          : `$${cost.toFixed(4)} (no limit)`
      }
    >
      <span className="font-mono">${cost.toFixed(4)}</span>
      {budget != null && budget > 0 && pct !== null && (
        <div className="w-12 h-1.5 rounded-full bg-neutral-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${Math.min(pct * 100, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}
