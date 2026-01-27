import { ForgeObservation } from "#/types/core/observations";

export type ObservationResultStatus = "success" | "error" | "timeout";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const getExitCodeFromExtras = (
  extras: ForgeObservation["extras"],
): number | undefined => {
  if (!isRecord(extras)) {
    return undefined;
  }

  const { metadata } = extras as Record<string, unknown>;

  if (!isRecord(metadata)) {
    return undefined;
  }

  const exitCode = (metadata as Record<string, unknown>).exit_code;

  return typeof exitCode === "number" ? exitCode : undefined;
};

const getRunObservationStatus = (
  event: ForgeObservation,
  hasContent: boolean,
) => {
  const exitCode = getExitCodeFromExtras(event.extras);

  if (exitCode === -1) {
    return "timeout";
  }

  if (exitCode === 0) {
    return "success";
  }

  if (typeof exitCode === "number") {
    return "error";
  }

  return hasContent ? "success" : "error";
};

const isContentError = (event: ForgeObservation, hasContent: boolean) => {
  if (!hasContent) {
    return true;
  }

  if (typeof event.content !== "string") {
    return false;
  }

  return event.content.toLowerCase().includes("error:");
};

export const getObservationResult = (event: ForgeObservation) => {
  const hasContent =
    typeof event.content === "string" && event.content.length > 0;

  switch (event.observation) {
    case "run":
      return getRunObservationStatus(event, hasContent);
    case "read":
    case "edit":
    case "mcp":
      return isContentError(event, hasContent) ? "error" : "success";
    default:
      return "success";
  }
};
