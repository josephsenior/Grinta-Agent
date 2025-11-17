import React from "react";
import type { ModelUsageStats } from "#/types/analytics";

interface ModelUsageTableProps {
  models: ModelUsageStats[];
}

export function ModelUsageTable({ models }: ModelUsageTableProps) {
  if (!models || models.length === 0) {
    return (
      <div className="p-6 rounded-xl border border-brand-500/20 bg-black/60">
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Model Usage
        </h3>
        <p className="text-sm text-foreground-secondary">No data available</p>
      </div>
    );
  }

  // Sort by total cost (highest first)
  const sortedModels = [...models].sort((a, b) => b.totalCost - a.totalCost);

  return (
    <div className="p-6 rounded-xl border border-brand-500/20 bg-black/60">
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Model Usage & Costs
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-black/70 border-b border-brand-500/20">
            <tr>
              <th className="text-left py-3 px-4 text-foreground-secondary font-medium">
                Model
              </th>
              <th className="text-right py-3 px-4 text-foreground-secondary font-medium">
                Requests
              </th>
              <th className="text-right py-3 px-4 text-foreground-secondary font-medium">
                Tokens
              </th>
              <th className="text-right py-3 px-4 text-foreground-secondary font-medium">
                Avg Latency
              </th>
              <th className="text-right py-3 px-4 text-foreground-secondary font-medium">
                Cache Hits
              </th>
              <th className="text-right py-3 px-4 text-foreground-secondary font-medium">
                Total Cost
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-500/15">
            {sortedModels.map((model, index) => {
              const totalTokens =
                model.totalPromptTokens + model.totalCompletionTokens;
              const cacheHitPercentage =
                model.totalPromptTokens > 0
                  ? (model.cacheHitTokens / model.totalPromptTokens) * 100
                  : 0;

              return (
                <tr
                  key={model.modelName}
                  className="border-b border-border/50 hover:bg-background-tertiary/50 transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      {index === 0 && (
                        <span className="px-1.5 py-0.5 text-xs bg-brand-500/10 text-violet-500 rounded">
                          Top
                        </span>
                      )}
                      <span className="text-foreground font-medium">
                        {model.modelName}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-foreground">
                    {model.requestCount.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="text-foreground">
                      {totalTokens.toLocaleString()}
                    </div>
                    <div className="text-xs text-foreground-secondary">
                      {model.totalPromptTokens.toLocaleString()} in /{" "}
                      {model.totalCompletionTokens.toLocaleString()} out
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right text-foreground">
                    {model.avgLatency.toFixed(2)}s
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="text-foreground">
                      {model.cacheHitTokens.toLocaleString()}
                    </div>
                    {cacheHitPercentage > 0 && (
                      <div className="text-xs text-success-500">
                        {cacheHitPercentage.toFixed(1)}% hit rate
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-foreground font-semibold">
                      ${model.totalCost.toFixed(3)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-border font-semibold">
              <td className="py-3 px-4 text-foreground">Total</td>
              <td className="py-3 px-4 text-right text-foreground">
                {sortedModels
                  .reduce((sum, m) => sum + m.requestCount, 0)
                  .toLocaleString()}
              </td>
              <td className="py-3 px-4 text-right text-foreground">
                {sortedModels
                  .reduce(
                    (sum, m) =>
                      sum + m.totalPromptTokens + m.totalCompletionTokens,
                    0,
                  )
                  .toLocaleString()}
              </td>
              <td className="py-3 px-4 text-right text-foreground">-</td>
              <td className="py-3 px-4 text-right text-foreground">
                {sortedModels
                  .reduce((sum, m) => sum + m.cacheHitTokens, 0)
                  .toLocaleString()}
              </td>
              <td className="py-3 px-4 text-right text-violet-500">
                $
                {sortedModels
                  .reduce((sum, m) => sum + m.totalCost, 0)
                  .toFixed(3)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
