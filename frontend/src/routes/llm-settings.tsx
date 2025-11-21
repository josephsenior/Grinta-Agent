import React from "react";
import { useTranslation } from "react-i18next";
import { AxiosError } from "axios";
import { organizeModelsAndProviders } from "#/utils/organize-models-and-providers";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";
import { useSettings } from "#/hooks/query/use-settings";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { useConfig } from "#/hooks/query/use-config";
import { LlmSettingsInputsSkeleton } from "#/components/features/settings/llm-settings/llm-settings-inputs-skeleton";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { SettingsErrorBoundary } from "#/components/features/settings/settings-error-boundary";
import { BasicSettingsSection } from "./llm-settings/basic-settings-section";
import { AdvancedSettingsSection } from "./llm-settings/advanced-settings-section";
import { ConfirmationSettingsSection } from "./llm-settings/confirmation-settings-section";
import {
  buildAdvancedPayload,
  buildBasicPayload,
  createDefaultDirtyInputs,
  type DirtyInputs,
} from "./llm-settings/llm-settings-helpers";
import { useLlmSettingsHandlers } from "./llm-settings/use-llm-settings-handlers";
import { useLlmSettingsState } from "./llm-settings/use-llm-settings-state";
import type { Settings } from "#/types/settings";

type SecurityAnalyzerOption = { key: string; label: string };

const getSecurityAnalyzerOptions = (
  analyzers: string[] | undefined,
  t: ReturnType<typeof useTranslation>["t"],
): SecurityAnalyzerOption[] => {
  const items = analyzers ?? [];
  const ordered: SecurityAnalyzerOption[] = [];

  if (items.includes("llm")) {
    ordered.push({
      key: "llm",
      label: t("SETTINGS$SECURITY_ANALYZER_LLM_DEFAULT"),
    });
  }

  ordered.push({
    key: "none",
    label: t("SETTINGS$SECURITY_ANALYZER_NONE"),
  });

  if (items.includes("invariant")) {
    ordered.push({
      key: "invariant",
      label: t("SETTINGS$SECURITY_ANALYZER_INVARIANT"),
    });
  }

  items.forEach((analyzer) => {
    if (!["llm", "invariant", "none"].includes(analyzer)) {
      ordered.push({ key: analyzer, label: analyzer });
    }
  });

  return ordered;
};

const getAgentOptions = (agent?: string) => {
  const defaults = [
    { key: "CodeActAgent", label: "CodeActAgent" },
    { key: "CoActAgent", label: "CoActAgent" },
  ];

  if (agent && !defaults.some((item) => item.key === agent)) {
    return [...defaults, { key: agent, label: agent }];
  }

  return defaults;
};

// ============================================================================
// Helper Utilities
// ============================================================================

function buildPayloadForView(view: "basic" | "advanced", formData: FormData) {
  if (view === "basic") {
    return buildBasicPayload({ formData });
  }
  return buildAdvancedPayload({ formData });
}

