import { Settings } from "#/types/settings";

export const LATEST_SETTINGS_VERSION = 5;

export const DEFAULT_SETTINGS: Settings = {
  LLM_MODEL: "Openhands/claude-sonnet-4-20250514",
  LLM_BASE_URL: "",
  AGENT: "CodeActAgent",
  LANGUAGE: "en",
  LLM_API_KEY_SET: false,
  SEARCH_API_KEY_SET: false,
  CONFIRMATION_MODE: false,
  SECURITY_ANALYZER: "llm",
  REMOTE_RUNTIME_RESOURCE_FACTOR: 1,
  PROVIDER_TOKENS_SET: {},
  ENABLE_DEFAULT_CONDENSER: true,
  CONDENSER_MAX_SIZE: 120,
  ENABLE_SOUND_NOTIFICATIONS: false,
  USER_CONSENTS_TO_ANALYTICS: false,
  ENABLE_PROACTIVE_CONVERSATION_STARTERS: false,
  ENABLE_SOLVABILITY_ANALYSIS: false,
  SEARCH_API_KEY: "",
  IS_NEW_USER: true,
  MAX_BUDGET_PER_TASK: null,
  EMAIL: "",
  EMAIL_VERIFIED: true, // Default to true to avoid restricting access unnecessarily
  MCP_CONFIG: {
    sse_servers: [],
    stdio_servers: [],
    shttp_servers: [],
  },
  GIT_USER_NAME: "josephsenior",
  GIT_USER_EMAIL: "yousef.yousefmejdi@esprit.tn",
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
