import { describe, expect, it, beforeEach, vi } from "vitest";
import ApiKeysClient from "#/api/api-keys";

const forgeGetMock = vi.hoisted(() => vi.fn());
const forgePostMock = vi.hoisted(() => vi.fn());
const forgeDeleteMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
    post: forgePostMock,
    delete: forgeDeleteMock,
  },
}));

describe("ApiKeysClient", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
    forgePostMock.mockReset();
    forgeDeleteMock.mockReset();
  });

  it("returns API keys array or empty fallback", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: [{ id: "1" }] });
    await expect(ApiKeysClient.getApiKeys()).resolves.toEqual([{ id: "1" }]);

    forgeGetMock.mockResolvedValueOnce({ data: null });
    await expect(ApiKeysClient.getApiKeys()).resolves.toEqual([]);
  });

  it("creates API key with provided name", async () => {
    const created = { id: "1", name: "CI", key: "secret", prefix: "sec", created_at: "now" };
    forgePostMock.mockResolvedValueOnce({ data: created });

    await expect(ApiKeysClient.createApiKey("CI")).resolves.toBe(created);
    expect(forgePostMock).toHaveBeenCalledWith("/api/keys", { name: "CI" });
  });

  it("deletes API key by id", async () => {
    forgeDeleteMock.mockResolvedValueOnce({});

    await ApiKeysClient.deleteApiKey("abc");
    expect(forgeDeleteMock).toHaveBeenCalledWith("/api/keys/abc");
  });
});
