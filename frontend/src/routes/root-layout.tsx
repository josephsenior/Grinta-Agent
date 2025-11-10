import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  useRouteError,
  isRouteErrorResponse,
  Outlet,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
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
import { RoutePreloader } from "#/utils/route-preloader";
import { injectCriticalCSS } from "#/utils/critical-css";

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
  const controller = useMainAppController();

  return (
    <AppErrorBoundary>
      <ToastProvider>
        <div
          data-testid="root-layout"
          className="min-h-screen w-full bg-black font-sans safe-area-top safe-area-bottom safe-area-left safe-area-right"
        >
          <div className="relative z-10 h-screen lg:min-w-[1024px] flex flex-col overflow-hidden">
            <MainLayoutShell controller={controller} />
          </div>

          <AppFooter isConversationPage={controller.isConversationPage} />
          <OverlayModals controller={controller} />
          <RoutePreloader />
        </div>
      </ToastProvider>
    </AppErrorBoundary>
  );
}

interface MainAppController {
  isConversationPage: boolean;
  showHeader: boolean;
  status: {
    renderAuthModal: boolean;
    renderReAuthModal: boolean;
    consentFormIsOpen: boolean;
  };
  config: ReturnType<typeof useConfig>["data"];
  settings: ReturnType<typeof useSettings>["data"];
  conversationPanelIsOpen: boolean;
  openConversationPanel: () => void;
  closeConversationPanel: () => void;
  closeConsentForm: () => void;
  effectiveGitHubAuthUrl: string | null;
  isAuthed: boolean | undefined;
  t: TFunction;
}

function useMainAppController(): MainAppController {
  const { navigate, pathname, isOnTosPage, isConversationPage } =
    useRouteContext();
  const { t } = useTranslation();

  const appData = useMainAppData(isOnTosPage);
  useMainAppLifecycle({
    isOnTosPage,
    settings: appData.settings,
    config: appData.config,
    balance: appData.balance,
    pathname,
    navigate,
    t,
  });

  const effectiveGitHubAuthUrl = useEffectiveGitHubAuthUrl({
    gitHubAuthUrl: appData.gitHubAuthUrl,
    isOnTosPage,
  });
  const loginMethodExists = useLoginMethodDetection(appData.isAuthed);
  const authModalState = useAuthModalState({
    isAuthed: appData.isAuthed,
    authQuery: appData.authQuery,
    isOnTosPage,
    config: appData.config,
    loginMethodExists,
  });
  const {
    conversationPanelIsOpen,
    openConversationPanel,
    closeConversationPanel,
  } = useConversationPanelState();
  const { consentFormIsOpen, closeConsentForm } = useConsentFormState({
    isOnTosPage,
    settings: appData.settings,
    migrateUserConsent: appData.migrateUserConsent,
  });

  return {
    isConversationPage,
    showHeader: !isConversationPage,
    status: {
      renderAuthModal: authModalState.renderAuthModal,
      renderReAuthModal: authModalState.renderReAuthModal,
      consentFormIsOpen,
    },
    config: appData.config.data,
    settings: appData.settings,
    conversationPanelIsOpen,
    openConversationPanel,
    closeConversationPanel,
    closeConsentForm,
    effectiveGitHubAuthUrl,
    isAuthed: appData.isAuthed,
    t,
  };
}

function useRouteContext() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isOnTosPage = useIsOnTosPage();
  const isConversationPage = pathname.startsWith("/conversations/");

  return { navigate, pathname, isOnTosPage, isConversationPage };
}

function useMainAppData(isOnTosPage: boolean) {
  const config = useConfig();
  const settingsQuery = useSettings();
  const settings = settingsQuery.data;
  const balance = useBalance();
  const migrateUserConsent = useMigrateUserConsent();
  const authQuery = useIsAuthed();
  const isAuthed = authQuery.data;
  const gitHubAuthUrl = useGitHubAuthUrl({
    appMode: config.data?.APP_MODE || null,
    gitHubClientId: config.data?.GITHUB_CLIENT_ID || null,
    authUrl: config.data?.AUTH_URL,
  });

  return {
    config,
    settings,
    balance,
    migrateUserConsent,
    authQuery,
    isAuthed,
    gitHubAuthUrl,
  };
}

function useMainAppLifecycle({
  isOnTosPage,
  settings,
  config,
  balance,
  pathname,
  navigate,
  t,
}: {
  isOnTosPage: boolean;
  settings: ReturnType<typeof useSettings>["data"];
  config: ReturnType<typeof useConfig>;
  balance: ReturnType<typeof useBalance>;
  pathname: string;
  navigate: ReturnType<typeof useNavigate>;
  t: TFunction;
}) {
  useAutoLogin();
  useAuthCallback();
  useCriticalCss();
  useLanguageSync({ isOnTosPage, settings });
  useNewUserToast({ settings, config, t });
  useBalanceRedirect({ isOnTosPage, balance, pathname, navigate });
}

function useCriticalCss() {
  useEffect(() => {
    injectCriticalCSS();
  }, []);
}

