import { WebSocketStatus } from "#/context/ws-client-provider";
import { I18nKey } from "#/i18n/declaration";
import { AgentState } from "#/types/agent-state";
import { ConversationStatus } from "#/types/conversation-status";
import { StatusMessage } from "#/types/message";
import { RuntimeStatus } from "#/types/runtime-status";

export enum IndicatorColor {
  BLUE = "bg-blue-500",
  GREEN = "bg-green-500",
  ORANGE = "bg-amber-500",
  YELLOW = "bg-yellow-500",
  RED = "bg-red-500",
  DARK_ORANGE = "bg-orange-600",
}

export const AGENT_STATUS_MAP: {
  [k: string]: string;
} = {
  [AgentState.INIT]: I18nKey.CHAT_INTERFACE$AGENT_INIT_MESSAGE,
  [AgentState.RUNNING]: I18nKey.CHAT_INTERFACE$AGENT_RUNNING_MESSAGE,
  [AgentState.AWAITING_USER_INPUT]:
    I18nKey.CHAT_INTERFACE$AGENT_AWAITING_USER_INPUT_MESSAGE,
  [AgentState.PAUSED]: I18nKey.CHAT_INTERFACE$AGENT_PAUSED_MESSAGE,
  [AgentState.LOADING]:
    I18nKey.CHAT_INTERFACE$INITIALIZING_AGENT_LOADING_MESSAGE,
  [AgentState.STOPPED]: I18nKey.CHAT_INTERFACE$AGENT_STOPPED_MESSAGE,
  [AgentState.FINISHED]: I18nKey.CHAT_INTERFACE$AGENT_FINISHED_MESSAGE,
  [AgentState.REJECTED]: I18nKey.CHAT_INTERFACE$AGENT_REJECTED_MESSAGE,
  [AgentState.ERROR]: I18nKey.CHAT_INTERFACE$AGENT_ERROR_MESSAGE,
  [AgentState.AWAITING_USER_CONFIRMATION]:
    I18nKey.CHAT_INTERFACE$AGENT_AWAITING_USER_CONFIRMATION_MESSAGE,
  [AgentState.USER_CONFIRMED]:
    I18nKey.CHAT_INTERFACE$AGENT_ACTION_USER_CONFIRMED_MESSAGE,
  [AgentState.USER_REJECTED]:
    I18nKey.CHAT_INTERFACE$AGENT_ACTION_USER_REJECTED_MESSAGE,
  [AgentState.RATE_LIMITED]: I18nKey.CHAT_INTERFACE$AGENT_RATE_LIMITED_MESSAGE,
};

const TRANSITION_AGENT_STATES = new Set([
  AgentState.LOADING,
  AgentState.PAUSED,
  AgentState.REJECTED,
  AgentState.RATE_LIMITED,
]);

type IndicatorContext = {
  webSocketStatus: WebSocketStatus;
  conversationStatus: ConversationStatus | null;
  runtimeStatus: RuntimeStatus | null;
  agentState: AgentState | null;
};

function isStoppedIndicatorState({
  webSocketStatus,
  conversationStatus,
  runtimeStatus,
  agentState,
}: IndicatorContext) {
  return (
    webSocketStatus === "DISCONNECTED" ||
    conversationStatus === "STOPPED" ||
    runtimeStatus === "STATUS$STOPPED" ||
    agentState === AgentState.STOPPED ||
    agentState === AgentState.ERROR
  );
}

function isTransitionIndicatorState({
  conversationStatus,
  runtimeStatus,
  agentState,
}: IndicatorContext) {
  const runtimeIsBusy = Boolean(
    runtimeStatus && runtimeStatus !== "STATUS$READY",
  );
  const agentIsTransitioning = Boolean(
    agentState != null && TRANSITION_AGENT_STATES.has(agentState),
  );

  return conversationStatus === "STARTING" || runtimeIsBusy || agentIsTransitioning;
}

export function getIndicatorColor(
  webSocketStatus: WebSocketStatus,
  conversationStatus: ConversationStatus | null,
  runtimeStatus: RuntimeStatus | null,
  agentState: AgentState | null,
) {
  const context: IndicatorContext = {
    webSocketStatus,
    conversationStatus,
    runtimeStatus,
    agentState,
  };

  if (isStoppedIndicatorState(context)) {
    return IndicatorColor.RED;
  }
  // Display a yellow working icon while the runtime is starting
  if (isTransitionIndicatorState(context)) {
    return IndicatorColor.YELLOW;
  }

  if (agentState === AgentState.AWAITING_USER_CONFIRMATION) {
    return IndicatorColor.ORANGE;
  }

  if (agentState === AgentState.AWAITING_USER_INPUT) {
    return IndicatorColor.BLUE;
  }

  // All other agent states are green
  return IndicatorColor.GREEN;
}

export function getStatusCode(
  statusMessage: StatusMessage,
  webSocketStatus: WebSocketStatus,
  conversationStatus: ConversationStatus | null,
  runtimeStatus: RuntimeStatus | null,
  agentState: AgentState | null,
) {
  const context: StatusContext = {
    statusMessage,
    webSocketStatus,
    conversationStatus,
    runtimeStatus,
    agentState,
  };

  for (const resolver of STATUS_RESOLVERS) {
    const result = resolver(context);
    if (result) {
      return result;
    }
  }

  return I18nKey.CHAT_INTERFACE$AGENT_ERROR_MESSAGE;
}

type StatusContext = {
  statusMessage: StatusMessage;
  webSocketStatus: WebSocketStatus;
  conversationStatus: ConversationStatus | null;
  runtimeStatus: RuntimeStatus | null;
  agentState: AgentState | null;
};

type StatusResolver = (context: StatusContext) => string | null | undefined;

const STATUS_RESOLVERS: StatusResolver[] = [
  ({ conversationStatus, runtimeStatus }) =>
    conversationStatus === "STOPPED" || runtimeStatus === "STATUS$STOPPED"
      ? I18nKey.CHAT_INTERFACE$STOPPED
      : null,
  ({ runtimeStatus }) => resolveRuntimeStatus(runtimeStatus),
  ({ webSocketStatus }) =>
    webSocketStatus === "DISCONNECTED"
      ? I18nKey.CHAT_INTERFACE$DISCONNECTED
      : null,
  ({ webSocketStatus }) =>
    webSocketStatus === "CONNECTING"
      ? I18nKey.CHAT_INTERFACE$CONNECTING
      : null,
  ({ agentState, statusMessage }) =>
    agentState === AgentState.LOADING &&
    statusMessage?.id &&
    statusMessage.id !== "STATUS$READY"
      ? statusMessage.id
      : null,
  ({ agentState }) => (agentState ? AGENT_STATUS_MAP[agentState] : null),
  ({ runtimeStatus, agentState }) =>
    runtimeStatus && runtimeStatus !== "STATUS$READY" && !agentState
      ? runtimeStatus
      : null,
];

function resolveRuntimeStatus(runtimeStatus: RuntimeStatus | null) {
  if (!runtimeStatus) {
    return null;
  }
  if (["STATUS$READY", "STATUS$RUNTIME_STARTED"].includes(runtimeStatus)) {
    return null;
  }
  const mapped = (I18nKey as { [key: string]: string })[runtimeStatus];
  return mapped ?? runtimeStatus;
}
