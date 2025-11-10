import { DEFAULT_SETTINGS } from "#/services/settings";
import { getProviderId } from "#/utils/map-provider";
import type { PostSettings } from "#/types/settings";

export type LlmSettingsView = "basic" | "advanced";

export type DirtyInputs = {
  model: boolean;
  apiKey: boolean;
  searchApiKey: boolean;
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
  searchApiKey: false,
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
  const searchApiKey = formData.get("search-api-key-input")?.toString();
  const confirmationMode =
    formData.get("enable-confirmation-mode-switch")?.toString() === "on";
  const securityAnalyzer = formData.get("security-analyzer-input")?.toString();

  const fullLlmModel = provider && model ? `${provider}/${model}` : model;

  return {
    LLM_MODEL: fullLlmModel,
    llm_api_key: apiKey || null,
    SEARCH_API_KEY: searchApiKey || "",
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
  const searchApiKey = formData.get("search-api-key-input")?.toString();
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
    SEARCH_API_KEY: searchApiKey || "",
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
