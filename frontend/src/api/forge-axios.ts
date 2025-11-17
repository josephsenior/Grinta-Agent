import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { tokenStorage } from "../utils/auth/token-storage";

export const Forge = axios.create({
  baseURL: `${window.location.protocol}//${import.meta.env.VITE_BACKEND_BASE_URL || window?.location.host}`,
});

// Request interceptor to add auth token
Forge.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Helper function to check if a response contains an email verification error
const checkForEmailVerificationError = (data: unknown): boolean => {
  const EMAIL_NOT_VERIFIED = "EmailNotVerifiedError";

  if (typeof data === "string") {
    return data.includes(EMAIL_NOT_VERIFIED);
  }

  if (typeof data === "object" && data !== null) {
    const obj = data as Record<string, unknown>;
    if (Object.hasOwn(obj, "message")) {
      const { message } = obj;
      if (typeof message === "string") {
        return message.includes(EMAIL_NOT_VERIFIED);
      }
      if (Array.isArray(message)) {
        return message.some(
          (msg) => typeof msg === "string" && msg.includes(EMAIL_NOT_VERIFIED),
        );
      }
    }

    // Search any values in object in case message key is different
    return Object.values(obj).some(
      (value) =>
        (typeof value === "string" && value.includes(EMAIL_NOT_VERIFIED)) ||
        (Array.isArray(value) &&
          value.some(
            (v) => typeof v === "string" && v.includes(EMAIL_NOT_VERIFIED),
          )),
    );
  }

  return false;
};

// Set up the global interceptor
Forge.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // If there's no response at all (network error / backend down), log a
    // concise message instead of spamming the console with full stack traces.
    if (!error.response) {
      // eslint-disable-next-line no-console
      console.warn(
        "Forge API: no response from backend (is the server running?)",
        error.message,
      );
      return Promise.reject(error);
    }

    // Check if it's a 403 error with the email verification message
    if (
      error.response?.status === 403 &&
      checkForEmailVerificationError(error.response?.data) &&
      window.location.pathname !== "/settings/user"
    ) {
      window.location.reload();
    }

    // Check if it's a 401 error (unauthorized - token expired or invalid)
    if (error.response?.status === 401) {
      // Don't redirect if already on auth pages
      const isAuthPage = window.location.pathname.startsWith("/auth/");
      if (!isAuthPage) {
        tokenStorage.clear();
        // Only redirect if not already on login page
        if (window.location.pathname !== "/auth/login") {
          window.location.href = "/auth/login";
        }
      }
    }

    // Check if it's a 503 error (runtime container crashed/unavailable)
    if (error.response?.status === 503) {
      // Dynamically import to avoid circular dependencies
      import("#/state/agent-slice").then(({ setCurrentAgentState }) => {
        import("#/store").then(({ default: store }) => {
          import("#/types/agent-state").then(({ AgentState }) => {
            console.error(
              "🔴 Runtime container permanently unavailable, setting agent to ERROR state",
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
