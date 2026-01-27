import { Settings } from "#/types/settings";

export const LATEST_SETTINGS_VERSION = 5;

export const DEFAULT_SETTINGS: Settings = {
  LLM_MODEL: "anthropic/claude-3-5-sonnet-20241022",
  LLM_BASE_URL: "",
  AGENT: "CodeActAgent",
  LANGUAGE: "en",
  LLM_API_KEY_SET: false,
  CONFIRMATION_MODE: false,
  SECURITY_ANALYZER: null,
  ENABLE_DEFAULT_CONDENSER: true,
  CONDENSER_MAX_SIZE: 120,
  ENABLE_SOUND_NOTIFICATIONS: false,
  USER_CONSENTS_TO_ANALYTICS: true,
  ENABLE_PROACTIVE_CONVERSATION_STARTERS: true,
  ENABLE_SOLVABILITY_ANALYSIS: true,
  MAX_BUDGET_PER_TASK: 10,
  IS_NEW_USER: true,
  GIT_USER_NAME: "forge",
  GIT_USER_EMAIL: "forge@forge.dev",
  EMAIL: "",
  PROVIDER_TOKENS_SET: {},
  REMOTE_RUNTIME_RESOURCE_FACTOR: 1,
  // Autonomy Configuration
  autonomy_level: "balanced",
  ENABLE_PERMISSIONS: true,
  ENABLE_CHECKPOINTS: true,
  // Advanced LLM Configuration
  LLM_TEMPERATURE: null,
  LLM_TOP_P: null,
  LLM_MAX_OUTPUT_TOKENS: null,
  LLM_TIMEOUT: null,
  LLM_NUM_RETRIES: null,
  LLM_CACHING_PROMPT: null,
  LLM_DISABLE_VISION: null,
  LLM_CUSTOM_LLM_PROVIDER: null,
};

/**
 * Get the default settings
 */
export const getDefaultSettings = (): Settings => DEFAULT_SETTINGS;