function useLanguageSync({
  isOnTosPage,
  settings,
}: {
  isOnTosPage: boolean;
  settings: ReturnType<typeof useSettings>["data"];
}) {
  useEffect(() => {
    if (!isOnTosPage && settings?.LANGUAGE) {
      i18n.changeLanguage(settings.LANGUAGE);
    }
  }, [isOnTosPage, settings?.LANGUAGE]);
}

function useNewUserToast({
  settings,
  config,
  t,
}: {
  settings: ReturnType<typeof useSettings>["data"];
  config: ReturnType<typeof useConfig>;
  t: TFunction;
}) {
  useEffect(() => {
    if (settings?.IS_NEW_USER && config.data?.APP_MODE === "saas") {
      displaySuccessToast(t(I18nKey.BILLING$YOURE_IN));
    }
  }, [settings?.IS_NEW_USER, config.data?.APP_MODE, t]);
}

function useBalanceRedirect({
  isOnTosPage,
  balance,
  pathname,
  navigate,
}: {
  isOnTosPage: boolean;
  balance: ReturnType<typeof useBalance>;
  pathname: string;
  navigate: ReturnType<typeof useNavigate>;
}) {
  useEffect(() => {
    if (!isOnTosPage && balance.error?.status === 402 && pathname !== "/") {
      navigate("/");
    }
  }, [balance.error?.status, pathname, isOnTosPage, navigate]);
}

function useEffectiveGitHubAuthUrl({
  gitHubAuthUrl,
  isOnTosPage,
}: {
  gitHubAuthUrl: string | null;
  isOnTosPage: boolean;
}) {
  return useMemo(
    () => (isOnTosPage ? null : gitHubAuthUrl),
    [gitHubAuthUrl, isOnTosPage],
  );
}

function useAuthModalState({
  isAuthed,
  authQuery,
  isOnTosPage,
  config,
  loginMethodExists,
}: {
  isAuthed: boolean | undefined;
  authQuery: ReturnType<typeof useIsAuthed>;
  isOnTosPage: boolean;
  config: ReturnType<typeof useConfig>;
  loginMethodExists: boolean;
}) {
  const baseConditions =
    !isAuthed &&
    !authQuery.isError &&
    !authQuery.isFetching &&
    !isOnTosPage &&
    config.data?.APP_MODE === "saas";

  return {
    renderAuthModal: baseConditions && !loginMethodExists,
    renderReAuthModal: baseConditions && loginMethodExists,
  };
}

