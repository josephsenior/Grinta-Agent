import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  listSnippets,
  createSnippet,
  getSnippet,
  updateSnippet,
  deleteSnippet,
  searchSnippets,
  getSnippetStats,
  exportSnippets,
  importSnippets,
  trackSnippetUsage,
} from "#/api/snippets";

const API_BASE = "/api/snippets";

const buildResponse = (data: unknown, ok = true, statusText = "OK") => ({
  ok,
  statusText,
  json: async () => data,
});

describe("snippets api", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("lists snippets with and without filters", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "1" }]));

    await expect(listSnippets({ language: "ts" as any, category: "utils" as any, is_favorite: true, limit: 10, offset: 5 }))
      .resolves.toEqual([{ id: "1" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}?language=ts&category=utils&is_favorite=true&limit=10&offset=5`,
    );

    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "2" }]));
    await expect(listSnippets()).resolves.toEqual([{ id: "2" }]);
    expect(fetchMock).toHaveBeenLastCalledWith(API_BASE);
  });

  it("throws when listing snippets fails", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Fail"));
    await expect(listSnippets()).rejects.toThrow("Failed to list snippets: Fail");
  });

  it("creates, gets, updates, and deletes snippets", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;

    fetchMock.mockResolvedValueOnce(buildResponse({ id: "created" }));
    await expect(createSnippet({} as any)).resolves.toEqual({ id: "created" });
    expect(fetchMock).toHaveBeenCalledWith(
      API_BASE,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Create"));
    await expect(createSnippet({} as any)).rejects.toThrow("Failed to create snippet: Create");

    fetchMock.mockResolvedValueOnce(buildResponse({ id: "get" }));
    await expect(getSnippet("id"))
      .resolves.toEqual({ id: "get" });
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/id`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Get"));
    await expect(getSnippet("id"))
      .rejects.toThrow("Failed to get snippet: Get");

    fetchMock.mockResolvedValueOnce(buildResponse({ id: "update" }));
    await expect(updateSnippet("id", { name: "new" } as any))
      .resolves.toEqual({ id: "update" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/id`,
      expect.objectContaining({ method: "PATCH" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Update"));
    await expect(updateSnippet("id", {} as any))
      .rejects.toThrow("Failed to update snippet: Update");

    fetchMock.mockResolvedValueOnce(buildResponse(undefined));
    await expect(deleteSnippet("id")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/id`,
      expect.objectContaining({ method: "DELETE" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Delete"));
    await expect(deleteSnippet("id"))
      .rejects.toThrow("Failed to delete snippet: Delete");
  });

  it("searches snippets and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "search" }]));

    await expect(searchSnippets({ query: "code" } as any)).resolves.toEqual([{ id: "search" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/search`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Search"));
    await expect(searchSnippets({} as any)).rejects.toThrow("Failed to search snippets: Search");
  });

  it("gets stats and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ total: 1 }));

    await expect(getSnippetStats()).resolves.toEqual({ total: 1 });
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/stats`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Stats"));
    await expect(getSnippetStats()).rejects.toThrow("Failed to get snippet stats: Stats");
  });

  it("exports snippets with filters and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ snippets: [] }));

    await expect(exportSnippets({ language: "ts" as any, category: "utils" as any, is_favorite: false }))
      .resolves.toEqual({ snippets: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/export?language=ts&category=utils&is_favorite=false`,
    );

    fetchMock.mockResolvedValueOnce(buildResponse({ snippets: [] }));
    await expect(exportSnippets()).resolves.toEqual({ snippets: [] });
    expect(fetchMock).toHaveBeenLastCalledWith(`${API_BASE}/export`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Export"));
    await expect(exportSnippets()).rejects.toThrow("Failed to export snippets: Export");
  });

  it("imports snippets and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ imported: 1, total: 1 }));

    await expect(importSnippets({ snippets: [] } as any)).resolves.toEqual({ imported: 1, total: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/import`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Import"));
    await expect(importSnippets({} as any)).rejects.toThrow("Failed to import snippets: Import");
  });

  it("tracks snippet usage and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ id: "use" }));

    await expect(trackSnippetUsage("id")).resolves.toEqual({ id: "use" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/id/use`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Use"));
    await expect(trackSnippetUsage("id")).rejects.toThrow("Failed to track snippet usage: Use");
  });
});
