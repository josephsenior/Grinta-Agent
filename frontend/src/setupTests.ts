import "@testing-library/jest-dom";

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
(globalThis as unknown as Record<string, unknown>).IntersectionObserver =
  class IntersectionObserver {
    root: Element | null = null;

    rootMargin: string = "";

    thresholds: ReadonlyArray<number> = [];

    constructor() {}

    observe() {
      return null;
    }

    disconnect() {
      return null;
    }

    unobserve() {
      return null;
    }

    takeRecords() {
      return [];
    }
  } as any;

// Mock ResizeObserver
(globalThis as unknown as Record<string, unknown>).ResizeObserver =
  class ResizeObserver {
    constructor() {}

    observe() {
      return null;
    }

    disconnect() {
      return null;
    }

    unobserve() {
      return null;
    }
  } as any;

// Mock localStorage
const localStorageMock: Record<string, unknown> = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn((i: number) => null),
};
(globalThis as unknown as Record<string, unknown>).localStorage =
  localStorageMock;

// Mock sessionStorage
const sessionStorageMock: Record<string, unknown> = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn((i: number) => null),
};
(globalThis as unknown as Record<string, unknown>).sessionStorage =
  sessionStorageMock;

// Mock fetch
(globalThis as unknown as Record<string, unknown>).fetch = jest.fn();

// Mock WebSocket
const WebSocketMock: Record<string, unknown> & { new?: unknown } = jest
  .fn()
  .mockImplementation(() => ({
    close: jest.fn(),
    send: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  })) as unknown as Record<string, unknown> & { new?: unknown };
(WebSocketMock as Record<string, unknown>).CONNECTING = 0;
(WebSocketMock as Record<string, unknown>).OPEN = 1;
(WebSocketMock as Record<string, unknown>).CLOSING = 2;
(WebSocketMock as Record<string, unknown>).CLOSED = 3;
(globalThis as unknown as Record<string, unknown>).WebSocket = WebSocketMock;

// Mock console methods to reduce noise in tests
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Warning: ReactDOM.render is no longer supported")
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: unknown[]) => {
    if (
      typeof args[0] === "string" &&
      (args[0].includes("componentWillReceiveProps") ||
        args[0].includes("componentWillMount"))
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});
