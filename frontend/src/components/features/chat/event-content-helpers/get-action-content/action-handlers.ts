import {
  FileWriteAction,
  CommandAction,
  BrowseAction,
  BrowseInteractiveAction,
  MCPAction,
  ThinkAction,
  FinishAction,
} from "#/types/core/actions";
import { ActionSecurityRisk } from "#/state/security-analyzer-slice";
import { MAX_CONTENT_LENGTH } from "../shared";
import i18n from "#/i18n";

export function getRiskText(risk: ActionSecurityRisk): string {
  switch (risk) {
    case ActionSecurityRisk.LOW:
      return i18n.t("SECURITY$LOW_RISK");
    case ActionSecurityRisk.MEDIUM:
      return i18n.t("SECURITY$MEDIUM_RISK");
    case ActionSecurityRisk.HIGH:
      return i18n.t("SECURITY$HIGH_RISK");
    case ActionSecurityRisk.UNKNOWN:
    default:
      return i18n.t("SECURITY$UNKNOWN_RISK");
  }
}

export function getWriteActionContent(event: FileWriteAction): string {
  let { content } = event.args;
  if (content.length > MAX_CONTENT_LENGTH) {
    content = `${event.args.content.slice(0, MAX_CONTENT_LENGTH)}...`;
  }
  return `${event.args.path}\n${content}`;
}

export function getRunActionContent(event: CommandAction): string {
  return `Running command: \`${event.args.command}\``;
}

export function getBrowseActionContent(event: BrowseAction): string {
  return `Browsing ${event.args.url}`;
}

export function getBrowseInteractiveActionContent(
  event: BrowseInteractiveAction,
): string {
  return `**Action:**\n\n\`\`\`python\n${event.args.browser_actions}\n\`\`\``;
}

export function getMcpActionContent(event: MCPAction): string {
  const name = event.args.name || "";
  const args = event.args.arguments || {};
  let details = `**MCP Tool Call:** ${name}\n\n`;
  if (event.args.thought) {
    details += `\n\n**Thought:**\n${event.args.thought}`;
  }
  details += `\n\n**Arguments:**\n\`\`\`json\n${JSON.stringify(args, null, 2)}\n\`\`\``;
  return details;
}

export function getThinkActionContent(event: ThinkAction): string {
  return event.args.thought;
}

export function getFinishActionContent(event: FinishAction): string {
  return event.args.final_thought.trim();
}

export function getNoContentActionContent(): string {
  return "";
}
