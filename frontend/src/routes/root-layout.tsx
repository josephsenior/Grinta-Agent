import React, { Suspense } from "react";
import {
  useRouteError,
  isRouteErrorResponse,
  Outlet,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ErrorBoundary as AppErrorBoundary } from "#/components/shared/error/error-boundary";
import { I18nKey } from "#/i18n/declaration";
import i18n from "#/i18n";
import { useGitHubAuthUrl } from "#/hooks/use-github-auth-url";
import { useIsAuthed } from "#/hooks/query/use-is-authed";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { useMigrateUserConsent } from "#/hooks/use-migrate-user-consent";
import { useBalance } from "#/hooks/query/use-balance";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";
import { useIsOnTosPage } from "#/hooks/use-is-on-tos-page";
import { useAutoLogin } from "#/hooks/use-auto-login";
import { useAuthCallback } from "#/hooks/use-auth-callback";
import { LOCAL_STORAGE_KEYS } from "#/utils/local-storage";
import { ToastProvider } from "#/components/shared/notifications/toast";

// Performance optimization imports
import { RoutePreloader } from "#/utils/route-preloader";
import { injectCriticalCSS } from "#/utils/critical-css";

// Lazy load heavy components for better performance
const ConversationPanelWrapper = React.lazy(() =>
  import(
    "#/components/features/conversation-panel/conversation-panel-wrapper"
  ).then((m) => ({ default: m.ConversationPanelWrapper })),
);
const ConversationPanel = React.lazy(() =>
  import("#/components/features/conversation-panel/conversation-panel").then(
    (m) => ({ default: m.ConversationPanel }),
  ),
);
const AuthModal = React.lazy(() =>
  import("#/components/features/waitlist/auth-modal").then((m) => ({
    default: m.AuthModal,
  })),
);
const ReauthModal = React.lazy(() =>
  import("#/components/features/waitlist/reauth-modal").then((m) => ({
    default: m.ReauthModal,
  })),
);
const AnalyticsConsentFormModal = React.lazy(() =>
  import("#/components/features/analytics/analytics-consent-form-modal").then(
    (m) => ({ default: m.AnalyticsConsentFormModal }),
  ),
);
const Sidebar = React.lazy(() =>
  import("#/components/features/sidebar/sidebar").then((m) => ({
    default: m.Sidebar,
  })),
);
const Header = React.lazy(() =>
  import("#/components/layout/Header").then((m) => ({ default: m.Header })),
);
const Footer = React.lazy(() =>
  import("#/components/layout/Footer").then((m) => ({ default: m.Footer })),
);
const SetupPaymentModal = React.lazy(() =>
  import("#/components/features/payment/setup-payment-modal").then((m) => ({
    default: m.SetupPaymentModal,
  })),
);
const EmailVerificationGuard = React.lazy(() =>
  import("#/components/features/guards/email-verification-guard").then((m) => ({
    default: m.EmailVerificationGuard,
  })),
);
const MaintenanceBanner = React.lazy(() =>
  import("#/components/features/maintenance/maintenance-banner").then((m) => ({
    default: m.MaintenanceBanner,
  })),
);

export function ErrorBoundary() {
  const error = useRouteError();
  const { t } = useTranslation();

  if (isRouteErrorResponse(error)) {
    return (
      <div>
        <h1 data-testid="page-title">{error.status}</h1>
        <p>{error.statusText}</p>
        <pre>
          {error.data instanceof Object
            ? JSON.stringify(error.data)
            : error.data}
        </pre>
      </div>
    );
  }
  if (error instanceof Error) {
    return (
      <div>
        <h1 data-testid="page-title">{t(I18nKey.ERROR$GENERIC)}</h1>
        <pre>{error.message}</pre>
      </div>
    );
  }

  return (
    <div>
      <h1 data-testid="page-title">{t(I18nKey.ERROR$UNKNOWN)}</h1>
    </div>
  );
}

