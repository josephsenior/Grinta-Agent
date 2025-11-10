import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AnalyticsSettingsScreen from "#/routes/analytics-settings";
import { useAnalyticsDashboard } from "#/hooks/query/use-analytics";
import { exportAnalytics } from "#/api/analytics";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import type { AnalyticsDashboard, AnalyticsPeriod } from "#/types/analytics";

vi.mock("#/hooks/query/use-analytics", () => ({
  useAnalyticsDashboard: vi.fn(),
}));

vi.mock("#/api/analytics", () => ({
  exportAnalytics: vi.fn(),
}));

vi.mock("#/components/features/analytics/stat-card", () => ({
  StatCard: ({ title }: { title: string }) => (
    <div data-testid={`stat-card-${title}`} />
  ),
}));

vi.mock("#/components/features/analytics/cost-chart", () => ({
  CostChart: ({ title }: { title: string }) => (
    <div data-testid={`cost-chart-${title}`} />
  ),
}));

vi.mock("#/components/features/analytics/model-usage-table", () => ({
  ModelUsageTable: ({ models }: { models: unknown[] }) => (
    <div data-testid="model-usage-table">{models.length}</div>
  ),
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: vi.fn(),
  displayErrorToast: vi.fn(),
}));

const mockedUseAnalyticsDashboard = vi.mocked(useAnalyticsDashboard);
const mockedExportAnalytics = vi.mocked(exportAnalytics);
const successToast = vi.mocked(displaySuccessToast);
const errorToast = vi.mocked(displayErrorToast);

const baseDashboard: AnalyticsDashboard = {
  period: "week",
  generatedAt: new Date("2024-01-01T00:00:00Z").toISOString(),
  summary: {
    totalCost: 42,
    totalTokens: 1000,
    totalConversations: 10,
    totalRequests: 25,
    avgResponseTime: 1.23,
  },
  costs: {
    totalCost: 42,
    byModel: { gpt: 20 },
    byDay: [],
    topExpensiveConversations: [
      {
        conversationId: "1",
        title: "Costly convo",
        cost: 12.5,
        timestamp: new Date("2024-01-01").toISOString(),
      },
    ],
  },
  performance: {
    avgResponseTime: 1,
    p95ResponseTime: 2,
    p99ResponseTime: 3,
    slowestRequests: [
      {
        conversationId: "1",
        responseId: "r1",
        latency: 4,
        model: "gpt",
        timestamp: new Date("2024-01-01").toISOString(),
      },
    ],
    requestsByHour: [],
  },
  conversations: {
    totalConversations: 10,
    activeConversations: 3,
    avgConversationDuration: 5,
    conversationsOverTime: [],
    conversationsByTrigger: {},
    conversationsByStatus: {},
  },
  files: {
    totalFilesModified: 0,
    totalLinesAdded: 0,
    totalLinesRemoved: 0,
    topModifiedFiles: [],
    fileTypeBreakdown: {},
  },
  agents: {
    totalActions: 0,
    actionsByType: {},
    successRate: 0,
    errorRate: 0,
    avgIterationsPerTask: 0,
    topAgents: [],
  },
  productivity: {
    estimatedTimeSaved: 5,
    tasksCompleted: 7,
    tasksRejected: 0,
    avgTaskCompletionTime: 30,
    codeQualityTrend: 5,
    productivityScore: 80,
  },
  models: [],
};

const createReturnValue = (overrides: Record<string, unknown> = {}) =>
  ({
    data: baseDashboard,
    isLoading: false,
    isPending: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
    ...overrides,
  }) as unknown as ReturnType<typeof useAnalyticsDashboard>;

