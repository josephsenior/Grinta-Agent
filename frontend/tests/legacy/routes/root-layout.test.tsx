import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, beforeEach, afterEach, expect, vi } from "vitest";
import { createRoutesStub } from "react-router-dom";
import * as ReactRouter from "react-router-dom";
import MainApp, {
  ErrorBoundary,
  shouldConversationStartOpen,
  checkLoginMethodExists,
} from "#/routes/root-layout";
import { LOCAL_STORAGE_KEYS } from "#/utils/local-storage";
import i18n from "#/i18n";
import { renderWithProviders, setPlaywrightFlag } from "#test-utils";

const {
  useConfigMock,
  useSettingsMock,
  useGitHubAuthUrlMock,
  useMigrateUserConsentMock,
  useBalanceMock,
  useIsOnTosPageMock,
  useAutoLoginMock,
  useAuthCallbackMock,
  useIsAuthedMock,
} = vi.hoisted(() => ({
  useConfigMock: vi.fn(),
  useSettingsMock: vi.fn(),
  useGitHubAuthUrlMock: vi.fn(),
  useMigrateUserConsentMock: vi.fn(),
  useBalanceMock: vi.fn(),
  useIsOnTosPageMock: vi.fn(),
  useAutoLoginMock: vi.fn(),
  useAuthCallbackMock: vi.fn(),
  useIsAuthedMock: vi.fn(),
}));

const injectCriticalCSSMock = vi.hoisted(() => vi.fn());
const displaySuccessToastMock = vi.hoisted(() => vi.fn());

vi.mock("#/utils/critical-css", () => ({
  injectCriticalCSS: injectCriticalCSSMock,
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: displaySuccessToastMock,
  displayErrorToast: vi.fn(),
}));

vi.mock("#/hooks/query/use-config", () => ({
  useConfig: useConfigMock,
}));

vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: useSettingsMock,
}));

vi.mock("#/hooks/use-github-auth-url", () => ({
  useGitHubAuthUrl: useGitHubAuthUrlMock,
}));

vi.mock("#/hooks/use-migrate-user-consent", () => ({
  useMigrateUserConsent: useMigrateUserConsentMock,
}));

vi.mock("#/hooks/query/use-balance", () => ({
  useBalance: useBalanceMock,
}));

vi.mock("#/hooks/use-is-on-tos-page", () => ({
  useIsOnTosPage: useIsOnTosPageMock,
}));

vi.mock("#/hooks/use-auto-login", () => ({
  useAutoLogin: useAutoLoginMock,
}));

vi.mock("#/hooks/use-auth-callback", () => ({
  useAuthCallback: useAuthCallbackMock,
}));

vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: useIsAuthedMock,
}));

vi.mock("#/components/features/conversation-panel/conversation-panel-wrapper", () => ({
  ConversationPanelWrapper: ({
    children,
    isOpen,
  }: {
    children: React.ReactNode;
    isOpen: boolean;
  }) => (
    <div data-testid="conversation-panel-wrapper" data-open={isOpen}>
      {isOpen ? children : null}
    </div>
  ),
}));

vi.mock("#/components/features/conversation-panel/conversation-panel", () => ({
  ConversationPanel: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="conversation-panel">
      <button data-testid="close-conversation" onClick={onClose}>
        close
      </button>
    </div>
  ),
}));

vi.mock("#/components/features/waitlist/auth-modal", () => ({
  AuthModal: ({ githubAuthUrl }: { githubAuthUrl: string | null }) => (
    <div data-testid="auth-modal">{githubAuthUrl}</div>
  ),
}));

vi.mock("#/components/features/waitlist/reauth-modal", () => ({
  ReauthModal: () => <div data-testid="reauth-modal" />,
}));

vi.mock("#/components/features/analytics/analytics-consent-form-modal", () => ({
  AnalyticsConsentFormModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="analytics-consent-modal">
      <button data-testid="close-consent" onClick={onClose}>
        close
      </button>
    </div>
  ),
}));

