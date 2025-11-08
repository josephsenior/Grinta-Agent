// See https://redux.js.org/usage/writing-tests#setting-up-a-reusable-test-render-function for more information

import React, { PropsWithChildren } from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { RenderOptions, render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import i18n from "i18next";
import { MemoryRouter } from "react-router-dom";
import { AxiosError } from "axios";
import { AppStore, RootState, rootReducer } from "./src/store";
import { ToastProvider } from "#/components/shared/notifications/toast";
import { TaskProvider } from "#/context/task-context";
// `vi` is a Vitest global used by unit tests. We use the ambient `vi`
// declaration and guard it at runtime with `typeof vi !== 'undefined'` so
// Playwright/dev servers don't attempt to use Vitest internals.
const hasVi = typeof vi !== "undefined";
const viGlobal = hasVi ? vi : undefined;
// Simple Playwright test flag stored on the global/window object so both
// Playwright E2E and unit tests can toggle Playwright-specific behavior.
export const setPlaywrightFlag = (value: boolean): void => {
  try {
    // Use the typed global/window flag when available
    try {
      globalThis.__Forge_PLAYWRIGHT = value;
    } catch (e) {
      // fallback to window if globalThis assignment fails
      if (typeof window !== "undefined") {
        window.__Forge_PLAYWRIGHT = value;
      }
    }
  } catch (e) {
    // ignore
  }
};

// Try to use MSW to mock a 404 for GET /api/settings. Returns true if MSW
// was used, false if test code should fall back to mocking hooks directly.
export const mockSettings404 = (): boolean => {
  try {
    // Attempt to access the MSW server instance installed by vitest.setup
    // This will work in the Vitest environment where vitest.setup imports
    // ./src/mocks/node and attaches `server` to the module exports.
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod = require("./src/mocks/node");
    const server = mod?.server;
    if (server && typeof server.use === "function") {
      // msw's rest handlers can be used to respond with a 404 for the
      // GET /api/settings endpoint. Use a one-off handler for this test.
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { rest } = require("msw");
      server.use(
        rest.get("/api/settings", (_req: any, res: any, ctx: any) =>
          res(ctx.status(404)),
        ),
      );
      return true;
    }
  } catch (e) {
    // If any require/import fails, fall back to mocking hooks below.
  }
  return false;
};

// The following test-only mocks should only run when Vitest executes tests.
// Guard them to avoid importing Vitest during Playwright / dev server runs.
if (viGlobal) {
  // Mock useParams before importing components
  viGlobal.mock("react-router", async () => {
    // Import the actual module at runtime and return an augmented version.
    const actual = await viGlobal.importActual("react-router");
    return {
      ...(actual as Record<string, unknown>),
      useParams: () => ({ conversationId: "test-conversation-id" }),
    };
  });

  // Mock authentication hook globally for tests so hooks that depend on
  // authentication (like useSettings) are enabled by default. Individual
  // tests can still override this with vi.spyOn or vi.resetAllMocks().
  viGlobal.mock("#/hooks/query/use-is-authed", () => ({
    useIsAuthed: () => ({ data: true, isLoading: false }),
  }));
}

// Initialize i18n for tests. Some test files mock `react-i18next` which can remove
// the `initReactI18next` export. Try to require it at runtime and fall back to
// calling i18n.init() directly if it's not available.
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const maybe = require("react-i18next");
  const initReactI18next = maybe?.initReactI18next;
  if (initReactI18next && typeof initReactI18next === "function") {
    i18n.use(initReactI18next).init({
      lng: "en",
      fallbackLng: "en",
      ns: ["translation"],
      defaultNS: "translation",
      resources: {
        en: {
          translation: {},
        },
      },
      interpolation: {
        escapeValue: false,
      },
    });
  } else {
    i18n.init({
      lng: "en",
      fallbackLng: "en",
      ns: ["translation"],
      defaultNS: "translation",
      resources: {
        en: {
          translation: {},
        },
      },
      interpolation: {
        escapeValue: false,
      },
    });
  }
} catch (e) {
  // If require fails for any reason, fall back to a simple init.
  i18n.init({
    lng: "en",
    fallbackLng: "en",
    ns: ["translation"],
    defaultNS: "translation",
    resources: {
      en: {
        translation: {},
      },
    },
    interpolation: {
      escapeValue: false,
    },
  });
}