describe("AnalyticsSettingsScreen", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockedUseAnalyticsDashboard.mockReset();
    mockedExportAnalytics.mockReset();
    successToast.mockReset();
    errorToast.mockReset();
    mockedUseAnalyticsDashboard.mockImplementation(() =>
      createReturnValue(),
    );
    mockedExportAnalytics
      .mockResolvedValueOnce({ data: { ok: true } } as any)
      .mockResolvedValueOnce({ data: "col1,col2" } as any);

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(() => undefined),
    });

    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );
  });

  it("renders loading state", () => {
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({ isLoading: true }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(screen.getByText("Loading analytics...")).toBeInTheDocument();
  });

  it("renders error state and retries", async () => {
    const refetch = vi.fn();
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({ error: new Error("boom"), refetch }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(
      screen.getByText("Failed to Load Analytics"),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Try Again" }));
    expect(refetch).toHaveBeenCalled();
  });

  it("renders empty state when summary missing", () => {
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({ data: { ...baseDashboard, summary: undefined } }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(screen.getByText("No Data Available")).toBeInTheDocument();
  });

  it("renders dashboard, changes period, refreshes and exports successfully", async () => {
    const refetch = vi.fn();
    mockedUseAnalyticsDashboard.mockImplementation((period?: AnalyticsPeriod) =>
      createReturnValue({
        data: { ...baseDashboard, generatedAt: baseDashboard.generatedAt },
        refetch,
      }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(
      screen.getByText("Analytics Dashboard"),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Refresh data" }));
    expect(refetch).toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "month" }));
    expect(mockedUseAnalyticsDashboard.mock.calls[1]?.[0]).toBe("month");

    await userEvent.click(screen.getByText("JSON"));
    await userEvent.click(screen.getByText("CSV"));

    await waitFor(() =>
      expect(mockedExportAnalytics).toHaveBeenCalledWith("month", "json"),
    );
    await waitFor(() =>
      expect(mockedExportAnalytics).toHaveBeenCalledWith("month", "csv"),
    );
    await waitFor(() => expect(successToast).toHaveBeenCalledTimes(2));
  });

  it("shows error toast when export fails", async () => {
    mockedExportAnalytics.mockReset();
    mockedExportAnalytics.mockRejectedValue(new Error("nope"));

    render(<AnalyticsSettingsScreen />);

    await userEvent.click(screen.getByText("JSON"));

    await waitFor(() =>
      expect(errorToast).toHaveBeenCalledWith(
        "Failed to export analytics: nope",
      ),
    );
  });

  it("renders ROI fallback and hides expensive conversations when no data", () => {
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({
        data: {
          ...baseDashboard,
          productivity: {
            estimatedTimeSaved: 0,
            tasksCompleted: 0,
            tasksRejected: 0,
            avgTaskCompletionTime: 0,
            codeQualityTrend: 0,
            productivityScore: 0,
          },
          summary: {
            totalCost: 0,
            totalTokens: 0,
            totalConversations: 0,
            totalRequests: 0,
            avgResponseTime: 0,
          },
          costs: {
            ...baseDashboard.costs,
            totalCost: 0,
            topExpensiveConversations: [],
          },
          conversations: {
            ...baseDashboard.conversations,
            totalConversations: 0,
            activeConversations: 0,
          },
        },
      }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(
      screen.queryByText("Most Expensive Conversations"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("ROI Estimate")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("omits slowest requests section when none exist", () => {
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({
        data: {
          ...baseDashboard,
          performance: {
            avgResponseTime: 1,
            p95ResponseTime: 2,
            p99ResponseTime: 3,
            slowestRequests: [],
          },
        },
      }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(screen.queryByText("Slowest Requests")).not.toBeInTheDocument();
  });

  it("uses fallback values when summary and time series data are missing", () => {
    mockedUseAnalyticsDashboard.mockReturnValue(
      createReturnValue({
        data: {
          ...baseDashboard,
          summary: {
            totalCost: 0,
            totalTokens: 0,
            totalConversations: 0,
            totalRequests: 0,
            avgResponseTime: 0,
          },
          costs: {
            totalCost: 0,
            byModel: {},
            byDay: [],
            topExpensiveConversations: [],
          },
          performance: {
            avgResponseTime: 0,
            p95ResponseTime: 0,
            p99ResponseTime: 0,
            slowestRequests: [],
            requestsByHour: [],
          },
          models: [],
        },
      }),
    );

    render(<AnalyticsSettingsScreen />);

    expect(screen.getAllByTestId(/stat-card-/)).toHaveLength(4);
    expect(screen.getAllByText(/0\.00s/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Most Expensive Conversations")).not.toBeInTheDocument();
  });
});

