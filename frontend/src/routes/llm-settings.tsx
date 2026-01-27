import React from "react";
import { useTranslation } from "react-i18next";
import { AxiosError } from "axios";
import { organizeModelsAndProviders } from "#/utils/organize-models-and-providers";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";
import { useSettings } from "#/hooks/query/use-settings";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { useConfig } from "#/hooks/query/use-config";
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";
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
    return (
      <Card className="bg-transparent border-0 shadow-none">
        <CardHeader className="space-y-4 px-0 pb-8">
          <div className="animate-pulse h-8 w-64 bg-black/50 rounded-xl mx-auto" />
        </CardHeader>
      </Card>
    );
  }

  return (
    <SettingsErrorBoundary fallbackMessage="Failed to load LLM settings. Please try refreshing the page.">
      <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
        <div className="mx-auto max-w-6xl w-full">
          <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-2xl p-6 sm:p-8 lg:p-10">
            <div data-testid="llm-settings-screen" className="w-full">
              <form onSubmit={handleSubmit} className="w-full space-y-6">
                <Card className="bg-transparent border-0 shadow-none">
                  <CardHeader className="space-y-4 px-0 pb-8">
                    <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
                      {t("SETTINGS$LLM_SETTINGS", "LLM Settings")}
                    </CardTitle>
                    <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
                      Configure your language model and AI settings
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="px-0 pt-0">
                    <div className="space-y-8">
                      <div className="flex items-center justify-between pb-4 border-b border-[var(--border-primary)]">
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {t("SETTINGS$VIEW_MODE", "View Mode")}
                        </span>
                        <SettingsSwitch
                          testId="advanced-settings-switch"
                          defaultIsToggled={view === "advanced"}
                          isToggled={view === "advanced"}
                          onToggle={handleToggleAdvancedSettings}
                        >
                          {t("SETTINGS$ADVANCED")}
                        </SettingsSwitch>
                      </div>

                      {view === "basic" && (
                        <div className="space-y-6">
                          <BasicSettingsSection
                            settings={settings}
                            modelsAndProviders={modelsAndProviders}
                            currentSelectedModel={currentSelectedModel}
                            isLoading={isLoading}
                            isFetching={isFetching}
                            onModelChange={handlers.handleModelIsDirty}
                            onApiKeyChange={handlers.handleApiKeyIsDirty}
                            t={t}
                          />
                        </div>
                      )}

                      {view === "advanced" && (
                        <div className="space-y-6">
                          <AdvancedSettingsSection
                            settings={settings}
                            advancedSettings={advancedSettings}
                            currentSelectedModel={currentSelectedModel}
                            agentValue={agentValue}
                            agentOptions={agentOptions}
                            appMode={config?.APP_MODE}
                            enableDefaultCondenser={enableDefaultCondenser}
                            condenserMaxSize={condenserMaxSize}
                            onCustomModelChange={
                              handlers.handleCustomModelIsDirty
                            }
                            onBaseUrlChange={handlers.handleBaseUrlIsDirty}
                            onApiKeyChange={handlers.handleApiKeyIsDirty}
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
                        </div>
                      )}

                      <div className="border-t border-[var(--border-primary)] pt-8">
                        <ConfirmationSettingsSection
                          confirmationModeEnabled={confirmationModeEnabled}
                          selectedSecurityAnalyzer={selectedSecurityAnalyzer}
                          securityAnalyzerOptions={securityAnalyzerOptions}
                          onToggleConfirmationMode={
                            handlers.handleConfirmationModeChange
                          }
                          onSecurityAnalyzerChange={
                            handlers.handleSecurityAnalyzerChange
                          }
                          onSecurityAnalyzerInputClear={
                            handlers.handleSecurityAnalyzerClear
                          }
                          t={t}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Save Button */}
                <div className="space-y-2 pt-4">
                  <button
                    type="submit"
                    disabled={!formIsDirty || isPending}
                    className="w-full h-12 rounded-xl bg-[var(--text-accent)] hover:bg-[var(--text-accent)]/90 text-white font-bold text-sm transition-all duration-200 shadow-lg shadow-[var(--text-accent)]/20 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isPending
                      ? t("SETTINGS$SAVING")
                      : t("SETTINGS$SAVE_CHANGES")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </SettingsErrorBoundary>
  );
}

export default LlmSettingsScreen;
