import React from "react";
import { useLocation } from "react-router-dom";
import { useGitUser } from "#/hooks/query/use-git-user";
import { SettingsModal } from "#/components/shared/modals/settings/settings-modal";
import { useSettings } from "#/hooks/query/use-settings";
import { ConversationPanel } from "../conversation-panel/conversation-panel";
import { ConversationPanelWrapper } from "../conversation-panel/conversation-panel-wrapper";
import { useLogout } from "#/hooks/mutation/use-logout";
import { useConfig } from "#/hooks/query/use-config";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

export function Sidebar() {
  const location = useLocation();
  // removed isConversationRoute usage since the top-aside header is removed globally
  useGitUser();
  const { data: config } = useConfig();
  const {
    data: settings,
    error: settingsError,
    isError: settingsIsError,
    isFetching: isFetchingSettings,
  } = useSettings();
  useLogout();

  const [settingsModalIsOpen, setSettingsModalIsOpen] = React.useState(false);

  const [conversationPanelIsOpen, setConversationPanelIsOpen] =
    React.useState(false);

  interface WindowWithE2E extends Window {
    __OPENHANDS_PLAYWRIGHT?: boolean;
  }

  const win =
    typeof window !== "undefined"
      ? (window as unknown as WindowWithE2E)
      : undefined;

  const isPlaywrightRun = win?.__OPENHANDS_PLAYWRIGHT === true;

  // TODO: Remove HIDE_LLM_SETTINGS check once released
  const shouldHideLlmSettings =
    config?.FEATURE_FLAGS?.HIDE_LLM_SETTINGS && config?.APP_MODE === "saas";

  React.useEffect(() => {
    // Open conversation panel when an external trigger requests it
    const openHandler = () => setConversationPanelIsOpen(true);
    window.addEventListener("openhands:open-conversation-panel", openHandler);

    // If Playwright is running, open immediately to guard against the
    // event being dispatched before this listener attaches.
    if (win?.__OPENHANDS_PLAYWRIGHT === true) {
      openHandler();
    }

    return () => {
      window.removeEventListener(
        "openhands:open-conversation-panel",
        openHandler,
      );
    };
  }, []);

  React.useEffect(() => {
    if (shouldHideLlmSettings) {
      return;
    }

    if (location.pathname === "/settings") {
      setSettingsModalIsOpen(false);
    } else if (
      !isFetchingSettings &&
      settingsIsError &&
      settingsError?.status !== 404
    ) {
      // We don't show toast errors for settings in the global error handler
      // because we have a special case for 404 errors
      displayErrorToast(
        "Something went wrong while fetching settings. Please reload the page.",
      );
    } else if (config?.APP_MODE === "oss" && settingsError?.status === 404) {
      setSettingsModalIsOpen(true);
    }
  }, [
    settingsError?.status,
    settingsError,
    isFetchingSettings,
    location.pathname,
  ]);

  return (
    <>
      {/* Top header removed globally per user request (logo + top buttons + settings/avatar). */}
      {/* Keep the conversation panel rendering (if open) and settings modal. */}
      {conversationPanelIsOpen && !isPlaywrightRun && (
        <ConversationPanelWrapper isOpen={conversationPanelIsOpen}>
          <div className="animate-slide-up">
            <ConversationPanel
              onClose={() => setConversationPanelIsOpen(false)}
            />
          </div>
        </ConversationPanelWrapper>
      )}

      {/* Enhanced Settings Modal */}
      {settingsModalIsOpen && (
        <div className="animate-scale-in">
          <SettingsModal
            settings={settings}
            onClose={() => setSettingsModalIsOpen(false)}
          />
        </div>
      )}
    </>
  );
}