function useLoginMethodDetection(isAuthed: boolean | undefined) {
  const [loginMethodExists, setLoginMethodExists] = useState(
    checkLoginMethodExists(),
  );

  useEffect(() => {
    setLoginMethodExists(checkLoginMethodExists());
  }, [isAuthed]);

  useEffect(() => {
    const onStorageChange = (event: StorageEvent) => {
      if (event.key === LOCAL_STORAGE_KEYS.LOGIN_METHOD) {
        setLoginMethodExists(checkLoginMethodExists());
      }
    };
    const onFocus = () => setLoginMethodExists(checkLoginMethodExists());

    window.addEventListener("storage", onStorageChange);
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("storage", onStorageChange);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  return loginMethodExists;
}

function useConversationPanelState() {
  const [conversationPanelIsOpen, setConversationPanelIsOpen] = useState(() =>
    shouldConversationStartOpen(),
  );

  const openConversationPanel = useCallback(() => {
    setConversationPanelIsOpen(true);
  }, []);

  const closeConversationPanel = useCallback(() => {
    setConversationPanelIsOpen(false);
  }, []);

  useEffect(() => {
    const openHandler = () => openConversationPanel();
    window.addEventListener("Forge:open-conversation-panel", openHandler);

    if (shouldConversationStartOpen()) {
      openHandler();
    }

    return () => {
      window.removeEventListener("Forge:open-conversation-panel", openHandler);
    };
  }, [openConversationPanel]);

  return {
    conversationPanelIsOpen,
    openConversationPanel,
    closeConversationPanel,
  };
}

function useConsentFormState({
  isOnTosPage,
  settings,
  migrateUserConsent,
}: {
  isOnTosPage: boolean;
  settings: ReturnType<typeof useSettings>["data"];
  migrateUserConsent: ReturnType<typeof useMigrateUserConsent>;
}) {
  const [consentFormIsOpen, setConsentFormIsOpen] = useState(false);

  useEffect(() => {
    if (!isOnTosPage) {
      const consentRequired = settings?.USER_CONSENTS_TO_ANALYTICS === null;
      setConsentFormIsOpen(Boolean(consentRequired));
    }
  }, [isOnTosPage, settings?.USER_CONSENTS_TO_ANALYTICS]);

  useEffect(() => {
    if (isOnTosPage) {
      return;
    }

    migrateUserConsent.migrateUserConsent({
      handleAnalyticsWasPresentInLocalStorage: () => {
        setConsentFormIsOpen(false);
      },
    });
  }, [isOnTosPage, migrateUserConsent]);

  const closeConsentForm = useCallback(() => {
    setConsentFormIsOpen(false);
  }, []);

  return { consentFormIsOpen, closeConsentForm };
}

function MainLayoutShell({ controller }: { controller: MainAppController }) {
  const maintenanceEnabled = controller.config?.MAINTENANCE;

  return (
    <>
      {controller.showHeader && (
        <Suspense
          fallback={
            <div className="h-16 bg-background-tertiary animate-pulse" />
          }
        >
          <Header />
        </Suspense>
      )}

      <Suspense
        fallback={
          <div
            className={`fixed left-0 w-64 h-full bg-background-tertiary animate-pulse ${
              controller.isConversationPage ? "top-0" : "top-16"
            }`}
          />
        }
      >
        <Sidebar />
      </Suspense>

      <div
        className={cn(
          "flex flex-1 h-full min-h-0",
          controller.isConversationPage ? "" : "pt-14",
        )}
      >
        <div
          className={
            controller.isConversationPage
              ? "w-full h-full"
              : "p-3 md:p-4 lg:p-6 w-full"
          }
        >
          <div className="flex flex-col flex-1 gap-3 md:gap-4 lg:gap-5 min-w-0 h-full">
            {maintenanceEnabled &&
              controller.config?.MAINTENANCE?.startTime && (
                <div className="flex-shrink-0 animate-slide-down">
                  <div className="glass rounded-xl p-3 md:p-4 border-primary-600/30 bg-primary-985/20 backdrop-blur-lg shadow-lg">
                    <Suspense
                      fallback={
                        <div className="h-8 bg-background-tertiary/70 animate-pulse rounded" />
                      }
                    >
                      <MaintenanceBanner
                        startTime={controller.config.MAINTENANCE.startTime}
                      />
                    </Suspense>
                  </div>
                </div>
              )}

            <div
              id="root-outlet"
              className="flex-1 relative rounded-2xl bg-black h-full min-h-0"
            >
              <div className="h-full min-h-0 overflow-auto scrollbar-thin scrollbar-thumb-grey-700 scrollbar-track-transparent">
                <Suspense
                  fallback={
                    <div className="h-full bg-background-secondary animate-pulse" />
                  }
                >
                  <EmailVerificationGuard>
                    <div className="h-full min-h-0">
                      <Outlet />
                    </div>
                  </EmailVerificationGuard>
                </Suspense>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function AppFooter({ isConversationPage }: { isConversationPage: boolean }) {
  if (isConversationPage) {
    return null;
  }

  return (
    <Suspense
      fallback={<div className="h-16 bg-background-tertiary animate-pulse" />}
    >
      <Footer />
    </Suspense>
  );
}

function OverlayModals({ controller }: { controller: MainAppController }) {
  return (
    <>
      {controller.conversationPanelIsOpen && (
        <Suspense
          fallback={
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
              <div className="bg-background-tertiary w-96 h-96 animate-pulse rounded-lg" />
            </div>
          }
        >
          <ConversationPanelWrapper isOpen={controller.conversationPanelIsOpen}>
            <div className="animate-slide-up">
              <ConversationPanel onClose={controller.closeConversationPanel} />
            </div>
          </ConversationPanelWrapper>
        </Suspense>
      )}

      {controller.status.renderAuthModal && (
        <Suspense fallback={<ModalFallback />}>
          <AuthModal
            githubAuthUrl={controller.effectiveGitHubAuthUrl}
            appMode={controller.config?.APP_MODE}
            providersConfigured={controller.config?.PROVIDERS_CONFIGURED}
            authUrl={controller.config?.AUTH_URL}
          />
        </Suspense>
      )}

      {controller.status.renderReAuthModal && (
        <Suspense fallback={<ModalFallback />}>
          <ReauthModal />
        </Suspense>
      )}

      {controller.config?.APP_MODE === "oss" &&
        controller.status.consentFormIsOpen && (
          <Suspense fallback={<ModalFallback />}>
            <AnalyticsConsentFormModal onClose={controller.closeConsentForm} />
          </Suspense>
        )}

      {controller.config?.FEATURE_FLAGS?.ENABLE_BILLING &&
        controller.config?.APP_MODE === "saas" &&
        controller.settings?.IS_NEW_USER && (
          <Suspense fallback={<ModalFallback />}>
            <SetupPaymentModal />
          </Suspense>
        )}
    </>
  );
}

function ModalFallback() {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-background-tertiary w-96 h-64 animate-pulse rounded-lg" />
    </div>
  );
}

function shouldConversationStartOpen(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const win = window as Window & { __Forge_PLAYWRIGHT?: boolean };
  return win?.__Forge_PLAYWRIGHT === true;
}

function checkLoginMethodExists(): boolean {
  if (typeof window === "undefined" || !window.localStorage) {
    return false;
  }
  return localStorage.getItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD) !== null;
}

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

// Minimal hydrate fallback used by React Router to improve UX while route modules
// hydrate on the client. This also silences the 'hydrateFallback' developer hint.
export const hydrateFallback = <div aria-hidden className="route-loading" />;

export { shouldConversationStartOpen, checkLoginMethodExists };
