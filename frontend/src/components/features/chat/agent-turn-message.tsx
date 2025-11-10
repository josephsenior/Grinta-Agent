import React from "react";
import { EventMessage } from "./event-message";

interface AgentTurnMessageProps {
  events: (
    | import("#/types/core").ForgeAction
    | import("#/types/core").ForgeObservation
  )[];
  isLastTurn: boolean;
  isAwaitingUserConfirmation: boolean;
  showTechnicalDetails: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
}

/**
 * AgentTurnMessage - Groups consecutive agent events into a single visual "turn"
 *
 * This matches bolt.new's UX where all agent actions/thoughts/outputs
 * are shown as ONE unified message instead of separate bubbles.
 *
 * Features:
 * - Single avatar for the entire turn
 * - Compact spacing between events
 * - Visual grouping with subtle background
 * - Streaming updates happen within the same turn
 */
export function AgentTurnMessage({
  events,
  isLastTurn,
  isAwaitingUserConfirmation,
  showTechnicalDetails,
  onAskAboutCode,
  onRunCode,
}: AgentTurnMessageProps) {
  return (
    <div className="w-full flex items-start gap-2 group">
      {/* Agent Avatar - Only show once per turn */}
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

      {/* Turn Content - All events grouped together */}
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        {events.map((event, index) => {
          const isLastInTurn = index === events.length - 1;
          const isLastOverall = isLastTurn && isLastInTurn;

          return (
            <div key={`turn-event-${event.id || index}`} className="w-full">
              <EventMessage
                event={event}
                hasObservationPair={false}
                isAwaitingUserConfirmation={isAwaitingUserConfirmation}
                isLastMessage={isLastOverall}
                showTechnicalDetails={showTechnicalDetails}
                isInLast10Actions={isLastTurn}
                onAskAboutCode={onAskAboutCode}
                onRunCode={onRunCode}
                // Don't show avatar - we're already showing it for the turn
                hideAvatar
                // Reduce margins for compact grouping
                compactMode
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
