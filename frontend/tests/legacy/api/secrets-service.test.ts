import { beforeEach, describe, expect, it, vi } from "vitest";
import { SecretsService } from "#/api/secrets-service";
import type { Provider } from "#/types/settings";

const forgeGetMock = vi.hoisted(() => vi.fn());
const forgePostMock = vi.hoisted(() => vi.fn());
const forgePutMock = vi.hoisted(() => vi.fn());
const forgeDeleteMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge-axios", () => ({
  Forge: {
    get: forgeGetMock,
    post: forgePostMock,
    put: forgePutMock,
    delete: forgeDeleteMock,
  },
}));

describe("SecretsService", () => {
  beforeEach(() => {
    forgeGetMock.mockReset();
    forgePostMock.mockReset();
    forgePutMock.mockReset();
    forgeDeleteMock.mockReset();
  });

  it("fetches custom secrets", async () => {
    forgeGetMock.mockResolvedValueOnce({ data: { custom_secrets: [{ id: "1" }] } });

    await expect(SecretsService.getSecrets()).resolves.toEqual([{ id: "1" }]);
    expect(forgeGetMock).toHaveBeenCalledWith("/api/secrets");
  });

  it("creates secrets and returns success state", async () => {
    forgePostMock
      .mockResolvedValueOnce({ status: 201 })
      .mockResolvedValueOnce({ status: 500 });

    await expect(SecretsService.createSecret("name", "value", "desc"))
      .resolves.toBe(true);
    expect(forgePostMock).toHaveBeenNthCalledWith(1, "/api/secrets", {
      name: "name",
      value: "value",
      description: "desc",
    });

    await expect(SecretsService.createSecret("name", "value"))
      .resolves.toBe(false);
  });

  it("updates and deletes secrets", async () => {
    forgePutMock
      .mockResolvedValueOnce({ status: 200 })
      .mockResolvedValueOnce({ status: 404 });

    await expect(SecretsService.updateSecret("id", "new", "desc"))
      .resolves.toBe(true);
    expect(forgePutMock).toHaveBeenNthCalledWith(1, "/api/secrets/id", {
      name: "new",
      description: "desc",
    });

    await expect(SecretsService.updateSecret("id", "new"))
      .resolves.toBe(false);

    forgeDeleteMock
      .mockResolvedValueOnce({ status: 200 })
      .mockResolvedValueOnce({ status: 500 });

    await expect(SecretsService.deleteSecret("id"))
      .resolves.toBe(true);
    expect(forgeDeleteMock).toHaveBeenNthCalledWith(1, "/api/secrets/id");

    await expect(SecretsService.deleteSecret("id"))
      .resolves.toBe(false);
  });

  it("adds git providers", async () => {
    const providers = { github: { token: "123" } } as Record<Provider, any>;
    forgePostMock.mockResolvedValueOnce({ data: true });

    await expect(SecretsService.addGitProvider(providers)).resolves.toBe(true);
    expect(forgePostMock).toHaveBeenCalledWith(
      "/api/add-git-providers",
      { provider_tokens: providers },
    );
  });
});
