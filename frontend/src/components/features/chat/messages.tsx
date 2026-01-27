import React from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { createPortal } from "react-dom";
import { ForgeAction } from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";
import {
  isForgeAction,
  isForgeObservation,
  isForgeEvent,
  isAgentStateChangeObservation,
  isFinishAction,
  isAssistantMessage,
  hasExtras,
  hasArgs,
} from "#/types/core/guards";
import { groupMessagesIntoTurns } from "#/utils/group-messages-into-turns";
import { getEventSpacing } from "#/utils/coalesce-messages";
import { shouldRenderEvent } from "#/utils/should-render-event";
import { EventMessage } from "./event-message";
import { ChatMessage } from "./chat-message";
import { ActionSummary } from "./action-summary";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useUserConversation } from "#/hooks/query/use-user-conversation";
import { useConversationId } from "#/hooks/use-conversation-id";
import { AgentState } from "#/types/agent-state";
import { cn } from "#/utils/utils";
import { logger } from "#/utils/logger";

// Small runtime helper to safely treat unknown values as records when appropriate
const asRecord = (v: unknown): Record<string, unknown> | undefined =>
  typeof v === "object" && v !== null
    ? (v as Record<string, unknown>)
    : undefined;

const isErrorEvent = (evt: unknown): evt is { error: true; message: string } =>
  typeof evt === "object" &&
  evt !== null &&
  "error" in evt &&
  evt.error === true;

const isAgentStatusError = (evt: unknown): boolean =>
  isForgeEvent(evt) &&
  isAgentStateChangeObservation(evt) &&
  hasExtras(evt) &&
  (() => {
    try {
      const r = asRecord(evt);
      const ex = asRecord(r?.extras);
      const agentState =
        typeof ex?.agent_state === "string"
          ? (ex!.agent_state as AgentState)
          : undefined;
      return typeof agentState === "string" && agentState === AgentState.ERROR;
    } catch {
      return false;
    }
  })();

const hasId = (value: unknown): value is { id: number | string } =>
  typeof value === "object" &&
  value !== null &&
  (typeof (value as Record<string, unknown>).id === "string" ||
    typeof (value as Record<string, unknown>).id === "number");

const shouldLogStreamingDebug = () =>
  typeof process !== "undefined" && process.env?.NODE_ENV !== "production";

const getSequenceNumber = (event: unknown): number => {
  try {
    const record = asRecord(event);
    if (typeof record?.sequence === "number") {
      return record.sequence as number;
    }
    if (typeof record?.id === "number") {
      return record.id as number;
    }
    if (typeof record?.id === "string") {
      return Number(record.id) || 0;
    }
  } catch {
    /* ignore */
  }

  return 0;
};

const logStreamingDebug = (
  messages: Array<ForgeAction | ForgeObservation>,
  turns: Array<{ type: string; events: Array<unknown> }>,
) => {
  if (!shouldLogStreamingDebug()) {
    return;
  }

  logger.debug("⚡ LIVE STREAMING (no coalescing):", {
    totalMessages: messages.length,
    totalTurns: turns.length,
    turnsBreakdown: turns.map((turnItem, index) => ({
      index,
      type: turnItem.type,
      eventCount: turnItem.events.length,
      eventIds: turnItem.events
        .map((event) =>
          hasId(event as unknown)
            ? (event as { id: number | string }).id
            : undefined,
        )
        .filter(Boolean)
        .join(","),
      sequences: turnItem.events
        .map((event) => asRecord(event)?.sequence)
        .filter(Boolean)
        .join(","),
    })),
  });
};

const buildTurns = (messages: Array<ForgeAction | ForgeObservation>) => {
  const sortedMessages = [...messages].sort(
    (a, b) => getSequenceNumber(a) - getSequenceNumber(b),
  );

  const grouped = groupMessagesIntoTurns(sortedMessages);
  logStreamingDebug(messages, grouped);
  return grouped;
};

interface MessagesProps {
  messages: (ForgeAction | ForgeObservation)[];
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails?: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
}

// Type definitions for helper functions
interface TurnRenderContext {
  turns: Array<{
    type: string;
    events: Array<ForgeAction | ForgeObservation>;
    startIndex: number;
  }>;
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  actionHasObservationPair: (event: unknown) => boolean;
  conversation: ReturnType<typeof useUserConversation>["data"];
  t: TFunction;
}

type EventGroup = {
  type: "message" | "other";
  events: Array<ForgeAction | ForgeObservation>;
};

// Helper functions - defined in dependency order
function extractMessageContent(event: ForgeAction | ForgeObservation): string {
  try {
    const args = hasArgs(event) ? (event as ForgeAction).args : undefined;
    if (args) {
      const record = args as Record<string, unknown>;
      if (typeof record.content === "string") return record.content;
      if (typeof record.message === "string") return record.message;
      if (typeof record.thought === "string") return record.thought;
    }

    const ev = asRecord(event);
    if (typeof ev?.message === "string") return ev.message;
    if (typeof ev?.content === "string") return ev.content;
  } catch {
    return "";
  }

  return "";
}

