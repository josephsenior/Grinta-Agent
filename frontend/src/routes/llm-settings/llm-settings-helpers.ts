import React from "react";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { getProviderId } from "#/utils/map-provider";
import type { PostSettings, Settings } from "#/types/settings";
import { hasAdvancedSettingsSet } from "#/utils/has-advanced-settings-set";
import { isCustomModel } from "#/utils/is-custom-model";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";

export type LlmSettingsView = "basic" | "advanced";

export type DirtyInputs = {
  model: boolean;
  apiKey: boolean;
  baseUrl: boolean;
  agent: boolean;
  confirmationMode: boolean;
  enableDefaultCondenser: boolean;
  securityAnalyzer: boolean;
  condenserMaxSize: boolean;
};

export const createDefaultDirtyInputs = (): DirtyInputs => ({
  model: false,
  apiKey: false,
  baseUrl: false,
  agent: false,
  confirmationMode: false,
  enableDefaultCondenser: false,
  securityAnalyzer: false,
  condenserMaxSize: false,
});

export interface BasicPayloadParams {
  formData: FormData;
}

export interface AdvancedPayloadParams {
  formData: FormData;
}

export const buildBasicPayload = ({
  formData,
}: BasicPayloadParams): Partial<PostSettings> => {
  const providerDisplay = formData.get("llm-provider-input")?.toString();
  const provider = providerDisplay ? getProviderId(providerDisplay) : undefined;
  const model = formData.get("llm-model-input")?.toString();
  const apiKey = formData.get("llm-api-key-input")?.toString();
  const confirmationMode =
    formData.get("enable-confirmation-mode-switch")?.toString() === "on";
  const securityAnalyzer = formData.get("security-analyzer-input")?.toString();

  const fullLlmModel = provider && model ? `${provider}/${model}` : model;

  return {
    LLM_MODEL: fullLlmModel,
    llm_api_key: apiKey || null,
    CONFIRMATION_MODE: confirmationMode,
    SECURITY_ANALYZER:
      securityAnalyzer === "none"
        ? null
        : securityAnalyzer || DEFAULT_SETTINGS.SECURITY_ANALYZER,
    LLM_BASE_URL: DEFAULT_SETTINGS.LLM_BASE_URL,
    AGENT: DEFAULT_SETTINGS.AGENT,
    ENABLE_DEFAULT_CONDENSER: DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
    CONDENSER_MAX_SIZE: DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
  };
};

const parseNumber = (value: string | undefined | null): number | null => {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const parseBoolean = (value: string | undefined | null): boolean | null => {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  if (value === "true") {
    return true;
  }

  if (value === "false") {
    return false;
  }

  return null;
};

const deriveCondenserMaxSize = (value: string | undefined | null): number => {
  if (!value) {
    return DEFAULT_SETTINGS.CONDENSER_MAX_SIZE as number;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_SETTINGS.CONDENSER_MAX_SIZE as number;
  }

  return Math.max(20, parsed);
};

export const buildAdvancedPayload = ({
  formData,
}: AdvancedPayloadParams): Partial<PostSettings> => {
  const model = formData.get("llm-custom-model-input")?.toString();
  const baseUrl = formData.get("base-url-input")?.toString();
  const apiKey = formData.get("llm-api-key-input")?.toString();
  const agent = formData.get("agent-input")?.toString();
  const confirmationMode =
    formData.get("enable-confirmation-mode-switch")?.toString() === "on";
  const enableDefaultCondenser =
    formData.get("enable-memory-condenser-switch")?.toString() === "on";
  const condenserMaxSize = deriveCondenserMaxSize(
    formData.get("condenser-max-size-input")?.toString(),
  );
  const securityAnalyzer = formData.get("security-analyzer-input")?.toString();

  return {
    LLM_MODEL: model || DEFAULT_SETTINGS.LLM_MODEL,
    LLM_BASE_URL: baseUrl ?? DEFAULT_SETTINGS.LLM_BASE_URL,
    llm_api_key: apiKey || null,
    AGENT: agent || DEFAULT_SETTINGS.AGENT,
    CONFIRMATION_MODE: confirmationMode,
    ENABLE_DEFAULT_CONDENSER: enableDefaultCondenser,
    CONDENSER_MAX_SIZE: condenserMaxSize,
    SECURITY_ANALYZER:
      securityAnalyzer === "none"
        ? null
        : securityAnalyzer || DEFAULT_SETTINGS.SECURITY_ANALYZER,
    LLM_TEMPERATURE: parseNumber(formData.get("LLM_TEMPERATURE")?.toString()),
    LLM_TOP_P: parseNumber(formData.get("LLM_TOP_P")?.toString()),
    LLM_MAX_OUTPUT_TOKENS: parseNumber(
      formData.get("LLM_MAX_OUTPUT_TOKENS")?.toString(),
    ),
    LLM_TIMEOUT: parseNumber(formData.get("LLM_TIMEOUT")?.toString()),
    LLM_NUM_RETRIES: parseNumber(formData.get("LLM_NUM_RETRIES")?.toString()),
    LLM_CACHING_PROMPT: parseBoolean(
      formData.get("LLM_CACHING_PROMPT")?.toString(),
    ),
    LLM_DISABLE_VISION: parseBoolean(
      formData.get("LLM_DISABLE_VISION")?.toString(),
    ),
    LLM_CUSTOM_LLM_PROVIDER:
      formData.get("LLM_CUSTOM_LLM_PROVIDER")?.toString() || null,
  };
};

export const normalizeSecurityAnalyzerSelection = (
  analyzer: string | null | undefined,
): string => {
  if (!analyzer) {
    return "none";
  }

  return analyzer;
};

export const mergeAdvancedSettings = (
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
      securityAnalyzer === "none"
        ? null
        : securityAnalyzer || base.SECURITY_ANALYZER,
    AGENT: agentValue || DEFAULT_SETTINGS.AGENT,
  };
};

