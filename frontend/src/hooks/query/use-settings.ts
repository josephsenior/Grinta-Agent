import { useQuery, UseQueryResult } from "@tanstack/react-query";
import React from "react";
import posthog from "posthog-js";
import Forge from "#/api/forge";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { useIsOnTosPage } from "#/hooks/use-is-on-tos-page";
import { Settings } from "#/types/settings";
import { useIsAuthed } from "./use-is-authed";

const getSettingsQueryFn = async (): Promise<Settings> => {
  const apiSettings = await Forge.getSettings();

  return mapApiSettingsToClient(apiSettings);
};

export const useSettings = () => {
  const isOnTosPage = useIsOnTosPage();
  const { data: userIsAuthenticated } = useIsAuthed();

  const query = useQuery({
    queryKey: ["settings"],
    queryFn: getSettingsQueryFn,
    retry: shouldRetrySettings,
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
    enabled: !isOnTosPage && !!userIsAuthenticated,
    meta: {
      disableToast: true,
    },
  });

  React.useEffect(() => {
    trackUserActivation(query);
  }, [query.data?.LLM_API_KEY_SET, query.isFetched]);

  // We want to return the defaults if the settings aren't found so the user can still see the
  // options to make their initial save. We don't set the defaults in `initialData` above because
  // that would prepopulate the data to the cache and mess with expectations. Read more:
  // https://tanstack.com/query/latest/docs/framework/react/guides/initial-query-data#using-initialdata-to-prepopulate-a-query
  if (query.error?.status === 404) {
    // Create a new object with only the properties we need, avoiding rest destructuring
    return {
      data: DEFAULT_SETTINGS,
      error: query.error,
      isError: query.isError,
      isLoading: query.isLoading,
      isFetching: query.isFetching,
      isFetched: query.isFetched,
      isSuccess: query.isSuccess,
      status: query.status,
      fetchStatus: query.fetchStatus,
      refetch: query.refetch,
    };
  }

  return query;
};

function mapApiSettingsToClient(
  apiSettings: Awaited<ReturnType<typeof Forge.getSettings>>,
): Settings {
  return {
    ...DEFAULT_SETTINGS,
    ...buildPrimarySettings(apiSettings),
    ...buildAutonomySettings(apiSettings),
    ...buildAdvancedLlmSettings(apiSettings),
    IS_NEW_USER: false,
  };
}

function buildPrimarySettings(
  apiSettings: Awaited<ReturnType<typeof Forge.getSettings>>,
) {
  return {
    LLM_MODEL: apiSettings.llm_model,
    LLM_BASE_URL: apiSettings.llm_base_url,
    AGENT: apiSettings.agent,
    LANGUAGE: apiSettings.language,
    CONFIRMATION_MODE: apiSettings.confirmation_mode,
    SECURITY_ANALYZER: apiSettings.security_analyzer,
    LLM_API_KEY_SET: apiSettings.llm_api_key_set,
    SEARCH_API_KEY_SET: apiSettings.search_api_key_set,
    REMOTE_RUNTIME_RESOURCE_FACTOR: apiSettings.remote_runtime_resource_factor,
    PROVIDER_TOKENS_SET: apiSettings.provider_tokens_set,
    ENABLE_DEFAULT_CONDENSER: apiSettings.enable_default_condenser,
    CONDENSER_MAX_SIZE:
      apiSettings.condenser_max_size ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
    ENABLE_SOUND_NOTIFICATIONS: apiSettings.enable_sound_notifications,
    ENABLE_PROACTIVE_CONVERSATION_STARTERS:
      apiSettings.enable_proactive_conversation_starters,
    ENABLE_SOLVABILITY_ANALYSIS: apiSettings.enable_solvability_analysis,
    USER_CONSENTS_TO_ANALYTICS: apiSettings.user_consents_to_analytics,
    SEARCH_API_KEY: apiSettings.search_api_key || "",
    MAX_BUDGET_PER_TASK: apiSettings.max_budget_per_task,
    EMAIL: apiSettings.email || "",
    EMAIL_VERIFIED: apiSettings.email_verified,
    MCP_CONFIG: apiSettings.mcp_config,
    GIT_USER_NAME: apiSettings.git_user_name || DEFAULT_SETTINGS.GIT_USER_NAME,
    GIT_USER_EMAIL:
      apiSettings.git_user_email || DEFAULT_SETTINGS.GIT_USER_EMAIL,
  } as Partial<Settings>;
}

function buildAutonomySettings(
  apiSettings: Awaited<ReturnType<typeof Forge.getSettings>>,
) {
  return {
    autonomy_level:
      apiSettings.autonomy_level || DEFAULT_SETTINGS.autonomy_level,
    ENABLE_PERMISSIONS:
      apiSettings.enable_permissions ?? DEFAULT_SETTINGS.ENABLE_PERMISSIONS,
    ENABLE_CHECKPOINTS:
      apiSettings.enable_checkpoints ?? DEFAULT_SETTINGS.ENABLE_CHECKPOINTS,
  } as Partial<Settings>;
}

function buildAdvancedLlmSettings(
  apiSettings: Awaited<ReturnType<typeof Forge.getSettings>>,
) {
  return {
    LLM_TEMPERATURE:
      apiSettings.llm_temperature ?? DEFAULT_SETTINGS.LLM_TEMPERATURE,
    LLM_TOP_P: apiSettings.llm_top_p ?? DEFAULT_SETTINGS.LLM_TOP_P,
    LLM_MAX_OUTPUT_TOKENS:
      apiSettings.llm_max_output_tokens ??
      DEFAULT_SETTINGS.LLM_MAX_OUTPUT_TOKENS,
    LLM_TIMEOUT: apiSettings.llm_timeout ?? DEFAULT_SETTINGS.LLM_TIMEOUT,
    LLM_NUM_RETRIES:
      apiSettings.llm_num_retries ?? DEFAULT_SETTINGS.LLM_NUM_RETRIES,
    LLM_CACHING_PROMPT:
      apiSettings.llm_caching_prompt ?? DEFAULT_SETTINGS.LLM_CACHING_PROMPT,
    LLM_DISABLE_VISION:
      apiSettings.llm_disable_vision ?? DEFAULT_SETTINGS.LLM_DISABLE_VISION,
    LLM_CUSTOM_LLM_PROVIDER:
      apiSettings.llm_custom_llm_provider ??
      DEFAULT_SETTINGS.LLM_CUSTOM_LLM_PROVIDER,
  } as Partial<Settings>;
}

function shouldRetrySettings(_: number, error: { status?: number }) {
  return error.status !== 404;
}

function trackUserActivation(query: UseQueryResult<Settings, unknown>) {
  if (query.isFetched && query.data?.LLM_API_KEY_SET) {
    posthog.capture("user_activated");
  }
}