function groupEventsByType(
  events: Array<ForgeAction | ForgeObservation>,
): EventGroup[] {
  const groups: EventGroup[] = [];
  let currentGroup: EventGroup | null = null;

  events.forEach((event) => {
    const isMessage = isAssistantMessage(event);
    const groupType: EventGroup["type"] = isMessage ? "message" : "other";

    if (!currentGroup || currentGroup.type !== groupType) {
      currentGroup = { type: groupType, events: [event] };
      groups.push(currentGroup);
    } else {
      currentGroup.events.push(event);
    }
  });

  return groups;
}

function buildEventActions({
  event,
  context,
}: {
  event: ForgeAction | ForgeObservation;
  context: TurnRenderContext;
}):
  | Array<{ icon: React.ReactNode; onClick: () => void; tooltip?: string }>
  | undefined {
  return undefined;
}

function renderCombinedMessageGroup({
  group,
  groupIndex,
  turnIndex,
  isLastTurn,
  context,
}: {
  group: EventGroup;
  groupIndex: number;
  turnIndex: number;
  isLastTurn: boolean;
  context: TurnRenderContext;
}) {
  const combinedContent = group.events
    .map(extractMessageContent)
    .filter(Boolean)
    .join("\n\n");

  const firstEvent = group.events[0];
  const eventKey = hasId(firstEvent)
    ? `agent-message-group-${turnIndex}-${groupIndex}-${firstEvent.id}`
    : `agent-message-group-${turnIndex}-${groupIndex}`;

  const combinedEvent = {
    ...(firstEvent as ForgeAction | ForgeObservation),
    content: combinedContent,
    message: combinedContent,
  };

  return (
    <div key={eventKey} className="event-message mb-2">
      <EventMessage
        event={combinedEvent as ForgeAction | ForgeObservation}
        hasObservationPair={false}
        isAwaitingUserConfirmation={context.isAwaitingUserConfirmation}
        isLastMessage={groupIndex === group.events.length - 1}
        showTechnicalDetails={context.showTechnicalDetails}
        isInLast10Actions={isLastTurn}
        onAskAboutCode={context.onAskAboutCode}
        onRunCode={context.onRunCode}
        hideAvatar
        compactMode
      />
    </div>
  );
}

function renderAgentEvent({
  event,
  eventIndex,
  group,
  groupIndex,
  turnIndex,
  isLastTurn,
  context,
}: {
  event: ForgeAction | ForgeObservation;
  eventIndex: number;
  group: EventGroup;
  groupIndex: number;
  turnIndex: number;
  isLastTurn: boolean;
  context: TurnRenderContext;
}) {
  const nextEvent = group.events[eventIndex + 1];
  const eventKey = hasId(event)
    ? `agent-event-${turnIndex}-${groupIndex}-${eventIndex}-${event.id}`
    : `agent-event-${turnIndex}-${groupIndex}-${eventIndex}`;
  const eventId = hasId(event) ? Number(event.id) : undefined;
  const spacingClass = getEventSpacing(event, nextEvent);

  return (
    <div key={eventKey} className={cn("event-message", spacingClass)}>
      <EventMessage
        event={event}
        hasObservationPair={context.actionHasObservationPair(event)}
        isAwaitingUserConfirmation={context.isAwaitingUserConfirmation}
        isLastMessage={
          groupIndex === group.events.length - 1 &&
          eventIndex === group.events.length - 1
        }
        showTechnicalDetails={context.showTechnicalDetails}
        actions={buildEventActions({ event, context })}
        isInLast10Actions={isLastTurn}
        onAskAboutCode={context.onAskAboutCode}
        onRunCode={context.onRunCode}
        hideAvatar
        compactMode
      />
    </div>
  );
}

function renderEventGroup({
  group,
  groupIndex,
  turnIndex,
  isLastTurn,
  context,
}: {
  group: EventGroup;
  groupIndex: number;
  turnIndex: number;
  isLastTurn: boolean;
  context: TurnRenderContext;
}) {
  if (group.type === "message") {
    return renderCombinedMessageGroup({
      group,
      groupIndex,
      turnIndex,
      isLastTurn,
      context,
    });
  }

  return group.events.map((event, eventIndex) =>
    renderAgentEvent({
      event,
      eventIndex,
      group,
      groupIndex,
      turnIndex,
      isLastTurn,
      context,
    }),
  );
}

