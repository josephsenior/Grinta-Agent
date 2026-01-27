import { Settings } from "#/types/settings";

interface SettingsStatusContext {
  settings?: Settings;
  isSaas: boolean;
  hasPro: boolean;
  gitConnected: boolean;
  mcpServerCount: number;
  userProfileStatus: string;
}

export type SettingsStatusMap = Record<string, string | undefined>;

export function buildSettingsStatusMap({
  settings,
  isSaas,
  hasPro,
  gitConnected,
  mcpServerCount,
  userProfileStatus,
}: SettingsStatusContext): SettingsStatusMap {
  const map: SettingsStatusMap = {};

  map.llm = settings?.LLM_MODEL || "Model not configured";
  map.mcp = mcpServerCount > 0 ? `${mcpServerCount} servers` : "Not configured";
  map.memory = settings?.ENABLE_DEFAULT_CONDENSER
    ? "Hybrid memory on"
    : "Disabled";
  map.user = userProfileStatus;
  map.billing = hasPro ? "Pro active" : "Free tier";
  map["api-keys"] = settings?.LLM_API_KEY_SET ? "Forge key stored" : "BYO keys";
  map.app = settings?.LANGUAGE?.toUpperCase() || "Not set";
  map.integrations = gitConnected ? "Connected" : "Connect repo";
  map.slack = isSaas ? "Workspace alerts" : "Optional";
  map.databases = isSaas ? "Managed" : "Self-hosted";
  map["knowledge-base"] = settings?.ENABLE_DEFAULT_CONDENSER
    ? "Synced nightly"
    : "Manual";
  map.backup = isSaas ? "Automated" : "CLI run";
  map.secrets = gitConnected ? "Runtime ready" : "Add secrets";
  map.analytics = hasPro ? "Full telemetry" : "Beta insights";

  return map;
}
