import {
  ReadObservation,
  CommandObservation,
  IPythonObservation,
  EditObservation,
  BrowseObservation,
  ForgeObservation,
  RecallObservation,
  TaskTrackingObservation,
} from "#/types/core/observations";
import { getObservationResult } from "./get-observation-result";
import { getDefaultEventContent, MAX_CONTENT_LENGTH } from "./shared";
import i18n from "#/i18n";

const getReadObservationContent = (event: ReadObservation): string =>
  `\`\`\`\n${event.content}\n\`\`\``;

const getCommandObservationContent = (
  event: CommandObservation | IPythonObservation,
): string => {
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

  const runtimeHosts = extras.runtime_hosts as
    | Record<string, unknown>
    | undefined;
  if (runtimeHosts && Object.keys(runtimeHosts).length > 0) {
    const hostLines = Object.entries(runtimeHosts)
      .map(([host, port]) => `\n\n- ${host} (port ${port})`)
      .join("");
    lines.push(`\n\n**Available Hosts**${hostLines}`);
  }

  pushIfString("Repository Instructions", "repo_instructions");
  pushIfString("Conversation Instructions", "conversation_instructions");
  pushIfString("Additional Instructions", "additional_agent_instructions");

  return lines.join("");
}

function buildMicroagentKnowledgeDetails(
  extras: Record<string, unknown>,
): string | null {
  const knowledge = extras.microagent_knowledge as unknown[] | undefined;
  if (!Array.isArray(knowledge) || knowledge.length === 0) {
    return null;
  }

  const entries = knowledge
    .map((item) => {
      const record = item as Record<string, unknown>;
      return `\n\n- **${String(record.name)}** (triggered by keyword: ${String(
        record.trigger,
      )})\n\n${String(record.content)}`;
    })
    .join("");

  return `\n\n**Triggered Microagent Knowledge:**${entries}`;
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

function formatTaskResult(content: string | undefined): string | null {
  if (!content || !content.trim()) {
    return null;
  }
  return `**Result:** ${content.trim()}`;
}

function formatTaskItem(
  task: TaskTrackingObservation["extras"]["task_list"][number],
  index: number,
): string {
  const statusIcons: Record<string, string> = {
    todo: "⏳",
    in_progress: "🔄",
    done: "✅",
  };
  const statusIcon = statusIcons[task.status] ?? "❓";
  const notesLine = task.notes ? `\n   *Notes: ${task.notes}*` : "";

  return `\n\n${index + 1}. ${statusIcon} **[${task.status.toUpperCase().replace("_", " ")}]** ${
    task.title
  }\n   *ID: ${task.id}*${notesLine}`;
}

function buildTaskListSection(
  taskList: TaskTrackingObservation["extras"]["task_list"],
): string {
  if (!Array.isArray(taskList) || taskList.length === 0) {
    return "**Task List:** Empty";
  }

  const header = `**Task List (${taskList.length} ${taskList.length === 1 ? "item" : "items"}):**`;
  const items = taskList
    .map((task, index) => formatTaskItem(task, index))
    .join("");
  return `${header}${items}`;
}

const getBrowseObservationContent = (event: BrowseObservation) => {
  const extras = (event.extras as Record<string, unknown>) ?? {};
  let contentDetails = `**URL:** ${String(extras.url ?? "")}\n`;
  if (typeof extras.error !== "undefined") {
    contentDetails += `\n\n**Error:**\n${String(extras.error)}\n`;
  }
  contentDetails += `\n\n**Output:**\n${event.content}`;
  if (contentDetails.length > MAX_CONTENT_LENGTH) {
    contentDetails = `${contentDetails.slice(0, MAX_CONTENT_LENGTH)}...(truncated)`;
  }
  return contentDetails;
};

const getRecallObservationContent = (event: RecallObservation): string => {
  const extras = (event.extras as Record<string, unknown>) ?? {};
  const sections: string[] = [];

  if (extras.recall_type === "workspace_context") {
    sections.push(buildWorkspaceContextDetails(extras));
  }

  const microagentKnowledge = buildMicroagentKnowledgeDetails(extras);
  if (microagentKnowledge) {
    sections.push(microagentKnowledge);
  }

  const customSecrets = buildCustomSecretsDetails(extras);
  if (customSecrets) {
    sections.push(customSecrets);
  }

  return sections.filter(Boolean).join("");
};

const getTaskTrackingObservationContent = (
  event: TaskTrackingObservation,
): string => {
  const { command, task_list: taskList } = event.extras;
  const sections: string[] = [`**Command:** \`${command}\``];

  if (command === "plan") {
    sections.push(buildTaskListSection(taskList));
  }

  const resultSection = formatTaskResult(event.content);
  if (resultSection) {
    sections.push(resultSection);
  }

  return sections.filter(Boolean).join("\n\n");
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
    case "run_ipython":
    case "run":
      return getCommandObservationContent(event);
    case "browse":
      return getBrowseObservationContent(event);
    case "recall":
      return getRecallObservationContent(event);
    case "task_tracking":
      return getTaskTrackingObservationContent(event);
    default:
      return getDefaultEventContent(event);
  }
};
