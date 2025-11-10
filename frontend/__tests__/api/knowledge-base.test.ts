import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createCollection,
  getCollections,
  getCollection,
  updateCollection,
  deleteCollection,
  uploadDocument,
  getDocuments,
  getDocument,
  deleteDocument,
  searchKnowledgeBase,
  getKnowledgeBaseStats,
} from "#/api/knowledge-base";

type MockResponse = {
  ok: boolean;
  statusText: string;
  json: () => Promise<any>;
};

const createResponse = (data: unknown, ok = true, statusText = "OK"): MockResponse => ({
  ok,
  statusText,
  json: async () => data,
});

describe("knowledge-base api", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("creates collection and handles errors", async () => {
    (global.fetch as any).mockResolvedValueOnce(createResponse({ id: "1" }));
    await expect(createCollection({ name: "Docs" } as any)).resolves.toEqual({ id: "1" });
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/knowledge-base/collections",
      expect.objectContaining({ method: "POST" }),
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Bad"));
    await expect(createCollection({} as any)).rejects.toThrow("Failed to create collection: Bad");
  });

  it("retrieves collections and single collection", async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createResponse([{ id: "1" }]))
      .mockResolvedValueOnce(createResponse({ id: "1" }));

    await expect(getCollections()).resolves.toEqual([{ id: "1" }]);
    await expect(getCollection("1")).resolves.toEqual({ id: "1" });
  });

  it("throws when collections endpoint fails", async () => {
    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Nope"));
    await expect(getCollections()).rejects.toThrow("Failed to fetch collections: Nope");

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Missing"));
    await expect(getCollection("abc")).rejects.toThrow("Failed to fetch collection: Missing");
  });

  it("updates collection and deletes it", async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createResponse({ id: "1", name: "Updated" }))
      .mockResolvedValueOnce(createResponse(undefined));

    await expect(updateCollection("1", { name: "Updated" }))
      .resolves.toEqual({ id: "1", name: "Updated" });
    await expect(deleteCollection("1")).resolves.toBeUndefined();
  });

  it("throws when update or delete fails", async () => {
    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Bad update"));
    await expect(updateCollection("1", {} as any)).rejects.toThrow(
      "Failed to update collection: Bad update",
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Bad delete"));
    await expect(deleteCollection("1")).rejects.toThrow(
      "Failed to delete collection: Bad delete",
    );
  });

  it("uploads document and lists documents", async () => {
    const file = new File(["content"], "doc.txt", { type: "text/plain" });
    (global.fetch as any)
      .mockResolvedValueOnce(createResponse({ id: "doc" }))
      .mockResolvedValueOnce(createResponse([{ id: "doc" }]))
      .mockResolvedValueOnce(createResponse({ id: "doc" }));

    await expect(uploadDocument("1", file)).resolves.toEqual({ id: "doc" });
    await expect(getDocuments("1")).resolves.toEqual([{ id: "doc" }]);
    await expect(getDocument("1", "doc")).resolves.toEqual({ id: "doc" });
  });

  it("throws when document endpoints fail", async () => {
    const file = new File(["content"], "doc.txt", { type: "text/plain" });
    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Upload"));
    await expect(uploadDocument("1", file)).rejects.toThrow(
      "Failed to upload document: Upload",
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Docs"));
    await expect(getDocuments("1")).rejects.toThrow(
      "Failed to fetch documents: Docs",
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Doc"));
    await expect(getDocument("1", "doc")).rejects.toThrow(
      "Failed to fetch document: Doc",
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Delete"));
    await expect(deleteDocument("1", "doc")).rejects.toThrow(
      "Failed to delete document: Delete",
    );
  });

  it("searches knowledge base and fetches stats", async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createResponse([{ score: 1 }]))
      .mockResolvedValueOnce(createResponse({ documents: 10 }));

    await expect(searchKnowledgeBase({ query: "test" } as any)).resolves.toEqual([{ score: 1 }]);
    await expect(getKnowledgeBaseStats()).resolves.toEqual({ documents: 10 });
  });

  it("throws when search or stats fail", async () => {
    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Search"));
    await expect(searchKnowledgeBase({} as any)).rejects.toThrow(
      "Failed to search knowledge base: Search",
    );

    (global.fetch as any).mockResolvedValueOnce(createResponse({}, false, "Stats"));
    await expect(getKnowledgeBaseStats()).rejects.toThrow(
      "Failed to fetch knowledge base stats: Stats",
    );
  });
});
