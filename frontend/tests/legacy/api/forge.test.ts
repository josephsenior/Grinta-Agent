import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ForgeClient from "#/api/forge";

const forgeGetMock = vi.hoisted(() => vi.fn());
const forgePostMock = vi.hoisted(() => vi.fn());
const forgePatchMock = vi.hoisted(() => vi.fn());
const forgeDeleteMock = vi.hoisted(() => vi.fn());
const extractNextPageMock = vi.hoisted(() => vi.fn(() => null));
const setCurrentAgentStateMock = vi.hoisted(() =>
  vi.fn((state: unknown) => ({ type: "agent/set", payload: state })),
);
const dispatchMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
    post: forgePostMock,
    patch: forgePatchMock,
    delete: forgeDeleteMock,
  },
}));

vi.mock("#/state/agent-slice", () => ({
  setCurrentAgentState: setCurrentAgentStateMock,
}));

vi.mock("#/store", () => ({
  default: {
    dispatch: dispatchMock,
  },
}));

vi.mock("#/types/agent-state", () => ({
  AgentState: {
    ERROR: "ERROR",
  },
}));

vi.mock("#/utils/extract-next-page-from-link", () => ({
  extractNextPageFromLink: extractNextPageMock,
}));

const conversation = {
  conversation_id: "conv-123",
  url: "https://custom",
  session_api_key: "session-key",
} as any;

