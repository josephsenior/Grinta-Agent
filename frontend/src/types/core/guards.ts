import { OpenHandsParsedEvent, OpenHandsEvent } from ".";
import {
  UserMessageAction,
  AssistantMessageAction,
  OpenHandsAction,
  SystemMessageAction,
  CommandAction,
  FinishAction,
  TaskTrackingAction,
  FileWriteAction,
  FileEditAction,
  StreamingChunkAction,
} from "./actions";
import {
  AgentStateChangeObservation,
  CommandObservation,
  ErrorObservation,
  MCPObservation,
  OpenHandsObservation,
  TaskTrackingObservation,
} from "./observations";
import { StatusUpdate } from "./variances";

export const isOpenHandsEvent = (
  event: unknown,
): event is OpenHandsParsedEvent =>
  typeof event === "object" &&
  event !== null &&
  "id" in event &&
  "source" in event &&
  "message" in event &&
  "timestamp" in event;

export const isOpenHandsAction = (
  event: unknown,
): event is OpenHandsAction =>
  typeof event === "object" &&
  event !== null &&
  "action" in event &&
  typeof (event as any).action === "string";

export const isOpenHandsObservation = (
  event: unknown,
): event is OpenHandsObservation =>
  typeof event === "object" &&
  event !== null &&
  "observation" in event &&
  typeof (event as any).observation === "string";

export const isUserMessage = (
  event: unknown,
): event is UserMessageAction =>
  isOpenHandsAction(event) &&
  event.source === "user" &&
  event.action === "message";

export const isAssistantMessage = (
  event: unknown,
): event is AssistantMessageAction =>
  isOpenHandsAction(event) &&
  event.source === "agent" &&
  (event.action === "message" || event.action === "finish");

export const isErrorObservation = (
  event: unknown,
): event is ErrorObservation =>
  isOpenHandsObservation(event) && event.observation === "error";

export const isCommandAction = (
  event: unknown,
): event is CommandAction => isOpenHandsAction(event) && event.action === "run";

export const isAgentStateChangeObservation = (
  event: unknown,
): event is AgentStateChangeObservation =>
  isOpenHandsObservation(event) && event.observation === "agent_state_changed";

export const isCommandObservation = (
  event: unknown,
): event is CommandObservation =>
  isOpenHandsObservation(event) && event.observation === "run";

export const isFinishAction = (
  event: unknown,
): event is FinishAction =>
  isOpenHandsAction(event) && event.action === "finish";

export const isSystemMessage = (
  event: unknown,
): event is SystemMessageAction =>
  isOpenHandsAction(event) && event.action === "system";

export const isRejectObservation = (
  event: unknown,
): event is OpenHandsObservation =>
  isOpenHandsObservation(event) && event.observation === "user_rejected";

export const isMcpObservation = (
  event: unknown,
): event is MCPObservation =>
  isOpenHandsObservation(event) && event.observation === "mcp";

export const isTaskTrackingAction = (
  event: unknown,
): event is TaskTrackingAction =>
  isOpenHandsAction(event) && event.action === "task_tracking";

export const isTaskTrackingObservation = (
  event: unknown,
): event is TaskTrackingObservation =>
  isOpenHandsObservation(event) && event.observation === "task_tracking";

export const isFileWriteAction = (
  event: unknown,
): event is FileWriteAction =>
  isOpenHandsAction(event) && event.action === "write";

export const isFileEditAction = (
  event: unknown,
): event is FileEditAction =>
  isOpenHandsAction(event) && event.action === "edit";

export const isStreamingChunkAction = (
  event: unknown,
): event is StreamingChunkAction =>
  isOpenHandsAction(event) && event.action === "streaming_chunk";

export const isStatusUpdate = (event: unknown): event is StatusUpdate =>
  typeof event === "object" &&
  event !== null &&
  "status_update" in event &&
  "type" in event &&
  "id" in event;

// Helpers to check that action/observation containers include runtime payloads
export const hasArgs = (
  event: unknown,
): event is OpenHandsAction & { args: Record<string, unknown> } =>
  isOpenHandsAction(event) &&
  typeof (event as any).args === "object" &&
  (event as any).args !== null;

export const hasExtras = (
  event: unknown,
): event is OpenHandsObservation & { extras: Record<string, unknown> } =>
  isOpenHandsObservation(event) &&
  typeof (event as any).extras === "object" &&
  (event as any).extras !== null;

// Dynamic name checks (useful for safe runtime branching)
export const isActionNamed = (event: unknown, name: string): event is OpenHandsAction =>
  isOpenHandsAction(event) && (event as any).action === name;

export const isObservationNamed = (
  event: unknown,
  name: string,
): event is OpenHandsObservation =>
  isOpenHandsObservation(event) && (event as any).observation === name;