export default function MainApp() {
  interface WindowWithE2E extends Window {
    __OPENHANDS_PLAYWRIGHT?: boolean;
  }

  const getWin = () =>
    typeof window !== "undefined"
      ? (window as unknown as WindowWithE2E)
      : undefined;
  // Conversation overlay open/close managed at root level
  const [conversationPanelIsOpen, setConversationPanelIsOpen] = React.useState(
    () => {
      const win = getWin();
      // If Playwright is running, open panel by default so tests don't
      // depend on socket-driven events or event ordering.
      if (win?.__OPENHANDS_PLAYWRIGHT === true) {
        return true;
      }
      return false;
    },
  );

  React.useEffect(() => {
    const openHandler = () => setConversationPanelIsOpen(true);
    window.addEventListener("openhands:open-conversation-panel", openHandler);
    // If Playwright test flag is present, open the panel immediately on mount
    // This guards against the test harness dispatching the event before the
    // listener is attached.
    const win = getWin();
    if (win?.__OPENHANDS_PLAYWRIGHT === true) {
      openHandler();
    }
    return () =>
      window.removeEventListener(
        "openhands:open-conversation-panel",
        openHandler,
      );
  }, []);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isOnTosPage = useIsOnTosPage();
  const isConversationPage = pathname.startsWith("/conversations/");
  const { data: settings } = useSettings();
  const { error } = useBalance();
  const { migrateUserConsent } = useMigrateUserConsent();
  const { t } = useTranslation();

  const config = useConfig();
  const {
    data: isAuthed,
    isFetching: isFetchingAuth,
    isError: isAuthError,
  } = useIsAuthed();

  // Always call the hook, but we'll only use the result when not on TOS page
  const gitHubAuthUrl = useGitHubAuthUrl({
    appMode: config.data?.APP_MODE || null,
    gitHubClientId: config.data?.GITHUB_CLIENT_ID || null,
    authUrl: config.data?.AUTH_URL,
  });

  // When on TOS page, we don't use the GitHub auth URL
  const effectiveGitHubAuthUrl = isOnTosPage ? null : gitHubAuthUrl;

  const [consentFormIsOpen, setConsentFormIsOpen] = React.useState(false);

  // Auto-login if login method is stored in local storage
  useAutoLogin();

  // Handle authentication callback and set login method after successful authentication
  useAuthCallback();

  React.useEffect(() => {
    // Don't change language when on TOS page
    if (!isOnTosPage && settings?.LANGUAGE) {
      i18n.changeLanguage(settings.LANGUAGE);
    }
    // (removed unused dev-only references)
  }, [settings?.LANGUAGE, isOnTosPage]);

  React.useEffect(() => {
    // Don't show consent form when on TOS page
    if (!isOnTosPage) {
      const consentFormModalIsOpen =
        settings?.USER_CONSENTS_TO_ANALYTICS === null;

      setConsentFormIsOpen(consentFormModalIsOpen);
    }
  }, [settings, isOnTosPage]);

  React.useEffect(() => {
    // Don't migrate user consent when on TOS page
    if (!isOnTosPage) {
      // Migrate user consent to the server if it was previously stored in localStorage
      migrateUserConsent({
        handleAnalyticsWasPresentInLocalStorage: () => {
          setConsentFormIsOpen(false);
        },
      });
    }
  }, [isOnTosPage]);

  React.useEffect(() => {
    if (settings?.IS_NEW_USER && config.data?.APP_MODE === "saas") {
      displaySuccessToast(t(I18nKey.BILLING$YOURE_IN));
    }
  }, [settings?.IS_NEW_USER, config.data?.APP_MODE]);

  React.useEffect(() => {
    // Don't do any redirects when on TOS page
    // Don't allow users to use the app if it 402s
    if (!isOnTosPage && error?.status === 402 && pathname !== "/") {
      navigate("/");
    }
  }, [error?.status, pathname, isOnTosPage]);

  // Function to check if login method exists in local storage
  const checkLoginMethodExists = React.useCallback(() => {
    // Only check localStorage if we're in a browser environment
    if (typeof window !== "undefined" && window.localStorage) {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD) !== null;
    }
    return false;
  }, []);

  // State to track if login method exists
  const [loginMethodExists, setLoginMethodExists] = React.useState(
    checkLoginMethodExists(),
  );

  // Listen for storage events to update loginMethodExists when logout happens
  React.useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === LOCAL_STORAGE_KEYS.LOGIN_METHOD) {
        setLoginMethodExists(checkLoginMethodExists());
      }
    };

    // Also check on window focus, as logout might happen in another tab
    const handleWindowFocus = () => {
      setLoginMethodExists(checkLoginMethodExists());
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("focus", handleWindowFocus);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("focus", handleWindowFocus);
    };
  }, [checkLoginMethodExists]);

  // Check login method status when auth status changes
  React.useEffect(() => {
    // When auth status changes (especially on logout), recheck login method
    setLoginMethodExists(checkLoginMethodExists());
  }, [isAuthed, checkLoginMethodExists]);

  const renderAuthModal =
    !isAuthed &&
    !isAuthError &&
    !isFetchingAuth &&
    !isOnTosPage &&
    config.data?.APP_MODE === "saas" &&
    !loginMethodExists; // Don't show auth modal if login method exists in local storage

  const renderReAuthModal =
    !isAuthed &&
    !isAuthError &&
    !isFetchingAuth &&
    !isOnTosPage &&
    config.data?.APP_MODE === "saas" &&
    loginMethodExists;

  // Inject critical CSS for performance
  React.useEffect(() => {
    injectCriticalCSS();
  }, []);

  return (
    <AppErrorBoundary>
      <ToastProvider>
        <div
          data-testid="root-layout"
          className="min-h-screen w-full bg-black font-outfit safe-area-top safe-area-bottom safe-area-left safe-area-right"
        >
        {/* Pure black background */}

        {/* Main Layout Container with Sidebar Above Extensions */}
        <div className="relative z-10 h-screen lg:min-w-[1024px] flex flex-col min-h-0">
          {/* Header (template-wide) - Hidden on conversation pages */}
          {!isConversationPage && (
            <Suspense
              fallback={<div className="h-16 bg-background-tertiary animate-pulse" />}
            >
              <Header />
            </Suspense>
          )}

          {/* Sidebar (kept mounted so global UI effects like Settings modal on 404 run) */}
          <Suspense
            fallback={
              <div
                className={`fixed left-0 w-64 h-full bg-background-tertiary animate-pulse ${
                  isConversationPage ? "top-0" : "top-16"
                }`}
              />
            }
          >
            <Sidebar />
          </Suspense>

          {/* Main Content Area Below Sidebar */}
          <div
            className={`flex flex-1 h-full min-h-0 ${
              isConversationPage ? "" : "pt-14"
            }`}
          >
            <div className={isConversationPage ? "w-full h-full" : "p-3 md:p-4 lg:p-6 w-full"}>
              <div className="flex flex-col flex-1 gap-3 md:gap-4 lg:gap-5 min-w-0 h-full">
              {/* Maintenance Banner with Better Spacing */}
              {config.data?.MAINTENANCE && (
                <div className="flex-shrink-0 animate-slide-down">
                  <div className="glass rounded-xl p-3 md:p-4 border-primary-600/30 bg-primary-985/20 backdrop-blur-lg shadow-lg">
                    <Suspense
                      fallback={
                        <div className="h-8 bg-background-tertiary/70 animate-pulse rounded" />
                      }
                    >
                      <MaintenanceBanner
                        startTime={config.data.MAINTENANCE.startTime}
                      />
                    </Suspense>
                  </div>
                </div>
              )}

              {/* Main Content Outlet with Enhanced Container */}
              <div
                id="root-outlet"
                className="flex-1 relative overflow-auto rounded-2xl bg-black h-full min-h-0 max-h-full"
              >
                <div className="h-full min-h-0">
                  <div className="h-full min-h-0 overflow-auto scrollbar-thin scrollbar-thumb-grey-700 scrollbar-track-transparent">
                    <Suspense
                      fallback={
                        <div className="h-full bg-background-secondary animate-pulse" />
                      }
                    >
                      <EmailVerificationGuard>
                        <div className="h-full min-h-0 p-0 md:p-0 lg:p-0">
                          <Outlet />
                        </div>
                      </EmailVerificationGuard>
                    </Suspense>
                  </div>
                </div>
              </div>
            </div>
            </div>
          </div>
        </div>

        {/* Footer (template-wide) - Hidden on conversation pages */}
        {!isConversationPage && (
          <Suspense fallback={<div className="h-16 bg-background-tertiary animate-pulse" />}>
            <Footer />
          </Suspense>
        )}

        {/* Modals */}
        {/* Conversation Panel Overlay */}
        {conversationPanelIsOpen && (
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
                <div className="bg-background-tertiary w-96 h-96 animate-pulse rounded-lg" />
              </div>
            }
          >
            <ConversationPanelWrapper isOpen={conversationPanelIsOpen}>
              <div className="animate-slide-up">
                <ConversationPanel
                  onClose={() => setConversationPanelIsOpen(false)}
                />
              </div>
            </ConversationPanelWrapper>
          </Suspense>
        )}
        {renderAuthModal && (
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
                <div className="bg-background-tertiary w-96 h-64 animate-pulse rounded-lg" />
              </div>
            }
          >
            <AuthModal
              githubAuthUrl={effectiveGitHubAuthUrl}
              appMode={config.data?.APP_MODE}
              providersConfigured={config.data?.PROVIDERS_CONFIGURED}
              authUrl={config.data?.AUTH_URL}
            />
          </Suspense>
        )}
        {renderReAuthModal && (
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
                <div className="bg-background-tertiary w-96 h-64 animate-pulse rounded-lg" />
              </div>
            }
          >
            <ReauthModal />
          </Suspense>
        )}
        {config.data?.APP_MODE === "oss" && consentFormIsOpen && (
          <Suspense
            fallback={
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
                <div className="bg-background-tertiary w-96 h-64 animate-pulse rounded-lg" />
              </div>
            }
          >
            <AnalyticsConsentFormModal
              onClose={() => {
                setConsentFormIsOpen(false);
              }}
            />
          </Suspense>
        )}

        {config.data?.FEATURE_FLAGS?.ENABLE_BILLING &&
          config.data?.APP_MODE === "saas" &&
          settings?.IS_NEW_USER && (
            <Suspense
              fallback={
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
                  <div className="bg-background-tertiary w-96 h-64 animate-pulse rounded-lg" />
                </div>
              }
            >
              <SetupPaymentModal />
            </Suspense>
          )}

        {/* Route Preloader for performance optimization */}
        <RoutePreloader />
        </div>
      </ToastProvider>
    </AppErrorBoundary>
  );
}

// Minimal hydrate fallback used by React Router to improve UX while route modules
// hydrate on the client. This also silences the 'hydrateFallback' developer hint.
export const hydrateFallback = <div aria-hidden className="route-loading" />;
