import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  listPrompts,
  createPrompt,
  getPrompt,
  updatePrompt,
  deletePrompt,
  searchPrompts,
  getPromptStats,
  exportPrompts,
  importPrompts,
  renderPrompt,
  trackPromptUsage,
} from "#/api/prompts";

const API_BASE = "/api/prompts";

const buildResponse = (data: unknown, ok = true, statusText = "OK") => ({
  ok,
  statusText,
  json: async () => data,
});

describe("prompts api", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("lists prompts with filters and without filters", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "1" }]));

    const resultWithFilters = await listPrompts({
      category: "system" as any,
      is_favorite: true,
      limit: 10,
      offset: 5,
    });

    expect(resultWithFilters).toEqual([{ id: "1" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}?category=system&is_favorite=true&limit=10&offset=5`,
    );

    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "2" }]));
    const resultNoFilters = await listPrompts();
    expect(resultNoFilters).toEqual([{ id: "2" }]);
    expect(fetchMock).toHaveBeenLastCalledWith(API_BASE);
  });

  it("throws when listPrompts fails", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Bad"));
    await expect(listPrompts()).rejects.toThrow("Failed to list prompts: Bad");
  });

  it("creates a prompt and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ id: "p" }));

    await expect(createPrompt({ name: "Prompt" } as any)).resolves.toEqual({ id: "p" });
    expect(fetchMock).toHaveBeenCalledWith(API_BASE, expect.objectContaining({ method: "POST" }));

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Nope"));
    await expect(createPrompt({} as any)).rejects.toThrow("Failed to create prompt: Nope");
  });

  it("gets a prompt and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ id: "prompt" }));

    await expect(getPrompt("prompt")).resolves.toEqual({ id: "prompt" });
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/prompt`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Missing"));
    await expect(getPrompt("missing")).rejects.toThrow("Failed to get prompt: Missing");
  });

  it("updates a prompt and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ id: "update" }));

    await expect(updatePrompt("update", { name: "Updated" } as any)).resolves.toEqual({
      id: "update",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/update`,
      expect.objectContaining({ method: "PATCH" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Fail"));
    await expect(updatePrompt("update", {} as any)).rejects.toThrow("Failed to update prompt: Fail");
  });

  it("deletes a prompt and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse(undefined));

    await expect(deletePrompt("del")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/del`, expect.objectContaining({ method: "DELETE" }));

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Denied"));
    await expect(deletePrompt("del")).rejects.toThrow("Failed to delete prompt: Denied");
  });

  it("searches prompts and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse([{ id: "s" }]));

    await expect(searchPrompts({ query: "test" } as any)).resolves.toEqual([{ id: "s" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/search`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Search"));
    await expect(searchPrompts({} as any)).rejects.toThrow("Failed to search prompts: Search");
  });

  it("gets prompt stats and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ total: 1 }));

    await expect(getPromptStats()).resolves.toEqual({ total: 1 });
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/stats`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Stats"));
    await expect(getPromptStats()).rejects.toThrow("Failed to get prompt stats: Stats");
  });

  it("exports prompts with filters and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ prompts: [] }));

    await expect(exportPrompts({ category: "system" as any, is_favorite: false })).resolves.toEqual({
      prompts: [],
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/export?category=system&is_favorite=false`,
    );

    fetchMock.mockResolvedValueOnce(buildResponse({ prompts: [] }));
    await expect(exportPrompts()).resolves.toEqual({ prompts: [] });
    expect(fetchMock).toHaveBeenLastCalledWith(`${API_BASE}/export`);

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Export"));
    await expect(exportPrompts()).rejects.toThrow("Failed to export prompts: Export");
  });

  it("imports prompts and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ imported: 1, total: 1 }));

    await expect(importPrompts({ prompts: [] } as any)).resolves.toEqual({ imported: 1, total: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/import`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Import"));
    await expect(importPrompts({} as any)).rejects.toThrow("Failed to import prompts: Import");
  });

  it("renders prompt and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ rendered: "text" }));

    await expect(renderPrompt({ template: "{{value}}" } as any)).resolves.toEqual({ rendered: "text" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/render`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Render"));
    await expect(renderPrompt({} as any)).rejects.toThrow("Failed to render prompt: Render");
  });

  it("tracks prompt usage and handles failure", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(buildResponse({ id: "use" }));

    await expect(trackPromptUsage("use")).resolves.toEqual({ id: "use" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/use/use`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({ id: "use" }));
    await expect(trackPromptUsage("track-id")).resolves.toEqual({ id: "use" });
    expect(fetchMock).toHaveBeenLastCalledWith(
      `${API_BASE}/track-id/use`,
      expect.objectContaining({ method: "POST" }),
    );

    fetchMock.mockResolvedValueOnce(buildResponse({}, false, "Use"));
    await expect(trackPromptUsage("fail"))
      .rejects.toThrow("Failed to track prompt usage: Use");
  });
});
