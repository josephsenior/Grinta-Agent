// Here are the list of verified models and providers that we know work well with Forge.
export const VERIFIED_PROVIDERS = [
  "openai",
  "anthropic",
  "gemini",
  "xai",
];
export const VERIFIED_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "claude-3-5-sonnet-20241022",
  "claude-3-7-sonnet-20250219",
  "gemini-1.5-pro",
  "gemini-1.5-flash",
  "grok-beta",
];

// Some SDKs do not return OpenAI models with the provider prefix, so we list them here for consistency
// (e.g., they return `gpt-4o` instead of `openai/gpt-4o`)
export const VERIFIED_OPENAI_MODELS = [
  "gpt-5-2025-08-07",
  "gpt-5-mini-2025-08-07",
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4.1",
  "gpt-4.1-2025-04-14",
  "o3",
  "o3-2025-04-16",
  "o4-mini",
  "o4-mini-2025-04-16",
  "codex-mini-latest",
];

// Some SDKs do not return the compatible Anthropic models with the provider prefix, so we list them here
// (e.g., they return `claude-3-5-sonnet-20241022` instead of `anthropic/claude-3-5-sonnet-20241022`)
export const VERIFIED_ANTHROPIC_MODELS = [
  "claude-3-5-sonnet-20240620",
  "claude-3-5-sonnet-20241022",
  "claude-3-5-haiku-20241022",
  "claude-3-7-sonnet-20250219",
];

export const DEFAULT_Forge_MODEL = "claude-3-5-sonnet-20241022";
