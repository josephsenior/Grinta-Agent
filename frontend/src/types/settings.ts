export type Provider = "github" | "enterprise_sso" | "bitbucket" | "gitlab";

export type ProviderToken = {
  token: string | null;
  host?: string | null;
  user_id?: string | null;
  installation_id?: string | null;
};

export type MCPSSEServer = {
  url: string;
  api_key?: string;
};

export type MCPStdioServer = {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
};

export type MCPSHTTPServer = {
  url: string;
  api_key?: string;
};

export type MCPConfig = {
  sse_servers: MCPSSEServer[];
  stdio_servers: MCPStdioServer[];
  shttp_servers: MCPSHTTPServer[];
};

export type Settings = {
  LLM_MODEL: string;
  LLM_BASE_URL: string;
  AGENT: string;
  LANGUAGE: string;
  LLM_API_KEY_SET: boolean;
  CONFIRMATION_MODE: boolean;
  SECURITY_ANALYZER: string | null;
  ENABLE_DEFAULT_CONDENSER: boolean;
  // Maximum number of events before the condenser runs
  CONDENSER_MAX_SIZE: number | null;
  ENABLE_SOUND_NOTIFICATIONS: boolean;
  USER_CONSENTS_TO_ANALYTICS: boolean;
  ENABLE_PROACTIVE_CONVERSATION_STARTERS: boolean;
  ENABLE_SOLVABILITY_ANALYSIS: boolean;
  MAX_BUDGET_PER_TASK: number | null;
  IS_NEW_USER?: boolean;
  GIT_USER_NAME?: string;
  GIT_USER_EMAIL?: string;
  EMAIL?: string;
  PROVIDER_TOKENS_SET?: Record<string, string | null>;
  REMOTE_RUNTIME_RESOURCE_FACTOR?: number;
  // Advanced LLM Configuration
  LLM_TEMPERATURE?: number | null;
  LLM_TOP_P?: number | null;
  LLM_MAX_OUTPUT_TOKENS?: number | null;
  LLM_TIMEOUT?: number | null;
  LLM_NUM_RETRIES?: number | null;
  LLM_CUSTOM_LLM_PROVIDER?: string | null;
  LLM_CACHING_PROMPT?: boolean | null;
  LLM_DISABLE_VISION?: boolean | null;
  // Autonomy Configuration
  autonomy_level?: string;
  ENABLE_PERMISSIONS?: boolean;
  ENABLE_CHECKPOINTS?: boolean;
  MCP_CONFIG?: MCPConfig;
};

export type ApiSettings = {
  llm_model: string;
  llm_base_url: string;
  agent: string;
  language: string;
  llm_api_key: string | null;
  llm_api_key_set: boolean;
  confirmation_mode: boolean;
  security_analyzer: string | null;
  enable_default_condenser: boolean;
  // Max size for condenser in backend settings
  condenser_max_size: number | null;
  enable_sound_notifications: boolean;
  user_consents_to_analytics: boolean;
  enable_proactive_conversation_starters: boolean;
  enable_solvability_analysis: boolean;
  max_budget_per_task: number | null;
  git_user_name?: string;
  git_user_email?: string;
  email?: string;
  remote_runtime_resource_factor?: number;
  // Advanced LLM Configuration
  llm_temperature?: number | null;
  llm_top_p?: number | null;
  llm_max_output_tokens?: number | null;
  llm_timeout?: number | null;
  llm_num_retries?: number | null;
  llm_custom_llm_provider?: string | null;
  llm_caching_prompt?: boolean | null;
  llm_disable_vision?: boolean | null;
  // Autonomy Configuration
  autonomy_level?: string;
  enable_permissions?: boolean;
  enable_checkpoints?: boolean;
  provider_tokens_set?: Record<string, string | null>;
  mcp_config?: MCPConfig;
};

export type PostSettings = Settings & {
  llm_api_key?: string | null;
};

export type PostApiSettings = ApiSettings;
