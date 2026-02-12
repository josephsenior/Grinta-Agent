import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { logger } from "../utils/logger";
import { getCurrentConversation } from "#/api/forge-helpers";

// Resolve backend base URL robustly for dev/prod:
function resolveBackendBase(): string {
  const envBase = import.meta.env.VITE_BACKEND_BASE_URL as string | undefined;
  const envHost = import.meta.env.VITE_BACKEND_HOST as string | undefined;

  if (envBase && envBase.includes("://")) {
    return envBase;
  }
  if (envBase) {
    return `${window.location.protocol}//${envBase}`;
  }
  if (envHost && envHost.includes("://")) {
    return envHost;
  }
  if (envHost) {
    return `${window.location.protocol}//${envHost}`;
  }
  if (typeof window !== "undefined" && window.location) {
    return window.location.origin;
  }
  return "http://localhost:3000";
}

export const Forge = axios.create({
  baseURL: resolveBackendBase(),
});

// ---------------------------------------------------------------------------
// Request interceptor — auto-inject X-Session-API-Key on every request
// ---------------------------------------------------------------------------
Forge.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const conversation = getCurrentConversation();
    const sessionApiKey = conversation?.session_api_key;
    if (sessionApiKey && !config.headers.get("X-Session-API-Key")) {
      config.headers.set("X-Session-API-Key", sessionApiKey);
    }
    return config;
  },
);

// Set up the global response interceptor
Forge.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // If there's no response at all (network error / backend down), log a
    // concise message instead of spamming the console with full stack traces.
    if (!error.response) {
      logger.warn(
        "Forge API: no response from backend (is the server running?)",
        error.message,
      );
      return Promise.reject(error);
    }

    // Check if it's a 503 error (runtime unavailable)
    // Only mark as ERROR if it's NOT a RUNTIME_NOT_READY error (which is expected during startup)
    const errorData = error.response?.data as
      | { error_code?: string }
      | undefined;
    const errorCode = errorData?.error_code;

    if (error.response?.status === 503 && errorCode !== "RUNTIME_NOT_READY") {
      // Dynamically import to avoid circular dependencies
      import("#/state/agent-slice")
        .then(({ setCurrentAgentState }) => {
          return Promise.all([
            setCurrentAgentState,
            import("#/store"),
            import("#/types/agent-state"),
          ]);
        })
        .then(([setCurrentAgentState, storeModule, agentStateModule]) => {
          logger.error(
            "🔴 Runtime unavailable (503), setting agent to ERROR state",
          );
          storeModule.default.dispatch(
            setCurrentAgentState(agentStateModule.AgentState.ERROR),
          );
        })
        .catch((importError) => {
          logger.error("Failed to set agent ERROR state:", importError);
        });
    }

    // Continue with the error for other error handlers
    return Promise.reject(error);
  },
);
