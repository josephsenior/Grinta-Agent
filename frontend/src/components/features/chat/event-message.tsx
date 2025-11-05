import React from "react";
import { useTranslation } from "react-i18next";
import { ConfirmationButtons } from "#/components/shared/buttons/confirmation-buttons";
import { OpenHandsAction } from "#/types/core/actions";
import {
  isUserMessage,
  isErrorObservation,
  isAssistantMessage,
  isOpenHandsAction,
  isOpenHandsObservation,
  isFinishAction,
  isRejectObservation,
  isMcpObservation,
  isTaskTrackingObservation,
  isFileWriteAction,
  isFileEditAction,
  isStreamingChunkAction,
  hasArgs,
  hasExtras,
} from "#/types/core/guards";
import { OpenHandsObservation } from "#/types/core/observations";
import { ImageCarousel } from "../images/image-carousel";
import { ChatMessage } from "./chat-message";
import { ErrorMessage } from "./error-message";
import { MCPObservationContent } from "./mcp-observation-content";
import { TaskTrackingObservationContent } from "./task-tracking-observation-content";
import { getObservationResult } from "./event-content-helpers/get-observation-result";
import { getEventContent } from "./event-content-helpers/get-event-content";
import { GenericEventMessage } from "./generic-event-message";
import { MicroagentStatus } from "#/types/microagent-status";
import { MicroagentStatusIndicator } from "./microagent/microagent-status-indicator";
import { FileList } from "../files/file-list";
import { parseMessageFromEvent } from "./event-content-helpers/parse-message-from-event";
import { LikertScale } from "../feedback/likert-scale";
import { useWsClient } from "#/context/ws-client-provider";
import { StreamingTerminal } from "../terminal/streaming-terminal";
import { StreamingThought } from "./streaming-thought";
import { CodeArtifact } from "./code-artifact";
import { StreamingCodeArtifact } from "./streaming-code-artifact";

import { useConfig } from "#/hooks/query/use-config";
import { useFeedbackExists } from "#/hooks/query/use-feedback-exists";
import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";

// Detect important commands that should be shown even when technical details are hidden
const isImportantCommand = (cmd?: string | null): boolean => {
  if (!cmd) return false;
  const command = String(cmd).toLowerCase();
  const importantPatterns = [
    /npm\s+(install|i|run|build|start|test)/,
    /yarn\s+(install|add|build|start|test)/,
    /pnpm\s+(install|add|build|start|test)/,
    /pip\s+install/,
    /docker\s+(build|run|compose)/,
    /git\s+(clone|pull|push|commit|checkout|branch)/,
    /pytest/,
    /cargo\s+(build|run|test)/,
    /make\s+(build|install|test)/,
    /cmake/,
    /deploy/,
    /build/,
  ];
  return importantPatterns.some((pattern) => pattern.test(command));
};

// small heuristic reused from CommandConsole to detect shell-like lines
export const looksLikeShell = (s?: string | null): boolean => {
  if (!s) {
    return false;
  }
  const text = String(s);
  const shellTokens = [
    "rm -",
    "&&",
    "||",
    "npm ",
    "yarn ",
    "docker ",
    "kubectl ",
    "/workspace/",
    "cd ",
    "git ",
    "ls ",
    "pwd",
    "echo ",
  ];
  if (text.startsWith("Ran ") || text.startsWith("ran ")) {
    return true;
  }
  for (const tk of shellTokens)
    if (text.includes(tk)) {
      return true;
    }
  if (/\/[\w\-./~]/.test(text)) {
    return true;
  }
  return false;
};

const hasThoughtProperty = (
  obj: Record<string, unknown>,
): obj is { thought: string } => "thought" in obj && !!obj.thought;

// Detect language from file extension
const getLanguageFromPath = (filePath: string): string => {
  const ext = filePath.split(".").pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    java: "java",
    cpp: "cpp",
    c: "c",
    h: "c",
    hpp: "cpp",
    cs: "csharp",
    go: "go",
    rs: "rust",
    rb: "ruby",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    scala: "scala",
    sql: "sql",
    sh: "shell",
    bash: "shell",
    yaml: "yaml",
    yml: "yaml",
    json: "json",
    xml: "xml",
    html: "html",
    css: "css",
    scss: "scss",
    less: "less",
    md: "markdown",
    dockerfile: "dockerfile",
  };
  return languageMap[ext || ""] || "plaintext";
};

interface EventMessageProps {
  event: OpenHandsAction | OpenHandsObservation;
  hasObservationPair: boolean;
  isAwaitingUserConfirmation: boolean;
  isLastMessage: boolean;
  showTechnicalDetails?: boolean;
  autoExpandTechnicalDetails?: boolean; // Smart expansion control
  microagentStatus?: MicroagentStatus | null;
  microagentConversationId?: string;
  microagentPRUrl?: string;
  actions?: Array<{
    icon: React.ReactNode;
    onClick: () => void;
    tooltip?: string;
  }>;
  isInLast10Actions: boolean;
  onAskAboutCode?: (code: string) => void;
  onRunCode?: (code: string, language: string) => void;
  // New props for turn-based grouping
  hideAvatar?: boolean;
  compactMode?: boolean;
}

