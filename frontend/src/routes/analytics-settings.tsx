import React, { useState } from "react";
import {
  DollarSign,
  Zap,
  MessageSquare,
  TrendingUp,
  Download,
  RefreshCw,
  BarChart3,
  AlertTriangle,
} from "lucide-react";
import { useAnalyticsDashboard } from "#/hooks/query/use-analytics";
import { StatCard } from "#/components/features/analytics/stat-card";
import { CostChart } from "#/components/features/analytics/cost-chart";
import { ModelUsageTable } from "#/components/features/analytics/model-usage-table";
import { exportAnalytics } from "#/api/analytics";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import type { AnalyticsPeriod } from "#/types/analytics";

function AnalyticsSettingsScreen() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("week");
  const { data: dashboard, isLoading, error, refetch } = useAnalyticsDashboard(period);
  

  const handleExport = async (format: "json" | "csv") => {
    try {
      const result = await exportAnalytics(period, format);
      
      // Download the file
      const blob = new Blob(
        [typeof result.data === "string" ? result.data : JSON.stringify(result.data, null, 2)],
        { type: format === "json" ? "application/json" : "text/csv" }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analytics-${period}-${Date.now()}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      displaySuccessToast(`Analytics exported as ${format.toUpperCase()}`);
    } catch (error) {
      displayErrorToast(
        `Failed to export analytics: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  };

  if (isLoading) {
    return (
      <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-foreground-secondary">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Failed to Load Analytics</h3>
          <p className="text-foreground-secondary mb-4">
            {error instanceof Error ? error.message : "An unknown error occurred"}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!dashboard || !dashboard.summary) {
    return (
      <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-16 h-16 bg-neutral-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-8 h-8 text-neutral-500" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No Data Available</h3>
          <p className="text-foreground-secondary">
            Analytics data will appear here once you have active conversations
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-brand-500" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">Analytics Dashboard</h2>
            <p className="text-sm text-foreground-secondary mt-1">
              Track usage, costs, and performance insights
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Period selector */}
          <div className="flex items-center gap-1 p-1 bg-black border border-violet-500/20 rounded-lg">
            {(["today", "week", "month", "all"] as AnalyticsPeriod[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all capitalize ${
                  period === p
                    ? "bg-brand-500 text-white shadow-sm"
                    : "text-foreground-secondary hover:text-foreground hover:bg-black"
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Export dropdown */}
          <div className="relative group">
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2 text-sm text-foreground bg-black hover:bg-black border border-violet-500/20 rounded-md transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            
            <div className="absolute right-0 top-full mt-2 w-32 bg-black border border-violet-500/20 rounded-lg shadow-lg overflow-hidden opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                type="button"
                onClick={() => handleExport("json")}
                className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
              >
                JSON
              </button>
              <button
                type="button"
                onClick={() => handleExport("csv")}
                className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
              >
                CSV
              </button>
            </div>
          </div>

          {/* Refresh button */}
          <button
            type="button"
            onClick={() => refetch()}
            className="p-2 text-foreground-secondary hover:text-foreground hover:bg-black border border-violet-500/20 rounded-md transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Cost"
          value={`$${(dashboard.summary?.totalCost || 0).toFixed(3)}`}
          icon={DollarSign}
          subtitle={`${dashboard.summary?.totalConversations || 0} conversations`}
        />
        <StatCard
          title="Total Tokens"
          value={(dashboard.summary?.totalTokens || 0).toLocaleString()}
          icon={TrendingUp}
          subtitle={`${dashboard.summary?.totalRequests || 0} requests`}
        />
        <StatCard
          title="Avg Response Time"
          value={`${(dashboard.summary?.avgResponseTime || 0).toFixed(2)}s`}
          icon={Zap}
          subtitle="Average latency"
        />
        <StatCard
          title="Conversations"
          value={dashboard.summary?.totalConversations || 0}
          icon={MessageSquare}
          subtitle={`${dashboard.conversations?.activeConversations || 0} active`}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost over time */}
        <CostChart data={dashboard.costs?.byDay || []} title="Cost Over Time" />

        {/* Performance chart */}
        <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Performance Metrics
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground-secondary">Average Response</span>
              <span className="text-lg font-semibold text-foreground">
                {(dashboard.performance?.avgResponseTime || 0).toFixed(2)}s
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground-secondary">95th Percentile</span>
              <span className="text-lg font-semibold text-foreground">
                {(dashboard.performance?.p95ResponseTime || 0).toFixed(2)}s
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground-secondary">99th Percentile</span>
              <span className="text-lg font-semibold text-foreground">
                {(dashboard.performance?.p99ResponseTime || 0).toFixed(2)}s
              </span>
            </div>

            {/* Slowest requests */}
            {(dashboard.performance?.slowestRequests || []).length > 0 && (
              <div className="mt-6 pt-4 border-t border-violet-500/20">
                <h4 className="text-sm font-medium text-foreground-secondary mb-3">
                  Slowest Requests
                </h4>
                <div className="space-y-2">
                  {(dashboard.performance?.slowestRequests || []).slice(0, 5).map((req, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="text-foreground-secondary truncate max-w-[200px]">
                        {req.model}
                      </span>
                      <span className="text-warning-500 font-medium">
                        {req.latency.toFixed(2)}s
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Model Usage Table */}
      <ModelUsageTable models={dashboard.models} />

      {/* Top Expensive Conversations */}
      {(dashboard.costs?.topExpensiveConversations || []).length > 0 && (
        <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Most Expensive Conversations
          </h3>
          
          <div className="space-y-2">
            {(dashboard.costs?.topExpensiveConversations || []).map((conv, idx) => (
              <div
                key={conv.conversationId}
                className="flex items-center justify-between p-3 bg-black rounded-lg hover:bg-black transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-sm font-medium text-brand-500">
                    #{idx + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {conv.title}
                    </p>
                    <p className="text-xs text-foreground-secondary">
                      {new Date(conv.timestamp).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-foreground ml-4">
                  ${conv.cost.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Productivity Insights */}
      <div className="p-6 bg-gradient-to-br from-brand-500/10 to-brand-500/5 border border-brand-500/20 rounded-lg">
        <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-500" />
          Productivity Insights
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-foreground-secondary mb-2">
              Estimated Time Saved
            </p>
            <p className="text-3xl font-bold text-brand-500">
              ~{(dashboard.productivity?.estimatedTimeSaved || 0).toFixed(1)} hours
            </p>
            <p className="text-xs text-foreground-secondary mt-1">
              Based on {dashboard.productivity?.tasksCompleted || 0} completed tasks
            </p>
          </div>
          
          <div>
            <p className="text-sm text-foreground-secondary mb-2">
              Productivity Score
            </p>
            <p className="text-3xl font-bold text-success-500">
              {(dashboard.productivity?.productivityScore || 0).toFixed(0)}/100
            </p>
            <p className="text-xs text-foreground-secondary mt-1">
              Above industry average
            </p>
          </div>
          
          <div>
            <p className="text-sm text-foreground-secondary mb-2">
              ROI Estimate
            </p>
            <p className="text-3xl font-bold text-brand-500">
              {(dashboard.productivity?.estimatedTimeSaved || 0) > 0 && (dashboard.summary?.totalCost || 0) > 0
                ? `${(((dashboard.productivity?.estimatedTimeSaved || 0) * 50) / (dashboard.summary?.totalCost || 1)).toFixed(0)}x`
                : "N/A"}
            </p>
            <p className="text-xs text-foreground-secondary mt-1">
              Time saved vs. cost (@ $50/hour)
            </p>
          </div>
        </div>
      </div>

      {/* Data timestamp */}
      <div className="text-center text-xs text-foreground-secondary">
        Generated at {new Date(dashboard.generatedAt).toLocaleString()} • Auto-refreshes every 5 minutes
      </div>
    </div>
  );
}

export default AnalyticsSettingsScreen;


