import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

export function useSidebarSettings() {
  const location = useLocation();
  const { data: config } = useConfig();
  const {
    data: settings,
    error: settingsError,
    isError: settingsIsError,
    isFetching: isFetchingSettings,
  } = useSettings();

  const [settingsModalIsOpen, setSettingsModalIsOpen] = useState(false);

  const shouldHideLlmSettings =
    config?.FEATURE_FLAGS?.HIDE_LLM_SETTINGS && config?.APP_MODE === "saas";

  useEffect(() => {
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
      displayErrorToast(
        "Something went wrong while fetching settings. Please reload the page.",
      );
    } else if (config?.APP_MODE === "oss" && settingsError?.status === 404) {
      setSettingsModalIsOpen(true);
    }
  }, [
    shouldHideLlmSettings,
    location.pathname,
    isFetchingSettings,
    settingsIsError,
    settingsError?.status,
    config?.APP_MODE,
  ]);

  return {
    settingsModalIsOpen,
    setSettingsModalIsOpen,
    settings,
  };
}
