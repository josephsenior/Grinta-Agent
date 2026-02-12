import type { ForgeEvent } from "#/types/core/base";
import type { ForgeParsedEvent } from "#/types/core/index";
import {
  isStatusUpdate,
  isAgentStateChangeObservation,
  isForgeEvent,
} from "#/types/core/guards";
import { AgentState } from "#/types/agent-state";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { shouldAddEvent } from "./event-deduplication";

const isErrorEvent = (
  event: unknown,
): event is { error: true; message: string } =>
  typeof event === "object" &&
  event !== null &&
  "error" in event &&
  event.error === true &&
  "message" in event &&
  typeof event.message === "string";

const isAgentStatusError = (event: unknown): event is ForgeParsedEvent =>
  isForgeEvent(event) &&
  isAgentStateChangeObservation(event) &&
  event.extras.agent_state === AgentState.ERROR;

export function handleForgeEvent(
  event: ForgeEvent,
  conversationId: string,
  currentEvents: ForgeEvent[],
): ForgeEvent[] {
  if (!shouldAddEvent(currentEvents, event)) {
    return currentEvents;
  }

  return [...currentEvents, event];
}

export function handleErrorEvents(
  event: unknown,
  conversationId: string,
): void {
  if (isErrorEvent(event) || isAgentStatusError(event)) {
    displayErrorToast(
      isErrorEvent(event) ? event.message : "PLAYBOOK$UNKNOWN_ERROR",
    );
  }
}

export function handleStatusEvents(
  event: unknown,
  conversationId: string,
): void {
  if (isStatusUpdate(event)) {
    if (event.type === "info" && event.id === "STATUS$STARTING_RUNTIME") {
      displaySuccessToast("PLAYBOOK$CREATED");
    }
  }
}

export function handleAgentStateEvents(
  event: unknown,
  conversationId: string,
  onUnsubscribe: (id: string) => void,
): void {
  if (
    isAgentStateChangeObservation(event) &&
    event.extras.agent_state === AgentState.FINISHED
  ) {
    displaySuccessToast("PLAYBOOK$FINISHED");
    onUnsubscribe(conversationId);
  }
}