function LlmSettingsScreen() {
  const { t } = useTranslation();

  const { mutate: saveSettings, isPending } = useSaveSettings();
  const { data: resources } = useAIConfigOptions();
  const { data: settings, isFetching, isLoading } = useSettings();
  const { data: config } = useConfig();

  const modelsAndProviders = React.useMemo(
    () => organizeModelsAndProviders(resources?.models || []),
    [resources?.models],
  );

  const [view, setView] = React.useState<"basic" | "advanced">("basic");
  const [userToggledView, setUserToggledView] = React.useState(false);

  const state = useLlmSettingsState({
    settings,
    resources,
    userToggledView,
    setView,
  });

  const {
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
    setAdvancedOverrides,
    advancedSettings,
  } = state;

  const agentOptions = React.useMemo(
    () => getAgentOptions(settings?.AGENT),
    [settings?.AGENT],
  );

  const securityAnalyzerOptions = React.useMemo(
    () => getSecurityAnalyzerOptions(resources?.securityAnalyzers, t),
    [resources?.securityAnalyzers, t],
  );

  const handleSuccessfulMutation = () => {
    displaySuccessToast("Settings saved successfully! ✅");
    setDirtyInputs(createDefaultDirtyInputs());
  };

  const handleErrorMutation = (error: AxiosError) => {
    const errorMessage = retrieveAxiosErrorMessage(error);
    displayErrorToast(t("ERROR$GENERIC", { defaultValue: errorMessage }));
  };

  const handleToggleAdvancedSettings = (isToggled: boolean) => {
    setUserToggledView(true);
    setView(isToggled ? "advanced" : "basic");
    setDirtyInputs(createDefaultDirtyInputs());
  };

  const markDirty = (field: keyof DirtyInputs, isDirty: boolean) => {
    setDirtyInputs((prev) => ({ ...prev, [field]: isDirty }));
  };

  const handlers = useLlmSettingsHandlers({
    settings,
    selectedSecurityAnalyzer,
    setCurrentSelectedModel,
    setAgentValue,
    setConfirmationModeEnabled,
    setSelectedSecurityAnalyzer,
    setEnableDefaultCondenser,
    setCondenserMaxSize,
    markDirty,
  });

  const handleAdvancedConfigChange = (updates: Partial<Settings>) => {
    setAdvancedOverrides((prev) => ({ ...prev, ...updates }));
    markDirty("model", true);
  };

  const formIsDirty = React.useMemo(
    () => Object.values(dirtyInputs).some(Boolean),
    [dirtyInputs],
  );

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const payload = buildPayloadForView(view, formData);

    saveSettings(payload, {
      onSuccess: handleSuccessfulMutation,
      onError: handleErrorMutation,
    });
  };

  if (!settings || isFetching) {
    return <LlmSettingsInputsSkeleton />;
  }

  return (
    <SettingsErrorBoundary fallbackMessage="Failed to load LLM settings. Please try refreshing the page.">
      <div data-testid="llm-settings-screen" className="h-full">
        <form
          onSubmit={handleSubmit}
          className="flex h-full flex-col justify-between"
        >
          <div className="flex flex-col gap-6 lg:gap-8 p-6 sm:p-8 lg:p-10">
            <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
              <SettingsSwitch
                testId="advanced-settings-switch"
                defaultIsToggled={view === "advanced"}
                isToggled={view === "advanced"}
                onToggle={handleToggleAdvancedSettings}
              >
                {t("SETTINGS$ADVANCED")}
              </SettingsSwitch>

              {view === "basic" && (
                <BasicSettingsSection
                  settings={settings}
                  modelsAndProviders={modelsAndProviders}
                  currentSelectedModel={currentSelectedModel}
                  isLoading={isLoading}
                  isFetching={isFetching}
                  onModelChange={handlers.handleModelIsDirty}
                  onApiKeyChange={handlers.handleApiKeyIsDirty}
                  onSearchApiKeyChange={handlers.handleSearchApiKeyIsDirty}
                  t={t}
                />
              )}

              {view === "advanced" && (
                <AdvancedSettingsSection
                  settings={settings}
                  advancedSettings={advancedSettings}
                  currentSelectedModel={currentSelectedModel}
                  agentValue={agentValue}
                  agentOptions={agentOptions}
                  appMode={config?.APP_MODE}
                  enableDefaultCondenser={enableDefaultCondenser}
                  condenserMaxSize={condenserMaxSize}
                  onCustomModelChange={handlers.handleCustomModelIsDirty}
                  onBaseUrlChange={handlers.handleBaseUrlIsDirty}
                  onApiKeyChange={handlers.handleApiKeyIsDirty}
                  onSearchApiKeyChange={handlers.handleSearchApiKeyIsDirty}
                  onAgentChange={handlers.handleAgentChange}
                  onAdvancedConfigChange={handleAdvancedConfigChange}
                  onCondenserMaxSizeChange={
                    handlers.handleCondenserMaxSizeChange
                  }
                  onEnableDefaultCondenserToggle={
                    handlers.handleEnableDefaultCondenserChange
                  }
                  t={t}
                />
              )}

              <ConfirmationSettingsSection
                confirmationModeEnabled={confirmationModeEnabled}
                selectedSecurityAnalyzer={selectedSecurityAnalyzer}
                securityAnalyzerOptions={securityAnalyzerOptions}
                onToggleConfirmationMode={handlers.handleConfirmationModeChange}
                onSecurityAnalyzerChange={handlers.handleSecurityAnalyzerChange}
                onSecurityAnalyzerInputClear={
                  handlers.handleSecurityAnalyzerClear
                }
                t={t}
              />
            </div>
          </div>

          <div className="flex justify-end gap-6 border-t border-white/10 bg-black/80 backdrop-blur-xl px-6 sm:px-8 lg:px-10 py-6">
            <BrandButton
              testId="submit-button"
              type="submit"
              variant="primary"
              isDisabled={!formIsDirty || isPending}
            >
              {isPending ? t("SETTINGS$SAVING") : t("SETTINGS$SAVE_CHANGES")}
            </BrandButton>
          </div>
        </form>
      </div>
    </SettingsErrorBoundary>
  );
}

export default LlmSettingsScreen;
