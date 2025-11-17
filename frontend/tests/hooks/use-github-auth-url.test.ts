import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const useAuthUrlMock = vi.fn();

vi.mock("#/hooks/use-auth-url", () => ({
  useAuthUrl: (args: unknown) => useAuthUrlMock(args),
}));

import { useGitHubAuthUrl } from "#/hooks/use-github-auth-url";

describe("useGitHubAuthUrl", () => {
  it("passes through config to useAuthUrl", () => {
    useGitHubAuthUrl({ appMode: "saas", gitHubClientId: "abc123" });

    expect(useAuthUrlMock).toHaveBeenCalledWith({
      appMode: "saas",
      identityProvider: "github",
      authUrl: "https://github.com/login/oauth/authorize?client_id=abc123",
    });
  });

  it("prefers explicit authUrl when provided", () => {
    useGitHubAuthUrl({
      appMode: "oss",
      gitHubClientId: "abc123",
      authUrl: "https://example.com/oauth",
    });

    expect(useAuthUrlMock).toHaveBeenCalledWith({
      appMode: "oss",
      identityProvider: "github",
      authUrl: "https://example.com/oauth",
    });
  });

  it("allows missing client id and authUrl", () => {
    useGitHubAuthUrl({ appMode: null, gitHubClientId: null });

    expect(useAuthUrlMock).toHaveBeenCalledWith({
      appMode: null,
      identityProvider: "github",
      authUrl: undefined,
    });
  });
});