vi.mock("#/components/features/sidebar/sidebar", () => ({
  Sidebar: () => <div data-testid="sidebar" />,
}));

vi.mock("#/components/layout/Header", () => ({
  Header: () => <div data-testid="header" />,
}));

vi.mock("#/components/layout/Footer", () => ({
  Footer: () => <div data-testid="footer" />,
}));

vi.mock("#/components/features/payment/setup-payment-modal", () => ({
  SetupPaymentModal: () => <div data-testid="setup-payment-modal" />,
}));

vi.mock("#/components/features/guards/email-verification-guard", () => ({
  EmailVerificationGuard: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="email-verification-guard">{children}</div>
  ),
}));

vi.mock("#/components/features/maintenance/maintenance-banner", () => ({
  MaintenanceBanner: ({ startTime }: { startTime: string }) => (
    <div data-testid="maintenance-banner">{startTime}</div>
  ),
}));

const RoutesStub = createRoutesStub([{ Component: MainApp, path: "/*" }]);

describe("root-layout", () => {
  let configResult: any;
  let settingsResult: any;
  let balanceResult: any;
  let migrateUserConsentHandlers: any;
  let migrateUserConsentSpy: ReturnType<typeof vi.fn>;
  let navigateMock: ReturnType<typeof vi.fn>;
  let useNavigateSpy: ReturnType<typeof vi.spyOn>;
  let changeLanguageSpy: ReturnType<typeof vi.spyOn>;
  let authResult: any;
  let gitHubAuthUrl: string;
  let isOnTosPageValue: boolean;

  const renderMainApp = (initialRoute = "/") =>
    renderWithProviders(<RoutesStub initialEntries={[initialRoute]} />);

  beforeEach(() => {
    configResult = {
      data: {
        APP_MODE: "oss",
        FEATURE_FLAGS: {
          ENABLE_BILLING: false,
          HIDE_LLM_SETTINGS: false,
          ENABLE_JIRA: false,
          ENABLE_JIRA_DC: false,
          ENABLE_LINEAR: false,
        },
      },
      isLoading: false,
      isFetching: false,
      error: null,
    };
    settingsResult = {
      data: {
        LANGUAGE: "en",
        USER_CONSENTS_TO_ANALYTICS: true,
        IS_NEW_USER: false,
      },
      isLoading: false,
    };
    balanceResult = { error: null };
    migrateUserConsentHandlers = undefined;
    migrateUserConsentSpy = vi.fn((handlers) => {
      migrateUserConsentHandlers = handlers;
    });
    gitHubAuthUrl = "https://github.test";
    isOnTosPageValue = false;
    authResult = {
      data: true,
      isFetching: false,
      isError: false,
    };

    useConfigMock.mockImplementation(() => configResult);
    useSettingsMock.mockImplementation(() => settingsResult);
    useGitHubAuthUrlMock.mockImplementation(() => gitHubAuthUrl);
    useMigrateUserConsentMock.mockImplementation(() => ({
      migrateUserConsent: migrateUserConsentSpy,
    }));
    useBalanceMock.mockImplementation(() => balanceResult);
    useIsOnTosPageMock.mockImplementation(() => isOnTosPageValue);
    useAutoLoginMock.mockImplementation(() => {});
    useAuthCallbackMock.mockImplementation(() => {});
    useIsAuthedMock.mockImplementation(() => authResult);

    injectCriticalCSSMock.mockClear();
    displaySuccessToastMock.mockClear();
    migrateUserConsentSpy.mockClear();

    localStorage.clear();
    setPlaywrightFlag(false);

    navigateMock = vi.fn();
    useNavigateSpy = vi.spyOn(ReactRouter, "useNavigate").mockReturnValue(navigateMock);
    changeLanguageSpy = vi.spyOn(i18n, "changeLanguage") as any;
  });

  afterEach(() => {
    useNavigateSpy.mockRestore();
    changeLanguageSpy.mockRestore();
    setPlaywrightFlag(false);
  });

  it("opens and toggles the conversation panel when the Playwright flag is set and events are fired", async () => {
    authResult.data = true;
    setPlaywrightFlag(true);

    renderMainApp("/conversations/test");

    await screen.findByTestId("conversation-panel");
    expect(injectCriticalCSSMock).toHaveBeenCalled();

    await userEvent.click(screen.getByTestId("close-conversation"));
    await waitFor(() =>
      expect(screen.queryByTestId("conversation-panel")).not.toBeInTheDocument(),
    );

    window.dispatchEvent(new Event("Forge:open-conversation-panel"));

    await screen.findByTestId("conversation-panel");
  });

  it("renders the auth modal when unauthenticated without stored login method", async () => {
    localStorage.removeItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD);
    configResult.data.APP_MODE = "saas";
    authResult.data = false;
    gitHubAuthUrl = "https://auth.example";

    renderMainApp("/");

    await screen.findByTestId("auth-modal");
    expect(screen.queryByTestId("reauth-modal")).not.toBeInTheDocument();
  });

  it("renders the reauth modal when a login method exists", async () => {
    localStorage.setItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD, "github");
    configResult.data.APP_MODE = "saas";
    authResult.data = false;

    renderMainApp("/");

    await screen.findByTestId("reauth-modal");
    expect(screen.queryByTestId("auth-modal")).not.toBeInTheDocument();
  });

  it("switches between auth and reauth modals when login method storage events fire", async () => {
    localStorage.removeItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD);
    configResult.data.APP_MODE = "saas";
    authResult.data = false;
    gitHubAuthUrl = "https://auth.example";

    renderMainApp("/");

    await screen.findByTestId("auth-modal");

    localStorage.setItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD, "github");
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: LOCAL_STORAGE_KEYS.LOGIN_METHOD,
        newValue: "github",
        storageArea: window.localStorage,
      }),
    );

    await screen.findByTestId("reauth-modal");

    localStorage.removeItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD);
    window.dispatchEvent(new Event("focus"));

    await screen.findByTestId("auth-modal");
  });

  it("renders and closes the analytics consent modal for OSS users without stored consent", async () => {
    configResult.data.APP_MODE = "oss";
    settingsResult.data.USER_CONSENTS_TO_ANALYTICS = null;
    authResult.data = true;

    renderMainApp("/settings");

    await screen.findByTestId("analytics-consent-modal");
    expect(migrateUserConsentSpy).toHaveBeenCalled();

    await userEvent.click(screen.getByTestId("close-consent"));
    await waitFor(() =>
      expect(screen.queryByTestId("analytics-consent-modal")).not.toBeInTheDocument(),
    );

    migrateUserConsentHandlers?.handleAnalyticsWasPresentInLocalStorage?.();

    await waitFor(() =>
      expect(screen.queryByTestId("analytics-consent-modal")).not.toBeInTheDocument(),
    );
  });

  it("skips analytics consent migration while on the terms page", async () => {
    configResult.data.APP_MODE = "oss";
    settingsResult.data.USER_CONSENTS_TO_ANALYTICS = null;
    authResult.data = true;
    isOnTosPageValue = true;

    renderMainApp("/accept-tos");

    await waitFor(() => expect(migrateUserConsentSpy).not.toHaveBeenCalled());
    expect(screen.queryByTestId("analytics-consent-modal")).not.toBeInTheDocument();
  });

  it("renders the setup payment modal and fires the new user toast for SaaS users with billing", async () => {
    configResult.data.APP_MODE = "saas";
    configResult.data.FEATURE_FLAGS.ENABLE_BILLING = true;
    settingsResult.data.IS_NEW_USER = true;
    authResult.data = true;

    renderMainApp("/settings");

    await screen.findByTestId("setup-payment-modal");
    await waitFor(() =>
      expect(displaySuccessToastMock).toHaveBeenCalledWith("BILLING$YOURE_IN"),
    );
  });

  it("renders the maintenance banner when maintenance is configured", async () => {
    configResult.data.MAINTENANCE = { startTime: "2024-01-01T00:00:00Z" };
    authResult.data = true;

    renderMainApp("/");

    await screen.findByTestId("maintenance-banner");
  });

  it("redirects to the root when the balance API returns a payment required error", async () => {
    configResult.data.APP_MODE = "saas";
    configResult.data.FEATURE_FLAGS.ENABLE_BILLING = true;
    balanceResult.error = { status: 402 };
    authResult.data = true;

    renderMainApp("/analytics");

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/"));
  });

  it("syncs the language preference when settings specify a language", async () => {
    settingsResult.data.LANGUAGE = "es";
    authResult.data = true;

    renderMainApp("/settings");

    await waitFor(() => expect(changeLanguageSpy).toHaveBeenCalledWith("es"));
  });

  it("renders route error boundary fallback for thrown errors", async () => {
    const ErrorRouteStub = createRoutesStub([
      {
        path: "/error",
        Component: () => {
          throw new Error("boom");
        },
        ErrorBoundary,
      },
    ]);

    renderWithProviders(<ErrorRouteStub initialEntries={["/error"]} />);

    await screen.findByTestId("page-title");
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("renders error boundary content for route error responses", () => {
    const useRouteErrorSpy = vi.spyOn(ReactRouter, "useRouteError").mockReturnValue({
      status: 404,
      statusText: "Not Found",
      internal: false,
      data: { detail: "missing" },
    });

    renderWithProviders(<ErrorBoundary />);

    expect(screen.getByTestId("page-title")).toHaveTextContent("404");
    expect(screen.getByText("Not Found")).toBeInTheDocument();
    expect(screen.getByText('{"detail":"missing"}')).toBeInTheDocument();

    useRouteErrorSpy.mockRestore();
  });

  it("renders primitive data inside the route error response", () => {
    const useRouteErrorSpy = vi.spyOn(ReactRouter, "useRouteError").mockReturnValue({
      status: 500,
      statusText: "Server Error",
      internal: false,
      data: "boom",
    });

    renderWithProviders(<ErrorBoundary />);

    expect(screen.getByTestId("page-title")).toHaveTextContent("500");
    expect(screen.getByText("Server Error")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();

    useRouteErrorSpy.mockRestore();
  });

  it("passes null GitHub auth params when config values are missing", () => {
    delete configResult.data.APP_MODE;
    delete configResult.data.GITHUB_CLIENT_ID;
    delete configResult.data.AUTH_URL;
    authResult.data = true;

    renderMainApp("/");

    expect(useGitHubAuthUrlMock).toHaveBeenCalledWith({
      appMode: null,
      gitHubClientId: null,
      authUrl: undefined,
    });
  });

  it("renders unknown error fallback when error type is unexpected", () => {
    const useRouteErrorSpy = vi.spyOn(ReactRouter, "useRouteError").mockReturnValue("unhandled");

    renderWithProviders(<ErrorBoundary />);

    expect(screen.getByTestId("page-title")).toHaveTextContent("ERROR$UNKNOWN");

    useRouteErrorSpy.mockRestore();
  });

  it("returns false from shouldConversationStartOpen when window is undefined", () => {
    const originalWindow = globalThis.window;
    try {
      (globalThis as unknown as { window: Window | undefined }).window = undefined;
      expect(shouldConversationStartOpen()).toBe(false);
    } finally {
      (globalThis as unknown as { window: Window | undefined }).window = originalWindow;
    }
  });

  it("returns false from checkLoginMethodExists when localStorage is unavailable", () => {
    const originalWindow = globalThis.window;
    try {
      (globalThis as unknown as { window: Partial<Window> }).window = {};
      expect(checkLoginMethodExists()).toBe(false);
    } finally {
      (globalThis as unknown as { window: Window | undefined }).window = originalWindow;
    }
  });
});