export const setupStore = (preloadedState?: Partial<RootState>): AppStore =>
  configureStore({
    reducer: rootReducer,
    preloadedState,
  });

// This type interface extends the default options for render from RTL, as well
// as allows the user to specify other things such as initialState, store.
type MemoryRouterProps = React.ComponentProps<typeof MemoryRouter>;

interface RenderRouterOptions {
  initialEntries?: MemoryRouterProps["initialEntries"];
  initialIndex?: MemoryRouterProps["initialIndex"];
}

interface ExtendedRenderOptions extends Omit<RenderOptions, "queries"> {
  preloadedState?: Partial<RootState>;
  store?: AppStore;
  queryClient?: QueryClient;
  route?: string;
  router?: RenderRouterOptions;
}

// Export our own customized renderWithProviders function that creates a new Redux store and renders a <Provider>
// Note that this creates a separate Redux store instance for every test, rather than reusing the same store instance and resetting its state
export function renderWithProviders(
  ui: React.ReactElement,
  {
    preloadedState = {},
    // Automatically create a store instance if no store was passed in
    store = setupStore(preloadedState),
    queryClient: providedQueryClient,
    route,
    router,
    ...renderOptions
  }: ExtendedRenderOptions = {},
) {
  const queryClient =
    providedQueryClient ??
    new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

  const routerConfig: RenderRouterOptions | undefined = (() => {
    if (router) {
      return router;
    }
    if (route) {
      return { initialEntries: [route] };
    }
    return undefined;
  })();

  function Wrapper({ children }: PropsWithChildren) {
    const content = routerConfig ? (
      <MemoryRouter
        initialEntries={routerConfig.initialEntries ?? ["/"]}
        initialIndex={routerConfig.initialIndex}
      >
        {children}
      </MemoryRouter>
    ) : (
      children
    );

    return (
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <I18nextProvider i18n={i18n}>
            <ToastProvider>
              <TaskProvider>
                {content}
              </TaskProvider>
            </ToastProvider>
          </I18nextProvider>
        </QueryClientProvider>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}

export const createAxiosNotFoundErrorObject = () =>
  new AxiosError(
    "Request failed with status code 404",
    "ERR_BAD_REQUEST",
    undefined,
    undefined,
    {
      status: 404,
      statusText: "Not Found",
      data: { message: "Settings not found" },
      headers: {},
      // @ts-expect-error - we only need the response object for this test
      config: {},
    },
  );

// Simple helper to create a plain 404-like error object that some tests
// (and components like Sidebar) check via `error?.status === 404`.
export const create404Error = () => ({ status: 404 });



// Render helper that wraps a UI with the standard providers plus a
// MemoryRouter, useful for components that depend on react-router.
export function renderWithRouter(
  ui: React.ReactElement,
  {
    initialEntries,
    initialIndex,
    route,
    router,
    ...renderOptions
  }: ExtendedRenderOptions & {
    initialEntries?: MemoryRouterProps["initialEntries"];
    initialIndex?: MemoryRouterProps["initialIndex"];
  } = {},
) {
  return renderWithProviders(
    ui,
    {
      route,
      router: {
        initialEntries:
          initialEntries ?? router?.initialEntries ?? [route ?? "/"],
        initialIndex: initialIndex ?? router?.initialIndex,
      },
      ...renderOptions,
    },
  );
}

export function renderWithAllProviders(
  ui: React.ReactElement,
  options: ExtendedRenderOptions = {},
) {
  const { route = "/", router, ...rest } = options;
  return renderWithProviders(ui, {
    route,
    router: router ?? { initialEntries: [route] },
    ...rest,
  });
}

// Helper for flexible text matching when emoji or text might be split across elements
export const createTextMatcher = (partial: string) => (content: string) =>
  content.toLowerCase().includes(partial.toLowerCase());

// Helper for finding elements by flexible text that might be split
export const getByFlexibleText = (screen: any, text: string) => {
  return screen.getByText(createTextMatcher(text));
};

