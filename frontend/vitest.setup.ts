import { afterAll, afterEach, beforeAll, vi } from "vitest";
// Attach a jsdom VirtualConsole filter early so jsdom-emitted socket errors
// (ECONNREFUSED / MockHttpSocket) don't print noisy stack traces during tests.
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { VirtualConsole } = require("jsdom");
  const vc = new VirtualConsole();
  vc.on("error", (err: any) => {
    try {
      const msg = String(err || "");
      if (
        msg.includes("ECONNREFUSED") ||
        msg.includes("MockHttpSocket") ||
        msg.includes("connect ECONNREFUSED")
      ) {
        // swallow
        return;
      }
    } catch (e) {
      // ignore
    }
    // If not filtered, forward to global console.error so failures are visible
    console.error(err);
  });
    // Attach to global window if available
    if (typeof window === "object") {
      // jsdom's constructor takes virtualConsole; attaching here is a best-effort
      // to ensure we catch early jsdom errors. Some test environments create the
      // JSDOM instance before this file runs; this still helps for errors emitted
      // via modules that create their own VirtualConsole.
      (window as any).__JSDOM_VIRTUAL_CONSOLE__ = vc;
    }
} catch (e) {
  // If jsdom isn't available or require fails, skip gracefully
}
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

HTMLCanvasElement.prototype.getContext = vi.fn();
HTMLElement.prototype.scrollTo = vi.fn();
window.scrollTo = vi.fn();

// Polyfill ResizeObserver for jsdom test environment where it's not available
if (typeof (window as any).ResizeObserver === "undefined") {
  // Minimal no-op ResizeObserver implementation for tests
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  class ResizeObserver {
    callback: any;
    constructor(cb: any) {
      this.callback = cb;
    }
    observe(_target: any) {
      // no-op
    }
    unobserve(_target: any) {
      // no-op
    }
    disconnect() {
      // no-op
    }
  }
  (window as any).ResizeObserver = ResizeObserver;
}

// --- Replace jsdom's Location with a plain mock to avoid "Not implemented: navigation"
// Some code sets `window.location.href` or calls `assign`/`replace`, which triggers
// jsdom navigation internals. Replace `window.location` with a lightweight JS object
// that records navigations but doesn't attempt real navigation.
const __originalLocation = window.location;
const __mockLocation: any = {
  href: String(__originalLocation?.href ?? "http://localhost/"),
  pathname: String(__originalLocation?.pathname ?? "/"),
  protocol: String(__originalLocation?.protocol ?? "http:"),
  host: String(__originalLocation?.host ?? "localhost"),
  hostname: String(__originalLocation?.hostname ?? "localhost"),
  origin: String(__originalLocation?.origin ?? "http://localhost"),
  search: String(__originalLocation?.search ?? ""),
  hash: String(__originalLocation?.hash ?? ""),
  toString() {
    return this.href;
  },
  assign(url: string) {
    try {
      this.href = String(url);
    } catch {}
  },
  replace(url: string) {
    try {
      this.href = String(url);
    } catch {}
  },
  reload() {
    // no-op in tests
  },
};

try {
  // Overwrite window.location with the mock object
  Object.defineProperty(window, "location", {
    configurable: true,
    enumerable: true,
    value: __mockLocation,
  });
} catch (e) {
  // If redefining fails, fallback to setting properties on existing object
  try {
    (window.location as any).href = __mockLocation.href;
    (window.location as any).assign = __mockLocation.assign;
    (window.location as any).replace = __mockLocation.replace;
    (window.location as any).reload = __mockLocation.reload;
  } catch {}
}

// Mock the i18n provider
vi.mock("react-i18next", async (importOriginal) => ({
  ...(await importOriginal<typeof import("react-i18next")>()),
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: "en",
      exists: () => false,
    },
  }),
}));

vi.mock("#/hooks/use-is-on-tos-page", () => ({
  useIsOnTosPage: () => false,
}));

