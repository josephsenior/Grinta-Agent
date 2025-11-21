import React from "react";
import type { Settings } from "#/types/settings";
import type { DirtyInputs } from "./llm-settings-helpers";
import {
  onModelDirtyChange,
  onCustomModelDirtyChange,
  onAgentChange,
  onConfirmationModeChange,
  onCondenserMaxSizeChange,
  onSecurityAnalyzerChange,
  onSecurityAnalyzerClear,
} from "./llm-settings-helpers";

interface UseLlmSettingsHandlersProps {
  settings: Settings | undefined;
  selectedSecurityAnalyzer: string;
  setCurrentSelectedModel: React.Dispatch<React.SetStateAction<string | null>>;
  setAgentValue: React.Dispatch<React.SetStateAction<string>>;
  setConfirmationModeEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  setSelectedSecurityAnalyzer: React.Dispatch<React.SetStateAction<string>>;
  setEnableDefaultCondenser: React.Dispatch<React.SetStateAction<boolean>>;
  setCondenserMaxSize: React.Dispatch<React.SetStateAction<number | null>>;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}

export function useLlmSettingsHandlers({
  settings,
  selectedSecurityAnalyzer,
  setCurrentSelectedModel,
  setAgentValue,
  setConfirmationModeEnabled,
  setSelectedSecurityAnalyzer,
  setEnableDefaultCondenser,
  setCondenserMaxSize,
  markDirty,
}: UseLlmSettingsHandlersProps) {
  const handleModelIsDirty = React.useCallback(
    (model: string | null) => {
      onModelDirtyChange({
        model,
        settings,
        markDirty,
        setCurrentSelectedModel,
      });
    },
    [settings, markDirty, setCurrentSelectedModel],
  );

  const handleCustomModelIsDirty = React.useCallback(
    (model: string) => {
      onCustomModelDirtyChange({
        model,
        settings,
        markDirty,
        setCurrentSelectedModel,
      });
    },
    [settings, markDirty, setCurrentSelectedModel],
  );

  const handleApiKeyIsDirty = React.useCallback(
    (apiKey: string) => {
      markDirty("apiKey", apiKey.trim() !== "");
    },
    [markDirty],
  );

  const handleSearchApiKeyIsDirty = React.useCallback(
    (apiKey: string) => {
      markDirty("searchApiKey", apiKey !== (settings?.SEARCH_API_KEY ?? ""));
    },
    [settings, markDirty],
  );

  const handleBaseUrlIsDirty = React.useCallback(
    (baseUrl: string) => {
      markDirty("baseUrl", baseUrl !== (settings?.LLM_BASE_URL ?? ""));
    },
    [settings, markDirty],
  );

  const handleAgentChange = React.useCallback(
    (agent: string) => {
      onAgentChange({
        agent,
        settings,
        setAgentValue,
        markDirty,
      });
    },
    [settings, setAgentValue, markDirty],
  );

  const handleConfirmationModeChange = React.useCallback(
    (isToggled: boolean) => {
      onConfirmationModeChange({
        isToggled,
        settings,
        selectedSecurityAnalyzer,
        setConfirmationModeEnabled,
        setSelectedSecurityAnalyzer,
        markDirty,
      });
    },
    [
      settings,
      selectedSecurityAnalyzer,
      setConfirmationModeEnabled,
      setSelectedSecurityAnalyzer,
      markDirty,
    ],
  );

  const handleEnableDefaultCondenserChange = React.useCallback(
    (isToggled: boolean) => {
      setEnableDefaultCondenser(isToggled);
      markDirty(
        "enableDefaultCondenser",
        isToggled !== (settings?.ENABLE_DEFAULT_CONDENSER ?? true),
      );
    },
    [settings, setEnableDefaultCondenser, markDirty],
  );

  const handleCondenserMaxSizeChange = React.useCallback(
    (value: string) => {
      onCondenserMaxSizeChange({
        value,
        settings,
        setCondenserMaxSize,
        markDirty,
      });
    },
    [settings, setCondenserMaxSize, markDirty],
  );

  const handleSecurityAnalyzerChange = React.useCallback(
    (value: string) => {
      onSecurityAnalyzerChange({
        value,
        settings,
        setSelectedSecurityAnalyzer,
        markDirty,
      });
    },
    [settings, setSelectedSecurityAnalyzer, markDirty],
  );

  const handleSecurityAnalyzerClear = React.useCallback(() => {
    onSecurityAnalyzerClear({
      settings,
      setSelectedSecurityAnalyzer,
      markDirty,
    });
  }, [settings, setSelectedSecurityAnalyzer, markDirty]);

  return {
    handleModelIsDirty,
    handleCustomModelIsDirty,
    handleApiKeyIsDirty,
    handleSearchApiKeyIsDirty,
    handleBaseUrlIsDirty,
    handleAgentChange,
    handleConfirmationModeChange,
    handleEnableDefaultCondenserChange,
    handleCondenserMaxSizeChange,
    handleSecurityAnalyzerChange,
    handleSecurityAnalyzerClear,
  };
}
