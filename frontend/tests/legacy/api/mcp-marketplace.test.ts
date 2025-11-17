import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchMarketplaceMCPs,
  fetchMarketplaceMCP,
  clearMarketplaceCache,
} from "#/api/mcp-marketplace";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

const CACHE_KEY = "mcp-marketplace-cache";

declare global {
  // eslint-disable-next-line no-var
  var localStorage: Storage;
}

const createResponse = (data: unknown, ok = true, statusText = "OK", status = 200) => ({
  ok,
  status,
  statusText,
  json: async () => data,
});

describe("mcp-marketplace api", () => {
  const originalFetch = global.fetch;
  const originalLocalStorage = global.localStorage;
  let loggerWarnSpy: ReturnType<typeof vi.spyOn>;
  let loggerErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    const storage = new Map<string, string>();
    global.localStorage = {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
      removeItem: (key: string) => {
        storage.delete(key);
      },
      clear: () => storage.clear(),
      key: (index: number) => Array.from(storage.keys())[index] ?? null,
      get length() {
        return storage.size;
      },
    } as Storage;

    global.fetch = vi.fn() as unknown as typeof fetch;
    loggerWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    loggerErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    loggerWarnSpy.mockRestore();
    loggerErrorSpy.mockRestore();
    global.fetch = originalFetch;
    global.localStorage = originalLocalStorage;
  });

  it("uses cached data when available", async () => {
    const cached: MCPMarketplaceItem[] = [
      {
        id: "cached",
        name: "Cached",
        slug: "cached",
        description: "cached item",
        longDescription: "cached item",
        author: "Test",
        icon: "🌐",
        category: "browser",
        type: "stdio",
        featured: true,
        popular: true,
        installCount: 1,
        rating: 4.5,
        version: "1.0.0",
        homepage: "https://example.com",
        repository: "https://example.com/repo",
        documentation: "https://example.com/docs",
        config: { command: "npx", args: ["pkg"] },
        tags: ["browser"],
        requirements: { node: ">=18.0.0" },
      },
    ];

    const cachePayload = {
      timestamp: Date.now(),
      data: cached,
    };
    global.localStorage.setItem(CACHE_KEY, JSON.stringify(cachePayload));

    const response = await fetchMarketplaceMCPs();
    expect(response.items).toEqual(cached);
    expect(global.fetch).not.toHaveBeenCalled();

    const single = await fetchMarketplaceMCP("cached");
    expect(single).toEqual(cached[0]);
  });

  it("applies filters and search against cached data", async () => {
    const cachedItems: MCPMarketplaceItem[] = [
      {
        id: "feature",
        name: "Browser Helper",
        slug: "browser-helper",
        description: "Automates browsers",
        longDescription: "Automates browsers",
        author: "Tester",
        icon: "🌐",
        category: "browser",
        type: "stdio",
        featured: true,
        popular: false,
        installCount: 10,
        rating: 4,
        version: "1.0",
        homepage: "https://example.com",
        repository: "https://example.com/repo",
        documentation: "https://example.com/docs",
        config: { command: "npx", args: ["pkg"] },
        tags: ["automation"],
        requirements: { node: ">=18.0.0" },
      },
      {
        id: "popular",
        name: "Database Tool",
        slug: "database-tool",
        description: "Manage databases",
        longDescription: "Manage databases",
        author: "Tester",
        icon: "🗄️",
        category: "database",
        type: "stdio",
        featured: false,
        popular: true,
        installCount: 2000,
        rating: 5,
        version: "1.0",
        homepage: "https://example.com",
        repository: "https://example.com/repo",
        documentation: "https://example.com/docs",
        config: { command: "npx", args: ["pkg"] },
        tags: ["database"],
        requirements: { node: ">=18.0.0" },
      },
    ];

    global.localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ timestamp: Date.now(), data: cachedItems }),
    );

    const featuredResult = await fetchMarketplaceMCPs({ category: "browser", featured: true, search: "automation" });
    expect(featuredResult.items).toHaveLength(1);
    expect(featuredResult.items[0].id).toBe("feature");

    const popularResult = await fetchMarketplaceMCPs({ category: "database", popular: true, search: "nomatch" });
    expect(popularResult.items).toHaveLength(0);
  });

  it("fetches live data from multiple sources and caches result", async () => {
    const smitheryData = {
      servers: [
        {
          id: "smithery-1",
          name: "Browser Tool",
          description: "browser automation",
          qualifiedName: "browser/tool",
          tags: ["browser"],
          config: { command: "npx", args: ["smithery/pkg"] },
          rating: 4.6,
          version: "2.0",
          homepage: "https://smithery.dev",
          repository: "https://github.com/smithery/browser",
          documentation: "https://smithery.dev/docs",
        },
        {
          name: "github-tool",
          description: "general purpose tool",
          popular: true,
          downloads: 500,
          rating: "4.2",
          tags: ["git"],
        },
      ],
    };
    const npmData = {
      objects: [
        {
          package: {
            name: "@modelcontextprotocol/server-db",
            description: "database helper",
            homepage: "https://npm.dev",
            version: "1.2.3",
            author: { name: "MCP" },
          },
          score: { final: 0.8 },
        },
      ],
    };
    const githubData = {
      items: [
        {
          name: "github-tool",
          description: "git helper",
          topics: ["git"],
          stargazers_count: 120,
          owner: { login: "owner" },
          html_url: "https://github.com/owner/github-tool",
          homepage: "https://github.com/owner",
          full_name: "owner/github-tool",
        },
        {
          name: "utility-tool",
          description: "helper",
          stargazers_count: 10,
          owner: { login: "helper" },
          html_url: "https://github.com/helper/utility",
        },
      ],
    };
    const officialData = {
      servers: [
        {
          id: "official-1",
          name: "Security Tool",
          description: "security helper",
          slug: "security-tool",
          type: "stdio",
          homepage: "https://official.dev",
          repository: "https://github.com/official/security",
          documentation: "https://docs.official.dev",
          tags: ["security"],
        },
        {
          name: "Misc Tool",
          description: "miscellaneous",
        },
      ],
    };

    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    global.localStorage.setItem("smithery-api-key", "token");
    fetchMock
      .mockResolvedValueOnce(createResponse(smitheryData))
      .mockResolvedValueOnce(createResponse(npmData))
      .mockResolvedValueOnce(createResponse(githubData))
      .mockResolvedValueOnce(createResponse(officialData));

    const response = await fetchMarketplaceMCPs({ category: "browser", type: "all" });

    expect(fetchMock).toHaveBeenCalledTimes(4);
    const firstCallHeaders = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(firstCallHeaders?.Authorization).toBe("Bearer token");
    expect(response.total).toBeGreaterThan(0);
    expect(response.categories.length).toBeGreaterThan(0);
    expect(global.localStorage.getItem(CACHE_KEY)).not.toBeNull();

    const cachedItem = await fetchMarketplaceMCP("smithery-1");
    expect(cachedItem?.id).toBe("smithery-1");
  });

  it("falls back to curated MCPs when all sources fail", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(createResponse({}, false, "error", 500));

    const response = await fetchMarketplaceMCPs();
    expect(response.items.length).toBeGreaterThan(0);
    expect(loggerWarnSpy).toHaveBeenCalled();
  });

  it("clears marketplace cache gracefully", async () => {
    global.localStorage.setItem(CACHE_KEY, "test");
    clearMarketplaceCache();
    expect(global.localStorage.getItem(CACHE_KEY)).toBeNull();
  });

  it("ignores errors when clearing marketplace cache", () => {
    const throwingStorage = {
      ...global.localStorage,
      removeItem: () => {
        throw new Error("fail");
      },
    } as Storage;
    global.localStorage = throwingStorage;

    expect(() => clearMarketplaceCache()).not.toThrow();
  });

  it("handles invalid cached data", async () => {
    global.localStorage.setItem(CACHE_KEY, "not-json");

    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(createResponse({ servers: [] }));

    await fetchMarketplaceMCPs();
    expect(loggerErrorSpy).toHaveBeenCalledWith("Error reading cache:", expect.any(SyntaxError));
  });

  it("falls back when caching live data fails", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(createResponse({ servers: [] }));

    global.localStorage.setItem = () => {
      throw new Error("write fail");
    };

    const result = await fetchMarketplaceMCPs();
    expect(result.items.length).toBeGreaterThan(0);
    expect(loggerErrorSpy).toHaveBeenCalledWith(
      "Error writing cache:",
      expect.any(Error),
    );
  });
});
