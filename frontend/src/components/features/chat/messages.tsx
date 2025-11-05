import React from "react";
import { useTranslation } from "react-i18next";
import { createPortal } from "react-dom";
import { OpenHandsAction } from "#/types/core/actions";
import { OpenHandsObservation } from "#/types/core/observations";
import {
  isOpenHandsAction,
  isOpenHandsObservation,
  isOpenHandsEvent,
  isAgentStateChangeObservation,
  isFinishAction,
  isUserMessage,
  isAssistantMessage,
  hasExtras,
  hasArgs,
} from "#/types/core/guards";
import { groupMessagesIntoTurns } from "#/utils/group-messages-into-turns";
import { coalesceMessages, getEventSpacing } from "#/utils/coalesce-messages";
import { shouldRenderEvent } from "#/utils/should-render-event";
import { EventMessage } from "./event-message";
import { ChatMessage } from "./chat-message";
import { ActionSummary } from "./action-summary";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { LaunchMicroagentModal } from "./microagent/launch-microagent-modal";
import { useUserConversation } from "#/hooks/query/use-user-conversation";
import { useConversationId } from "#/hooks/use-conversation-id";
import { useCreateConversationAndSubscribeMultiple } from "#/hooks/use-create-conversation-and-subscribe-multiple";
import {
  MicroagentStatus,
  EventMicroagentStatus,
} from "#/types/microagent-status";
import { AgentState } from "#/types/agent-state";
import { getFirstPRUrl } from "#/utils/parse-pr-url";
import MemoryIcon from "#/icons/memory_icon.svg?react";
import { cn } from "#/utils/utils";

// Small runtime helper to safely treat unknown values as records when appropriate
const asRecord = (v: unknown): Record<string, unknown> | undefined =>
  typeof v === "object" && v !== null ? (v as Record<string, unknown>) : undefined;

const isErrorEvent = (evt: unknown): evt is { error: true; message: string } =>
  typeof evt === "object" &&
  evt !== null &&
  "error" in evt &&
  evt.error === true;

  const isAgentStatusError = (evt: unknown): boolean =>
    isOpenHandsEvent(evt) &&
    isAgentStateChangeObservation(evt) &&
    hasExtras(evt) &&
    (() => {
      try {
        const r = asRecord(evt);
        const ex = asRecord(r?.extras);
        const agentState = typeof ex?.agent_state === "number" ? (ex!.agent_state as unknown as AgentState) : undefined;
        return typeof agentState === "number" && agentState === AgentState.ERROR;
      } catch {
        return false;
      }
    })();

interface MessagesProps {
  messages: (OpenHandsAction | OpenHandsObservation)[];
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails?: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
}

