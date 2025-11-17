import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  listMemories,
  getMemory,
  createMemory,
  updateMemory,
  deleteMemory,
  searchMemories,
  getMemoryStats,
  trackMemoryUsage,
  exportMemories,
  importMemories,
} from "#/api/memory";

const forgeGetMock = vi.hoisted(() => vi.fn());
const forgePostMock = vi.hoisted(() => vi.fn());
const forgePatchMock = vi.hoisted(() => vi.fn());
const forgeDeleteMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
    post: forgePostMock,
    patch: forgePatchMock,
    delete: forgeDeleteMock,
  },
}));

describe("memory api", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
    forgePostMock.mockReset();
    forgePatchMock.mockReset();
    forgeDeleteMock.mockReset();
  });

  it("lists and retrieves memory", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: [{ id: "1" }] })
      .mockResolvedValueOnce({ data: { id: "1" } });

    await expect(listMemories()).resolves.toEqual([{ id: "1" }]);
    await expect(getMemory("1")).resolves.toEqual({ id: "1" });
  });

  it("creates and updates memory", async () => {
    forgePostMock.mockResolvedValueOnce({ data: { status: "ok", memory: { id: "2" } } });
    forgePatchMock.mockResolvedValueOnce({ data: { status: "updated" } });

    await expect(createMemory({ title: "mem" } as any)).resolves.toEqual({
      status: "ok",
      memory: { id: "2" },
    });
    await expect(updateMemory("2", { title: "new" } as any)).resolves.toEqual({ status: "updated" });
    expect(forgePostMock).toHaveBeenCalledWith("/api/memory", { title: "mem" });
    expect(forgePatchMock).toHaveBeenCalledWith("/api/memory/2", { title: "new" });
  });

  it("deletes memory and searches", async () => {
    forgeDeleteMock.mockResolvedValueOnce({});
    forgePostMock.mockResolvedValueOnce({ data: [{ id: "3" }] });

    await deleteMemory("3");
    expect(forgeDeleteMock).toHaveBeenCalledWith("/api/memory/3");

    await expect(searchMemories({ query: "test" } as any)).resolves.toEqual([{ id: "3" }]);
    expect(forgePostMock).toHaveBeenLastCalledWith("/api/memory/search", { query: "test" });
  });

  it("fetches stats, tracks usage, exports and imports", async () => {
    forgeGetMock
      .mockResolvedValueOnce({ data: { total: 1 } })
      .mockResolvedValueOnce({ data: { entries: [] } });
    forgePostMock
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ data: { status: "ok", imported: 1, total: 1 } });

    await expect(getMemoryStats()).resolves.toEqual({ total: 1 });
    await trackMemoryUsage("1");
    expect(forgePostMock).toHaveBeenNthCalledWith(1, "/api/memory/1/track-usage");

    await expect(exportMemories()).resolves.toEqual({ entries: [] });
    await expect(importMemories({ data: [] }, true)).resolves.toEqual({
      status: "ok",
      imported: 1,
      total: 1,
    });
    expect(forgePostMock).toHaveBeenLastCalledWith("/api/memory/import?merge=true", { data: [] });
  });
});
