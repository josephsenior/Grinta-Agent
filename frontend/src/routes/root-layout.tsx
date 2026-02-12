import React, {
  useEffect,
  useMemo,
} from "react";
import {
  useRouteError,
  isRouteErrorResponse,
  Outlet,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LOCAL_STORAGE_KEYS, checkLoginMethodExists } from "#/utils/local-storage";
import type { TFunction } from "i18next";
import { ErrorBoundary as AppErrorBoundary } from "#/components/shared/error/error-boundary";
import { I18nKey } from "#/i18n/declaration";
import i18n from "#/i18n";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { ToastProvider } from "#/components/shared/notifications/toast";
import { RoutePreloader } from "#/utils/route-preloader";
import { injectCriticalCSS } from "#/utils/critical-css";
import { Button } from "#/components/ui/button";
import { SkipLink } from "#/components/layout/skip-link";
import { SidebarProvider } from "#/context/sidebar-context";

const DesktopLayout = React.lazy(() =>
  import("#/components/layout/desktop-layout").then((m) => ({
    default: m.DesktopLayout,
  })),
);

export function ErrorBoundary() {
  const error = useRouteError();
  const navigate = useNavigate();
  const { t } = useTranslation();

  if (isRouteErrorResponse(error)) {
    // Handle 404 errors
    if (error.status === 404) {
      navigate("/404", { replace: true });
      return null;
    }

    // Handle other HTTP errors
    return (
      <div className="relative min-h-screen overflow-hidden bg-(--bg-primary) text-(--text-primary)">
        <div className="relative z-1 flex min-h-screen flex-col items-center justify-center px-6 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <div className="mb-8">
              <h1 className="text-9xl font-bold text-transparent bg-clip-text bg-linear-to-r from-brand-500 via-accent-500 to-brand-600">
                {error.status}
              </h1>
            </div>
            <div className="mb-8 space-y-4">
              <h2 className="text-3xl font-semibold text-(--text-primary) sm:text-4xl">
                {error.statusText || "Something went wrong"}
              </h2>
              <p className="text-lg text-(--text-tertiary)">
                {error.data instanceof Object
                  ? JSON.stringify(error.data)
                  : error.data || "An error occurred while loading this page."}
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                onClick={() => navigate("/conversations")}
                className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl px-6 py-3"
              >
                {t("common.goToConversations", "Go to Conversations")}
              </Button>
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
              >
                {t("common.reloadPage", "Reload Page")}
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error instanceof Error) {
    return (
      <div className="relative min-h-screen overflow-hidden bg-(--bg-primary) text-(--text-primary)">
        <div className="relative z-1 flex min-h-screen flex-col items-center justify-center px-6 py-20">
          <div className="mx-auto max-w-2xl text-center">
            <div className="mb-8">
              <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-linear-to-r from-brand-500 via-accent-500 to-brand-600">
                {t("error.title", "Error")}
              </h1>
            </div>
            <div className="mb-8 space-y-4">
              <h2 className="text-3xl font-semibold text-(--text-primary) sm:text-4xl">
                {t(I18nKey.ERROR$GENERIC)}
              </h2>
              <p className="text-lg text-(--text-tertiary)">
                {error.message || "An unexpected error occurred."}
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                onClick={() => navigate("/conversations")}
                className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl px-6 py-3"
              >
                {t("common.goToConversations", "Go to Conversations")}
              </Button>
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
                className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
              >
                {t("common.reloadPage", "Reload Page")}
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative min-h-screen overflow-hidden text-foreground bg-[var(--bg-primary)]"
    >
      <div className="relative z-1 flex min-h-screen flex-col items-center justify-center px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mb-8">
            <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-linear-to-r from-brand-500 via-accent-500 to-brand-600">
              {t("error.title", "Error")}
            </h1>
          </div>
          <div className="mb-8 space-y-4">
            <h2
              className="text-3xl font-semibold sm:text-4xl text-[var(--text-primary)]"
            >
              {t(I18nKey.ERROR$UNKNOWN)}
            </h2>
            <p className="text-lg text-[var(--text-secondary)]">
              {t(
                "error.unknownError",
                "An unknown error occurred. Please try again.",
              )}
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              onClick={() => navigate("/conversations")}
              className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl px-6 py-3"
            >
              {t("common.goToConversations", "Go to Conversations")}
            </Button>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
            >
              {t(I18nKey.ERROR$RELOAD_PAGE)}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MainAppController {
  isConversationPage: boolean;
  config: ReturnType<typeof useConfig>["data"];
  settings: ReturnType<typeof useSettings>["data"];
  t: TFunction;
}

function useRouteContext() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isConversationPage = pathname.startsWith("/conversations/");

  return {
    navigate,
    pathname,
    isConversationPage,
  };
}

function useMainAppData() {
  const config = useConfig();
  const settingsQuery = useSettings();
  const settings = settingsQuery.data;

  return {
    config,
    settings,
  };
}

function useCriticalCss() {
  useEffect(() => {
    injectCriticalCSS();
  }, []);
}

function useLanguageSync({
  settings,
}: {
  settings: ReturnType<typeof useSettings>["data"];
}) {
  useEffect(() => {
    if (settings?.LANGUAGE) {
      i18n.changeLanguage(settings.LANGUAGE);
    }
  }, [settings?.LANGUAGE]);
}

function useMainAppLifecycle({
  settings,
  config: _config,
  pathname: _pathname,
  navigate: _navigate,
  t: _t,
}: {
  settings: ReturnType<typeof useSettings>["data"];
  config: ReturnType<typeof useConfig>;
  pathname: string;
  navigate: ReturnType<typeof useNavigate>;
  t: TFunction;
}) {
  useCriticalCss();
  useLanguageSync({ settings });
}

function shouldConversationStartOpen(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const win = window as Window & { __Forge_PLAYWRIGHT?: boolean };
  return win?.__Forge_PLAYWRIGHT === true;
}

function useMainAppController(): MainAppController {
  const { navigate, pathname, isConversationPage } =
    useRouteContext();
  const { t } = useTranslation();

  const appData = useMainAppData();
  useMainAppLifecycle({
    settings: appData.settings,
    config: appData.config,
    pathname,
    navigate,
    t,
  });

  return {
    isConversationPage,
    config: appData.config.data,
    settings: appData.settings,
    t,
  };
}

export default function MainApp() {
  const controller = useMainAppController();

  return (
    <AppErrorBoundary>
      <ToastProvider>
        <SidebarProvider>
          <div
            data-testid="root-layout"
            className="min-h-screen w-full bg-(--bg-primary) font-sans safe-area-top safe-area-bottom safe-area-left safe-area-right"
          >
            <SkipLink />
      <DesktopLayout>
        <div className="h-full w-full">
          <Outlet />
        </div>
      </DesktopLayout>
      <RoutePreloader />
          </div>
        </SidebarProvider>
      </ToastProvider>
    </AppErrorBoundary>
  );
}

// Minimal hydrate fallback used by React Router to improve UX while route modules
// hydrate on the client. This also silences the 'hydrateFallback' developer hint.
export const hydrateFallback = <div aria-hidden className="route-loading" />;

export { shouldConversationStartOpen, checkLoginMethodExists };