describe("ForgeClient", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
    forgePostMock.mockReset();
    forgePatchMock.mockReset();
    forgeDeleteMock.mockReset();
    dispatchMock.mockReset();
    setCurrentAgentStateMock.mockReset();
    extractNextPageMock.mockReset();
    ForgeClient.setCurrentConversation(conversation);
  });

  afterEach(() => {
    ForgeClient.setCurrentConversation(null);
    vi.useRealTimers();
  });

  it("returns cached conversation URL when available", () => {
    ForgeClient.setCurrentConversation({
      conversation_id: "abc",
      url: "https://cached",
    } as any);

    expect(ForgeClient.getConversationUrl("abc")).toBe("https://cached");
    expect(ForgeClient.getConversationUrl("xyz")).toBe("/api/conversations/xyz");
  });

  it("creates headers with optional session api key", () => {
    ForgeClient.setCurrentConversation({
      conversation_id: "123",
      session_api_key: "secret",
    } as any);
    // expect(ForgeClient.getConversationHeaders().get("X-Session-API-Key")).toBe("secret");

    ForgeClient.setCurrentConversation({ conversation_id: "123" } as any);
    // expect(ForgeClient.getConversationHeaders().get("X-Session-API-Key")).toBeUndefined();
  });

  it("fetches files without retry", async () => {
    const response = { entries: [] };
    forgeGetMock.mockResolvedValueOnce({ data: response });

    const result = await ForgeClient.getFiles("conv-123", "/src");

    expect(result).toBe(response);
    expect(forgeGetMock).toHaveBeenCalledTimes(1);
    const [url, options] = forgeGetMock.mock.calls[0];
    expect(url).toBe("https://custom/files/list-files");
    expect(options.params).toEqual({ path: "/src" });
    expect(options.headers.get("X-Session-API-Key")).toBe("session-key");
  });

  it("retries when runtime is temporarily unavailable", async () => {
    vi.useFakeTimers();
    forgeGetMock
      .mockRejectedValueOnce({ message: "Runtime unavailable" })
      .mockResolvedValueOnce({ data: { entries: ["file"] } });

    const promise = ForgeClient.getFiles("conv-123");
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toEqual({ entries: ["file"] });
    expect(forgeGetMock).toHaveBeenCalledTimes(2);
  });

  it("propagates unknown errors from getFiles", async () => {
    const error = new Error("boom");
    forgeGetMock.mockRejectedValueOnce(error);

    await expect(ForgeClient.getFiles("conv-123")).rejects.toBe(error);
  });

  it("marks agent error and throws for permanent 503 failures", async () => {
    forgeGetMock.mockRejectedValueOnce({
      response: { status: 503 },
      message: "permanent failure",
    });

    await expect(ForgeClient.getFiles("conv-123")).rejects.toThrow(
      "Runtime container unavailable. Please start a new conversation.",
    );

    expect(setCurrentAgentStateMock).toHaveBeenCalledWith("ERROR");
    expect(dispatchMock).toHaveBeenCalledWith({
      type: "agent/set",
      payload: "ERROR",
    });
  });

  it("throws specific error when selecting binary files", async () => {
    forgeGetMock.mockRejectedValueOnce({ message: "binary content" });

    await expect(ForgeClient.getFile("conv-123", "binary.dat")).rejects.toThrow(
      "Cannot read binary file",
    );
  });

  it("throws specific errors for directory paths and unsupported media", async () => {
    forgeGetMock.mockRejectedValueOnce({ message: "read directory" });
    await expect(ForgeClient.getFile("conv-123", "dir"))
      .rejects.toThrow("Cannot read directory as file");

    forgeGetMock.mockRejectedValueOnce({ response: { status: 415 }, message: "unsupported" });
    await expect(ForgeClient.getFile("conv-123", "file.ts"))
      .rejects.toThrow("Unsupported file type");
  });

  it("retries reading file when runtime is unavailable", async () => {
    vi.useFakeTimers();
    forgeGetMock
      .mockRejectedValueOnce({ response: { status: 500 }, message: "Runtime unavailable" })
      .mockResolvedValueOnce({ data: { code: "console.log('hi');" } });

    const promise = ForgeClient.getFile("conv-123", "index.ts");
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toBe("console.log('hi');");
    expect(forgeGetMock).toHaveBeenCalledTimes(2);
  });

  it("retries file retrieval when connection is refused", async () => {
    vi.useFakeTimers();
    forgeGetMock
      .mockRejectedValueOnce({ message: "Connection refused" })
      .mockResolvedValueOnce({ data: { code: "ok" } });

    const promise = ForgeClient.getFile("conv-123", "file.ts");
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toBe("ok");
  });

  it("marks agent error when file retrieval receives 503", async () => {
    forgeGetMock.mockRejectedValueOnce({
      response: { status: 503 },
      message: "permanent",
    });

    await expect(ForgeClient.getFile("conv-123", "index.ts"))
      .rejects.toThrow("Runtime container unavailable. Please start a new conversation.");
    expect(setCurrentAgentStateMock).toHaveBeenCalledWith("ERROR");
    expect(dispatchMock).toHaveBeenCalled();
  });

  it("propagates errors that are not retryable for getFile", async () => {
    forgeGetMock.mockRejectedValueOnce(new Error("network"));

    await expect(
      ForgeClient.getFile("conv-123", "file.ts"),
    ).rejects.toThrowError("network");
  });

  it("returns false when feedback existence check fails", async () => {
    forgeGetMock.mockRejectedValueOnce(new Error("network"));

    await expect(
      ForgeClient.checkFeedbackExists("conv-123", 42),
    ).resolves.toEqual({ exists: false });
  });

  it("submit feedback variants use correct endpoints", async () => {
    forgePostMock
      .mockResolvedValueOnce({ data: { ok: true } })
      .mockResolvedValueOnce({ data: { status: "ok", message: "saved" } });

    await expect(
      ForgeClient.submitFeedback("conv", { rating: 5 } as any),
    ).resolves.toEqual({ ok: true });
    await expect(ForgeClient.submitConversationFeedback("conv", 4)).resolves.toEqual({
      status: "ok",
      message: "saved",
    });

    expect(forgePostMock).toHaveBeenNthCalledWith(
      1,
      "/api/conversations/conv/submit-feedback",
      { rating: 5 },
    );
    expect(forgePostMock).toHaveBeenNthCalledWith(
      2,
      "/feedback/conversation",
      expect.objectContaining({ rating: 4, metadata: { source: "likert-scale" } }),
    );
  });

  it("authenticates based on app mode", async () => {
    await expect(ForgeClient.authenticate("oss")).resolves.toBe(true);
    expect(forgePostMock).not.toHaveBeenCalled();

    forgePostMock.mockResolvedValueOnce({ data: {} });
    await expect(ForgeClient.authenticate("saas" as any)).resolves.toBe(true);
    expect(forgePostMock).toHaveBeenCalledWith("/api/authenticate");
  });

  it("wraps simple GET endpoints and returns data", async () => {
    const tests: Array<{
      call: () => Promise<unknown>;
      expectedUrl: string;
      response: unknown;
    }> = [
      { call: () => ForgeClient.getModels(), expectedUrl: "/api/options/models", response: ["gpt"] },
      { call: () => ForgeClient.getAgents(), expectedUrl: "/api/options/agents", response: ["agent"] },
      {
        call: () => ForgeClient.getSecurityAnalyzers(),
        expectedUrl: "/api/options/security-analyzers",
        response: ["trivy"],
      },
      {
        call: () => ForgeClient.getConfig(),
        expectedUrl: "/api/options/config",
        response: {
          APP_MODE: "oss",
          GITHUB_CLIENT_ID: "test-id",
          FEATURE_FLAGS: { HIDE_LLM_SETTINGS: false },
        },
      },
      {
        call: () => ForgeClient.getSettings(),
        expectedUrl: "/api/settings",
        response: { theme: "dark" },
      },
      {
        call: () => ForgeClient.getSubscriptionAccess(),
        expectedUrl: "/api/billing/subscription-access",
        response: { allowed: true },
      },
      {
        call: () => ForgeClient.getUserInstallationIds("github" as any),
        expectedUrl: "/api/user/installations?provider=github",
        response: ["1", "2"],
      },
    ];

    for (const { call, expectedUrl, response } of tests) {
      forgeGetMock.mockResolvedValueOnce({ data: response });
      await expect(call()).resolves.toEqual(response);
      const lastCall = forgeGetMock.mock.calls.at(-1);
      expect(lastCall?.[0]).toBe(expectedUrl);
    }
  });

  it("wraps conversation-based GET endpoints", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: { blob: true } }) // getWorkspaceZip
      .mockResolvedValueOnce({ data: { hosts: { a: {}, b: {} } } })
      .mockResolvedValueOnce({ data: { runtime_id: "r1" } });

    await expect(ForgeClient.getWorkspaceZip("conv-123")).resolves.toEqual({ blob: true });
    await expect(ForgeClient.getWebHosts("conv-123")).resolves.toEqual(["a", "b"]);
    await expect(ForgeClient.getRuntimeId("conv-123")).resolves.toEqual({ runtime_id: "r1" });
  });

  it("queries user conversations and search results", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }] } })
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }, { id: 2 }] } });

    await expect(ForgeClient.getUserConversations(10, "page"))
      .resolves.toEqual({ results: [{ id: 1 }] });
    const firstCall = forgeGetMock.mock.calls[0];
    expect(firstCall[0]).toBe("/api/conversations?limit=10&page_id=page");

    await expect(ForgeClient.searchConversations("repo", "trigger", 5)).resolves.toEqual([
      { id: 1 },
      { id: 2 },
    ]);
  });

  it("mutates conversations via POST/PATCH/DELETE", async () => {
    forgeDeleteMock.mockResolvedValueOnce({});
    forgePostMock
      .mockResolvedValueOnce({ data: { id: "created" } })
      .mockResolvedValueOnce({ data: { started: true } })
      .mockResolvedValueOnce({ data: { stopped: true } });
    forgePatchMock.mockResolvedValueOnce({ data: true });

    await ForgeClient.deleteUserConversation("conv");
    expect(forgeDeleteMock).toHaveBeenCalledWith("/api/conversations/conv");

    await expect(ForgeClient.createConversation("repo"))
      .resolves.toEqual({ id: "created" });
    await expect(ForgeClient.startConversation("conv"))
      .resolves.toEqual({ started: true });
    await expect(ForgeClient.stopConversation("conv"))
      .resolves.toEqual({ stopped: true });
    await expect(ForgeClient.updateConversation("conv", { title: "Hi" }))
      .resolves.toBe(true);

    expect(forgePatchMock).toHaveBeenCalledWith(
      "/api/conversations/conv",
      { title: "Hi" },
    );
  });

  it("handles billing and settings POST endpoints", async () => {
    forgePostMock.mockResolvedValueOnce({ status: 200 });
    forgeGetMock.mockResolvedValueOnce({ data: { APP_MODE: "saas" } });

    await expect(ForgeClient.saveSettings({})).resolves.toBe(true);
    await expect(ForgeClient.getConfig()).resolves.toEqual({ APP_MODE: "saas" });
  });

  it("maps git user payload", async () => {
    const apiUser = {
      id: 1,
      login: "me",
      avatar_url: "avatar",
      company: "co",
      name: "User",
      email: "user@example.com",
    };
    forgeGetMock.mockResolvedValueOnce({ data: apiUser });

    await expect(ForgeClient.getGitUser()).resolves.toEqual(apiUser);
  });

  it("searches git repositories with query parameters", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: [{ id: "repo" }] });

    await expect(ForgeClient.searchGitRepositories("demo", 10, "github" as any))
      .resolves.toEqual([{ id: "repo" }]);
    expect(forgeGetMock).toHaveBeenCalledWith(
      "/api/user/search/repositories",
      {
        params: {
          query: "demo",
          per_page: 10,
          selected_provider: "github",
        },
      },
    );
  });

  it("searches git repositories and supports pagination helpers", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: [{ link_header: "<next>; rel=next" }] })
      .mockResolvedValueOnce({ data: [{ link_header: "" }] });
    extractNextPageMock.mockReturnValueOnce(20 as any).mockReturnValueOnce(null);

    await expect(
      ForgeClient.retrieveUserGitRepositories("github" as any, 1, 30),
    ).resolves.toEqual({ data: [{ link_header: "<next>; rel=next" }], nextPage: 20 });
    await expect(
      ForgeClient.retrieveInstallationRepositories("github" as any, 0, ["inst"], 1, 30),
    ).resolves.toEqual({ data: [{ link_header: "" }], nextPage: null, installationIndex: null });
  });

  it("advances installation pagination when more pages exist", async () => {
    extractNextPageMock.mockReturnValueOnce(2 as any);
    forgeGetMock.mockResolvedValueOnce({ data: [{ link_header: "link" }] });

    await expect(
      ForgeClient.retrieveInstallationRepositories("github" as any, 2, ["a", "b", "c"], 1, 30),
    ).resolves.toEqual({ data: [{ link_header: "link" }], nextPage: 2, installationIndex: 2 });

    extractNextPageMock.mockReturnValueOnce(null);
    forgeGetMock.mockResolvedValueOnce({ data: [{ link_header: "link" }] });

    await expect(
      ForgeClient.retrieveInstallationRepositories("github" as any, 0, ["a", "b"], 1, 30),
    ).resolves.toEqual({ data: [{ link_header: "link" }], nextPage: null, installationIndex: 1 });
  });

  it("fetches git info and trajectory data", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: { diff: true } })
      .mockResolvedValueOnce({ data: { changes: [] } })
      .mockResolvedValueOnce({ data: { branches: [] } })
      .mockResolvedValueOnce({ data: [{ name: "branch" }] })
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }] } })
      .mockResolvedValueOnce({ data: { runtime_id: "r2" } });

    await expect(ForgeClient.getGitChangeDiff("conv-123", "path"))
      .resolves.toEqual({ diff: true });
    await expect(ForgeClient.getGitChanges("conv-123")).resolves.toEqual({ changes: [] });
    await expect(ForgeClient.getRepositoryBranches("repo", 2, 10)).resolves.toEqual({ branches: [] });
    await expect(ForgeClient.searchRepositoryBranches("repo", "main", 5))
      .resolves.toEqual([{ name: "branch" }]);
    await expect(ForgeClient.getPlaybookManagementConversations("repo"))
      .resolves.toEqual([{ id: 1 }]);
  });

  it("handles playbook endpoints", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: { agents: [] } })
      .mockResolvedValueOnce({ data: [{ id: "m1" }] })
      .mockResolvedValueOnce({ data: { content: "file" } });

    await expect(ForgeClient.getPlaybooks("conv-123"))
      .resolves.toEqual({ agents: [] });
    await expect(ForgeClient.getRepositoryPlaybooks("me", "repo"))
      .resolves.toEqual([{ id: "m1" }]);
    await expect(ForgeClient.getRepositoryPlaybookContent("me", "repo", "path"))
      .resolves.toEqual({ content: "file" });
  });

  it("includes page identifier when fetching playbook management conversations", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: { results: [] } });

    await ForgeClient.getPlaybookManagementConversations("repo", "next", 50);
    expect(forgeGetMock).toHaveBeenCalledWith(
      "/api/playbook-management/conversations",
      { params: { limit: 50, selected_repository: "repo", page_id: "next" } },
    );
  });

  it("logout respects app mode", async () => {
    forgePostMock.mockResolvedValueOnce({}).mockResolvedValueOnce({});

    await ForgeClient.logout("saas" as any);
    expect(forgePostMock).toHaveBeenNthCalledWith(1, "/api/logout");

    await ForgeClient.logout("oss" as any);
    expect(forgePostMock).toHaveBeenNthCalledWith(2, "/api/unset-provider-tokens");
  });

  it("uploads files with multipart form data", async () => {
    forgePostMock.mockResolvedValueOnce({ data: { uploaded: ["a"] } });
    const file = new File(["content"], "test.txt", { type: "text/plain" });

    await expect(ForgeClient.uploadFiles("conv-123", [file]))
      .resolves.toEqual({ uploaded: ["a"] });
    const [, formData] = forgePostMock.mock.calls[0];
    expect((formData as FormData).getAll("files").length).toBe(1);
  });

  it("retrieves workspace trajectory", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: { path: [] } });

    await expect(ForgeClient.getTrajectory("conv-123"))
      .resolves.toEqual({ path: [] });
  });
});