// ============================================================================
// Handler Functions
// ============================================================================

export function onModelDirtyChange({
  model,
  settings,
  markDirty,
  setCurrentSelectedModel,
}: {
  model: string | null;
  settings?: import("#/types/settings").Settings;
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

export function onCustomModelDirtyChange({
  model,
  settings,
  markDirty,
  setCurrentSelectedModel,
}: {
  model: string;
  settings?: import("#/types/settings").Settings;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
  setCurrentSelectedModel: (value: string | null) => void;
}) {
  const current = settings?.LLM_MODEL ?? "";
  const isDirty = model !== "" && model !== current;
  markDirty("model", isDirty);
  setCurrentSelectedModel(model);
}

export function onAgentChange({
  agent,
  settings,
  setAgentValue,
  markDirty,
}: {
  agent: string;
  settings?: import("#/types/settings").Settings;
  setAgentValue: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setAgentValue(agent);
  const current = settings?.AGENT ?? "";
  const isDirty = agent !== "" && agent !== current;
  markDirty("agent", isDirty);
}

export function onConfirmationModeChange({
  isToggled,
  settings,
  selectedSecurityAnalyzer,
  setConfirmationModeEnabled,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  isToggled: boolean;
  settings?: import("#/types/settings").Settings;
  selectedSecurityAnalyzer: string;
  setConfirmationModeEnabled: (value: boolean) => void;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setConfirmationModeEnabled(isToggled);
  markDirty(
    "confirmationMode",
    isToggled !== (settings?.CONFIRMATION_MODE ?? false),
  );

  if (isToggled && !selectedSecurityAnalyzer) {
    setSelectedSecurityAnalyzer(DEFAULT_SETTINGS.SECURITY_ANALYZER ?? "llm");
    markDirty("securityAnalyzer", true);
  }
}

export function onCondenserMaxSizeChange({
  value,
  settings,
  setCondenserMaxSize,
  markDirty,
}: {
  value: string;
  settings?: import("#/types/settings").Settings;
  setCondenserMaxSize: (value: number | null) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  const parsed = value ? Number.parseInt(value, 10) : null;
  const bounded =
    parsed !== null && Number.isFinite(parsed) ? Math.max(20, parsed) : null;
  setCondenserMaxSize(bounded);
  const previous =
    settings?.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE;
  const next = bounded ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE;
  markDirty("condenserMaxSize", next !== previous);
}

export function onSecurityAnalyzerChange({
  value,
  settings,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  value: string;
  settings?: import("#/types/settings").Settings;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setSelectedSecurityAnalyzer(value);
  markDirty(
    "securityAnalyzer",
    value !== normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER),
  );
}

export function onSecurityAnalyzerClear({
  settings,
  setSelectedSecurityAnalyzer,
  markDirty,
}: {
  settings?: import("#/types/settings").Settings;
  setSelectedSecurityAnalyzer: (value: string) => void;
  markDirty: (field: keyof DirtyInputs, isDirty: boolean) => void;
}) {
  setSelectedSecurityAnalyzer("");
  markDirty(
    "securityAnalyzer",
    normalizeSecurityAnalyzerSelection(settings?.SECURITY_ANALYZER) !== "",
  );
}

// ============================================================================
// State Initialization Functions
// ============================================================================

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
  setAgentValue(settings.AGENT ?? DEFAULT_SETTINGS.AGENT ?? "Orchestrator");
  setConfirmationModeEnabled(
    settings.CONFIRMATION_MODE ?? DEFAULT_SETTINGS.CONFIRMATION_MODE,
  );
  setSelectedSecurityAnalyzer(
    normalizeSecurityAnalyzerSelection(settings.SECURITY_ANALYZER),
  );
  setEnableDefaultCondenser(
    settings.ENABLE_DEFAULT_CONDENSER ??
      DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
  );
  setCondenserMaxSize(
    settings.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
  );
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

export function initializeStateFromSettings({
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

export function updateViewFromSettings({
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
