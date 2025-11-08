import { useMutation, useQueryClient } from "@tanstack/react-query";
import posthog from "posthog-js";
import { DEFAULT_SETTINGS } from "#/services/settings";
import Forge from "#/api/forge";
import { PostSettings, PostApiSettings } from "#/types/settings";
import { useSettings } from "../query/use-settings";

const saveSettingsMutationFn = async (settings: Partial<PostSettings>) => {
  const apiSettings: Partial<PostApiSettings> = {
    llm_model: settings.LLM_MODEL,
    llm_base_url: settings.LLM_BASE_URL,
    agent: settings.AGENT || DEFAULT_SETTINGS.AGENT,
    language: settings.LANGUAGE || DEFAULT_SETTINGS.LANGUAGE,
    confirmation_mode: settings.CONFIRMATION_MODE,
    security_analyzer: settings.SECURITY_ANALYZER,
    llm_api_key:
      settings.llm_api_key === ""
        ? ""
        : settings.llm_api_key?.trim() || undefined,
    remote_runtime_resource_factor: settings.REMOTE_RUNTIME_RESOURCE_FACTOR,
    enable_default_condenser: settings.ENABLE_DEFAULT_CONDENSER,
    condenser_max_size:
      settings.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
    enable_sound_notifications: settings.ENABLE_SOUND_NOTIFICATIONS,
    user_consents_to_analytics: settings.user_consents_to_analytics,
    provider_tokens_set: settings.PROVIDER_TOKENS_SET,
    mcp_config: settings.MCP_CONFIG,
    enable_proactive_conversation_starters:
      settings.ENABLE_PROACTIVE_CONVERSATION_STARTERS,
    enable_solvability_analysis: settings.ENABLE_SOLVABILITY_ANALYSIS,
    search_api_key: settings.SEARCH_API_KEY?.trim() || "",
    max_budget_per_task: settings.MAX_BUDGET_PER_TASK,
    git_user_name:
      settings.GIT_USER_NAME?.trim() || DEFAULT_SETTINGS.GIT_USER_NAME,
    git_user_email:
      settings.GIT_USER_EMAIL?.trim() || DEFAULT_SETTINGS.GIT_USER_EMAIL,
    // Advanced LLM Configuration
    llm_temperature: settings.LLM_TEMPERATURE,
    llm_top_p: settings.LLM_TOP_P,
    llm_max_output_tokens: settings.LLM_MAX_OUTPUT_TOKENS,
    llm_timeout: settings.LLM_TIMEOUT,
    llm_num_retries: settings.LLM_NUM_RETRIES,
    llm_caching_prompt: settings.LLM_CACHING_PROMPT,
    llm_disable_vision: settings.LLM_DISABLE_VISION,
    llm_custom_llm_provider: settings.LLM_CUSTOM_LLM_PROVIDER,
    // Autonomy Configuration
    autonomy_level: settings.autonomy_level,
    enable_permissions: settings.ENABLE_PERMISSIONS,
    enable_checkpoints: settings.ENABLE_CHECKPOINTS,
  };

  console.log("[useSaveSettings] Sending to backend:", apiSettings);
  console.log("[useSaveSettings] autonomy_level specifically:", apiSettings.autonomy_level);
  await Forge.saveSettings(apiSettings);
};

export const useSaveSettings = () => {
  const queryClient = useQueryClient();
  const { data: currentSettings } = useSettings();

  return useMutation({
    mutationFn: async (settings: Partial<PostSettings>) => {
      const newSettings = { ...currentSettings, ...settings };

      // Track MCP configuration changes
      if (
        settings.MCP_CONFIG &&
        currentSettings?.MCP_CONFIG !== settings.MCP_CONFIG
      ) {
        const hasMcpConfig = !!settings.MCP_CONFIG;
        const sseServersCount = settings.MCP_CONFIG?.sse_servers?.length || 0;
        const stdioServersCount =
          settings.MCP_CONFIG?.stdio_servers?.length || 0;

        // Track MCP configuration usage
        posthog.capture("mcp_config_updated", {
          has_mcp_config: hasMcpConfig,
          sse_servers_count: sseServersCount,
          stdio_servers_count: stdioServersCount,
        });
      }

      await saveSettingsWithRetry(newSettings);
      return newSettings;
    },
    onMutate: async (settings: Partial<PostSettings>) => {
      // Cancel any outgoing refetches to avoid overwriting our optimistic update
      await queryClient.cancelQueries({ queryKey: ["settings"] });

      // Snapshot the previous value
      const previousSettings = queryClient.getQueryData(["settings"]);

      // Optimistically update to the new value
      queryClient.setQueryData(["settings"], (old: any) => {
        const updated = { ...old, ...settings };
        console.log("[useSaveSettings] Optimistic update:", settings);
        return updated;
      });

      // Return a context object with the snapshotted value
      return { previousSettings };
    },
    onSuccess: async () => {
      // Keep the optimistic update - no need to refetch since we know the save succeeded
      console.log("[useSaveSettings] Settings saved successfully, keeping optimistic update");
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousSettings) {
        queryClient.setQueryData(["settings"], context.previousSettings);
      }
      console.error("[useSaveSettings] Failed to save settings after all retries:", err);
    },
    meta: {
      disableToast: true,
    },
  });
};

async function saveSettingsWithRetry(settings: Partial<PostSettings>) {
  const maxRetries = process.env.NODE_ENV === "test" ? 0 : 3;
  const baseDelay = 1000;

  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    try {
      await saveSettingsMutationFn(settings);
      if (attempt > 0) {
        posthog.capture("settings_save_retry_success", { retries: attempt });
      }
      return;
    } catch (error) {
      if (attempt >= maxRetries) {
        posthog.capture("settings_save_failed", {
          retries: attempt,
          error: error instanceof Error ? error.message : "Unknown error",
        });
        throw error;
      }

      const delay = baseDelay * Math.pow(2, attempt);
      console.warn(
        `[useSaveSettings] Retry ${attempt + 1}/${maxRetries} after ${delay}ms...`,
      );
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}
