import React from "react";
import { useTranslation } from "react-i18next";
import { AutonomyMode } from "#/components/features/controls/autonomy-mode-selector";
import { useSettings } from "./query/use-settings";
import { useSaveSettings } from "./mutation/use-save-settings";

/**
 * Custom hook to manage autonomy mode state and API calls
 * Handles persistence and backend synchronization
 */
export function useAutonomyMode() {
  const { t } = useTranslation();
  const { data: settings } = useSettings();
  const { mutate: saveSettings } = useSaveSettings();
  const [isLoading, setIsLoading] = React.useState(false);

  // Use settings value directly if available, otherwise check localStorage, then default to "balanced"
  // This ensures we always show the correct mode (with localStorage fallback for older backends)
  const currentMode = React.useMemo(() => {
    // First, try to get from backend settings (using the correct field name from backend)
    if (
      settings?.autonomy_level &&
      ["supervised", "balanced", "full"].includes(settings.autonomy_level)
    ) {
      return settings.autonomy_level as AutonomyMode;
    }

    // Fallback to localStorage if backend doesn't support autonomy_level
    const stored = localStorage.getItem("autonomy_mode");
    if (stored && ["supervised", "balanced", "full"].includes(stored)) {
      return stored as AutonomyMode;
    }

    return "balanced";
  }, [settings?.autonomy_level]);

  // Save mode changes to backend API
  const handleModeChange = React.useCallback(
    async (mode: AutonomyMode) => {
      setIsLoading(true);

      console.log(`[useAutonomyMode] Changing mode: ${currentMode} → ${mode}`);

      // Save to backend API - React Query will automatically update the cache
      saveSettings(
        {
          autonomy_level: mode,
        },
        {
          onSuccess: () => {
            console.log(`[useAutonomyMode] Successfully saved mode: ${mode}`);
            setIsLoading(false);
          },
          onError: (error) => {
            console.error("[useAutonomyMode] Failed to save mode:", error);
            setIsLoading(false);
          },
        },
      );
    },
    [currentMode, saveSettings],
  );

  // Get mode description for tooltips/help
  const getModeDescription = React.useCallback(
    (mode: AutonomyMode) => {
      switch (mode) {
        case "supervised":
          return t(
            "Supervised mode: Agent will always ask for confirmation before taking actions",
          );
        case "balanced":
          return t(
            "Balanced mode: Agent will ask for confirmation only for high-risk actions",
          );
        case "full":
          return t(
            "Full autonomous mode: Agent will execute tasks without asking for confirmation",
          );
        default:
          return "";
      }
    },
    [t],
  );

  // Get mode icon and color
  const getModeInfo = React.useCallback((mode: AutonomyMode) => {
    switch (mode) {
      case "supervised":
        return { color: "orange", icon: "shield" };
      case "balanced":
        return { color: "blue", icon: "eye" };
      case "full":
        return { color: "green", icon: "zap" };
      default:
        return { color: "gray", icon: "settings" };
    }
  }, []);

  return {
    currentMode,
    handleModeChange,
    isLoading,
    getModeDescription,
    getModeInfo,
  };
}
