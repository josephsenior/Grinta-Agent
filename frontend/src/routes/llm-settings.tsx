import React from "react";
import { useTranslation } from "react-i18next";
import { AxiosError } from "axios";
import { organizeModelsAndProviders } from "#/utils/organize-models-and-providers";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";
import { useSettings } from "#/hooks/query/use-settings";
import { hasAdvancedSettingsSet } from "#/utils/has-advanced-settings-set";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { useConfig } from "#/hooks/query/use-config";
import { isCustomModel } from "#/utils/is-custom-model";
import { LlmSettingsInputsSkeleton } from "#/components/features/settings/llm-settings/llm-settings-inputs-skeleton";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { displayErrorToast, displaySuccessToast } from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { SettingsErrorBoundary } from "#/components/features/settings/settings-error-boundary";
import { BasicSettingsSection } from "./llm-settings/basic-settings-section";
import { AdvancedSettingsSection } from "./llm-settings/advanced-settings-section";
import { ConfirmationSettingsSection } from "./llm-settings/confirmation-settings-section";
import {
  buildAdvancedPayload,
  buildBasicPayload,
  createDefaultDirtyInputs,
  DirtyInputs,
  normalizeSecurityAnalyzerSelection,
} from "./llm-settings/llm-settings-helpers";
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

