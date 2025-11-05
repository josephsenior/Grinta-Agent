import {
  ReadObservation,
  CommandObservation,
  IPythonObservation,
  EditObservation,
  BrowseObservation,
  OpenHandsObservation,
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
  let content = "";

  const extras = (event.extras as Record<string, unknown>) ?? {};
  if (extras.recall_type === "workspace_context") {
    if (typeof extras.repo_name === "string") {
      content += `\n\n**Repository:** ${extras.repo_name}`;
    }
    if (typeof extras.repo_directory === "string") {
      content += `\n\n**Directory:** ${extras.repo_directory}`;
    }
    if (typeof extras.date === "string") {
      content += `\n\n**Date:** ${extras.date}`;
    }
    if (extras.runtime_hosts && Object.keys(extras.runtime_hosts as Record<string, unknown>).length > 0) {
      content += `\n\n**Available Hosts**`;
      for (const [host, port] of Object.entries(extras.runtime_hosts as Record<string, unknown>)) {
        content += `\n\n- ${host} (port ${port})`;
      }
    }
    if (typeof extras.repo_instructions === "string") {
      content += `\n\n**Repository Instructions:**\n\n${extras.repo_instructions}`;
    }
    if (typeof extras.conversation_instructions === "string") {
      content += `\n\n**Conversation Instructions:**\n\n${extras.conversation_instructions}`;
    }
    if (typeof extras.additional_agent_instructions === "string") {
      content += `\n\n**Additional Instructions:**\n\n${extras.additional_agent_instructions}`;
    }
  }

  // Handle microagent knowledge
  if (Array.isArray(extras.microagent_knowledge) && (extras.microagent_knowledge as unknown[]).length > 0) {
    content += `\n\n**Triggered Microagent Knowledge:**`;
    for (const knowledge of extras.microagent_knowledge as unknown[]) {
      const k = knowledge as Record<string, unknown>;
      content += `\n\n- **${String(k.name)}** (triggered by keyword: ${String(k.trigger)})\n\n${String(k.content)}`;
    }
  }

  if (extras.custom_secrets_descriptions && Object.keys(extras.custom_secrets_descriptions as Record<string, unknown>).length > 0) {
    content += `\n\n**Custom Secrets**`;
    for (const [name, description] of Object.entries(extras.custom_secrets_descriptions as Record<string, unknown>)) {
      content += `\n\n- $${name}: ${String(description)}`;
    }
  }

  return content;
};

const getTaskTrackingObservationContent = (
  event: TaskTrackingObservation,
): string => {
  const { command, task_list: taskList } = event.extras;
  let content = `**Command:** \`${command}\``;

  if (command === "plan" && taskList.length > 0) {
    content += `\n\n**Task List (${taskList.length} ${taskList.length === 1 ? "item" : "items"}):**\n`;

    taskList.forEach((task, index) => {
      const statusIcon =
        {
          todo: "⏳",
          in_progress: "🔄",
          done: "✅",
        }[task.status] || "❓";

      content += `\n${index + 1}. ${statusIcon} **[${task.status.toUpperCase().replace("_", " ")}]** ${task.title}`;
      content += `\n   *ID: ${task.id}*`;
      if (task.notes) {
        content += `\n   *Notes: ${task.notes}*`;
      }
    });
  } else if (command === "plan") {
    content += "\n\n**Task List:** Empty";
  }

  if (event.content && event.content.trim()) {
    content += `\n\n**Result:** ${event.content.trim()}`;
  }

  return content;
};

export const getObservationContent = (event: OpenHandsObservation): string => {
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
