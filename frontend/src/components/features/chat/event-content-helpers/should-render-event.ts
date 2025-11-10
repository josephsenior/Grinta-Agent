import { ForgeAction } from "#/types/core/actions";
import { ForgeEventType } from "#/types/core/base";
import {
  isCommandAction,
  isCommandObservation,
  isForgeAction,
  isForgeObservation,
} from "#/types/core/guards";
import { ForgeObservation } from "#/types/core/observations";

const COMMON_NO_RENDER_LIST: ForgeEventType[] = [
  "system",
  "agent_state_changed",
  "change_agent_state",
];

const ACTION_NO_RENDER_LIST: ForgeEventType[] = ["recall"];

const OBSERVATION_NO_RENDER_LIST: ForgeEventType[] = ["think"];

// Streaming chunks should always be rendered for real-time display
const ALWAYS_RENDER_ACTIONS: ForgeEventType[] = ["streaming_chunk"];

export const shouldRenderEvent = (event: ForgeAction | ForgeObservation) => {
  if (isForgeAction(event)) {
    // Always render streaming chunks
    if (ALWAYS_RENDER_ACTIONS.includes(event.action)) {
      return true;
    }

    if (isCommandAction(event) && event.source === "user") {
      // For user commands, we always hide them from the chat interface
      return false;
    }

    const noRenderList = COMMON_NO_RENDER_LIST.concat(ACTION_NO_RENDER_LIST);
    return !noRenderList.includes(event.action);
  }

  if (isForgeObservation(event)) {
    if (isCommandObservation(event) && event.source === "user") {
      // For user commands, we always hide them from the chat interface
      return false;
    }

    const noRenderList = COMMON_NO_RENDER_LIST.concat(
      OBSERVATION_NO_RENDER_LIST,
    );
    return !noRenderList.includes(event.observation);
  }

  return true;
};
