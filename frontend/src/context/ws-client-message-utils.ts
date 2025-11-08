import { Conversation } from "#/api/forge.types";
import { ForgeParsedEvent } from "#/types/core";
import {
  isAgentStateChangeObservation,
  isAssistantMessage,
  isCommandAction,
  isFileEditAction,
  isFileWriteAction,
  isForgeAction,
  isForgeObservation,
  isStatusUpdate,
  isUserMessage,
} from "#/types/core/guards";

export const getProp = (obj: unknown, key: string): unknown =>
  obj && typeof obj === "object"
    ? (obj as Record<string, unknown>)[key]
    : undefined;

export const getEventId = (
  event: Record<string, unknown>,
): string | undefined => {
  const value = getProp(event, "id");
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return undefined;
};

export const warnIfNullPayload = (event: Record<string, unknown>): void => {
  try {
    const message = getProp(event, "message");
    const args = getProp(event, "args");
    const candidates: unknown[] = [message];

    if (args && typeof args === "object") {
      const record = args as Record<string, unknown>;
      candidates.push(record.content, record.command, record.message);
    }

    for (const candidate of candidates) {
      if (typeof candidate === "string" && candidate.toUpperCase() === "NULL") {
        // eslint-disable-next-line no-console
        console.warn("Received event with literal 'NULL' in payload", {
          id: getEventId(event),
          field: candidate,
          event,
        });
        break;
      }
    }
  } catch (error) {
    // Ignore logging issues; this helper is best-effort only.
  }
};

export const isMessageAction = (event: ForgeParsedEvent): boolean =>
  isUserMessage(event) || isAssistantMessage(event);

export const shouldAppendParsedEvent = (event: ForgeParsedEvent): boolean =>
  isForgeAction(event) || isForgeObservation(event);

export const getStatusErrorMessage = (
  event: ForgeParsedEvent,
): string | undefined => {
  if (isStatusUpdate(event) && event.type === "error") {
    return typeof event.message === "string" ? event.message : "Unknown error";
  }

  if (
    isAgentStateChangeObservation(event) &&
    event.extras.agent_state === "error"
  ) {
    return event.extras.reason || "Unknown error";
  }

  return undefined;
};

export interface ServerReadyInfo {
  port: number;
  url: string;
  protocol: string;
  health_status: string;
}

const normalizeServerReadyPartial = (
  value?: Record<string, unknown>,
): ServerReadyInfo => ({
  port: typeof value?.port === "number" ? value.port : 0,
  url: typeof value?.url === "string" ? value.url : "",
  protocol: typeof value?.protocol === "string" ? value.protocol : "http",
  health_status:
    typeof value?.health_status === "string" ? value.health_status : "unknown",
});

export const extractServerReadyInfo = (
  event: ForgeParsedEvent,
): ServerReadyInfo | undefined => {
  if (!isForgeObservation(event)) {
    return undefined;
  }

  if (getProp(event, "observation") === "server_ready") {
    const extras = (getProp(event, "extras") as Record<string, unknown>) ?? {};
    return normalizeServerReadyPartial(extras as Record<string, unknown>);
  }

  const extras = getProp(event, "extras");
  if (extras && typeof extras === "object" && "server_ready" in extras) {
    const nested = (extras as Record<string, unknown>).server_ready;
    if (nested && typeof nested === "object") {
      return normalizeServerReadyPartial(nested as Record<string, unknown>);
    }
  }

  return undefined;
};

export const shouldInvalidateFileChanges = (event: ForgeParsedEvent): boolean =>
  isFileWriteAction(event) || isFileEditAction(event) || isCommandAction(event);

export const getDiffInvalidatePath = (
  event: ForgeParsedEvent,
  conversation?: Conversation | null,
): string | undefined => {
  if (!isFileWriteAction(event) && !isFileEditAction(event)) {
    return undefined;
  }

  const rawPath = getProp(event, "args");
  const pathValue =
    rawPath && typeof rawPath === "object"
      ? (rawPath as Record<string, unknown>).path
      : undefined;

  if (typeof pathValue !== "string") {
    return undefined;
  }

  let normalized = pathValue.replace("/workspace/", "");
  const repoDirectory = conversation?.selected_repository?.split("/").pop();

  if (repoDirectory) {
    normalized = normalized.replace(`${repoDirectory}/`, "");
  }

  return normalized;
};
