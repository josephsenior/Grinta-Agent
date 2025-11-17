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
import { useTranslation } from "react-i18next";
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

type ExportFormat = "json" | "csv";

const PERIODS: AnalyticsPeriod[] = ["today", "week", "month", "all"];

function useAnalyticsExport(period: AnalyticsPeriod) {
  const { t } = useTranslation("analytics");

  return useCallback(
    async (format: ExportFormat) => {
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

        displaySuccessToast(
          t("export.success", {
            format: format.toUpperCase(),
            defaultValue: "Analytics exported as {{format}}",
          }),
        );
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : t("common.unknownError", "Unknown error");
        displayErrorToast(
          t("export.error", {
            message,
            defaultValue: "Failed to export analytics: {{message}}",
          }),
        );
      }
    },
    [period, t],
  );
}

function useAnalyticsSettings() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("week");
  const {
    data: dashboard,
    isLoading,
    error,
    refetch,
  } = useAnalyticsDashboard(period);

  const handleExport = useAnalyticsExport(period);
  const handleRefresh = useCallback(() => {
    refetch().catch(() => undefined);
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

function AnalyticsLoadingState() {
  const { t } = useTranslation("analytics");

  return (
    <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin w-8 h-8 border-4 border-white/20 border-t-white/60 rounded-full mx-auto mb-4" />
        <p className="text-foreground-secondary">
          {t("loading.message", "Loading analytics...")}
        </p>
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
  const { t } = useTranslation("analytics");
  const message =
    error instanceof Error
      ? error.message
      : t("error.genericMessage", "An unknown error occurred");

  return (
    <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-8 h-8 text-foreground-tertiary" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          {t("error.title", "Failed to Load Analytics")}
        </h3>
        <p className="text-foreground-secondary mb-4">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-colors"
        >
          {t("error.retry", "Try Again")}
        </button>
      </div>
    </div>
  );
}

function AnalyticsEmptyState() {
  const { t } = useTranslation("analytics");

  return (
    <div className="px-11 py-9 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="w-16 h-16 bg-neutral-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <BarChart3 className="w-8 h-8 text-neutral-500" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          {t("empty.title", "No Data Available")}
        </h3>
        <p className="text-foreground-secondary">
          {t(
            "empty.description",
            "Analytics data will appear here once you have active conversations.",
          )}
        </p>
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
  onChange: (nextPeriod: AnalyticsPeriod) => void;
}) {
  const { t } = useTranslation("analytics");

  return (
    <div className="flex items-center gap-1 p-1 bg-black/60 border border-white/10 rounded-xl">
      {periods.map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all capitalize ${
            period === value
              ? "bg-white text-black shadow-sm"
              : "text-foreground-secondary hover:text-foreground hover:bg-white/5"
          }`}
        >
          {t(`period.${value}`, value)}
        </button>
      ))}
    </div>
  );
}

function ExportMenu({
  onExport,
}: {
  onExport: (format: ExportFormat) => void;
}) {
  const { t } = useTranslation("analytics");

  return (
    <div className="relative group">
      <button
        type="button"
        className="flex items-center gap-2 px-4 py-2 text-sm text-foreground bg-black/60 hover:bg-white/5 border border-white/10 rounded-xl transition-colors"
      >
        <Download className="w-4 h-4" />
        {t("export.button", "Export")}
      </button>
      <div className="absolute right-0 top-full mt-2 w-32 bg-black/90 border border-white/10 rounded-xl shadow-lg overflow-hidden opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 backdrop-blur-xl">
        <button
          type="button"
          onClick={() => onExport("json")}
          className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
        >
          {t("export.formats.json", "JSON")}
        </button>
        <button
          type="button"
          onClick={() => onExport("csv")}
          className="w-full px-4 py-2 text-left text-sm text-foreground hover:bg-black transition-colors"
        >
          {t("export.formats.csv", "CSV")}
        </button>
      </div>
    </div>
  );
}

function PerformanceMetric({
  label,
  value,
}: {
  label: string;
  value?: number;
}) {
  const { t } = useTranslation("analytics");
  const formatted = (value ?? 0).toFixed(2);
  const formattedLabel = t("performance.metricValue", {
    value: formatted,
    defaultValue: "{{value}}s",
  });

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-foreground-secondary">{label}</span>
      <span className="text-lg font-semibold text-foreground">
        {formattedLabel}
      </span>
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
  const { t } = useTranslation("analytics");
  const totalConversations = summary?.totalConversations ?? 0;
  const totalRequests = summary?.totalRequests ?? 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title={t("summary.totalCost.title", "Total Cost")}
        value={`$${(summary?.totalCost ?? 0).toFixed(3)}`}
        icon={DollarSign}
        subtitle={t("summary.totalCost.subtitle", {
          count: totalConversations,
          defaultValue: "{{count}} conversations",
        })}
      />
      <StatCard
        title={t("summary.totalTokens.title", "Total Tokens")}
        value={(summary?.totalTokens ?? 0).toLocaleString()}
        icon={TrendingUp}
        subtitle={t("summary.totalTokens.subtitle", {
          count: totalRequests,
          defaultValue: "{{count}} requests",
        })}
      />
      <StatCard
        title={t("summary.avgResponse.title", "Average Response Time")}
        value={`${(summary?.avgResponseTime ?? 0).toFixed(2)}s`}
        icon={Zap}
        subtitle={t("summary.avgResponse.subtitle", "Average latency")}
      />
      <StatCard
        title={t("summary.conversations.title", "Conversations")}
        value={totalConversations}
        icon={MessageSquare}
        subtitle={t("summary.conversations.subtitle", {
          count: activeConversations,
          defaultValue: "{{count}} active",
        })}
      />
    </div>
  );
}

function PerformanceCard({
  performance,
}: {
  performance: AnalyticsDashboard["performance"];
}) {
  const { t } = useTranslation("analytics");
  const slowestRequests = performance?.slowestRequests ?? [];

  return (
    <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
      <h3 className="text-lg font-semibold text-foreground mb-4">
        {t("performance.heading", "Performance Metrics")}
      </h3>
      <div className="space-y-4">
        <PerformanceMetric
          label={t("performance.average", "Average Response")}
          value={performance?.avgResponseTime}
        />
        <PerformanceMetric
          label={t("performance.percentile95", "95th Percentile")}
          value={performance?.p95ResponseTime}
        />
        <PerformanceMetric
          label={t("performance.percentile99", "99th Percentile")}
          value={performance?.p99ResponseTime}
        />
        {slowestRequests.length > 0 ? (
          <div className="mt-6 pt-4 border-t border-white/10">
            <h4 className="text-sm font-medium text-foreground-secondary mb-3">
              {t("performance.slowestRequests", "Slowest Requests")}
            </h4>
            <div className="space-y-2">
              {slowestRequests.slice(0, 5).map((request, index) => (
                <div
                  key={`${request.model}-${index}`}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-foreground-secondary truncate max-w-[200px]">
                    {request.model}
                  </span>
                  <span className="text-warning-500 font-medium">
                    {t("performance.latencyValue", {
                      value: request.latency.toFixed(2),
                      defaultValue: "{{value}}s",
                    })}
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

function AnalyticsChartsRow({ dashboard }: { dashboard: AnalyticsDashboard }) {
  const { t } = useTranslation("analytics");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <CostChart
        data={dashboard.costs?.byDay || []}
        title={t("charts.costOverTime", "Cost Over Time")}
      />
      <PerformanceCard performance={dashboard.performance} />
    </div>
  );
}

function TopExpensiveConversationsSection({
  conversations,
}: {
  conversations?: AnalyticsDashboard["costs"]["topExpensiveConversations"];
}) {
  const { t } = useTranslation("analytics");

  if (!conversations || conversations.length === 0) {
    return null;
  }

  return (
    <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
      <h3 className="text-lg font-semibold text-foreground mb-4">
        {t("costs.heading", "Most Expensive Conversations")}
      </h3>
      <div className="space-y-2">
        {conversations.map((conversation, index) => (
          <div
            key={conversation.conversationId}
            className="flex items-center justify-between p-3 bg-black rounded-lg hover:bg-black transition-colors"
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="text-sm font-medium text-foreground">
                #{index + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {conversation.title}
                </p>
                <p className="text-xs text-foreground-secondary">
                  {new Date(conversation.timestamp).toLocaleDateString()}
                </p>
              </div>
            </div>
            <span className="text-sm font-semibold text-foreground ml-4">
              {(() => {
                const formattedCost = conversation.cost.toFixed(3);
                const localizedCost = t("costs.amount", {
                  value: formattedCost,
                  defaultValue: "{{value}}",
                });
                return `$${localizedCost}`;
              })()}
            </span>
          </div>
        ))}
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

function ProductivityInsightsSection({
  productivity,
  summary,
}: {
  productivity: AnalyticsDashboard["productivity"];
  summary: AnalyticsDashboard["summary"];
}) {
  const { t } = useTranslation("analytics");
  const estimatedTimeSaved = productivity?.estimatedTimeSaved ?? 0;
  const tasksCompleted = productivity?.tasksCompleted ?? 0;
  const totalCost = summary?.totalCost ?? 0;
  const roiEstimate =
    estimatedTimeSaved > 0 && totalCost > 0
      ? `${(((estimatedTimeSaved || 0) * 50) / (totalCost || 1)).toFixed(0)}x`
      : t("productivity.roi.na", "N/A");

  return (
    <div className="p-5 bg-black/60 border border-white/10 rounded-2xl">
      <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-foreground-tertiary" />
        {t("productivity.heading", "Productivity Insights")}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ProductivityItem
          label={t(
            "productivity.estimatedTimeSaved.label",
            "Estimated Time Saved",
          )}
          value={t("productivity.estimatedTimeSaved.value", {
            value: estimatedTimeSaved.toFixed(1),
            defaultValue: "~{{value}} hours",
          })}
          helper={t("productivity.estimatedTimeSaved.helper", {
            count: tasksCompleted,
            defaultValue: "Based on {{count}} completed tasks",
          })}
          valueClassName="text-foreground"
        />
        <ProductivityItem
          label={t("productivity.score.label", "Productivity Score")}
          value={t("productivity.score.value", {
            score: (productivity?.productivityScore ?? 0).toFixed(0),
            defaultValue: "{{score}}/100",
          })}
          helper={t("productivity.score.helper", "Above industry average")}
          valueClassName="text-success-500"
        />
        <ProductivityItem
          label={t("productivity.roi.label", "ROI Estimate")}
          value={roiEstimate}
          helper={t(
            "productivity.roi.helper",
            "Time saved vs. cost (@ $50/hour)",
          )}
          valueClassName="text-foreground"
        />
      </div>
    </div>
  );
}

function AnalyticsFooter({ generatedAt }: { generatedAt: string }) {
  const { t } = useTranslation("analytics");
  const timestamp = new Date(generatedAt).toLocaleString();

  return (
    <div className="text-center text-xs text-foreground-secondary">
      {t("footer.generatedAt", {
        timestamp,
        refreshInterval: t("footer.refreshInterval", "every 5 minutes"),
        defaultValue:
          "Generated at {{timestamp}} • Auto-refreshes {{refreshInterval}}",
      })}
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
  onChangePeriod: (nextPeriod: AnalyticsPeriod) => void;
  onExport: (format: ExportFormat) => void;
  onRefresh: () => void;
}) {
  const { t } = useTranslation("analytics");

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-8 h-8 text-foreground-tertiary" />
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            {t("header.title", "Analytics Dashboard")}
          </h2>
          <p className="text-sm text-foreground-secondary mt-1">
            {t(
              "header.subtitle",
              "Track usage, costs, and performance insights",
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <PeriodSelector
          period={period}
          periods={PERIODS}
          onChange={onChangePeriod}
        />
        <ExportMenu onExport={onExport} />
        <button
          type="button"
          onClick={onRefresh}
          className="p-2 text-foreground-secondary hover:text-foreground hover:bg-white/5 border border-white/10 rounded-xl transition-colors"
          title={t("header.refresh", "Refresh data")}
        >
          <RefreshCw className="w-5 h-5" />
        </button>
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
  onChangePeriod: (nextPeriod: AnalyticsPeriod) => void;
  onExport: (format: ExportFormat) => void;
  onRefresh: () => void;
}) {
  const activeConversations = useMemo(
    () => dashboard.conversations?.activeConversations ?? 0,
    [dashboard.conversations?.activeConversations],
  );

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <AnalyticsHeader
          period={period}
          onChangePeriod={onChangePeriod}
          onExport={onExport}
          onRefresh={onRefresh}
        />

        <AnalyticsSummaryCards
          summary={dashboard.summary}
          activeConversations={activeConversations}
        />
        <AnalyticsChartsRow dashboard={dashboard} />
        <ModelUsageTable models={dashboard.models} />
        <TopExpensiveConversationsSection
          conversations={dashboard.costs?.topExpensiveConversations}
        />
        <ProductivityInsightsSection
          productivity={dashboard.productivity}
          summary={dashboard.summary}
        />
        <AnalyticsFooter generatedAt={dashboard.generatedAt} />
      </div>
    </div>
  );
}

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

export default AnalyticsSettingsScreen;
