import { renderHook, waitFor, cleanup } from "@testing-library/react";
import {
  afterAll,
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { useAutoLogin } from "#/hooks/use-auto-login";
import { LoginMethod } from "#/utils/local-storage";

const authUrlMap: Record<string, string | null> = {
  github: null,
  gitlab: null,
  bitbucket: null,
  enterprise_sso: null,
};

const useAuthUrlMock = vi.hoisted(() =>
  vi.fn(
    (config: { identityProvider: string }) =>
      authUrlMap[config.identityProvider] ?? null,
  ),
);

vi.mock("#/hooks/use-auth-url", () => ({
  useAuthUrl: useAuthUrlMock,
}));

const configState = {
  data: { APP_MODE: "saas", AUTH_URL: "" },
  isLoading: false,
} as {
  data: { APP_MODE: string; AUTH_URL?: string } | null;
  isLoading: boolean;
};
vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => configState,
}));

const isAuthedState = { data: false, isLoading: false } as {
  data: boolean | null;
  isLoading: boolean;
};
vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => isAuthedState,
}));

const getLoginMethodMock = vi.hoisted(() =>
  vi.fn<() => LoginMethod | null>(() => null),
);

vi.mock("#/utils/local-storage", async () => {
  const actual = await vi.importActual<typeof import("#/utils/local-storage")>(
    "#/utils/local-storage",
  );
  return {
    ...actual,
    getLoginMethod: getLoginMethodMock,
  };
});

describe("useAutoLogin", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    authUrlMap.github = null;
    authUrlMap.gitlab = null;
    authUrlMap.bitbucket = null;
    authUrlMap.enterprise_sso = null;
    useAuthUrlMock.mockClear();
    getLoginMethodMock.mockClear();
    configState.data = { APP_MODE: "saas", AUTH_URL: "" };
    configState.isLoading = false;
    isAuthedState.data = false;
    isAuthedState.isLoading = false;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { href: "https://app.example.com" },
    });
  });

  afterEach(() => {
    cleanup();
  });

  afterAll(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("redirects to stored login method", async () => {
    authUrlMap.github = "https://auth.example.com/github";
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);

    renderHook(() => useAutoLogin());

    await waitFor(() => {
      expect(window.location.href).toBe(
        "https://auth.example.com/github?login_method=github",
      );
    });
  });

  it("does not redirect when config is not saas", async () => {
    configState.data = { APP_MODE: "oss" } as any;
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = "https://auth.example.com/github";

    renderHook(() => useAutoLogin());

    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );
  });

  it("does not redirect when auth still loading", async () => {
    isAuthedState.isLoading = true;
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = "https://auth.example.com/github";

    renderHook(() => useAutoLogin());

    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );
  });

  it("does not redirect when user already authed", async () => {
    isAuthedState.data = true;
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = "https://auth.example.com/github";

    renderHook(() => useAutoLogin());

    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );
  });

  it("does not redirect when login method missing or auth url unavailable", async () => {
    // missing login method
    getLoginMethodMock.mockReturnValue(null);
    renderHook(() => useAutoLogin());
    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );

    cleanup();
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = null;
    renderHook(() => useAutoLogin());
    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );

    cleanup();
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = undefined as any;
    renderHook(() => useAutoLogin());
    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );

    cleanup();
    getLoginMethodMock.mockReturnValue("" as any);
    authUrlMap.github = "https://auth.example.com/github";
    renderHook(() => useAutoLogin());
    await waitFor(() =>
      expect(window.location.href).toBe("https://app.example.com"),
    );
  });

  it("passes null app mode when config is missing", async () => {
    configState.data = null;
    getLoginMethodMock.mockReturnValue(LoginMethod.GITHUB);
    authUrlMap.github = "https://auth.example.com/github";

    renderHook(() => useAutoLogin());

    await waitFor(() => {
      expect(useAuthUrlMock).toHaveBeenCalledWith(
        expect.objectContaining({
          appMode: null,
          identityProvider: "github",
        }),
      );
    });
    expect(window.location.href).toBe("https://app.example.com");
  });
});
