/**
 * File operations for the Forge workspace.
 *
 * Extracted from ForgeClient — handles getFiles, getFile, and uploadFiles
 * with transient-failure retry logic.
 */

import { AxiosError } from "axios";
import {
  GetFilesResponse,
  GetFileResponse,
  FileUploadSuccessResponse,
} from "#/api/forge.types";
import { Forge } from "./forge-axios";
import {
  getConversationUrl,
  safeErrorMessage,
} from "./forge-helpers";
import { logger } from "#/utils/logger";

/**
 * Retrieve the list of files available in the workspace.
 *
 * Includes retry logic for transient runtime unavailability (503 / 500).
 */
export async function getFiles(
  conversationId: string,
  path?: string,
): Promise<GetFilesResponse> {
  const url = `${getConversationUrl(conversationId)}/files/list-files`;
  const maxRetries = 3;
  const retryDelayMs = 1000;

  let attempt = 1;
  while (attempt <= maxRetries) {
    try {
      // eslint-disable-next-line no-await-in-loop
      const { data } = await Forge.get<GetFilesResponse>(url, {
        params: { path },
      });
      return data;
    } catch (err: unknown) {
      const errorMsg = safeErrorMessage(err);
      const axiosError = err as AxiosError;
      const errorData = axiosError?.response?.data as
        | { error_code?: string }
        | undefined;
      const errorCode = errorData?.error_code;

      // 503 with RUNTIME_NOT_READY = Runtime is still starting up - retry
      if (
        axiosError?.response?.status === 503 &&
        errorCode === "RUNTIME_NOT_READY"
      ) {
        if (attempt < maxRetries) {
          logger.debug(
            `Runtime not ready yet, retrying file list (${attempt}/${maxRetries})...`,
          );
          const currentAttempt = attempt;
          // eslint-disable-next-line no-await-in-loop
          await new Promise<void>((resolve) => {
            setTimeout(() => {
              resolve();
            }, retryDelayMs * currentAttempt);
          });
          attempt += 1;
        } else {
          // After all retries, return empty array instead of throwing
          logger.warn(
            "Runtime not ready after retries, returning empty file list",
          );
          return [];
        }
      } else if (axiosError?.response?.status === 503) {
        // 503 = Runtime is permanently unavailable (crashed, not starting)
        logger.error("❌ Runtime unavailable (503):", errorMsg);
        // Dynamically import to avoid circular dependencies - with error handling
        try {
          const [{ setCurrentAgentState }, { default: store }, { AgentState }] =
            await Promise.all([
              import("#/state/agent-slice"),
              import("#/store"),
              import("#/types/agent-state"),
            ]);
          store.dispatch(setCurrentAgentState(AgentState.ERROR));
        } catch (importError) {
          logger.error("Failed to set agent ERROR state:", importError);
        }
        throw new Error(
          "Runtime unavailable. The runtime may be starting up or has encountered an error. Please try again or start a new conversation.",
        );
      } else {
        const isRuntimeUnavailable =
          errorMsg.includes("Runtime unavailable") ||
          errorMsg.includes("Connection refused") ||
          axiosError?.response?.status === 500;

        if (isRuntimeUnavailable && attempt < maxRetries) {
          logger.warn(
            `Runtime temporarily unavailable, retrying file list (${attempt}/${maxRetries})...`,
          );
          const currentAttempt = attempt;
          // eslint-disable-next-line no-await-in-loop
          await new Promise<void>((resolve) => {
            setTimeout(() => {
              resolve();
            }, retryDelayMs * currentAttempt);
          });
          attempt += 1;
        } else {
          throw err;
        }
      }
    }
  }

  throw new Error("Failed to load files after retries");
}

/**
 * Retrieve the content of a single file.
 *
 * Includes retry logic and special handling for binary / directory errors.
 */
export async function getFile(
  conversationId: string,
  filePath: string,
): Promise<string> {
  const url = `${getConversationUrl(conversationId)}/files/select-file`;

  const nonRetryableError = (errorMsg: string, status?: number) => {
    if (errorMsg.includes("directory")) {
      throw new Error("Cannot read directory as file");
    }
    if (errorMsg.includes("binary")) {
      throw new Error("Cannot read binary file");
    }
    if (status === 415) {
      throw new Error("Unsupported file type");
    }
  };

  const handlePermanentFailure = async (errorMsg: string) => {
    logger.error("❌ Runtime container permanently unavailable:", errorMsg);
    const { setCurrentAgentState } = await import("#/state/agent-slice");
    const { default: store } = await import("#/store");
    const { AgentState } = await import("#/types/agent-state");
    store.dispatch(setCurrentAgentState(AgentState.ERROR));
    throw new Error(
      "Runtime container unavailable. Please start a new conversation.",
    );
  };

  const shouldRetry = (errorMsg: string, status?: number) =>
    errorMsg.includes("Runtime unavailable") ||
    errorMsg.includes("Connection refused") ||
    status === 500;

  const maxRetries = 3;
  const retryDelayMs = 1000;

  let attempt = 1;
  while (attempt <= maxRetries) {
    try {
      // eslint-disable-next-line no-await-in-loop
      const { data } = await Forge.get<GetFileResponse>(url, {
        params: { file: filePath },
      });
      return data.code;
    } catch (err: unknown) {
      const axiosError = err as AxiosError;
      const responseStatus = axiosError?.response?.status;
      const errorMsg = safeErrorMessage(err);

      nonRetryableError(errorMsg, responseStatus);

      if (responseStatus === 503) {
        // eslint-disable-next-line no-await-in-loop
        await handlePermanentFailure(errorMsg);
      }

      if (shouldRetry(errorMsg, responseStatus) && attempt < maxRetries) {
        logger.warn(
          `Runtime temporarily unavailable, retrying (${attempt}/${maxRetries})...`,
        );
        const currentAttempt = attempt;
        // eslint-disable-next-line no-await-in-loop
        await new Promise<void>((resolve) => {
          setTimeout(() => {
            resolve();
          }, retryDelayMs * currentAttempt);
        });
        attempt += 1;
      } else {
        throw err;
      }
    }
  }

  throw new Error("Failed to load file after retries");
}

/**
 * Upload multiple files to the workspace.
 */
export async function uploadFiles(
  conversationId: string,
  files: File[],
): Promise<FileUploadSuccessResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const url = `${getConversationUrl(conversationId)}/files/upload-files`;
  const response = await Forge.post<FileUploadSuccessResponse>(url, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}