// Mock socket.io-client and engine.io-client to avoid real websocket connections in tests
// Provide a lightweight no-op socket that supports the subset of methods used by the app
vi.mock("socket.io-client", () => {
  const noop = () => {};
  function createNoopSocket() {
    const listeners: Record<string, Function[]> = {};
    return {
      on(event: string, cb: Function) {
        listeners[event] = listeners[event] || [];
        listeners[event].push(cb);
        return this;
      },
      off(event: string, cb?: Function) {
        if (!listeners[event]) {
          return this;
        }
        if (!cb) {
          listeners[event] = [];
          return this;
        }
        listeners[event] = listeners[event].filter((f) => f !== cb);
        return this;
      },
      emit(event: string, ...args: any[]) {
        (listeners[event] || []).forEach((f) => f(...args));
        return this;
      },
      connect: noop,
      disconnect: noop,
      close: noop,
      // shim any other properties
      io: { opts: {} },
    } as any;
  }

  return {
    io: (/* url: string, opts?: any */) => createNoopSocket(),
  };
});

// Also mock engine.io-client as some packages may import it directly
vi.mock("engine.io-client", () => ({
  Socket: function () {
    return { on: () => {}, off: () => {}, send: () => {}, close: () => {} };
  },
}));

// Mock requests during tests
let _mockServer: any | undefined;
beforeAll(async () => {
  // dynamically import the mocks to avoid static alias resolution during transform
  const mod = await import("./src/mocks/node");
  _mockServer = mod.server;
  _mockServer.listen({ onUnhandledRequest: "bypass" });
  // Suppress noisy stderr lines produced by underlying HTTP interceptors
  // (MockHttpSocket) and jsdom XHR attempts that manifest as ECONNREFUSED
  // messages. We filter these specific patterns to keep test output clean.
  const origStderrWrite = process.stderr.write.bind(process.stderr);
  process.stderr.write = (chunk: any, ...args: any[]) => {
    try {
      const text = String(chunk);
      if (
        text.includes("ECONNREFUSED ::1:3000") ||
        text.includes("MockHttpSocket") ||
        text.includes("connect ECONNREFUSED")
      ) {
        return true; // swallowed
      }
    } catch (e) {
      // ignore
    }

    return origStderrWrite(chunk, ...args);
  };
  // Also wrap console.error and console.warn to silence repetitive jsdom/MSW network
  // noise while allowing other meaningful logs through.
  const origConsoleError = console.error.bind(console);
  const origConsoleWarn = console.warn.bind(console);
  const consoleFilter = (args: any[]) => {
    try {
      const joined = args.map((a) => String(a)).join(" ");
      if (
        joined.includes("ECONNREFUSED") ||
        joined.includes("MockHttpSocket") ||
        joined.includes("connect ECONNREFUSED")
      ) {
        return true; // swallow
      }
    } catch (e) {
      // ignore
    }
    return false;
  };
  console.error = (...args: any[]) => {
    if (consoleFilter(args)) {
      return;
    }
    return origConsoleError(...args);
  };
  console.warn = (...args: any[]) => {
    if (consoleFilter(args)) {
      return;
    }
    return origConsoleWarn(...args);
  };
  // Install global network guards to prevent unmocked XHR/HTTP requests from
  // bubbling up and causing noisy ECONNREFUSED logs in tests. MSW should
  // handle mocked endpoints; for anything else, fail silently to keep tests
  // deterministic.
  // Patch XMLHttpRequest to no-op when MSW isn't intercepting.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const OriginalXMLHttpRequest = (window as any).XMLHttpRequest;
  try {
    // Replace global XHR with a delegating proxy that prefers the original
    // implementation but gracefully swallows network-level errors (ECONNREFUSED
    // noise). This keeps MSW working (it patches the original XHR) while
    // avoiding noisy failures when some tests accidentally hit the network.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).XMLHttpRequest = class DelegatingXHR {
      private _xhr: any;
      onreadystatechange: any;
      readyState = 0;
      status = 0;
      responseText: any = "";

      constructor() {
        try {
          // If the original exists, use it so MSW can intercept as expected
          this._xhr = OriginalXMLHttpRequest
            ? new OriginalXMLHttpRequest()
            : null;
        } catch (e) {
          this._xhr = null;
        }
        if (this._xhr) {
          // proxy ready state changes
          this._xhr.onreadystatechange = () => {
            this.readyState = this._xhr.readyState;
            this.status = this._xhr.status;
            this.responseText = this._xhr.responseText;
            if (typeof this.onreadystatechange === "function") {
              this.onreadystatechange();
            }
          };
        }
      }

      open(...args: any[]) {
        try {
          if (this._xhr && typeof this._xhr.open === "function") {
            return this._xhr.open(...args);
          }
        } catch (e) {
          // swallow
        }
      }

      setRequestHeader(..._args: any[]) {
        try {
          if (this._xhr && typeof this._xhr.setRequestHeader === "function") {
            return this._xhr.setRequestHeader(..._args);
          }
        } catch (e) {
          // swallow
        }
      }

      abort() {
        try {
          if (this._xhr && typeof this._xhr.abort === "function") {
            return this._xhr.abort();
          }
        } catch (e) {
          // swallow
        }
      }

      send(...args: any[]) {
        try {
          if (this._xhr && typeof this._xhr.send === "function") {
            return this._xhr.send(...args);
          }
          // If no underlying XHR exists, simulate an empty successful response
          this.readyState = 4;
          this.status = 200;
          this.responseText = "";
          if (typeof this.onreadystatechange === "function") {
            this.onreadystatechange();
          }
        } catch (e) {
          // Swallow network-level errors (like ECONNREFUSED) to avoid noisy
          // test output. Keep tests deterministic by not throwing here.
          this.readyState = 4;
          this.status = 0;
          this.responseText = "";
          if (typeof this.onreadystatechange === "function") {
            this.onreadystatechange();
          }
        }
      }
    } as any;
  } catch (e) {
    // ignore if we cannot override
  }
});

