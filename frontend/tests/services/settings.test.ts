import { describe, expect, it } from "vitest";
import {
  DEFAULT_SETTINGS,
  getDefaultSettings,
  LATEST_SETTINGS_VERSION,
} from "#/services/settings";

describe("settings service", () => {
  it("exposes latest settings version", () => {
    expect(LATEST_SETTINGS_VERSION).toBe(5);
  });

  it("returns the default settings singleton", () => {
    const defaults = getDefaultSettings();

    expect(defaults).toBe(DEFAULT_SETTINGS);
    expect(defaults.LLM_MODEL).toBe("anthropic/claude-3-5-sonnet-20241022");
  });
});
