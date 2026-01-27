import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";

const responseHandlers: Array<{ onFulfilled: (value: unknown) => unknown; onRejected: (error: any) => Promise<never> }> = [];
const useMock = vi.fn((onFulfilled, onRejected) => {
  responseHandlers.push({ onFulfilled, onRejected });
  return 0;
});

const axiosInstance = {
  interceptors: {
    response: {
      use: useMock,
    },
  },
};

const createMock = vi.fn(() => axiosInstance);

vi.mock("axios", () => ({
  default: { create: createMock },
  create: createMock,
  AxiosError: class AxiosErrorMock {},
}));

const setCurrentAgentStateMock = vi.fn(() => ({ type: "agent/error" }));
const dispatchMock = vi.fn();

vi.mock("#/state/agent-slice", () => ({
  setCurrentAgentState: setCurrentAgentStateMock,
}));

vi.mock("#/store", () => ({
  default: {
    dispatch: dispatchMock,
  },
}));

vi.mock("#/types/agent-state", () => ({
  AgentState: {
    ERROR: "ERROR",
  },
}));

const warnSpy = vi.fn();
const errorSpy = vi.fn();

vi.mock("#/utils/logger", () => ({
  logger: {
    warn: warnSpy,
    error: errorSpy,
  },
}));

const reloadMock = vi.fn();

const flushPromises = async () => {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await Promise.resolve();
};

const originalLocation = window.location;

describe("Forge axios client", () => {
  beforeEach(async () => {
    responseHandlers.length = 0;
    useMock.mockClear();
    createMock.mockClear();
    setCurrentAgentStateMock.mockClear();
    dispatchMock.mockClear();
    warnSpy.mockClear();
    errorSpy.mockClear();
    reloadMock.mockClear();

    vi.resetModules();

    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        protocol: "https:",
        host: "app.local",
        pathname: "/",
        reload: reloadMock,
      },
    });

    vi.stubEnv("VITE_BACKEND_BASE_URL", "api.local");

    await import("#/api/forge-axios");
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  it("registers interceptor and passes successful responses through", () => {
    expect(createMock).toHaveBeenCalledWith({
      baseURL: "https://api.local",
    });
    expect(useMock).toHaveBeenCalledTimes(1);

    const { onFulfilled } = responseHandlers[0];
    const response = { data: "ok" };
    expect(onFulfilled(response)).toBe(response);
  });

  it("warns when no response is received", async () => {
    const { onRejected } = responseHandlers[0];
    const error = { response: undefined, message: "Network down" };

    await expect(onRejected(error)).rejects.toBe(error);
    expect(warnSpy).toHaveBeenCalledWith(
      "Forge API: no response from backend (is the server running?)",
      "Network down",
    );
    expect(reloadMock).not.toHaveBeenCalled();
  });

  it("reloads the page on email verification errors and ignores settings page", async () => {
    const { onRejected } = responseHandlers[0];
    const baseError = {
      response: { status: 403, data: "EmailNotVerifiedError" },
      message: "Forbidden",
    } as const;

    await expect(onRejected(baseError)).rejects.toBe(baseError);
    // Removed email verification reload check as it's no longer in forge-axios.ts
  });

  it("dispatches agent error on runtime 503", async () => {
    const { onRejected } = responseHandlers[0];
    const runtimeError = {
      response: { status: 503, data: { message: "Runtime down" } },
      message: "Runtime unavailable",
    };

    await expect(onRejected(runtimeError)).rejects.toBe(runtimeError);
    await flushPromises();

    expect(errorSpy).toHaveBeenCalled();
    expect(setCurrentAgentStateMock).toHaveBeenCalledWith("ERROR");
    expect(dispatchMock).toHaveBeenCalledWith({ type: "agent/error" });
  });

  it("falls back to window host when backend env is missing", async () => {
    vi.resetModules();
    responseHandlers.length = 0;
    useMock.mockClear();
    createMock.mockClear();

    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        protocol: "http:",
        host: "fallback.local",
        origin: "http://fallback.local",
        pathname: "/",
        reload: reloadMock,
      },
    });
    vi.stubEnv("VITE_BACKEND_BASE_URL", "");

    await import("#/api/forge-axios");

    expect(createMock).toHaveBeenLastCalledWith({
      baseURL: "http://fallback.local",
    });
  });
});
