import React, { useCallback, useMemo, useState } from "react";
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
import type { AnalyticsPeriod, AnalyticsDashboard } from "#/types/analytics";

function AnalyticsSettingsScreen() {
  const {
    period,
    setPeriod,
    dashboard,
    isLoading,
    error,
    handleExport,
    handleRefresh,
  } = useAnalyticsSettings();

  if (isLoading) {
    return <AnalyticsLoadingState />;
  }

  if (error) {
    return <AnalyticsErrorState error={error} onRetry={handleRefresh} />;
  }

  if (!dashboard || !dashboard.summary) {
    return <AnalyticsEmptyState />;
  }

  return (
    <AnalyticsDashboardContent
      dashboard={dashboard}
      period={period}
      onChangePeriod={setPeriod}
      onExport={handleExport}
      onRefresh={handleRefresh}
    />
  );
}

function useAnalyticsSettings() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("week");
  const { data: dashboard, isLoading, error, refetch } = useAnalyticsDashboard(period);

  const handleExport = useAnalyticsExport(period);
  const handleRefresh = useCallback(() => {
    void refetch();
  }, [refetch]);

  return {
    period,
    setPeriod,
    dashboard,
    isLoading,
    error,
    handleExport,
    handleRefresh,
  } as const;
}

function useAnalyticsExport(period: AnalyticsPeriod) {
  return useCallback(
    async (format: "json" | "csv") => {
      try {
        const result = await exportAnalytics(period, format);
        const payload =
          typeof result.data === "string"
            ? result.data
            : JSON.stringify(result.data, null, 2);
        const blob = new Blob([payload], {
          type: format === "json" ? "application/json" : "text/csv",
        });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `analytics-${period}-${Date.now()}.${format}`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
        displaySuccessToast(`Analytics exported as ${format.toUpperCase()}`);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        displayErrorToast(`Failed to export analytics: ${message}`);
      }
    },
    [period],
  );
}

function AnalyticsLoadingState() {
  return (
    <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-foreground-secondary">Loading analytics...</p>
      </div>
    </div>
  );
}

function AnalyticsErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const message = error instanceof Error ? error.message : "An unknown error occurred";

  return (
    <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-8 h-8 text-red-500" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">Failed to Load Analytics</h3>
        <p className="text-foreground-secondary mb-4">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

function AnalyticsEmptyState() {
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

function AnalyticsDashboardContent({
  dashboard,
  period,
  onChangePeriod,
  onExport,
  onRefresh,
}: {
  dashboard: AnalyticsDashboard;
  period: AnalyticsPeriod;
  onChangePeriod: (period: AnalyticsPeriod) => void;
  onExport: (format: "json" | "csv") => void;
  onRefresh: () => void;
}) {
  const conversationSummary = useMemo(
    () => dashboard.conversations?.activeConversations ?? 0,
    [dashboard.conversations?.activeConversations],
  );

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      <AnalyticsHeader
        period={period}
        onChangePeriod={onChangePeriod}
        onExport={onExport}
        onRefresh={onRefresh}
      />

      <AnalyticsSummaryCards summary={dashboard.summary} activeConversations={conversationSummary} />

      <AnalyticsChartsRow dashboard={dashboard} />

      <ModelUsageTable models={dashboard.models} />

      <TopExpensiveConversationsSection conversations={dashboard.costs?.topExpensiveConversations} />

      <ProductivityInsightsSection
        productivity={dashboard.productivity}
        summary={dashboard.summary}
      />

      <AnalyticsFooter generatedAt={dashboard.generatedAt} />
    </div>
  );
}

function AnalyticsHeader({
  period,
  onChangePeriod,
  onExport,
  onRefresh,
}: {
  period: AnalyticsPeriod;
  onChangePeriod: (period: AnalyticsPeriod) => void;
  onExport: (format: "json" | "csv") => void;
  onRefresh: () => void;
}) {
  const periods: AnalyticsPeriod[] = ["today", "week", "month", "all"];

  return (
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
        <PeriodSelector period={period} periods={periods} onChange={onChangePeriod} />
        <ExportMenu onExport={onExport} />
        <button
          type="button"
          onClick={onRefresh}
          className="p-2 text-foreground-secondary hover:text-foreground hover:bg-black border border-violet-500/20 rounded-md transition-colors"
          title="Refresh data"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function PeriodSelector({
  period,
  periods,
  onChange,
}: {
  period: AnalyticsPeriod;
  periods: AnalyticsPeriod[];
  onChange: (period: AnalyticsPeriod) => void;
}) {
  return (
    <div className="flex items-center gap-1 p-1 bg-black border border-violet-500/20 rounded-lg">
      {periods.map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all capitalize ${
            period === value
              ? "bg-brand-500 text-white shadow-sm"
              : "text-foreground-secondary hover:text-foreground hover:bg-black"
          }`}
        >
          {value}
        </button>
      ))}
    </div>
  );
}

function ExportMenu({ onExport }: { onExport: (format: "json" | "csv") => void }) {
  return (
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
          onClick={() => onExport("json")}
          className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
        >
          JSON
        </button>
        <button
          type="button"
          onClick={() => onExport("csv")}
          className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
        >
          CSV
        </button>
      </div>
    </div>
  );
}

function AnalyticsSummaryCards({
  summary,
  activeConversations,
}: {
  summary: AnalyticsDashboard["summary"];
  activeConversations: number;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Total Cost"
        value={`$${(summary?.totalCost || 0).toFixed(3)}`}
        icon={DollarSign}
        subtitle={`${summary?.totalConversations || 0} conversations`}
      />
      <StatCard
        title="Total Tokens"
        value={(summary?.totalTokens || 0).toLocaleString()}
        icon={TrendingUp}
        subtitle={`${summary?.totalRequests || 0} requests`}
      />
      <StatCard
        title="Avg Response Time"
        value={`${(summary?.avgResponseTime || 0).toFixed(2)}s`}
        icon={Zap}
        subtitle="Average latency"
      />
      <StatCard
        title="Conversations"
        value={summary?.totalConversations || 0}
        icon={MessageSquare}
        subtitle={`${activeConversations} active`}
      />
    </div>
  );
}

function AnalyticsChartsRow({ dashboard }: { dashboard: AnalyticsDashboard }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <CostChart data={dashboard.costs?.byDay || []} title="Cost Over Time" />
      <PerformanceCard performance={dashboard.performance} />
    </div>
  );
}

function PerformanceCard({
  performance,
}: {
  performance: AnalyticsDashboard["performance"];
}) {
  const slowestRequests = performance?.slowestRequests ?? [];

  return (
    <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
      <h3 className="text-lg font-semibold text-foreground mb-4">Performance Metrics</h3>
      <div className="space-y-4">
        <PerformanceMetric label="Average Response" value={performance?.avgResponseTime} />
        <PerformanceMetric label="95th Percentile" value={performance?.p95ResponseTime} />
        <PerformanceMetric label="99th Percentile" value={performance?.p99ResponseTime} />
        {slowestRequests.length > 0 ? (
          <div className="mt-6 pt-4 border-t border-violet-500/20">
            <h4 className="text-sm font-medium text-foreground-secondary mb-3">Slowest Requests</h4>
            <div className="space-y-2">
              {slowestRequests.slice(0, 5).map((request, index) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <span className="text-foreground-secondary truncate max-w-[200px]">
                    {request.model}
                  </span>
                  <span className="text-warning-500 font-medium">
                    {request.latency.toFixed(2)}s
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PerformanceMetric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-foreground-secondary">{label}</span>
      <span className="text-lg font-semibold text-foreground">{(value || 0).toFixed(2)}s</span>
    </div>
  );
}

function TopExpensiveConversationsSection({
  conversations,
}: {
  conversations?: AnalyticsDashboard["costs"]["topExpensiveConversations"];
}) {
  if (!conversations || conversations.length === 0) {
    return null;
  }

  return (
    <div className="p-6 bg-black border border-violet-500/20 rounded-lg">
      <h3 className="text-lg font-semibold text-foreground mb-4">Most Expensive Conversations</h3>
      <div className="space-y-2">
        {conversations.map((conversation, index) => (
          <div
            key={conversation.conversationId}
            className="flex items-center justify-between p-3 bg-black rounded-lg hover:bg-black transition-colors"
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="text-sm font-medium text-brand-500">#{index + 1}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{conversation.title}</p>
                <p className="text-xs text-foreground-secondary">
                  {new Date(conversation.timestamp).toLocaleDateString()}
                </p>
              </div>
            </div>
            <span className="text-sm font-semibold text-foreground ml-4">
              ${conversation.cost.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProductivityInsightsSection({
  productivity,
  summary,
}: {
  productivity: AnalyticsDashboard["productivity"];
  summary: AnalyticsDashboard["summary"];
}) {
  const estimatedTimeSaved = productivity?.estimatedTimeSaved || 0;
  const totalCost = summary?.totalCost || 0;
  const roiEstimate = estimatedTimeSaved > 0 && totalCost > 0
    ? `${(((estimatedTimeSaved || 0) * 50) / (totalCost || 1)).toFixed(0)}x`
    : "N/A";

  return (
    <div className="p-6 bg-gradient-to-br from-brand-500/10 to-brand-500/5 border border-brand-500/20 rounded-lg">
      <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-brand-500" />
        Productivity Insights
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <ProductivityItem
          label="Estimated Time Saved"
          value={`~${estimatedTimeSaved.toFixed(1)} hours`}
          helper={`Based on ${productivity?.tasksCompleted || 0} completed tasks`}
          valueClassName="text-brand-500"
        />
        <ProductivityItem
          label="Productivity Score"
          value={`${(productivity?.productivityScore || 0).toFixed(0)}/100`}
          helper="Above industry average"
          valueClassName="text-success-500"
        />
        <ProductivityItem
          label="ROI Estimate"
          value={roiEstimate}
          helper="Time saved vs. cost (@ $50/hour)"
          valueClassName="text-brand-500"
        />
      </div>
    </div>
  );
}

function ProductivityItem({
  label,
  value,
  helper,
  valueClassName,
}: {
  label: string;
  value: string;
  helper: string;
  valueClassName: string;
}) {
  return (
    <div>
      <p className="text-sm text-foreground-secondary mb-2">{label}</p>
      <p className={`text-3xl font-bold ${valueClassName}`}>{value}</p>
      <p className="text-xs text-foreground-secondary mt-1">{helper}</p>
    </div>
  );
}

function AnalyticsFooter({ generatedAt }: { generatedAt: string }) {
  return (
    <div className="text-center text-xs text-foreground-secondary">
      Generated at {new Date(generatedAt).toLocaleString()} • Auto-refreshes every 5 minutes
    </div>
  );
}

export default AnalyticsSettingsScreen;


