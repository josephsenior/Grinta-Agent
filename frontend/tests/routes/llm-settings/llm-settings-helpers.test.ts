import { describe, expect, it } from "vitest";
import { DEFAULT_SETTINGS } from "#/services/settings";
import {
  buildAdvancedPayload,
  buildBasicPayload,
  normalizeSecurityAnalyzerSelection,
} from "#/routes/llm-settings/llm-settings-helpers";

describe("llm-settings helpers", () => {
  it("buildBasicPayload composes provider/model and resets advanced defaults", () => {
    const formData = new FormData();
    formData.set("llm-provider-input", "openai");
    formData.set("llm-model-input", "gpt-4o");
    formData.set("llm-api-key-input", "secret");
    formData.set("search-api-key-input", "search-key");
    formData.set("enable-confirmation-mode-switch", "on");
    formData.set("security-analyzer-input", "llm");

    const payload = buildBasicPayload({ formData });

    expect(payload).toMatchObject({
      LLM_MODEL: "openai/gpt-4o",
      llm_api_key: "secret",
      CONFIRMATION_MODE: true,
      SECURITY_ANALYZER: "llm",
      LLM_BASE_URL: DEFAULT_SETTINGS.LLM_BASE_URL,
      AGENT: DEFAULT_SETTINGS.AGENT,
      ENABLE_DEFAULT_CONDENSER: DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
    });
  });

  it("buildAdvancedPayload parses numeric and boolean fields", () => {
    const formData = new FormData();
    formData.set("llm-custom-model-input", "openai/gpt-4o");
    formData.set("base-url-input", "https://api.openai.com");
    formData.set("llm-api-key-input", "secret");
    formData.set("search-api-key-input", "search");
    formData.set("agent-input", "CoActAgent");
    formData.set("enable-confirmation-mode-switch", "on");
    formData.set("enable-memory-condenser-switch", "on");
    formData.set("condenser-max-size-input", "42");
    formData.set("security-analyzer-input", "none");
    formData.set("LLM_TEMPERATURE", "0.5");
    formData.set("LLM_TOP_P", "0.9");
    formData.set("LLM_MAX_OUTPUT_TOKENS", "2048");
    formData.set("LLM_TIMEOUT", "60");
    formData.set("LLM_NUM_RETRIES", "3");
    formData.set("LLM_CACHING_PROMPT", "true");
    formData.set("LLM_DISABLE_VISION", "false");
    formData.set("LLM_CUSTOM_LLM_PROVIDER", "azure");

    const payload = buildAdvancedPayload({ formData });

    expect(payload).toMatchObject({
      LLM_MODEL: "openai/gpt-4o",
      LLM_BASE_URL: "https://api.openai.com",
      CONFIRMATION_MODE: true,
      ENABLE_DEFAULT_CONDENSER: true,
      CONDENSER_MAX_SIZE: 42,
      SECURITY_ANALYZER: null,
      LLM_TEMPERATURE: 0.5,
      LLM_TOP_P: 0.9,
      LLM_MAX_OUTPUT_TOKENS: 2048,
      LLM_TIMEOUT: 60,
      LLM_NUM_RETRIES: 3,
      LLM_CACHING_PROMPT: true,
      LLM_DISABLE_VISION: false,
      LLM_CUSTOM_LLM_PROVIDER: "azure",
    });
  });

  it("normalizeSecurityAnalyzerSelection defaults missing values to 'none'", () => {
    expect(normalizeSecurityAnalyzerSelection(undefined)).toBe("none");
    expect(normalizeSecurityAnalyzerSelection(null)).toBe("none");
    expect(normalizeSecurityAnalyzerSelection("llm")).toBe("llm");
  });
});