export const Messages: React.FC<MessagesProps> = React.memo(
  ({ messages, isAwaitingUserConfirmation, showTechnicalDetails = false, onAskAboutCode, onRunCode }) => {
    const {
      createConversationAndSubscribe,
      isPending,
      unsubscribeFromConversation,
    } = useCreateConversationAndSubscribeMultiple();
    const { getOptimisticUserMessage } = useOptimisticUserMessage();
    const { conversationId } = useConversationId();
    const { data: conversation } = useUserConversation(conversationId);

    const optimisticUserMessage = getOptimisticUserMessage();

    const [selectedEventId, setSelectedEventId] = React.useState<number | null>(
      null,
    );
    const [showLaunchMicroagentModal, setShowLaunchMicroagentModal] =
      React.useState(false);
    const [microagentStatuses, setMicroagentStatuses] = React.useState<
      EventMicroagentStatus[]
    >([]);

    const { t } = useTranslation();

    const actionHasObservationPair = React.useCallback(
      (event: unknown): boolean => {
        try {
          const r = asRecord(event);
          if (isOpenHandsAction(event) && typeof r?.id !== "undefined") {
            const id = r!.id;
            return !!messages.some((msg) => isOpenHandsObservation(msg) && msg.cause === id);
          }
        } catch {
          /* ignore */
        }
        return false;
      },
      [messages],
    );

    const getMicroagentStatusForEvent = React.useCallback(
      (eventId: number): MicroagentStatus | null => {
        const statusEntry = microagentStatuses.find(
          (entry) => entry.eventId === eventId,
        );
        return statusEntry?.status || null;
      },
      [microagentStatuses],
    );

    const getMicroagentConversationIdForEvent = React.useCallback(
      (eventId: number): string | undefined => {
        const statusEntry = microagentStatuses.find(
          (entry) => entry.eventId === eventId,
        );
        return statusEntry?.conversationId || undefined;
      },
      [microagentStatuses],
    );

    const getMicroagentPRUrlForEvent = React.useCallback(
      (eventId: number): string | undefined => {
        const statusEntry = microagentStatuses.find(
          (entry) => entry.eventId === eventId,
        );
        return statusEntry?.prUrl || undefined;
      },
      [microagentStatuses],
    );

    const handleMicroagentEvent = React.useCallback(
      (socketEvent: unknown, microagentConversationId: string) => {
        if (isErrorEvent(socketEvent) || isAgentStatusError(socketEvent)) {
          setMicroagentStatuses((prev) =>
            prev.map((statusEntry) =>
              statusEntry.conversationId === microagentConversationId
                ? { ...statusEntry, status: MicroagentStatus.ERROR }
                : statusEntry,
            ),
          );
        } else if (
          isOpenHandsEvent(socketEvent) &&
          isAgentStateChangeObservation(socketEvent) &&
          hasExtras(socketEvent)
        ) {
          // Handle completion states
          try {
            const se = socketEvent as unknown as Record<string, unknown>;
            const sex = se.extras as unknown as Record<string, unknown> | undefined;
            const agentState = typeof sex?.agent_state === "number" ? (sex!.agent_state as unknown as AgentState) : undefined;
            if (
              typeof agentState === "number" &&
              (agentState === AgentState.FINISHED || agentState === AgentState.AWAITING_USER_INPUT)
            ) {
              setMicroagentStatuses((prev) =>
                prev.map((statusEntry) =>
                  statusEntry.conversationId === microagentConversationId
                    ? { ...statusEntry, status: MicroagentStatus.COMPLETED }
                    : statusEntry,
                ),
              );

              unsubscribeFromConversation(microagentConversationId);
            }
          } catch {
            // ignore malformed socketEvent
          }
        } else if (
          isOpenHandsEvent(socketEvent) &&
          isFinishAction(socketEvent)
        ) {
          // Check if the finish action contains a PR URL
          if (hasArgs(socketEvent)) {
            try {
              const se = socketEvent as unknown as Record<string, unknown>;
              const sargs = se.args as unknown as Record<string, unknown> | undefined;
              const finalThought = sargs?.final_thought;
              const prUrl = getFirstPRUrl(typeof finalThought === "string" ? finalThought : String(finalThought ?? ""));
              if (prUrl) {
                setMicroagentStatuses((prev) =>
                  prev.map((statusEntry) =>
                    statusEntry.conversationId === microagentConversationId
                      ? {
                          ...statusEntry,
                          status: MicroagentStatus.COMPLETED,
                          prUrl,
                        }
                      : statusEntry,
                  ),
                );
              }
            } catch {
              // ignore malformed finish action
            }
          }

          unsubscribeFromConversation(microagentConversationId);
        } else {
          // For any other event, transition from WAITING to CREATING if still waiting
          setMicroagentStatuses((prev) => {
            const currentStatus = prev.find(
              (entry) => entry.conversationId === microagentConversationId,
            )?.status;

            if (currentStatus === MicroagentStatus.WAITING) {
              return prev.map((statusEntry) =>
                statusEntry.conversationId === microagentConversationId
                  ? { ...statusEntry, status: MicroagentStatus.CREATING }
                  : statusEntry,
              );
            }
            return prev; // No change needed
          });
        }
      },
      [setMicroagentStatuses, unsubscribeFromConversation],
    );

    const handleLaunchMicroagent = (
      query: string,
      target: string,
      triggers: string[],
    ) => {
      const conversationInstructions = `Target file: ${target}\n\nDescription: ${query}\n\nTriggers: ${triggers.join(", ")}`;
      if (
        !conversation ||
        !conversation.selected_repository ||
        !conversation.selected_branch ||
        !conversation.git_provider ||
        !selectedEventId
      ) {
        return;
      }

      createConversationAndSubscribe({
        query,
        conversationInstructions,
        repository: {
          name: conversation.selected_repository,
          branch: conversation.selected_branch,
          gitProvider: conversation.git_provider,
        },
        onSuccessCallback: (newConversationId: string) => {
          setShowLaunchMicroagentModal(false);
          // Update status with conversation ID - start with WAITING
          setMicroagentStatuses((prev) => [
            ...prev.filter((status) => status.eventId !== selectedEventId),
            {
              eventId: selectedEventId,
              conversationId: newConversationId,
              status: MicroagentStatus.WAITING,
            },
          ]);
        },
        onEventCallback: (socketEvent: unknown, newConversationId: string) => {
          handleMicroagentEvent(socketEvent, newConversationId);
        },
      });
    };

    // Narrowing helper to detect presence of an id on the message without using `any`.
    const hasId = (obj: unknown): obj is { id: number | string } => {
      if (typeof obj !== "object" || obj === null) {
        return false;
      }
      const record = obj as Record<string, unknown>;
      if (!("id" in record)) {
        return false;
      }
      const { id } = record;
      return typeof id === "string" || typeof id === "number";
    };

    // Group messages into turns (bolt.new style)
    const turns = React.useMemo(() => {
      // 🔢 CRITICAL Fix: Sort events by sequence number for guaranteed ordering
      // Safely extract sequence or id without using `any` casts
      const getSeq = (ev: unknown): number => {
        try {
          const r = asRecord(ev);
          if (typeof r?.sequence === "number") return r.sequence as number;
          if (typeof r?.id === "number") return r.id as number;
          if (typeof r?.id === "string") return Number(r.id) || 0;
        } catch {
          /* ignore */
        }
        return 0;
      };

      const sortedMessages = [...messages].sort((a, b) => getSeq(a) - getSeq(b));
      
      const grouped = groupMessagesIntoTurns(sortedMessages);
      
      // BOLT.NEW-STYLE STREAMING: NO COALESCING
      // Each event renders immediately as it arrives for real-time streaming
      // Don't batch/merge messages - show them individually as they stream in
      
        console.log("⚡ LIVE STREAMING (no coalescing):", {
        totalMessages: messages.length,
        totalTurns: grouped.length,
          turnsBreakdown: grouped.map((t, i) => ({
            index: i,
            type: t.type,
            eventCount: t.events.length,
            eventIds: t.events.map((e) => hasId(e) ? (e as any).id : undefined).filter(Boolean).join(','),
            sequences: t.events.map((e) => {
              const r = asRecord(e);
              return r?.sequence;
            }).filter(Boolean).join('')
          }))
      });
      
      // Return uncoalesced turns for immediate event-by-event rendering
      return grouped;
    }, [messages]);
    
    return (
      <>
        {turns.map((turn, turnIndex) => {
          const isLastTurn = turnIndex === turns.length - 1;
          // Use turnIndex as primary key for stability
          const turnKey = `turn-${turnIndex}-${turn.type}-${turn.startIndex}`;
          
          // User message - render as single message
          if (turn.type === "user") {
            const message = turn.events[0];
            // Use turn-based key to avoid conflicts with agent messages
            const messageKey = hasId(message) ? `user-turn-${turnIndex}-${message.id}` : `user-turn-${turnIndex}`;
            
            return (
              <div 
                key={messageKey}
                className={cn(
                  "w-full group relative",
                  // Clean, minimal spacing like bolt.new
                  "mb-3"
                )}
              >
                <EventMessage
                  event={message as OpenHandsAction | OpenHandsObservation}
                  hasObservationPair={false}
                  isAwaitingUserConfirmation={isAwaitingUserConfirmation}
                  isLastMessage={false}
                  showTechnicalDetails={showTechnicalDetails}
                  isInLast10Actions={isLastTurn}
                  onAskAboutCode={onAskAboutCode}
                  onRunCode={onRunCode}
                />
              </div>
            );
          }
          
          // Agent turn - render all events with ONE avatar
          console.log(`🤖 Rendering agent turn ${turnIndex}:`, {
            key: turnKey,
            eventCount: turn.events.length,
            eventIds: turn.events.map(e => hasId(e) ? (e as any).id : undefined).filter(Boolean)
          });
          
          return (
            <div 
              key={turnKey} 
              className={cn(
                "w-full flex items-start gap-2 group relative",
                "mb-3"
              )}
            >
              {/* Single avatar for the entire turn - Simple logo */}
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
              
              {/* All events in the turn, grouped together */}
              <div className="flex-1 min-w-0 flex flex-col">
                {(() => {
                  // 💬 CRITICAL FIX: Group consecutive messages into ONE bubble (ChatGPT style)
                  // While keeping tool calls/observations separate
                  const filteredEvents = turn.events.filter(event => shouldRenderEvent(event, showTechnicalDetails));
                  const eventGroups: Array<{ type: 'message' | 'other', events: typeof filteredEvents }> = [];
                  let currentGroup: typeof eventGroups[0] | null = null;

                  filteredEvents.forEach((event) => {
                    const isMessage = isAssistantMessage(event);
                    
                    if (!currentGroup || currentGroup.type !== (isMessage ? 'message' : 'other')) {
                      // Start new group
                      currentGroup = { type: isMessage ? 'message' : 'other', events: [event] };
                      eventGroups.push(currentGroup);
                    } else {
                      // Add to existing group
                      currentGroup.events.push(event);
                    }
                  });

                  return eventGroups.map((group, groupIndex) => {
                    if (group.type === 'message') {
                      // Combine all message content into ONE bubble
                      // Use a defensive extractor to build combined content
                      const combinedContent = group.events
                        .map((e) => {
                          try {
                            // Prefer args.content/args.message/args.thought, then message/content
                            const a = hasArgs(e) ? (e as OpenHandsAction).args : undefined;
                            if (a && typeof (a as Record<string, unknown>).content === "string") return String((a as Record<string, unknown>).content);
                            if (a && typeof (a as Record<string, unknown>).message === "string") return String((a as Record<string, unknown>).message);
                            if (a && typeof (a as Record<string, unknown>).thought === "string") return String((a as Record<string, unknown>).thought);
                            const ev = asRecord(e);
                            if (typeof ev?.message === "string") return String(ev.message);
                            if (typeof ev?.content === "string") return String(ev.content);
                          } catch (_err) {
                            return "";
                          }
                          return "";
                        })
                        .filter(Boolean)
                        .join("\n\n");

                      const firstEvent = group.events[0];
                      const eventKey = hasId(firstEvent) 
                        ? `agent-message-group-${turnIndex}-${groupIndex}-${firstEvent.id}` 
                        : `agent-message-group-${turnIndex}-${groupIndex}`;

                      // Create a combined message event
                      const combinedEvent = {
                        ...firstEvent,
                        content: combinedContent,
                        message: combinedContent,
                      };

                      return (
                        <div 
                          key={eventKey}
                          className="event-message mb-2"
                        >
                          <EventMessage
                            event={combinedEvent as OpenHandsAction | OpenHandsObservation}
                            hasObservationPair={false}
                            isAwaitingUserConfirmation={isAwaitingUserConfirmation}
                            isLastMessage={groupIndex === eventGroups.length - 1}
                            showTechnicalDetails={showTechnicalDetails}
                            isInLast10Actions={isLastTurn}
                            onAskAboutCode={onAskAboutCode}
                            onRunCode={onRunCode}
                            hideAvatar={true}
                            compactMode={true}
                          />
                        </div>
                      );
                    } else {
                      // Render tool calls/observations separately
                      return group.events.map((event, eventIndex) => {
                        const nextEvent = group.events[eventIndex + 1];
                        const eventKey = hasId(event) 
                          ? `agent-event-${turnIndex}-${groupIndex}-${eventIndex}-${event.id}` 
                          : `agent-event-${turnIndex}-${groupIndex}-${eventIndex}`;
                        const eventId = hasId(event) ? event.id : undefined;
                        const spacingClass = getEventSpacing(event, nextEvent);

                        return (
                          <div 
                            key={eventKey}
                            className={cn("event-message", spacingClass)}
                          >
                            <EventMessage
                              event={event as OpenHandsAction | OpenHandsObservation}
                              hasObservationPair={actionHasObservationPair(event)}
                              isAwaitingUserConfirmation={isAwaitingUserConfirmation}
                              isLastMessage={groupIndex === eventGroups.length - 1 && eventIndex === group.events.length - 1}
                              showTechnicalDetails={showTechnicalDetails}
                              microagentStatus={eventId ? getMicroagentStatusForEvent(eventId) : undefined}
                              microagentConversationId={eventId ? getMicroagentConversationIdForEvent(eventId) : undefined}
                              microagentPRUrl={eventId ? getMicroagentPRUrlForEvent(eventId) : undefined}
                              actions={
                                conversation?.selected_repository
                                  ? [
                                      {
                                        icon: (
                                          <MemoryIcon className="w-[14px] h-[14px] text-white" />
                                        ),
                                        onClick: () => {
                                          if (hasId(event)) {
                                            setSelectedEventId(event.id as number);
                                            setShowLaunchMicroagentModal(true);
                                          }
                                        },
                                        tooltip: t("MICROAGENT$ADD_TO_MEMORY"),
                                      },
                                    ]
                                  : undefined
                              }
                              isInLast10Actions={isLastTurn}
                              onAskAboutCode={onAskAboutCode}
                              onRunCode={onRunCode}
                              hideAvatar={true}
                              compactMode={true}
                            />
                          </div>
                        );
                      });
                    }
                  });
                })()}
                
                {/* Compact action summary at end of turn (bolt.new style) */}
                {turn.events.length > 1 && !showTechnicalDetails && (
                  <ActionSummary 
                    events={turn.events.filter(e => !isAssistantMessage(e))} 
                  />
                )}
              </div>
            </div>
          );
        })}

        {optimisticUserMessage && (
          <ChatMessage
            type="user"
            message={optimisticUserMessage}
            onAskAboutCode={onAskAboutCode}
            onRunCode={onRunCode}
          />
        )}
        {conversation?.selected_repository &&
          showLaunchMicroagentModal &&
          selectedEventId &&
          createPortal(
            <LaunchMicroagentModal
              onClose={() => setShowLaunchMicroagentModal(false)}
              onLaunch={handleLaunchMicroagent}
              selectedRepo={
                conversation.selected_repository.split("/").pop() || ""
              }
              eventId={selectedEventId}
              isLoading={isPending}
            />,
            document.getElementById("modal-portal-exit") || document.body,
          )}
      </>
    );
  }
);

Messages.displayName = "Messages";
