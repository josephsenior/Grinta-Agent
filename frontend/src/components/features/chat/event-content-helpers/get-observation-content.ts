import {
  ReadObservation,
  CommandObservation,
  EditObservation,
  ForgeObservation,
  RecallObservation,
  BrowseObservation,
} from "#/types/core/observations";
import { getObservationResult } from "./get-observation-result";
import { getDefaultEventContent, MAX_CONTENT_LENGTH } from "./shared";
import i18n from "#/i18n";

const getReadObservationContent = (event: ReadObservation): string =>
  `\`\`\`\n${event.content}\n\`\`\``;

const getCommandObservationContent = (event: CommandObservation): string => {
  let { content } = event;
  if (content.length > MAX_CONTENT_LENGTH) {
    content = `${content.slice(0, MAX_CONTENT_LENGTH)}...`;
  }
  return `Output:\n\`\`\`sh\n${content.trim() || i18n.t("OBSERVATION$COMMAND_NO_OUTPUT")}\n\`\`\``;
};

const getEditObservationContent = (
  event: EditObservation,
  successMessage: boolean,
): string => {
  const extras = (event.extras as Record<string, unknown>) ?? {};
  if (successMessage && typeof extras.diff !== "undefined") {
    return `\`\`\`diff\n${String(extras.diff)}\n\`\`\``; // Content is already truncated by the ACI
  }
  return event.content;
};

const getBrowseObservationContent = (event: BrowseObservation): string => {
  if (event.extras?.error) {
    return `Error browsing ${event.extras.url}: ${event.extras.last_browser_action_error}`;
  }
  return `Successfully browsed ${event.extras?.url}`;
};

function buildWorkspaceContextDetails(extras: Record<string, unknown>): string {
  const lines: string[] = [];

  const pushIfString = (label: string, key: string) => {
    if (typeof extras[key] === "string") {
      lines.push(`\n\n**${label}:** ${String(extras[key])}`);
    }
  };

  pushIfString("Repository", "repo_name");
  pushIfString("Directory", "repo_directory");
  pushIfString("Date", "date");

  pushIfString("Conversation Instructions", "conversation_instructions");
  pushIfString("Additional Instructions", "additional_agent_instructions");

  return lines.join("");
}

function buildCustomSecretsDetails(
  extras: Record<string, unknown>,
): string | null {
  const secrets = extras.custom_secrets_descriptions as
    | Record<string, unknown>
    | undefined;
  if (!secrets || Object.keys(secrets).length === 0) {
    return null;
  }

  const entries = Object.entries(secrets)
    .map(([name, description]) => `\n\n- $${name}: ${String(description)}`)
    .join("");

  return `\n\n**Custom Secrets**${entries}`;
}

const getRecallObservationContent = (event: RecallObservation): string => {
  const extras = (event.extras as Record<string, unknown>) ?? {};
  const sections: string[] = [];

  if (extras.recall_type === "workspace_context") {
    sections.push(buildWorkspaceContextDetails(extras));
  }

  const customSecrets = buildCustomSecretsDetails(extras);
  if (customSecrets) {
    sections.push(customSecrets);
  }

  return sections.filter(Boolean).join("");
};

export const getObservationContent = (event: ForgeObservation): string => {
  switch (event.observation) {
    case "read":
      return getReadObservationContent(event);
    case "edit":
      return getEditObservationContent(
        event,
        getObservationResult(event) === "success",
      );
    case "run":
      return getCommandObservationContent(event);
    case "browse":
      return getBrowseObservationContent(event as BrowseObservation);
    case "recall":
      return getRecallObservationContent(event);
    default:
      return getDefaultEventContent(event);
  }
};