function renderUserTurn({
  turn,
  turnIndex,
  isLastTurn,
  context,
}: {
  turn: { events: Array<ForgeAction | ForgeObservation> };
  turnIndex: number;
  isLastTurn: boolean;
  context: TurnRenderContext;
}) {
  const message = turn.events[0] as ForgeAction | ForgeObservation;
  const messageKey = hasId(message)
    ? `user-turn-${turnIndex}-${message.id}`
    : `user-turn-${turnIndex}`;

  return (
    <div key={messageKey} className={cn("w-full group relative", "mb-3")}>
      <EventMessage
        event={message as ForgeAction | ForgeObservation}
        hasObservationPair={false}
        isAwaitingUserConfirmation={context.isAwaitingUserConfirmation}
        isLastMessage={false}
        showTechnicalDetails={context.showTechnicalDetails}
        isInLast10Actions={isLastTurn}
        onAskAboutCode={context.onAskAboutCode}
        onRunCode={context.onRunCode}
      />
    </div>
  );
}

function renderAgentTurn({
  turn,
  turnIndex,
  key,
  isLastTurn,
  context,
}: {
  turn: { events: Array<ForgeAction | ForgeObservation> };
  turnIndex: number;
  key: string;
  isLastTurn: boolean;
  context: TurnRenderContext;
}) {
  const filteredEvents = turn.events.filter((event) =>
    shouldRenderEvent(event, context.showTechnicalDetails),
  );
  const groups = groupEventsByType(filteredEvents);

  return (
    <div
      key={key}
      className={cn("w-full flex items-start gap-2 group relative", "mb-3")}
    >
      <div
        aria-label="Agent"
        className="shrink-0 w-8 h-8 flex items-center justify-center"
      >
        <img
          src="/agent-icon.png?v=2"
          alt="Forge Agent"
          className="w-8 h-8 object-contain"
        />
      </div>

      <div className="flex-1 min-w-0 flex flex-col">
        {groups.map((group, groupIndex) =>
          renderEventGroup({
            group,
            groupIndex,
            turnIndex,
            isLastTurn,
            context,
          }),
        )}

        {turn.events.length > 1 && !context.showTechnicalDetails && (
          <ActionSummary
            events={turn.events.filter((event) => !isAssistantMessage(event))}
          />
        )}
      </div>
    </div>
  );
}

function renderTurn({
  turn,
  turnIndex,
  context,
}: {
  turn: {
    type: string;
    events: Array<ForgeAction | ForgeObservation>;
    startIndex: number;
  };
  turnIndex: number;
  context: TurnRenderContext;
}) {
  const isLastTurn = turnIndex === context.turns.length - 1;
  const key = `turn-${turnIndex}-${turn.type}-${turn.startIndex}`;

  if (turn.type === "user") {
    return renderUserTurn({
      turn,
      turnIndex,
      isLastTurn,
      context,
    });
  }

  return renderAgentTurn({
    turn,
    turnIndex,
    key,
    isLastTurn,
    context,
  });
}

export const Messages: React.FC<MessagesProps> = React.memo(
  ({
    messages,
    isAwaitingUserConfirmation,
    showTechnicalDetails = false,
    onAskAboutCode,
    onRunCode,
  }) => {
    const { getOptimisticUserMessage } = useOptimisticUserMessage();
    const { conversationId } = useConversationId();
    const { data: conversation } = useUserConversation(conversationId);

    const optimisticUserMessage = getOptimisticUserMessage();

    const { t } = useTranslation();

    const actionHasObservationPair = React.useCallback(
      (event: unknown): boolean => {
        try {
          const r = asRecord(event);
          if (isForgeAction(event) && typeof r?.id !== "undefined") {
            const { id } = r!;
            return !!messages.some(
              (msg) => isForgeObservation(msg) && msg.cause === id,
            );
          }
        } catch {
          /* ignore */
        }
        return false;
      },
      [messages],
    );

    // Group messages into turns (bolt.new style)
    type Turn = {
      type: string;
      events: Array<ForgeAction | ForgeObservation>;
      startIndex: number;
    };

    const turns = React.useMemo(
      (): Turn[] =>
        buildTurns(messages as Array<ForgeAction | ForgeObservation>) as Turn[],
      [messages],
    );

    const renderContext: TurnRenderContext = {
      turns,
      isAwaitingUserConfirmation,
      showTechnicalDetails,
      onAskAboutCode,
      onRunCode,
      actionHasObservationPair,
      conversation,
      t,
    };

    return (
      <>
        {turns.map((turn: Turn, turnIndex: number) =>
          renderTurn({
            turn,
            turnIndex,
            context: renderContext,
          }),
        )}

        {optimisticUserMessage && (
          <ChatMessage
            type="user"
            message={optimisticUserMessage}
            onAskAboutCode={onAskAboutCode}
            onRunCode={onRunCode}
          />
        )}
      </>
    );
  },
);

Messages.displayName = "Messages";
