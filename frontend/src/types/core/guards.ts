import { ForgeParsedEvent } from ".";
import {
  UserMessageAction,
  AssistantMessageAction,
  ForgeAction,
  SystemMessageAction,
  CommandAction,
  FinishAction,
  FileWriteAction,
  FileEditAction,
  StreamingChunkAction,
} from "./actions";
import {
  AgentStateChangeObservation,
  CommandObservation,
  ErrorObservation,
  MCPObservation,
  ForgeObservation,
} from "./observations";
import { StatusUpdate } from "./variances";

export const isForgeEvent = (event: unknown): event is ForgeParsedEvent =>
  typeof event === "object" &&
  event !== null &&
  "id" in event &&
  "source" in event &&
  "message" in event &&
  "timestamp" in event;

export const isForgeAction = (event: unknown): event is ForgeAction =>
  typeof event === "object" &&
  event !== null &&
  "action" in event &&
  typeof (event as { action?: unknown }).action === "string";

export const isForgeObservation = (event: unknown): event is ForgeObservation =>
  typeof event === "object" &&
  event !== null &&
  "observation" in event &&
  typeof (event as { observation?: unknown }).observation === "string";

export const isUserMessage = (event: unknown): event is UserMessageAction =>
  isForgeAction(event) && event.source === "user" && event.action === "message";

export const isAssistantMessage = (
  event: unknown,
): event is AssistantMessageAction =>
  isForgeAction(event) &&
  event.source === "agent" &&
  (event.action === "message" || event.action === "finish");

export const isErrorObservation = (event: unknown): event is ErrorObservation =>
  isForgeObservation(event) && event.observation === "error";

export const isCommandAction = (event: unknown): event is CommandAction =>
  isForgeAction(event) && event.action === "run";

export const isAgentStateChangeObservation = (
  event: unknown,
): event is AgentStateChangeObservation =>
  isForgeObservation(event) && event.observation === "agent_state_changed";

export const isCommandObservation = (
  event: unknown,
): event is CommandObservation =>
  isForgeObservation(event) && event.observation === "run";

export const isFinishAction = (event: unknown): event is FinishAction =>
  isForgeAction(event) && event.action === "finish";

export const isSystemMessage = (event: unknown): event is SystemMessageAction =>
  isForgeAction(event) && event.action === "system";

export const isRejectObservation = (
  event: unknown,
): event is ForgeObservation =>
  isForgeObservation(event) && event.observation === "user_rejected";

export const isMcpObservation = (event: unknown): event is MCPObservation =>
  isForgeObservation(event) && event.observation === "mcp";

export const isFileWriteAction = (event: unknown): event is FileWriteAction =>
  isForgeAction(event) && event.action === "write";

export const isFileEditAction = (event: unknown): event is FileEditAction =>
  isForgeAction(event) && event.action === "edit";

export const isStreamingChunkAction = (
  event: unknown,
): event is StreamingChunkAction =>
  isForgeAction(event) && event.action === "streaming_chunk";

export const isStatusUpdate = (event: unknown): event is StatusUpdate =>
  typeof event === "object" &&
  event !== null &&
  "status_update" in event &&
  "type" in event &&
  "id" in event;

// Helpers to check that action/observation containers include runtime payloads
export const hasArgs = (
  event: unknown,
): event is ForgeAction & { args: Record<string, unknown> } =>
  isForgeAction(event) &&
  typeof (event as { args?: unknown }).args === "object" &&
  (event as { args?: unknown }).args !== null;

export const hasExtras = (
  event: unknown,
): event is ForgeObservation & { extras: Record<string, unknown> } =>
  isForgeObservation(event) &&
  typeof (event as { extras?: unknown }).extras === "object" &&
  (event as { extras?: unknown }).extras !== null;

export const hasThoughtProperty = (
  args: Record<string, unknown>,
): args is Record<string, unknown> & { thought: string } =>
  "thought" in args && typeof args.thought === "string";

// Dynamic name checks (useful for safe runtime branching)
export const isActionNamed = (
  event: unknown,
  name: string,
): event is ForgeAction =>
  isForgeAction(event) && (event as { action?: unknown }).action === name;

export const isObservationNamed = (
  event: unknown,
  name: string,
): event is ForgeObservation =>
  isForgeObservation(event) &&
  (event as { observation?: unknown }).observation === name;
