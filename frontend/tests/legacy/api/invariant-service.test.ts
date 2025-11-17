import { describe, expect, it, beforeEach, vi } from "vitest";
import InvariantService from "#/api/invariant-service";

const forgeGetMock = vi.hoisted(() => vi.fn());
const forgePostMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
    post: forgePostMock,
  },
}));

describe("InvariantService", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
    forgePostMock.mockReset();
  });

  it("retrieves policy", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: { policy: "{}" } });

    await expect(InvariantService.getPolicy()).resolves.toBe("{}");
    expect(forgeGetMock).toHaveBeenCalledWith("/api/security/policy");
  });

  it("retrieves risk severity", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: { RISK_SEVERITY: 3 } });

    await expect(InvariantService.getRiskSeverity()).resolves.toBe(3);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/security/settings");
  });

  it("retrieves traces", async () => {
    const traces = [{ id: 1 }];
    forgeGetMock.mockResolvedValueOnce({ data: traces });

    await expect(InvariantService.getTraces()).resolves.toEqual(traces);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/security/export-trace");
  });

  it("updates policy and risk severity", async () => {
    forgePostMock.mockResolvedValue({});

    await InvariantService.updatePolicy("policy");
    expect(forgePostMock).toHaveBeenNthCalledWith(1, "/api/security/policy", { policy: "policy" });

    await InvariantService.updateRiskSeverity(4);
    expect(forgePostMock).toHaveBeenNthCalledWith(2, "/api/security/settings", { RISK_SEVERITY: 4 });
  });
});
