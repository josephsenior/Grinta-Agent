import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { logger } from "../utils/logger";

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

// Set up the global interceptor
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
      import("#/state/agent-slice").then(({ setCurrentAgentState }) => {
        import("#/store").then(({ default: store }) => {
          import("#/types/agent-state").then(({ AgentState }) => {
            logger.error(
              "🔴 Runtime unavailable (503), setting agent to ERROR state",
            );
            store.dispatch(setCurrentAgentState(AgentState.ERROR));
          });
        });
      });
    }

    // Continue with the error for other error handlers
    return Promise.reject(error);
  },
);
