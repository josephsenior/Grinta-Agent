import { OpenHandsObservation } from "#/types/core/observations";

export type ObservationResultStatus = "success" | "error" | "timeout";

export const getObservationResult = (event: OpenHandsObservation) => {
  const hasContent = typeof event.content === "string" && event.content.length > 0;
  const contentIncludesError =
    typeof event.content === "string" && event.content.toLowerCase().includes("error:");

  switch (event.observation) {
    case "run": {
      const exitCode = ((): number | undefined => {
        try {
          const extras = event.extras as Record<string, unknown> | undefined;
          const meta = extras?.metadata as Record<string, unknown> | undefined;
          return typeof meta?.exit_code === "number" ? (meta.exit_code as number) : undefined;
        } catch {
          return undefined;
        }
      })();

      if (exitCode === -1) {
        return "timeout";
      } // Command timed out
      if (exitCode === 0) {
        return "success";
      } // Command executed successfully
      // If we couldn't determine an exit code, treat as success when there
      // is content; otherwise mark as error.
      return typeof exitCode === "number" ? "error" : hasContent ? "success" : "error";
    }
    case "run_ipython":
    case "read":
    case "edit":
    case "mcp":
      if (!hasContent || contentIncludesError) {
        return "error";
      }
      return "success"; // Content is valid
    default:
      return "success";
  }
};