const mergeAdvancedSettings = (
  settings: Settings | undefined,
  overrides: Partial<Settings>,
  enableDefaultCondenser: boolean,
  condenserMaxSize: number | null,
  confirmationModeEnabled: boolean,
  securityAnalyzer: string,
  agentValue: string,
): Settings => {
  const base = settings ?? DEFAULT_SETTINGS;

  return {
    ...DEFAULT_SETTINGS,
    ...base,
    ...overrides,
    ENABLE_DEFAULT_CONDENSER: enableDefaultCondenser,
    CONDENSER_MAX_SIZE: condenserMaxSize ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
    CONFIRMATION_MODE: confirmationModeEnabled,
    SECURITY_ANALYZER:
      securityAnalyzer === "none" ? null : securityAnalyzer || base.SECURITY_ANALYZER,
    AGENT: agentValue || DEFAULT_SETTINGS.AGENT,
  };
};

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
  const [dirtyInputs, setDirtyInputs] = React.useState<DirtyInputs>(
    createDefaultDirtyInputs,
  );
  const [currentSelectedModel, setCurrentSelectedModel] = React.useState<string | null>(null);
  const [confirmationModeEnabled, setConfirmationModeEnabled] = React.useState(
    settings?.CONFIRMATION_MODE ?? DEFAULT_SETTINGS.CONFIRMATION_MODE,
  );
  const [selectedSecurityAnalyzer, setSelectedSecurityAnalyzer] = React.useState(
    normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER),
  );
  const [agentValue, setAgentValue] = React.useState(
    settings?.AGENT ?? DEFAULT_SETTINGS.AGENT ?? "CodeActAgent",
  );
  const [enableDefaultCondenser, setEnableDefaultCondenser] = React.useState(
    settings?.ENABLE_DEFAULT_CONDENSER ?? DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
  );
  const [condenserMaxSize, setCondenserMaxSize] = React.useState<number | null>(
    settings?.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
  );
  const [advancedOverrides, setAdvancedOverrides] = React.useState<Partial<Settings>>({});

  React.useEffect(() => {
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

  React.useEffect(() => {
    updateViewFromSettings({ settings, resources, userToggledView, setView });
  }, [settings, resources, userToggledView]);

  const agentOptions = React.useMemo(
    () => getAgentOptions(settings?.AGENT),
    [settings?.AGENT],
  );

  const securityAnalyzerOptions = React.useMemo(
    () => getSecurityAnalyzerOptions(resources?.securityAnalyzers, t),
    [resources?.securityAnalyzers, t],
  );

  const advancedSettings = React.useMemo(
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

  const handleModelIsDirty = (model: string | null) => {
    onModelDirtyChange({
      model,
      settings,
      markDirty,
      setCurrentSelectedModel,
    });
  };

  const handleCustomModelIsDirty = (model: string) => {
    onCustomModelDirtyChange({
      model,
      settings,
      markDirty,
      setCurrentSelectedModel,
    });
  };

  const handleApiKeyIsDirty = (apiKey: string) => {
    markDirty("apiKey", apiKey.trim() !== "");
  };

  const handleSearchApiKeyIsDirty = (apiKey: string) => {
    markDirty("searchApiKey", apiKey !== (settings?.SEARCH_API_KEY ?? ""));
  };

  const handleBaseUrlIsDirty = (baseUrl: string) => {
    markDirty("baseUrl", baseUrl !== (settings?.LLM_BASE_URL ?? ""));
  };

  const handleAgentChange = (agent: string) => {
    onAgentChange({
      agent,
      settings,
      setAgentValue,
      markDirty,
    });
  };

  const handleConfirmationModeChange = (isToggled: boolean) => {
    onConfirmationModeChange({
      isToggled,
      settings,
      selectedSecurityAnalyzer,
      setConfirmationModeEnabled,
      setSelectedSecurityAnalyzer,
      markDirty,
    });
  };

  const handleEnableDefaultCondenserChange = (isToggled: boolean) => {
    setEnableDefaultCondenser(isToggled);
    markDirty("enableDefaultCondenser", isToggled !== (settings?.ENABLE_DEFAULT_CONDENSER ?? true));
  };

  const handleCondenserMaxSizeChange = (value: string) => {
    onCondenserMaxSizeChange({
      value,
      settings,
      setCondenserMaxSize,
      markDirty,
    });
  };

  const handleSecurityAnalyzerChange = (value: string) => {
    onSecurityAnalyzerChange({
      value,
      settings,
      setSelectedSecurityAnalyzer,
      markDirty,
    });
  };

  const handleSecurityAnalyzerClear = () => {
    onSecurityAnalyzerClear({
      settings,
      setSelectedSecurityAnalyzer,
      markDirty,
    });
  };

  const handleAdvancedConfigChange = (config: Partial<Settings>) => {
    setAdvancedOverrides((prev) => ({ ...prev, ...config }));
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
        <form onSubmit={handleSubmit} className="flex h-full flex-col justify-between">
          <div className="flex flex-col gap-6 p-9">
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
                onModelChange={handleModelIsDirty}
                onApiKeyChange={handleApiKeyIsDirty}
                onSearchApiKeyChange={handleSearchApiKeyIsDirty}
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
                onCustomModelChange={handleCustomModelIsDirty}
                onBaseUrlChange={handleBaseUrlIsDirty}
                onApiKeyChange={handleApiKeyIsDirty}
                onSearchApiKeyChange={handleSearchApiKeyIsDirty}
                onAgentChange={handleAgentChange}
                onAdvancedConfigChange={handleAdvancedConfigChange}
                onCondenserMaxSizeChange={handleCondenserMaxSizeChange}
                onEnableDefaultCondenserToggle={handleEnableDefaultCondenserChange}
                t={t}
              />
            )}

            <ConfirmationSettingsSection
              confirmationModeEnabled={confirmationModeEnabled}
              selectedSecurityAnalyzer={selectedSecurityAnalyzer}
              securityAnalyzerOptions={securityAnalyzerOptions}
              onToggleConfirmationMode={handleConfirmationModeChange}
              onSecurityAnalyzerChange={handleSecurityAnalyzerChange}
              onSecurityAnalyzerInputClear={handleSecurityAnalyzerClear}
              t={t}
            />
          </div>

          <div className="flex justify-end gap-6 border-t border-border-secondary p-6">
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

function initializeStateFromSettings({
  settings,
  setCurrentSelectedModel,
  setAgentValue,
  setConfirmationModeEnabled,
  setSelectedSecurityAnalyzer,
  setEnableDefaultCondenser,
  setCondenserMaxSize,
  setAdvancedOverrides,
  setDirtyInputs,
}: {
  settings?: Settings;
  setCurrentSelectedModel: (value: string | null) => void;
  setAgentValue: (value: string) => void;
  setConfirmationModeEnabled: (value: boolean) => void;
  setSelectedSecurityAnalyzer: (value: string) => void;
  setEnableDefaultCondenser: (value: boolean) => void;
  setCondenserMaxSize: (value: number | null) => void;
  setAdvancedOverrides: React.Dispatch<React.SetStateAction<Partial<Settings>>>;
  setDirtyInputs: React.Dispatch<React.SetStateAction<DirtyInputs>>;
}) {
  if (!settings) {
    return;
  }

  applyPrimarySettings({
    settings,
    setCurrentSelectedModel,
    setAgentValue,
    setConfirmationModeEnabled,
    setSelectedSecurityAnalyzer,
    setEnableDefaultCondenser,
    setCondenserMaxSize,
  });

  applyAdvancedOverrides({ settings, setAdvancedOverrides });
  setDirtyInputs(createDefaultDirtyInputs());
}

function applyPrimarySettings({
  settings,
  setCurrentSelectedModel,
  setAgentValue,
  setConfirmationModeEnabled,
  setSelectedSecurityAnalyzer,
  setEnableDefaultCondenser,
  setCondenserMaxSize,
}: {
  settings: Settings;
  setCurrentSelectedModel: (value: string | null) => void;
  setAgentValue: (value: string) => void;
  setConfirmationModeEnabled: (value: boolean) => void;
  setSelectedSecurityAnalyzer: (value: string) => void;
  setEnableDefaultCondenser: (value: boolean) => void;
  setCondenserMaxSize: (value: number | null) => void;
}) {
  setCurrentSelectedModel(settings.LLM_MODEL ?? null);
  setAgentValue(settings.AGENT ?? DEFAULT_SETTINGS.AGENT ?? "CodeActAgent");
  setConfirmationModeEnabled(settings.CONFIRMATION_MODE ?? DEFAULT_SETTINGS.CONFIRMATION_MODE);
  setSelectedSecurityAnalyzer(normalizeSecurityAnalyzerSelection(settings.SECURITY_ANALYZER));
  setEnableDefaultCondenser(
    settings.ENABLE_DEFAULT_CONDENSER ?? DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
  );
  setCondenserMaxSize(settings.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE);
}

function applyAdvancedOverrides({
  settings,
  setAdvancedOverrides,
}: {
  settings: Settings;
  setAdvancedOverrides: React.Dispatch<React.SetStateAction<Partial<Settings>>>;
}) {
  setAdvancedOverrides({
    LLM_TEMPERATURE: settings.LLM_TEMPERATURE ?? null,
    LLM_TOP_P: settings.LLM_TOP_P ?? null,
    LLM_MAX_OUTPUT_TOKENS: settings.LLM_MAX_OUTPUT_TOKENS ?? null,
    LLM_TIMEOUT: settings.LLM_TIMEOUT ?? null,
    LLM_NUM_RETRIES: settings.LLM_NUM_RETRIES ?? null,
    LLM_CACHING_PROMPT: settings.LLM_CACHING_PROMPT ?? null,
    LLM_DISABLE_VISION: settings.LLM_DISABLE_VISION ?? null,
    LLM_CUSTOM_LLM_PROVIDER: settings.LLM_CUSTOM_LLM_PROVIDER ?? null,
  });
}

function updateViewFromSettings({
  settings,
  resources,
  userToggledView,
  setView,
}: {
  settings?: Settings;
  resources?: ReturnType<typeof useAIConfigOptions>["data"];
  userToggledView: boolean;
  setView: React.Dispatch<React.SetStateAction<"basic" | "advanced">>;
}) {
  if (!settings || userToggledView) {
    return;
  }

  if (hasAdvancedSettingsSet(settings)) {
    setView("advanced");
    return;
  }

  if (resources && isCustomModel(resources.models, settings.LLM_MODEL)) {
    setView("advanced");
    return;
  }

  setView("basic");
}

function onModelDirtyChange({
  model,
  settings,
  markDirty,
  setCurrentSelectedModel,
}: {
  model: string | null;
  settings?: Settings;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
  setCurrentSelectedModel: (value: string | null) => void;
}) {
  const normalized = settings?.LLM_MODEL ?? DEFAULT_SETTINGS.LLM_MODEL;
  const cleanModel = normalized.startsWith("openai/")
    ? normalized.replace("openai/", "")
    : normalized;
  markDirty("model", model !== cleanModel);
  setCurrentSelectedModel(model);
}

function onCustomModelDirtyChange({
  model,
  settings,
  markDirty,
  setCurrentSelectedModel,
}: {
  model: string;
  settings?: Settings;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
  setCurrentSelectedModel: (value: string | null) => void;
}) {
  const current = settings?.LLM_MODEL ?? "";
  const isDirty = model !== "" && model !== current;
  markDirty("model", isDirty);
  setCurrentSelectedModel(model);
}

function onAgentChange({
  agent,
  settings,
  setAgentValue,
  markDirty,
}: {
  agent: string;
  settings?: Settings;
  setAgentValue: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setAgentValue(agent);
  const current = settings?.AGENT ?? "";
  const isDirty = agent !== "" && agent !== current;
  markDirty("agent", isDirty);
}

function onConfirmationModeChange({
  isToggled,
  settings,
  selectedSecurityAnalyzer,
  setConfirmationModeEnabled,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  isToggled: boolean;
  settings?: Settings;
  selectedSecurityAnalyzer: string;
  setConfirmationModeEnabled: (value: boolean) => void;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setConfirmationModeEnabled(isToggled);
  markDirty("confirmationMode", isToggled !== (settings?.CONFIRMATION_MODE ?? false));

  if (isToggled && !selectedSecurityAnalyzer) {
    setSelectedSecurityAnalyzer(DEFAULT_SETTINGS.SECURITY_ANALYZER ?? "llm");
    markDirty("securityAnalyzer", true);
  }
}

function onCondenserMaxSizeChange({
  value,
  settings,
  setCondenserMaxSize,
  markDirty,
}: {
  value: string;
  settings?: Settings;
  setCondenserMaxSize: (value: number | null) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  const parsed = value ? Number.parseInt(value, 10) : null;
  const bounded = parsed !== null && Number.isFinite(parsed) ? Math.max(20, parsed) : null;
  setCondenserMaxSize(bounded);
  const previous = settings?.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE;
  const next = bounded ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE;
  markDirty("condenserMaxSize", next !== previous);
}

function onSecurityAnalyzerChange({
  value,
  settings,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  value: string;
  settings?: Settings;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setSelectedSecurityAnalyzer(value);
  markDirty(
    "securityAnalyzer",
    value !== normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER),
  );
}

function onSecurityAnalyzerClear({
  settings,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  settings?: Settings;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setSelectedSecurityAnalyzer("");
  markDirty(
    "securityAnalyzer",
    "" !== normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER),
  );
}

function buildPayloadForView(view: "basic" | "advanced", formData: FormData) {
  if (view === "basic") {
    return buildBasicPayload({ formData });
  }
  return buildAdvancedPayload({ formData });
}
