import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  listSlackWorkspaces,
  getSlackInstallUrl,
  uninstallSlackWorkspace,
} from "#/api/slack";

const buildResponse = (data: unknown, ok = true, statusText = "OK") => ({
  ok,
  statusText,
  json: async () => data,
});

describe("slack api", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("lists workspaces and handles missing data", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ workspaces: [{ team_id: "T1", team_name: "Team" }] }));

    await expect(listSlackWorkspaces()).resolves.toEqual([
      { team_id: "T1", team_name: "Team" },
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/api/slack/workspaces");

    fetchMock.mockResolvedValueOnce(buildResponse({}));
    await expect(listSlackWorkspaces()).resolves.toEqual([]);
  });

  it("throws when listing workspaces fails", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Bad"));
    await expect(listSlackWorkspaces()).rejects.toThrow("Failed to list Slack workspaces: Bad");
  });

  it("gets install url with optional redirect", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ url: "https://install" }));

    await expect(getSlackInstallUrl({ redirect_url: "https://redirect" })).resolves.toEqual({ url: "https://install" });
    expect(fetchMock).toHaveBeenCalledWith("/api/slack/install?redirect_url=https%3A%2F%2Fredirect");

    fetchMock.mockResolvedValueOnce(buildResponse({ url: "https://install" }));
    await expect(getSlackInstallUrl()).resolves.toEqual({ url: "https://install" });
    expect(fetchMock).toHaveBeenLastCalledWith("/api/slack/install?");
  });

  it("throws when getting install url fails", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Install"));
    await expect(getSlackInstallUrl()).rejects.toThrow("Failed to get Slack install URL: Install");
  });

  it("uninstalls workspace and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse(undefined));

    await expect(uninstallSlackWorkspace("T1")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/slack/workspaces/T1",
      expect.objectContaining({ method: "DELETE" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Uninstall"));
    await expect(uninstallSlackWorkspace("T1")).rejects.toThrow(
      "Failed to uninstall Slack workspace: Uninstall",
    );
  });
});