export const EventMessage = React.memo(function EventMessage({
  event,
  hasObservationPair,
  isAwaitingUserConfirmation,
  isLastMessage,
  showTechnicalDetails = false,
  autoExpandTechnicalDetails = false,
  microagentStatus,
  microagentConversationId,
  microagentPRUrl,
  actions,
  isInLast10Actions,
  onAskAboutCode,
  onRunCode,
  hideAvatar = false,
  compactMode = false,
}: EventMessageProps) {
  const { t } = useTranslation();
  const { curAgentState } = useSelector((state: RootState) => state.agent);
  const shouldShowConfirmationButtons =
    isLastMessage && event.source === "agent" && isAwaitingUserConfirmation;

  const { data: config } = useConfig();
  
  const {
    data: feedbackData = { exists: false },
    isLoading: isCheckingFeedback,
  } = useFeedbackExists(event.id);

  // Safe accessors for action/observation runtime payloads
  const extras = hasExtras(event) ? event.extras : ({} as Record<string, unknown>);
  const args = hasArgs(event) ? event.args : ({} as Record<string, unknown>);
  const a = args;

  // Use WS client hook at top-level of component to access hydratedEventIds
  const { hydratedEventIds } = useWsClient();

  const getEventHydratedFlag = (ev: OpenHandsAction | OpenHandsObservation) => {
    try {
      const v = ev as unknown as Record<string, unknown>;
      const h = v.__hydrated;
      return Boolean(h);
    } catch (_e) {
      return false;
    }
  };
  
  // Hide technical events when showTechnicalDetails is false
  if (!showTechnicalDetails) {
    // Always show user and assistant messages
    if (isUserMessage(event) || isAssistantMessage(event)) {
      // Continue to render below
    }
    // Always show streaming chunks (real-time LLM responses)
    else if (isStreamingChunkAction(event)) {
      // Continue to render streaming text below
    }
    // Always show errors
    else if (isErrorObservation(event)) {
      // Continue to render below
    }
    // Always show file write/edit actions (code artifacts)
    else if (isFileWriteAction(event) || isFileEditAction(event)) {
      // Continue to render code artifact below
    }
    // Show important commands via terminal
    else if (
      isOpenHandsObservation(event) &&
      event.observation === "run" &&
      isImportantCommand(typeof extras.command === "string" ? extras.command : undefined)
    ) {
      // Continue to render terminal below
    }
    // Show agent thoughts
    else if (
      isOpenHandsAction(event) &&
      hasThoughtProperty(args as Record<string, unknown>) &&
      event.action !== "think"
    ) {
      // Continue to render thought below
    }
    // Show finish actions
    else if (isFinishAction(event)) {
      // Continue to render below
    }
    // Show reject observations
    else if (isRejectObservation(event)) {
      // Continue to render below
    }
    // Show MCP and task tracking observations
    else if (isMcpObservation(event) || isTaskTrackingObservation(event)) {
      // Continue to render below
    }
    // Hide everything else (verbose technical events)
    else {
      return null;
    }
  }

  const renderLikertScale = () => {
    if (config?.APP_MODE !== "saas" || isCheckingFeedback) {
      return null;
    }

    // For error observations, show if in last 10 actions
    // For other events, show only if it's the last message
    const shouldShow = isErrorObservation(event)
      ? isInLast10Actions
      : isLastMessage;

    if (!shouldShow) {
      return null;
    }

    return (
      <LikertScale
        eventId={event.id}
        initiallySubmitted={feedbackData.exists}
        initialRating={feedbackData.rating}
        initialReason={feedbackData.reason}
      />
    );
  };

  if (isErrorObservation(event)) {
    return (
      <div>
        <ErrorMessage
          errorId={typeof extras.error_id === "string" ? extras.error_id : undefined}
          defaultMessage={event.message}
        />
        {microagentStatus && actions && (
          <MicroagentStatusIndicator
            status={microagentStatus}
            conversationId={microagentConversationId}
            prUrl={microagentPRUrl}
          />
        )}
        {renderLikertScale()}
      </div>
    );
  }

  if (hasObservationPair && isOpenHandsAction(event)) {
    if (hasThoughtProperty(args) && event.action !== "think") {
      return (
        <div>
          <ChatMessage
            type="agent"
            message={typeof args.thought === "string" ? args.thought : ""}
            actions={actions}
            onAskAboutCode={onAskAboutCode}
            onRunCode={onRunCode}
            hideAvatar={hideAvatar}
            compactMode={compactMode}
          />
          {microagentStatus && actions && (
            <MicroagentStatusIndicator
              status={microagentStatus}
              conversationId={microagentConversationId}
              prUrl={microagentPRUrl}
            />
          )}
        </div>
      );
    }
    return microagentStatus && actions ? (
      <MicroagentStatusIndicator
        status={microagentStatus}
        conversationId={microagentConversationId}
        prUrl={microagentPRUrl}
      />
    ) : null;
  }

  // Render file write actions with streaming or static CodeArtifact
  if (isFileWriteAction(event)) {
    const isAgentRunning = curAgentState === AgentState.RUNNING;
    const isLastEvent = isLastMessage;
    
    return (
      <div>
        {(typeof args.thought === "string" && args.thought) && (
          <StreamingThought
            eventId={String(event.id)}
            thought={String(args.thought)}
          />
        )}
          {isAgentRunning && isLastEvent ? (
          <StreamingCodeArtifact
            filePath={typeof args.path === "string" ? args.path : ""}
            language={getLanguageFromPath(typeof args.path === "string" ? args.path : "")}
            code={typeof args.content === "string" ? args.content : ""}
            action="create"
            eventId={String(event.id)}
            isStreaming={true}
            onCopy={() => {
              // Copy handled by component
            }}
          />
        ) : (
          <CodeArtifact
            filePath={typeof args.path === "string" ? args.path : ""}
            language={getLanguageFromPath(typeof args.path === "string" ? args.path : "")}
            code={typeof args.content === "string" ? args.content : ""}
            action="create"
            onCopy={() => {
              // Copy handled by component
            }}
          />
        )}
        {microagentStatus && actions && (
          <MicroagentStatusIndicator
            status={microagentStatus}
            conversationId={microagentConversationId}
            prUrl={microagentPRUrl}
          />
        )}
      </div>
    );
  }

  // Render file edit actions with streaming or static CodeArtifact
  if (isFileEditAction(event)) {
    const code = String(
      typeof args.content === "string"
        ? args.content
        : typeof args.file_text === "string"
        ? args.file_text
        : typeof args.new_str === "string"
        ? args.new_str
        : "",
    );
    const isAgentRunning = curAgentState === AgentState.RUNNING;
    const isLastEvent = isLastMessage;
    
    return (
      <div>
        {(typeof args.thought === "string" && args.thought) && (
          <StreamingThought
            eventId={String(event.id)}
            thought={String(args.thought)}
          />
        )}
        {isAgentRunning && isLastEvent ? (
          <StreamingCodeArtifact
            filePath={typeof args.path === "string" ? args.path : ""}
            language={getLanguageFromPath(typeof args.path === "string" ? args.path : "")}
            code={code}
            action="edit"
            eventId={String(event.id)}
            isStreaming={true}
            onCopy={() => {
              // Copy handled by component
            }}
          />
        ) : (
          <CodeArtifact
            filePath={typeof args.path === "string" ? args.path : ""}
            language={getLanguageFromPath(typeof args.path === "string" ? args.path : "")}
            code={code}
            action="edit"
            onCopy={() => {
              // Copy handled by component
            }}
          />
        )}
        {microagentStatus && actions && (
          <MicroagentStatusIndicator
            status={microagentStatus}
            conversationId={microagentConversationId}
            prUrl={microagentPRUrl}
          />
        )}
      </div>
    );
  }

  // Render streaming chunks (real-time LLM token-by-token streaming)
  if (isStreamingChunkAction(event)) {
    return (
      <ChatMessage
        type="agent"
        message={typeof args.accumulated === "string" ? args.accumulated : ""}
        animate={true}  // ✅ Enable character-by-character animation for smooth streaming
        onAskAboutCode={onAskAboutCode}
        onRunCode={onRunCode}
        hideAvatar={hideAvatar}
        compactMode={compactMode}
      />
    );
  }

  if (isFinishAction(event)) {
    return (
      <>
        <ChatMessage
          type="agent"
          message={getEventContent(event).details}
          actions={actions}
          onAskAboutCode={onAskAboutCode}
          onRunCode={onRunCode}
          hideAvatar={hideAvatar}
          compactMode={compactMode}
        />
        {microagentStatus && actions && (
          <MicroagentStatusIndicator
            status={microagentStatus}
            conversationId={microagentConversationId}
            prUrl={microagentPRUrl}
          />
        )}
        {renderLikertScale()}
      </>
    );
  }

  if (isUserMessage(event) || isAssistantMessage(event)) {
    const message = parseMessageFromEvent(event);

    // Simplified animation logic - only animate if it's a new message and not hydrated
    const animateDecision =
      isAssistantMessage(event) &&
      isLastMessage &&
      !hydratedEventIds.has(String(event.id)) &&
      !getEventHydratedFlag(event);

    // Only render explicit run events as the terminal-style block. The user
    // asked for terminal appearance for actual run/command outputs, not for
    // all assistant messages, so we only match events with action === 'run'.
    // Keep legacy rendering: the event content helper shows commands and
    // task-tracking outputs. Run events are rendered via the generic
    // GenericEventMessage or ChatMessage as before.

    return (
      <>
        <ChatMessage
          type={event.source}
          message={message}
          actions={actions}
          // Don't animate messages that were hydrated from trajectory on page load
          animate={animateDecision}
          onAskAboutCode={onAskAboutCode}
          onRunCode={onRunCode}
          hideAvatar={hideAvatar}
          compactMode={compactMode}
        >
          {(Array.isArray(a.image_urls) && (a.image_urls as unknown[]).length > 0) && (
            <ImageCarousel size="small" images={(a.image_urls as string[])} />
          )}
          {(Array.isArray(a.file_urls) && (a.file_urls as unknown[]).length > 0) && (
            <FileList files={(a.file_urls as string[])} />
          )}
          {shouldShowConfirmationButtons && <ConfirmationButtons />}
        </ChatMessage>
        {microagentStatus && actions && (
          <MicroagentStatusIndicator
            status={microagentStatus}
            conversationId={microagentConversationId}
            prUrl={microagentPRUrl}
          />
        )}
        {isAssistantMessage(event) &&
          event.action === "message" &&
          renderLikertScale()}
      </>
    );
  }

  if (isRejectObservation(event)) {
    return (
      <div>
        <ChatMessage
          type="agent"
          message={typeof event.content === "string" ? event.content : ""}
          onAskAboutCode={onAskAboutCode}
          onRunCode={onRunCode}
          hideAvatar={hideAvatar}
          compactMode={compactMode}
        />
      </div>
    );
  }

  if (isMcpObservation(event)) {
    const eventContent = getEventContent(event);
    // 🛡️ CRITICAL FIX: Hide empty MCP bubbles too
    // Don't render if: observation is null, title is empty, or details are empty/whitespace
    if (
      event.observation === null ||
      event.observation == null ||
      eventContent.title === "" ||
      (typeof eventContent.title === "string" && eventContent.title.trim() === "") ||
      (typeof eventContent.title === "string" && eventContent.title.toUpperCase() === "NULL")
    ) {
      return null;
    }

    return (
      <div>
        <GenericEventMessage
          title={eventContent.title}
          details={<MCPObservationContent event={event} />}
          success={getObservationResult(event)}
        />
        {shouldShowConfirmationButtons && <ConfirmationButtons />}
      </div>
    );
  }

  if (isTaskTrackingObservation(event)) {
    // Update task context but don't render in conversation
    // The task panel will show the tasks, and typing indicator shows status
    return <TaskTrackingObservationContent event={event} />;
  }

  // Handle terminal output with streaming (RUN observations)
  if (
    isOpenHandsObservation(event) &&
    event.observation === "run" &&
    typeof event.content === "string" &&
    event.content
  ) {
    return (
      <div>
        <StreamingTerminal
          eventId={String(event.id)}
          content={String(typeof event.content === "string" ? event.content : "")}
          exitCode={typeof extras.exit_code === "number" ? extras.exit_code : undefined}
          command={typeof extras.command === "string" ? extras.command : undefined}
        />
        {shouldShowConfirmationButtons && <ConfirmationButtons />}
        {renderLikertScale()}
      </div>
    );
  }

  return (
    <div>
      {/* Agent thoughts with streaming */}
      {isOpenHandsAction(event) &&
        hasThoughtProperty(args as Record<string, unknown>) &&
        event.action !== "think" && (
          <StreamingThought
            eventId={String(event.id)}
            thought={String(typeof a.thought === "string" ? a.thought : "")}
          />
        )}

      {(() => {
        const eventContent = getEventContent(event);
        // 🛡️ CRITICAL FIX: Hide empty bubbles that destroy credibility
        // Don't render if: observation is null, or BOTH title AND details are empty/whitespace
        if (
          isOpenHandsObservation(event) &&
          (event.observation === null ||
            event.observation == null ||
            (eventContent.title === "" && eventContent.details === "") ||
            (typeof eventContent.title === "string" && eventContent.title.trim() === "" && 
             typeof eventContent.details === "string" && eventContent.details.trim() === ""))
        ) {
          return null;
        }

        // Also hide if title is just "NULL" or similar artifacts
        if (typeof eventContent.title === "string" && 
            (eventContent.title.toUpperCase() === "NULL" || eventContent.title === "")) {
          return null;
        }

        return (
          <GenericEventMessage
            title={eventContent.title}
            details={eventContent.details}
            success={
              isOpenHandsObservation(event)
                ? getObservationResult(event)
                : undefined
            }
          />
        );
      })()}

      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  );
});
