/**
 * LLM Configuration Presets
 *
 * Predefined configurations for different use cases:
 * - Conservative: Focused, deterministic responses (low temperature)
 * - Balanced: Mix of creativity and consistency (default)
 * - Creative: More varied and exploratory responses (high temperature)
 * - Custom: User-defined configuration
 */

export type LLMPreset = "conservative" | "balanced" | "creative" | "custom";

export interface LLMPresetConfig {
  name: string;
  description: string;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  timeout: number;
  num_retries: number;
  caching_prompt: boolean;
  disable_vision: boolean;
}

export const LLM_PRESETS: Record<LLMPreset, LLMPresetConfig> = {
  conservative: {
    name: "Conservative",
    description:
      "Focused and deterministic. Best for precise code generation and refactoring.",
    temperature: 0.0,
    top_p: 0.9,
    max_output_tokens: 4096,
    timeout: 120,
    num_retries: 5,
    caching_prompt: true,
    disable_vision: false,
  },
  balanced: {
    name: "Balanced",
    description:
      "Default settings. Good balance between creativity and consistency.",
    temperature: 0.1,
    top_p: 1.0,
    max_output_tokens: 4096,
    timeout: 120,
    num_retries: 5,
    caching_prompt: true,
    disable_vision: false,
  },
  creative: {
    name: "Creative",
    description:
      "Explorative and varied. Better for brainstorming and novel solutions.",
    temperature: 0.7,
    top_p: 1.0,
    max_output_tokens: 8192,
    timeout: 180,
    num_retries: 3,
    caching_prompt: true,
    disable_vision: false,
  },
  custom: {
    name: "Custom",
    description: "Manually configure all parameters.",
    temperature: 0.1,
    top_p: 1.0,
    max_output_tokens: 4096,
    timeout: 120,
    num_retries: 5,
    caching_prompt: true,
    disable_vision: false,
  },
};

/**
 * Detect which preset matches the given configuration
 */
export function detectPreset(config: Partial<LLMPresetConfig>): LLMPreset {
  const presets: LLMPreset[] = ["conservative", "balanced", "creative"];

  for (const preset of presets) {
    const presetConfig = LLM_PRESETS[preset];
    if (
      config.temperature === presetConfig.temperature &&
      config.top_p === presetConfig.top_p &&
      config.max_output_tokens === presetConfig.max_output_tokens
    ) {
      return preset;
    }
  }

  return "custom";
}

/**
 * Get configuration for a preset
 */
export function getPresetConfig(preset: LLMPreset): LLMPresetConfig {
  return LLM_PRESETS[preset];
}
