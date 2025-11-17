import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthCallback } from "#/hooks/use-auth-callback";
import { LoginMethod } from "#/utils/local-storage";

const navigateMock = vi.hoisted(() => vi.fn());
const locationValue = { search: "", pathname: "/callback" };

vi.mock("react-router-dom", () => ({
  useLocation: () => locationValue,
  useNavigate: () => navigateMock,
}));

const isAuthedState = { data: false, isLoading: false };
vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => isAuthedState,
}));

const configState = { data: { APP_MODE: "saas" } } as {
  data: { APP_MODE: string } | null;
};
vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => configState,
}));

const setLoginMethodMock = vi.hoisted(() => vi.fn());

vi.mock("#/utils/local-storage", async () => {
  const actual = await vi.importActual<typeof import("#/utils/local-storage")>(
    "#/utils/local-storage",
  );
  return {
    ...actual,
    setLoginMethod: setLoginMethodMock,
  };
});

describe("useAuthCallback", () => {
  beforeEach(() => {
    setLoginMethodMock.mockClear();
    navigateMock.mockClear();
    isAuthedState.data = false;
    isAuthedState.isLoading = false;
    configState.data = { APP_MODE: "saas" };
    locationValue.search = "";
  });

  afterEach(() => {
    cleanup();
  });

  it("sets login method and strips query when authed in saas mode", async () => {
    isAuthedState.data = true;
    locationValue.search = "?login_method=github&foo=1";

    renderHook(() => useAuthCallback());

    await waitFor(() =>
      expect(setLoginMethodMock).toHaveBeenCalledWith(LoginMethod.GITHUB),
    );
    expect(navigateMock).toHaveBeenCalledWith("/callback?foo=1", {
      replace: true,
    });
  });

  it("does nothing when config is not saas", async () => {
    configState.data = { APP_MODE: "oss" } as any;
    isAuthedState.data = true;
    locationValue.search = "?login_method=github";

    renderHook(() => useAuthCallback());

    await waitFor(() => {
      expect(setLoginMethodMock).not.toHaveBeenCalled();
    });
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("waits for auth loading to finish", async () => {
    isAuthedState.isLoading = true;
    isAuthedState.data = true;
    locationValue.search = "?login_method=github";

    const { rerender } = renderHook(() => useAuthCallback());

    await waitFor(() => expect(setLoginMethodMock).not.toHaveBeenCalled());

    // simulate auth finishing
    isAuthedState.isLoading = false;
    rerender();

    await waitFor(() => expect(setLoginMethodMock).toHaveBeenCalled());
  });

  it("ignores unauthenticated users", async () => {
    isAuthedState.data = false;
    locationValue.search = "?login_method=github";

    renderHook(() => useAuthCallback());

    await waitFor(() => {
      expect(setLoginMethodMock).not.toHaveBeenCalled();
    });
  });

  it("ignores invalid login methods", async () => {
    isAuthedState.data = true;
    locationValue.search = "?login_method=unknown";

    renderHook(() => useAuthCallback());

    await waitFor(() => expect(setLoginMethodMock).not.toHaveBeenCalled());
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("ignores when config is unavailable", async () => {
    configState.data = null;
    isAuthedState.data = true;
    locationValue.search = "?login_method=github";

    renderHook(() => useAuthCallback());

    await waitFor(() => expect(setLoginMethodMock).not.toHaveBeenCalled());
  });
});
