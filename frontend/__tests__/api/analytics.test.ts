import { describe, expect, it, beforeEach, vi } from "vitest";
import {
  getAnalyticsDashboard,
  getAnalyticsSummary,
  getModelUsageStats,
  getCostBreakdown,
  exportAnalytics,
} from "#/api/analytics";

const forgeGetMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
  },
}));

describe("analytics api", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
  });

  it("fetches analytics dashboard with default period", async () => {
    const data = { charts: [] };
    forgeGetMock.mockResolvedValueOnce({ data });

    await expect(getAnalyticsDashboard()).resolves.toBe(data);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/analytics/dashboard", {
      params: { period: "week" },
    });
  });

  it("fetches analytics summary for custom period", async () => {
    const data = { totalRequests: 10 };
    forgeGetMock.mockResolvedValueOnce({ data });

    await expect(getAnalyticsSummary("month")).resolves.toBe(data);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/analytics/summary", {
      params: { period: "month" },
    });
  });

  it("fetches model usage stats", async () => {
    const data = [{ model: "gpt" }];
    forgeGetMock.mockResolvedValueOnce({ data });

    await expect(getModelUsageStats("day" as any)).resolves.toBe(data);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/analytics/models", {
      params: { period: "day" },
    });
  });

  it("fetches cost breakdown", async () => {
    const data = { totalCost: 42 };
    forgeGetMock.mockResolvedValueOnce({ data });

    await expect(getCostBreakdown("quarter" as any)).resolves.toBe(data);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/analytics/costs/breakdown", {
      params: { period: "quarter" },
    });
  });

  it("exports analytics data in specified format", async () => {
    const data = { format: "csv", exported_at: "now", data: [] };
    forgeGetMock.mockResolvedValueOnce({ data });

    await expect(exportAnalytics("year" as any, "csv")).resolves.toBe(data);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/analytics/export", {
      params: { period: "year", format: "csv" },
    });
  });
});
