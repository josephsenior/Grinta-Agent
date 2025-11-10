import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  listDatabaseConnections,
  createDatabaseConnection,
  updateDatabaseConnection,
  deleteDatabaseConnection,
  getDatabaseSchema,
  executeQuery,
  testDatabaseConnection,
} from "#/api/database-connections";

type ForgeMethods = {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

const forgeMocks = vi.hoisted<ForgeMethods>(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("#/api/forge-axios", () => ({
  Forge: forgeMocks,
}));

describe("database connections api", () => {
  beforeEach(() => {
    forgeMocks.get.mockReset();
    forgeMocks.post.mockReset();
    forgeMocks.patch.mockReset();
    forgeMocks.delete.mockReset();
  });

  it("lists database connections", async () => {
    const data = [{ id: "1" }];
    forgeMocks.get.mockResolvedValueOnce({ data });

    await expect(listDatabaseConnections()).resolves.toBe(data);
    expect(forgeMocks.get).toHaveBeenCalledWith("/api/database-connections");
  });

  it("creates database connection", async () => {
    const payload = { name: "db" } as any;
    const response = { connection: { id: "1" } };
    forgeMocks.post.mockResolvedValueOnce({ data: response });

    await expect(createDatabaseConnection(payload)).resolves.toEqual({ id: "1" });
    expect(forgeMocks.post).toHaveBeenCalledWith("/api/database-connections", payload);
  });

  it("updates database connection", async () => {
    const response = { connection: { id: "1", name: "updated" } };
    forgeMocks.patch.mockResolvedValueOnce({ data: response });

    await expect(updateDatabaseConnection("1", { name: "updated" })).resolves.toEqual({
      id: "1",
      name: "updated",
    });
    expect(forgeMocks.patch).toHaveBeenCalledWith("/api/database-connections/1", { name: "updated" });
  });

  it("deletes database connection", async () => {
    forgeMocks.delete.mockResolvedValueOnce({});

    await deleteDatabaseConnection("abc");
    expect(forgeMocks.delete).toHaveBeenCalledWith("/api/database-connections/abc");
  });

  it("retrieves schema information", async () => {
    const schema = { tables: [] };
    forgeMocks.get.mockResolvedValueOnce({ data: schema });

    await expect(getDatabaseSchema("1")).resolves.toBe(schema);
    expect(forgeMocks.get).toHaveBeenCalledWith("/api/database-connections/1/schema");
  });

  it("executes query with defaults", async () => {
    const result = { rows: [] };
    forgeMocks.post.mockResolvedValueOnce({ data: result });

    await expect(executeQuery("1", "SELECT 1"))
      .resolves.toBe(result);
    expect(forgeMocks.post).toHaveBeenCalledWith(
      "/api/database-connections/1/query",
      { query: "SELECT 1", limit: 1000, timeout: 30 },
    );
  });

  it("executes query with custom options", async () => {
    forgeMocks.post.mockResolvedValueOnce({ data: { rows: [1] } });

    await expect(executeQuery("2", "SELECT", 10, 5)).resolves.toEqual({ rows: [1] });
    expect(forgeMocks.post).toHaveBeenCalledWith(
      "/api/database-connections/2/query",
      { query: "SELECT", limit: 10, timeout: 5 },
    );
  });

  it("tests database connection", async () => {
    const data = { success: true } as any;
    forgeMocks.post.mockResolvedValueOnce({ data });

    await expect(testDatabaseConnection({ host: "localhost" } as any)).resolves.toBe(data);
    expect(forgeMocks.post).toHaveBeenCalledWith(
      "/api/database-connections/test",
      { host: "localhost" },
    );
  });
});
