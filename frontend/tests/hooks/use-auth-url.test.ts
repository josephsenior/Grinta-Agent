import { describe, expect, it, beforeEach, afterAll, vi } from "vitest";
import { useAuthUrl } from "#/hooks/use-auth-url";

const generateAuthUrlMock = vi.hoisted(() => vi.fn(() => "https://auth"));

vi.mock("#/utils/generate-auth-url", () => ({
  generateAuthUrl: generateAuthUrlMock,
}));

describe("useAuthUrl", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    generateAuthUrlMock.mockClear();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("https://app.example.com/dashboard"),
    });
  });

  afterAll(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("returns generated auth URL in saas mode", () => {
    const result = useAuthUrl({
      appMode: "saas",
      identityProvider: "github",
      authUrl: "https://auth.example.com",
    } as any);

    expect(result).toBe("https://auth");
    expect(generateAuthUrlMock).toHaveBeenCalledWith(
      "github",
      new URL("https://app.example.com/dashboard"),
      "https://auth.example.com",
    );
  });

  it("returns null for non-saas mode", () => {
    const result = useAuthUrl({
      appMode: "oss",
      identityProvider: "github",
    } as any);

    expect(result).toBeNull();
    expect(generateAuthUrlMock).not.toHaveBeenCalled();
  });
});