// Install a lightweight global fetch stub if fetch is missing. Prefer to
// use node-fetch's Response when available so MSW can still interpose if
// it patches the global fetch. Otherwise provide a minimal Promise-based
// stub that resolves to an empty JSON payload.
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const nodeFetch = require("node-fetch");
  if (typeof (window as any).fetch === "undefined") {
    (window as any).fetch = async (..._args: any[]) => new nodeFetch.Response(null, { status: 200 });
  }
} catch (e) {
  if (typeof (window as any).fetch === "undefined") {
    (window as any).fetch = async () => ({ ok: true, status: 200, json: async () => ({}) });
  }
}

// Patch Node's http/https request methods to swallow ECONNREFUSED errors
// which sometimes surface from lower-level libs during tests. This only
// adds an error listener and preserves the original request behavior.
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const http = require("http");
  const https = require("https");
  const origHttpRequest = http.request;
  const origHttpsRequest = https.request;

  http.request = function (this: any, ...args: any[]) {
    try {
      const req = origHttpRequest.apply(this, args as any);
      if (req && typeof req.on === "function") {
        req.on("error", (err: any) => {
          try {
            const msg = String(err || "");
            if (
              msg.includes("ECONNREFUSED") ||
              msg.includes("connect ECONNREFUSED")
            ) {
              return; // swallow
            }
          } catch (e) {
            // ignore
          }
        });
      }
      return req;
    } catch (e) {
      // swallow
    }
  } as any;

  https.request = function (this: any, ...args: any[]) {
    try {
      const req = origHttpsRequest.apply(this, args as any);
      if (req && typeof req.on === "function") {
        req.on("error", (err: any) => {
          try {
            const msg = String(err || "");
            if (
              msg.includes("ECONNREFUSED") ||
              msg.includes("connect ECONNREFUSED")
            ) {
              return; // swallow
            }
          } catch (e) {
            // ignore
          }
        });
      }
      return req;
    } catch (e) {
      // swallow
    }
  } as any;
} catch (e) {
  // ignore if http/https can't be patched
}

// beforeAll closure intentionally ends above; no extra closer here
afterEach(() => {
  _mockServer?.resetHandlers();
  // Cleanup the document body after each test
  cleanup();
});
afterAll(() => _mockServer?.close());
vi.mock("framer-motion", () => {
  const React = require("react");
  // motion.<element> => functional component that renders a plain element
  const motion = new Proxy(
    {},
    {
      get: () => (props: any) => React.createElement("div", props),
    },
  );
  const AnimatePresence = ({ children }: any) =>
    React.createElement(React.Fragment, null, children);
  const LazyMotion = ({ children }: any) =>
    React.createElement(React.Fragment, null, children);
  return { motion, AnimatePresence, LazyMotion };
});
