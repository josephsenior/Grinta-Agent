import { useState, useEffect, useMemo } from "react";
import type { Settings } from "#/types/settings";
import { DEFAULT_SETTINGS } from "#/services/settings";
import {
  createDefaultDirtyInputs,
  type DirtyInputs,
  normalizeSecurityAnalyzerSelection,
  initializeStateFromSettings,
  updateViewFromSettings,
  mergeAdvancedSettings,
} from "./llm-settings-helpers";

interface UseLlmSettingsStateProps {
  settings: Settings | undefined;
  resources?: {
    models?: unknown[];
    securityAnalyzers?: string[];
    agents?: string[];
  };
  userToggledView: boolean;
  setView: React.Dispatch<React.SetStateAction<"basic" | "advanced">>;
}

export function useLlmSettingsState({
  settings,
  resources,
  userToggledView,
  setView,
}: UseLlmSettingsStateProps) {
  const [dirtyInputs, setDirtyInputs] = useState<DirtyInputs>(
    createDefaultDirtyInputs,
  );
  const [currentSelectedModel, setCurrentSelectedModel] = useState<
    string | null
  >(null);
  const [confirmationModeEnabled, setConfirmationModeEnabled] = useState(
    settings?.CONFIRMATION_MODE ?? DEFAULT_SETTINGS.CONFIRMATION_MODE,
  );
  const [selectedSecurityAnalyzer, setSelectedSecurityAnalyzer] = useState(
    normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER),
  );
  const [agentValue, setAgentValue] = useState(
    settings?.AGENT ?? DEFAULT_SETTINGS.AGENT ?? "Orchestrator",
  );
  const [enableDefaultCondenser, setEnableDefaultCondenser] = useState(
    settings?.ENABLE_DEFAULT_CONDENSER ??
      DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
  );
  const [condenserMaxSize, setCondenserMaxSize] = useState<number | null>(
    settings?.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
  );
  const [advancedOverrides, setAdvancedOverrides] = useState<Partial<Settings>>(
    {},
  );

  useEffect(() => {
    initializeStateFromSettings({
      settings,
      setCurrentSelectedModel,
      setAgentValue,
      setConfirmationModeEnabled,
      setSelectedSecurityAnalyzer,
      setEnableDefaultCondenser,
      setCondenserMaxSize,
      setAdvancedOverrides,
      setDirtyInputs,
    });
  }, [settings]);

  useEffect(() => {
    updateViewFromSettings({
      settings,
      resources: resources
        ? {
            models: (resources.models || []) as string[],
            agents: resources.agents || [],
            securityAnalyzers: resources.securityAnalyzers || [],
          }
        : undefined,
      userToggledView,
      setView,
    });
  }, [settings, resources, userToggledView, setView]);

  const advancedSettings = useMemo(
    () =>
      mergeAdvancedSettings(
        settings,
        advancedOverrides,
        enableDefaultCondenser,
        condenserMaxSize,
        confirmationModeEnabled,
        selectedSecurityAnalyzer,
        agentValue,
      ),
    [
      settings,
      advancedOverrides,
      enableDefaultCondenser,
      condenserMaxSize,
      confirmationModeEnabled,
      selectedSecurityAnalyzer,
      agentValue,
    ],
  );

  return {
    dirtyInputs,
    setDirtyInputs,
    currentSelectedModel,
    setCurrentSelectedModel,
    confirmationModeEnabled,
    setConfirmationModeEnabled,
    selectedSecurityAnalyzer,
    setSelectedSecurityAnalyzer,
    agentValue,
    setAgentValue,
    enableDefaultCondenser,
    setEnableDefaultCondenser,
    condenserMaxSize,
    setCondenserMaxSize,
    advancedOverrides,
    setAdvancedOverrides,
    advancedSettings,
  };
}
